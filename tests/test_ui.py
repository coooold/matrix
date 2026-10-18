"""GUI tests run separately from the QCoreApplication worker tests."""
import os
import subprocess
import sys


def run_ui(script, tmp_path):
    for name in ['Alpha.txt', 'beta.txt', 'ALPINE.md']:
        (tmp_path / name).touch()
    bootstrap = r'''
from pathlib import Path
import time
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl, Slot, QCoreApplication, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem
from matrix_shell import app as module
from matrix_shell.backend import DesktopBackend
app = QGuiApplication([])
class FixtureBackend(DesktopBackend):
    @Slot()
    def scanHome(self):
        self.scan(os.environ['MATRIX_TEST_DIRECTORY'])
import os
backend = FixtureBackend(config_dir=Path(os.environ['MATRIX_TEST_DIRECTORY']) / 'profile',
                         application_dirs=[Path(os.environ['MATRIX_TEST_DIRECTORY']) / 'apps'])
engine = QQmlApplicationEngine()
engine.setInitialProperties({'backend': backend})
engine.load(QUrl.fromLocalFile(str(Path(module.__file__).parent / 'qml/Main.qml')))
assert engine.rootObjects()
window = engine.rootObjects()[0]
window.requestActivate()
QTest.qWait(100)
search = window.findChild(QQuickItem, 'fileSearch')
files = window.findChild(QQuickItem, 'fileList')
start = window.findChild(QQuickItem, 'startButton')
file_button = window.findChild(QQuickItem, 'fileButton')
def visual_item(name, item=None):
    item = item or window.contentItem()
    if item.objectName() == name:
        return item
    for child in item.childItems():
        found = visual_item(name, child)
        if found:
            return found
    return None
def open_files():
    point = file_button.mapToScene(QPointF(file_button.width() / 2, file_button.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
def type_text(text):
    for character in text:
        QTest.keyClick(window, Qt.Key(ord(character.upper())))
def settled():
    deadline = time.monotonic() + 5
    while (backend.busy or backend.filtering or backend.applications.busy or backend.applications.launching or backend.settings.busy) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert not backend.busy and not backend.filtering
'''
    result = subprocess.run([sys.executable, '-c', bootstrap + script + '\nbackend.shutdown()\nwindow.close()\nwindow.deleteLater()\nQCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)\n'],
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                 'QT_QUICK_BACKEND': 'software', 'MATRIX_TEST_DIRECTORY': str(tmp_path)},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    for warning in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']:
        assert warning not in result.stderr, result.stderr


def test_menu_scan_and_escape(tmp_path):
    run_ui(r'''
open_files()
settled()
assert window.property('launcherOpen')
assert all(name in backend.entries for name in ['Alpha.txt', 'ALPINE.md', 'beta.txt'])
assert search.hasActiveFocus()
QTest.keyClick(window, Qt.Key_Escape)
QTest.qWait(50)
assert not window.property('launcherOpen')
assert start.hasActiveFocus()
# The restored button supports keyboard activation.
QTest.keyClick(window, Qt.Key_Space)
settled()
assert window.property('launcherOpen')
''', tmp_path)


def test_search_keyboard_selection_and_empty_state(tmp_path):
    run_ui(r'''
open_files()
settled()
assert search.hasActiveFocus()
type_text('alp')
settled()
assert backend.entries == ['Alpha.txt', 'ALPINE.md']
QTest.keyClick(window, Qt.Key_Down)
assert files.hasActiveFocus()
assert files.property('currentIndex') == 0
QTest.keyClick(window, Qt.Key_Down)
assert files.property('currentIndex') == 1
QTest.keyClick(window, Qt.Key_Up)
QTest.keyClick(window, Qt.Key_Up)
assert search.hasActiveFocus()
QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
type_text('no-match')
settled()
assert files.property('count') == 0
QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
QTest.keyClick(window, Qt.Key_Backspace)
settled()
assert files.property('count') >= 3
QTest.keyClick(window, Qt.Key_Escape)
assert start.hasActiveFocus()
QTest.keyClick(window, Qt.Key_Tab)
assert window.activeFocusItem().property('text') == '文件'
''', tmp_path)


def test_compact_window_and_outside_dismiss(tmp_path):
    run_ui(r'''
window.resize(360, 480)
QTest.qWait(50)
QTest.keyClick(window, Qt.Key_Space, Qt.ControlModifier)
settled()
launcher = window.findChild(QQuickItem, 'launcher')
assert launcher.x() >= 0 and launcher.y() >= 0
assert launcher.x() + launcher.width() <= window.width()
assert launcher.y() + launcher.height() <= window.height()
QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(2, 2))
assert not window.property('launcherOpen')
''', tmp_path)


def test_real_application_launcher_keyboard_and_failure(tmp_path):
    apps = tmp_path / 'apps'
    apps.mkdir()
    marker = tmp_path / 'launched'
    executable = tmp_path / 'editor.sh'
    executable.write_text(f'#!/bin/sh\nprintf success > "{marker}"\n')
    executable.chmod(0o700)
    (apps / 'editor.desktop').write_text(f'[Desktop Entry]\nType=Application\nName=Editor\nCategories=Office;\nExec={executable}\n')
    (apps / 'broken.desktop').write_text('[Desktop Entry]\nType=Application\nName=Broken\nExec=/missing-app\n')
    run_ui(r'''
QTest.keyClick(window, Qt.Key_Space, Qt.ControlModifier)
settled()
assert window.property('launcherMode') == 'apps'
type_text('Office')
settled()
assert files.property('count') == 1
QTest.keyClick(window, Qt.Key_Return)
settled()
end = time.monotonic() + 5
while not (Path(os.environ['MATRIX_TEST_DIRECTORY']) / 'launched').exists() and time.monotonic() < end:
    app.processEvents()
    time.sleep(.001)
assert (Path(os.environ['MATRIX_TEST_DIRECTORY']) / 'launched').read_text() == 'success'
assert not window.property('launcherOpen')
QTest.keyClick(window, Qt.Key_Space, Qt.ControlModifier)
settled()
type_text('broken')
settled()
QTest.keyClick(window, Qt.Key_Return)
settled()
assert backend.applications.error
assert window.property('launcherOpen')
''', tmp_path)


def test_settings_panel_persists_and_mute_is_respected(tmp_path):
    run_ui(r'''
settled()
window.setProperty('settingsOpen', True)
QTest.qWait(50)
checkbox = visual_item('setting-sound')
point = checkbox.mapToScene(QPointF(checkbox.width() / 2, checkbox.height() / 2)).toPoint()
QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
settled()
assert backend.settings.values['sound']
feedback = []
backend.feedbackRequested.connect(lambda: feedback.append(True))
backend.feedback()
assert feedback == [True]
backend.settings.setValue('sound', False)
settled()
backend.feedback()
assert feedback == [True]
assert backend.settings.path.exists()
QTest.keyClick(window, Qt.Key_Escape)
assert not window.property('settingsOpen')
''', tmp_path)
