import os
from pathlib import Path
import subprocess
import sys


def test_real_dbus_notify_replace_actions_expiry_dnd_and_conflict():
    result = subprocess.run(['dbus-run-session', '--', sys.executable,
                             str(Path(__file__).with_name('notification_scenario.py'))],
                            capture_output=True, text=True, timeout=18)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'passed' in result.stdout
