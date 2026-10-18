"""Install a built wheel outside the checkout and exercise its real entry points."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/wheel-install.json')
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    report = {'wheel': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'kind': 'Isolated wheel install and offscreen startup; not hardware acceptance',
              'passed': False, 'checks': []}
    try:
        with tempfile.TemporaryDirectory(prefix='matrix-wheel-') as temporary:
            directory = Path(temporary)
            target = directory / 'installed'
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps',
                            '--target', str(target), str(wheel)], check=True, cwd=directory)
            env = {**os.environ, 'PYTHONPATH': str(target), 'QT_QPA_PLATFORM': 'offscreen',
                   'QT_QUICK_BACKEND': 'software', 'XDG_CACHE_HOME': str(directory / 'cache'),
                   'XDG_CONFIG_HOME': str(directory / 'config'), 'XDG_DATA_HOME': str(directory / 'data')}
            # A source/editable import would hide missing files in the distribution.
            probe = """import json
from pathlib import Path
import matrix_shell
root = Path(matrix_shell.__file__).parent
assert root.parent.name == 'installed', str(root)
for resource in ('qml/OverlaySurface.qml', 'sounds/click.wav', 'kwin/monitor.js'):
    assert (root / resource).is_file(), resource
print(json.dumps({'module': str(root), 'resources': 'present'}))
"""
            commands = [[sys.executable, '-c', probe],
                        [str(target / 'bin/matrix-shell'), '--smoke'],
                        [str(target / 'bin/matrix-app'), 'calculator', '--smoke']]
            for command in commands:
                result = subprocess.run(command, cwd=directory, env=env, capture_output=True,
                                        text=True, timeout=25)
                report['checks'].append({'command': command, 'exit_code': result.returncode,
                                         'stdout': result.stdout[-4000:], 'stderr': result.stderr[-4000:]})
                if result.returncode:
                    raise RuntimeError(f'Installed entry point failed: {command[0]}')
            report['passed'] = True
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
