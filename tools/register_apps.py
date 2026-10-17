"""Register Matrix clients in an explicitly selected XDG data directory."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def quote_exec(value):
    return '"' + str(value).replace('%', '%%').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'


def register(data, executable, konsole=None):
    directory = data / 'applications'
    names = {'calculator': 'Matrix 计算器', 'notes': 'Matrix 笔记', 'image': 'Matrix 图片', 'music': 'Matrix 音频'}
    entries = {}
    for kind, name in names.items():
        argument = '' if kind == 'calculator' else ' %f'
        mime = {'notes': 'text/plain;text/markdown;', 'image': 'image/png;image/jpeg;image/webp;image/svg+xml;', 'music': 'audio/wav;audio/x-wav;audio/mpeg;audio/flac;'}.get(kind, '')
        entries[f'org.matrixdesktop.{kind}.desktop'] = f'[Desktop Entry]\nType=Application\nName={name}\nExec={quote_exec(executable)} {kind}{argument}\nMimeType={mime}\nIcon=applications-utilities\nCategories=Utility;\nX-Matrix-Managed=true\n'
    if konsole:
        wrapper = data / 'matrix-konsole.py'
        prefix = konsole.parents[2]
        script = f'''# Matrix managed launcher
import os, sys
environment = dict(os.environ)
environment['QT_PLUGIN_PATH'] = {str(prefix / 'usr/lib/x86_64-linux-gnu/qt6/plugins')!r} + ':/usr/lib/x86_64-linux-gnu/qt6/plugins'
environment['LD_LIBRARY_PATH'] = {str(prefix / 'usr/lib/x86_64-linux-gnu')!r} + ':' + {str(prefix.parent / 'native-qt')!r}
for key in ('QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_WAYLAND_SHELL_INTEGRATION', 'QML_IMPORT_PATH'):
    environment.pop(key, None)
os.execve({str(konsole)!r}, [{str(konsole)!r}, '--separate', *sys.argv[1:]], environment)
'''
        if wrapper.exists() and not wrapper.read_text().startswith('# Matrix managed launcher\n'):
            raise ValueError('Refusing to overwrite unmanaged terminal wrapper')
        entries['org.matrixdesktop.terminal.desktop'] = f'[Desktop Entry]\nType=Application\nName=Matrix 终端 (Konsole)\nExec={quote_exec(sys.executable)} {quote_exec(wrapper)}\nIcon=utilities-terminal\nCategories=System;TerminalEmulator;\nX-Matrix-Managed=true\n'
    for name in entries:
        target = directory / name
        if target.exists() and 'X-Matrix-Managed=true\n' not in target.read_text():
            raise ValueError(f'Refusing to overwrite unmanaged {target}')
    directory.mkdir(parents=True, exist_ok=True)
    if konsole:
        wrapper.write_text(script)
        wrapper.chmod(0o700)
    for name, content in entries.items():
        (directory / name).write_text(content)
    return list(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--konsole', type=Path)
    args = parser.parse_args()
    executable = ROOT / '.venv/bin/matrix-app'
    if not executable.exists():
        parser.error('run tools/setup.sh first')
    if args.konsole and not args.konsole.is_file():
        parser.error('Konsole executable does not exist')
    print('\n'.join(register(args.data_dir.resolve(), executable, args.konsole.resolve() if args.konsole else None)))


if __name__ == '__main__':
    main()
