import os
import shutil
import subprocess
import sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from matrix_shell.host_services import HostServices
from test_backend import wait_until


def test_unavailable_flatpak_reports_error(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(shutil, 'which', lambda name: None)
    service = HostServices()
    service.refreshPackages()
    wait_until(app, lambda: not service.busy)
    assert 'Flatpak' in service.message
    assert service.entries == []
    service.install('bad remote', 'bad app')
    assert '无效' in service.message or 'Flatpak' in service.message


def test_missing_locker_is_not_reported_locked():
    source = '''
import asyncio
from matrix_shell.host_services import lock_session
try:
    asyncio.run(lock_session())
except RuntimeError as error:
    assert '不可用' in str(error)
else:
    raise AssertionError('private bus must not report locked')
'''
    result = subprocess.run(['dbus-run-session', '--', sys.executable, '-c', source], capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stdout + result.stderr
