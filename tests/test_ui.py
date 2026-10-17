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
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl, Slot
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
backend = FixtureBackend()
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
def type_text(text):
    for character in text:
        QTest.keyClick(window, Qt.Key(ord(character.upper())))
def settled():
    deadline = time.monotonic() + 5
    while (backend.busy or backend.filtering) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert not backend.busy and not backend.filtering
'''
    result = subprocess.run([sys.executable, '-c', bootstrap + script],
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                                 'QT_QUICK_BACKEND': 'software', 'MATRIX_TEST_DIRECTORY': str(tmp_path)},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    for warning in ['ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign']:
        assert warning not in result.stderr, result.stderr


def test_menu_scan_and_escape(tmp_path):
    run_ui(r'''
point = start.mapToScene(QPointF(start.width() / 2, start.height() / 2)).toPoint()
QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
settled()
assert window.property('launcherOpen')
assert backend.entries == ['Alpha.txt', 'ALPINE.md', 'beta.txt']
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
QTest.keyClick(window, Qt.Key_Space, Qt.ControlModifier)
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
assert files.property('count') == 3
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
