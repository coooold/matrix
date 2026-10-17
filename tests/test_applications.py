import os
from pathlib import Path
import time
import pytest
from PySide6.QtCore import QCoreApplication
from matrix_shell.applications import ApplicationCatalog, discover


def desktop(path, name='Test', extra='', command='/bin/true'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec={command}\n{extra}')


def settle(app, predicate):
    end = time.monotonic() + 8
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        time.sleep(.002)
    assert predicate()


def test_xdg_precedence_visibility_locale_categories(tmp_path):
    user, system = tmp_path / 'user', tmp_path / 'system'
    desktop(system / 'mask.desktop')
    desktop(user / 'mask.desktop', extra='Hidden=true\n')
    desktop(system / 'shown.desktop', extra='Name[zh_CN]=中文应用\nOnlyShowIn=KDE;\nCategories=Office;\n')
    desktop(system / 'other.desktop', extra='NotShowIn=KDE;\n')
    desktop(system / 'nodisplay.desktop', extra='NoDisplay=true\n')
    desktop(system / 'absent.desktop', extra='TryExec=/missing-binary\n')
    desktop(system / 'sub' / 'app.desktop', name='Nested')
    (system / 'invalid.desktop').write_text('not an entry')
    apps = discover([user, system], 'Matrix:KDE', 'zh_CN.UTF-8')
    assert {a['name'] for a in apps} == {'中文应用', 'Nested'}
    assert {a['id'] for a in apps} == {'shown.desktop', 'sub-app.desktop'}
    assert next(a for a in apps if a['id'] == 'shown.desktop')['categories'] == 'Office;'


def test_launch_real_processes_and_report_failure(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    catalog = ApplicationCatalog(directories=[tmp_path])
    # Use real GIO desktop Exec handling, including spaces and field-code expansion.
    for i in (1, 2):
        script = tmp_path / f'app {i}.sh'
        script.write_text(f'#!/bin/sh\nprintf launched > "{tmp_path / str(i)}"\n')
        script.chmod(0o700)
        desktop(tmp_path / f'app{i}.desktop', name=f'App {i}', command=f'"{script}" %f')
    desktop(tmp_path / 'broken.desktop', command='/not-an-executable')
    catalog.refresh()
    settle(app, lambda: not catalog.busy)
    for i in (1, 2):
        catalog.launch(f'app{i}.desktop')
        settle(app, lambda: not catalog.launching)
        settle(app, lambda: (tmp_path / str(i)).exists())
        assert (tmp_path / str(i)).read_text() == 'launched'
        assert not catalog.error
    catalog.launch('broken.desktop')
    settle(app, lambda: not catalog.launching)
    assert catalog.error
    catalog.launch('missing.desktop')
    assert catalog.error


def test_refresh_and_category_filter(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    catalog = ApplicationCatalog(directories=[tmp_path])
    desktop(tmp_path / 'office.desktop', name='Editor', extra='Categories=Office;\n')
    desktop(tmp_path / 'game.desktop', name='Pong', extra='Categories=Game;\n')
    catalog.setQuery('OFFICE')
    settle(app, lambda: not catalog.busy)
    assert [entry['name'] for entry in catalog.entries] == ['Editor']
    (tmp_path / 'office.desktop').unlink()
    catalog.refresh()
    settle(app, lambda: not catalog.busy)
    assert catalog.entries == []


def test_launcher_does_not_wait_for_app_lifetime(tmp_path):
    from matrix_shell.system_status import process_identity, terminate_process
    app = QCoreApplication.instance() or QCoreApplication([])
    marker = tmp_path / 'pid'
    script = tmp_path / 'long-running.sh'
    script.write_text(f'#!/bin/sh\necho $$ > "{marker}"\nexec /bin/sleep 10\n')
    script.chmod(0o700)
    desktop(tmp_path / 'long.desktop', command=f'"{script}"')
    catalog = ApplicationCatalog(directories=[tmp_path])
    catalog.refresh()
    settle(app, lambda: not catalog.busy)
    started = time.monotonic()
    catalog.launch('long.desktop')
    identity = None
    try:
        settle(app, lambda: marker.exists())
        identity = process_identity(int(marker.read_text()))
        settle(app, lambda: not catalog.launching)
        assert time.monotonic() - started < 3
        assert not catalog.error
    finally:
        if identity:
            terminate_process(identity['pid'], identity['start'])


def test_xdg_paths_and_flatpak_exports(tmp_path, monkeypatch):
    from matrix_shell.applications import application_directories
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    monkeypatch.setenv('XDG_DATA_DIRS', '')
    paths = application_directories()
    assert tmp_path / 'applications' in paths
    assert tmp_path / 'flatpak/exports/share/applications' in paths
    assert Path('/usr/share/applications') in paths
    monkeypatch.setenv('XDG_DATA_HOME', 'invalid-relative-path')
    assert all(path.is_absolute() for path in application_directories())
