"""Exercise the installed Windows executables; preserve failing diagnostics."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, default=Path('artifacts/windows-smoke.json'))
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    report = {'executable': str(executable), 'passed': False, 'checks': []}
    try:
        with tempfile.TemporaryDirectory(prefix='matrix-installed-') as temporary:
            directory = Path(temporary)
            env = {**os.environ, 'QT_QUICK_BACKEND': 'software',
                   'QT_MEDIA_BACKEND': 'windows', 'LOCALAPPDATA': str(directory / 'local'),
                   'APPDATA': str(directory / 'roaming')}
            model_report = directory / 'installed-models.json'
            diagnostic = directory / 'local/MatrixPreview/runtime.log'
            result = subprocess.run([str(executable), '--self-test', '--report', str(model_report)], cwd=directory, env=env, timeout=40)
            report['runtime_log'] = diagnostic.read_text(encoding='utf-8') if diagnostic.exists() else ''
            models = json.loads(model_report.read_text(encoding='utf-8')) if model_report.exists() else {}
            report['installed_models'] = models
            if result.returncode or not models.get('passed'):
                raise RuntimeError('Installed model/persistence checks failed')
            for kind in (None, 'calculator', 'notes', 'image', 'music'):
                result_path = directory / f'{kind or "shell"}.json'
                env['MATRIX_SMOKE_REPORT'] = str(result_path)
                command = [str(executable), *(['--app', kind] if kind else []), '--smoke']
                if not kind:
                    command += ['--config-dir', str(directory / 'profile')]
                result = subprocess.run(command, cwd=directory, env=env, timeout=40)
                report['runtime_log'] = diagnostic.read_text(encoding='utf-8') if diagnostic.exists() else ''
                evidence = json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {}
                report['checks'].append({'app': kind or 'shell', 'exit_code': result.returncode, 'evidence': evidence})
                if result.returncode != 0 or not evidence.get('passed') or not evidence.get('frames', 0):
                    raise RuntimeError(f'Installed {kind or "shell"} failed to submit frames: {evidence}')
            diagnostic = directory / 'local/MatrixPreview/runtime.log'
            report['runtime_log'] = diagnostic.read_text(encoding='utf-8') if diagnostic.exists() else ''
            if any(error in report['runtime_log'] for error in ('TypeError:', 'ReferenceError:', 'failed to load component', 'Traceback')):
                raise RuntimeError('Runtime contains QML/Python errors')
            report['passed'] = True
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
