import json
import time
from PySide6.QtCore import QCoreApplication
from matrix_shell.settings import Settings, DEFAULTS, read_settings, write_settings


def settle(app, settings):
    end = time.monotonic() + 5
    while settings.busy and time.monotonic() < end:
        app.processEvents()
        time.sleep(.002)
    assert not settings.busy


def test_persistence_coalescing_and_reset(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = Settings(directory=tmp_path)
    settle(app, settings)
    assert settings.ready
    settings.setValue('accent', '#b99aff')
    settings.setValue('sound', True)
    settings.setValue('reducedMotion', True)
    settings.setValue('lowEffects', False)
    settle(app, settings)
    again = Settings(directory=tmp_path)
    settle(app, again)
    assert again.values == settings.values
    assert again.values['sound']
    assert again.values['accent'] == '#b99aff'
    again.reset()
    settle(app, again)
    assert read_settings(again.path)[0] == DEFAULTS
    assert not list(tmp_path.glob('.settings-*'))


def test_corruption_falls_back_without_overwrite(tmp_path):
    path = tmp_path / 'settings.json'
    path.write_text('{broken')
    values, warning = read_settings(path)
    assert values == DEFAULTS and warning
    assert path.read_text() == '{broken'
    path.write_text(json.dumps({**DEFAULTS, 'sound': 'false'}))
    assert read_settings(path)[1]


def test_exit_flushes_last_pending_write(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    settings = Settings(directory=tmp_path)
    settle(app, settings)
    settings.setValue('accent', '#b99aff')
    settings.setValue('sound', True)
    settings.worker.shutdown()
    assert read_settings(settings.path)[0]['sound'] is True
