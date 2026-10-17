"""GUI-facing service facade. All blocking work lives in bounded workers."""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, Property
from .applications import ApplicationCatalog
from .settings import Settings
from .files import FileBrowser
from .system_status import SystemStatus
from .notifications import NotificationCenter
from .kwin_bridge import KWinBridge
from .host_services import HostServices


class DesktopBackend(QObject):
    changed = Signal()
    feedbackRequested = Signal()
    overlayOpened = Signal(QObject)

    def __init__(self, config_dir=None, application_dirs=None):
        super().__init__()
        self._applications = ApplicationCatalog(self, directories=application_dirs)
        self._settings = Settings(self, directory=config_dir)
        self._files = FileBrowser(self)
        self._system = SystemStatus(self)
        self._notifications = NotificationCenter(self)
        self._windows = KWinBridge(self)
        self._services = HostServices(self)
        self._services.worker.completed.connect(lambda result: self._applications.refresh() if isinstance(result, list) else None)
        self._notifications.notificationArrived.connect(self.feedback)
        self._files.changed.connect(self.changed)

    @Property(QObject, constant=True)
    def services(self):
        return self._services

    @Property(QObject, constant=True)
    def windows(self):
        return self._windows

    @Property(QObject, constant=True)
    def system(self):
        return self._system

    @Property(QObject, constant=True)
    def notifications(self):
        return self._notifications

    @Property(QObject, constant=True)
    def applications(self):
        return self._applications

    @Property(QObject, constant=True)
    def settings(self):
        return self._settings

    @Property(QObject, constant=True)
    def fileBrowser(self):
        return self._files

    @Property('QStringList', notify=changed)
    def entries(self):
        return self._files.entries

    @Property(bool, notify=changed)
    def busy(self):
        return self._files.busy

    @Property(bool, notify=changed)
    def filtering(self):
        return self._files.busy

    @Property(str, notify=changed)
    def error(self):
        return self._files.error

    @Slot(str)
    def setQuery(self, query):
        self._files.setQuery(query)

    @Slot(str)
    def scan(self, path):
        self._files.navigate(path)

    @Slot()
    def scanHome(self):
        self.scan(str(Path.home()))

    @Slot(QObject)
    def claimOverlay(self, window):
        self.overlayOpened.emit(window)

    @Slot()
    def feedback(self):
        if self.settings.values['sound']:
            self.feedbackRequested.emit()

    @Slot()
    def shutdown(self):
        self._files.cancel()
        self._files.worker.shutdown()
        self._applications.timer.stop()
        self._applications.worker.shutdown()
        self._applications.launcher.shutdown()
        self._settings.worker.shutdown()
        self._system.timer.stop()
        self._system.worker.shutdown()
        self._notifications.shutdown()
        self._windows.shutdown()
        self._services.cancel()
        self._services.worker.shutdown()
