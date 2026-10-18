"""Deterministic preview screenshots with labelled fixtures, not a hardware test."""
import os
from pathlib import Path
import tempfile
import time
from PySide6.QtCore import QUrl, QCoreApplication, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from matrix_shell.backend import DesktopBackend
from matrix_shell.qt_runtime import isolate_plugins

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / 'artifacts/matrix'
output.mkdir(parents=True, exist_ok=True)
plugins = isolate_plugins()
app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix='matrix-capture-') as directory:
    fixture = Path(directory)
    applications = fixture / 'applications'
    applications.mkdir()
    for index, name in enumerate(('测试应用 · 文本编辑', '测试应用 · 计算器', '测试应用 · 图片查看')):
        (applications / f'app-{index}.desktop').write_text(f'[Desktop Entry]\nType=Application\nName={name}\nExec=/bin/true\n')
    (fixture / '设计草案.md').write_text('Matrix capture fixture')
    (fixture / '壁纸').mkdir()
    backend = DesktopBackend(config_dir=fixture / 'profile', application_dirs=[applications])
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({'backend': backend})
    engine.load(QUrl.fromLocalFile(str(ROOT / 'src/matrix_shell/qml/Main.qml')))
    window = engine.rootObjects()[0]
    window.resize(1920, 1080)
    def settle():
        end = time.monotonic() + 5
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(.005)
            if not any((backend.busy, backend.applications.busy, backend.settings.busy)):
                break
        for _ in range(20):
            app.processEvents()
            time.sleep(.01)
    def capture(name):
        settle()
        if not window.grabWindow().save(str(output / name)):
            raise RuntimeError('No frame captured')
    capture('desktop.png')
    window.setProperty('launcherMode', 'apps')
    window.setProperty('launcherOpen', True)
    backend.applications.refresh()
    capture('applications.png')
    window.setProperty('launcherMode', 'files')
    backend.scan(str(fixture))
    capture('files.png')
    window.setProperty('launcherOpen', False)
    window.setProperty('settingsOpen', True)
    capture('settings.png')
    backend.shutdown()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
print('Captured fixture previews in artifacts/matrix; no visual acceptance was granted.')
