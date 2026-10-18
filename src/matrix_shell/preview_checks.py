"""Check bundled Windows models with real persistence, without Linux services."""
import json
import os
from pathlib import Path
import tempfile
import time
from PySide6.QtGui import QGuiApplication
from matrix_shell.backend import DesktopBackend
from matrix_shell.core_apps import CoreModel, calculate


def run(output):
    application = QGuiApplication([])
    def until(predicate):
        deadline = time.monotonic() + 10
        while not predicate() and time.monotonic() < deadline:
            application.processEvents()
            time.sleep(.005)
        assert predicate(), 'Timed out waiting for real asynchronous model'
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        backend = DesktopBackend(config_dir=directory / 'profile', windows_preview=True)
        try:
            until(lambda: backend.settings.ready)
            backend.applications.refresh()
            until(lambda: not backend.applications.busy)
            assert {entry['id'] for entry in backend.applications.entries} == {'calculator', 'notes', 'image', 'music'}
            backend.applications.setQuery('notes')
            until(lambda: not backend.applications.busy)
            assert [entry['id'] for entry in backend.applications.entries] == ['notes']
            assert not backend.windows.online and not backend.notifications.online
            assert 'Windows' in backend.services.message
            assert calculate('0.1+0.2') == '0.3'
            backend.settings.setValue('accent', '#b99aff')
        finally:
            backend.shutdown()
        restarted = DesktopBackend(config_dir=directory / 'profile', windows_preview=True)
        until(lambda: restarted.settings.ready)
        assert restarted.settings.values['accent'] == '#b99aff'
        note = directory / '中文笔记.txt'
        model = CoreModel('notes', note)
        until(lambda: model.ready)
        model.setText('中文重启不丢失 🌌')
        model.shutdown()
        assert note.read_text(encoding='utf-8') == '中文重启不丢失 🌌'
        restored = CoreModel('notes', note)
        until(lambda: restored.ready)
        assert restored.text == '中文重启不丢失 🌌'
        restored.shutdown()
        source = directory / 'preserve.txt'
        source.write_text('keep', encoding='utf-8')
        restarted.fileBrowser.navigate(str(directory))
        until(lambda: not restarted.fileBrowser.busy)
        restarted.fileBrowser.trash('preserve.txt')
        assert source.read_text() == 'keep'
        assert '未删除' in restarted.fileBrowser.error
        restarted.shutdown()
    output = Path(output)
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps({'passed': True, 'unicode_restart': True, 'settings_restart': True,
                                 'real_bundled_catalog': True, 'linux_services_disabled': True}), encoding='utf-8')
    print(output.read_text())
