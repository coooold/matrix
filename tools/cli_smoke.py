"""Verify the installed CLI in its own disposable compositor session."""
import json
import os
from pathlib import Path
import subprocess
import sys

result = Path(os.environ['MATRIX_KWIN_RESULT'])
command = [str(Path(sys.executable).with_name('matrix-shell')), '--session', '--notifications',
           '--smoke', '--config-dir', str(Path(os.environ['XDG_CONFIG_HOME']) / 'cli-profile')]
try:
    status = subprocess.run(command, timeout=18).returncode
    report = {'kind': 'Installed CLI, native layer-shell, notification and window service startup',
              'passed': status == 0, 'exit_code': status}
except subprocess.TimeoutExpired:
    report = {'kind': 'Installed CLI startup', 'passed': False, 'error': 'timeout'}
result.write_text(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
