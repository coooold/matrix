"""Upload one explicitly requested CI artifact using GitHub's runner token."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def gh(*arguments):
    return subprocess.check_output(['gh', *map(str, arguments)], text=True).strip()


def main():
    request = json.loads(Path('packaging/windows/upload-request.json').read_text())
    source = request['source_commit']
    assert re.fullmatch('[0-9a-f]{40}', source)
    assert re.fullmatch('[0-9a-f]{64}', request['sha256'])
    assert request['tag'] == f'windows-preview-v0.1.0-{source[:7]}'
    assert Path(request['installer']).name == request['installer']
    run = json.loads(gh('run', 'view', request['run_id'], '--json', 'conclusion,headSha,workflowName,url'))
    assert run['conclusion'] == 'success' and run['headSha'] == source
    assert run['workflowName'] == 'windows-installer'
    with tempfile.TemporaryDirectory(prefix='verified-windows-') as temporary:
        root = Path(temporary)
        gh('run', 'download', request['run_id'], '--dir', root)
        installers = list(root.rglob(request['installer']))
        assert len(installers) == 1
        installer = installers[0]
        assert hashlib.sha256(installer.read_bytes()).hexdigest() == request['sha256']
        checksum = installer.with_name(installer.name + '.sha256')
        assert checksum.read_text().split()[0] == request['sha256']
        reports = list(root.rglob('windows-smoke.json'))
        assert len(reports) == 1
        report = json.loads(reports[0].read_text(encoding='utf-8'))
        assert report['passed'] and report['installed_models']['passed']
        assert len(report['checks']) == 5
        assert all(check['exit_code'] == 0 and check['evidence']['passed']
                   and check['evidence']['frames'] > 0 for check in report['checks'])
        notes = root / 'release-notes.md'
        notes.write_text(f'''Windows 10/11 x64 的 Matrix 桌面预览安装包，约 41 MB，无需另装 Python。双击 `*-setup.exe` 按当前用户安装。\n
包含 Qt Quick 界面、应用菜单、文件浏览/创建/复制、个性化设置，以及计算器、笔记、图片和音频客户端。\n
此包为窗口化预览，不安装 Linux 或替换 Explorer。KWin 窗口管理、Linux 系统指标、freedesktop 通知、Linux 锁屏及 Flatpak 不可用；回收站操作请使用 Windows 资源管理器。安装器未进行代码签名。\n
已在 GitHub Windows Server 2022 x64 云端 runner 实际安装，验证安装目录内的壳和四种客户端出帧、中文笔记/设置重启持久化及卸载；尚无实体 Windows 10/11 人工体验验收。个人设置及笔记在卸载后保留。\n
来源提交：`{source}`。\n
[构建及安装后验证]({run['url']})，原始验证 JSON 随附件提供。\n
SHA256：`{request['sha256']}`，另附 `.sha256` 文件。\n
这不是 Linux 原生桌面完整发布验收结果。\n''', encoding='utf-8')
        # Idempotent reruns accept only an existing release of this exact build.
        existing = subprocess.run(['gh', 'release', 'view', request['tag'], '--json', 'targetCommitish,isPrerelease,assets'], capture_output=True, text=True)
        if existing.returncode == 0:
            release = json.loads(existing.stdout)
            assert release['targetCommitish'] == source and release['isPrerelease']
            gh('release', 'upload', request['tag'], installer, checksum, reports[0], '--clobber')
        else:
            print(gh('release', 'create', request['tag'], installer, checksum, reports[0],
                     '--target', source, '--prerelease', '--title', 'Matrix Windows Preview 0.1.0 (x64)',
                     '--notes-file', notes))


if __name__ == '__main__':
    main()
