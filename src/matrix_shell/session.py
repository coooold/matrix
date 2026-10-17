"""One real layer-shell wallpaper and panel per Qt screen; opt-in only."""
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtGui import QGuiApplication


class DesktopSession(QObject):
    def __init__(self, engine, backend):
        super().__init__(engine)
        self.engine, self.backend = engine, backend
        self.windows = {}
        self.components = []
        for name in ('DesktopSurface.qml', 'PanelSurface.qml'):
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / name)))
            if component.isError():
                raise RuntimeError('\n'.join(error.toString() for error in component.errors()))
            self.components.append(component)
        application = QGuiApplication.instance()
        application.primaryScreenChanged.connect(self._primary_changed)
        application.screenAdded.connect(self.add)
        application.screenRemoved.connect(self.remove)
        for screen in application.screens():
            self.add(screen)

    def add(self, screen):
        if screen in self.windows:
            return
        windows = []
        for component in self.components:
            window = component.createWithInitialProperties({'backend': self.backend})
            if window is None:
                raise RuntimeError('Cannot create layer-shell surface')
            window.setScreen(screen)
            if window.metaObject().indexOfProperty('primaryScreen') >= 0:
                window.setProperty('primaryScreen', screen == QGuiApplication.primaryScreen())
            window.show()
            windows.append(window)
        self.windows[screen] = windows

    def _primary_changed(self, primary):
        for screen, windows in self.windows.items():
            windows[1].setProperty('primaryScreen', screen == primary)

    def remove(self, screen):
        for window in self.windows.pop(screen, []):
            window.close()
            window.deleteLater()

    def shutdown(self):
        for screen in list(self.windows):
            self.remove(screen)
