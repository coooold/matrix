"""Start only a disposable KWin session and verify current-run result files."""
import argparse
import json
import os
import signal
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import PySide6

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=ROOT / '.cache/kwin/root')
    parser.add_argument('--session', action='store_true', help='Also verify native layer-shell desktop and panel roles')
    parser.add_argument('--outputs', type=int, choices=[1, 2], default=1)
    parser.add_argument('--scale', type=float, choices=[1, 1.25, 1.5, 2], default=1)
    parser.add_argument('--second-scale', type=float, choices=[1, 1.25, 1.5, 2])
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/kwin')
    parser.add_argument('--cli-smoke', action='store_true')
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    binary = prefix / 'usr/bin/kwin_wayland'
    if not binary.exists():
        parser.error('KWin unavailable; run tools/prepare_kwin.sh on Debian 13 first')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (ROOT / '.cache').mkdir(exist_ok=True)
    result = output / 'result.json'
    result.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='matrix-kwin-session-', dir=ROOT / '.cache') as name:
        directory = Path(name)
        runtime = directory / 'runtime'
        runtime.mkdir(mode=0o700)
        session = directory / 'client.sh'
        scenario = ROOT / 'tools' / ('cli_smoke.py' if args.cli_smoke else 'kwin_scenario.py')
        session.write_text('#!/bin/sh\nexec ' + shlex.join([sys.executable, str(scenario)]) + '\n')
        session.chmod(0o700)
        env = {**os.environ, 'XDG_RUNTIME_DIR': str(runtime), 'XDG_CONFIG_HOME': str(directory / 'config'),
               'XDG_CACHE_HOME': str(directory / 'cache'), 'XDG_DATA_HOME': str(directory / 'data'),
               'XDG_DATA_DIRS': f'{prefix}/usr/share:/usr/local/share:/usr/share',
               'LD_LIBRARY_PATH': f'{prefix}/usr/lib/x86_64-linux-gnu:{prefix.parent}/native-qt',
               'QT_PLUGIN_PATH': f'{prefix}/usr/lib/x86_64-linux-gnu/qt6/plugins:/usr/lib/x86_64-linux-gnu/qt6/plugins',
               'QT_QPA_PLATFORM': 'offscreen', 'KWIN_COMPOSE': 'Q', 'QT_QUICK_BACKEND': 'software',
               'MATRIX_LAUNCH_LOG_DIR': str(output / 'launch-logs'), 'MATRIX_KWIN_RESULT': str(result), 'MATRIX_LAYER_SESSION': '1' if args.session else '0',
               'MATRIX_KWIN_PREFIX': str(prefix), 'MATRIX_KWIN_OUTPUTS': str(args.outputs), 'MATRIX_KWIN_SCALE': str(args.scale),
               'MATRIX_KWIN_SECOND_SCALE': str(args.second_scale or args.scale),
               'QML_IMPORT_PATH': f'{prefix}/usr/lib/x86_64-linux-gnu/qt6/qml'}
        # Clients use Wayland; KWin's virtual backend uses an offscreen Qt platform.
        qt_libraries = Path(PySide6.__file__).parent / 'Qt/lib'
        source = session.read_text().replace('exec ', 'QT_QPA_PLATFORM=wayland LD_LIBRARY_PATH=' + shlex.quote(f'{qt_libraries}:{prefix}/usr/lib/x86_64-linux-gnu') + ' exec ')
        session.write_text(source)
        command = ['dbus-run-session', '--', str(binary), '--virtual', '--width', '1280', '--height', '800', '--output-count', str(args.outputs), '--scale', str(args.scale),
                   '--no-lockscreen', '--no-global-shortcuts', '--no-kactivities', '--exit-with-session', str(session)]
        with (output / 'session.log').open('w') as log:
            try:
                process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                process.wait(timeout=50)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
                parser.exit(1, 'KWin scenario timed out; inspect artifacts/kwin/session.log\n')
        if process.returncode or not result.exists() or not json.loads(result.read_text()).get('passed'):
            print((output / 'session.log').read_text()[-12000:], file=sys.stderr)
            parser.exit(1, f"KWin scenario failed; inspect {output / 'session.log'}\n")
    print(result.read_text())


if __name__ == '__main__':
    main()
