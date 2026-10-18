"""GUI-facing service facade. All blocking work lives in bounded workers."""
from pathlib import Path
import os
from PySide6.QtCore import QObject, Signal, Slot, Property
from .applications import ApplicationCatalog
from .settings import Settings
from .files import FileBrowser


class DesktopBackend(QObject):
    changed = Signal()
    feedbackRequested = Signal()
    overlayOpened = Signal(QObject)

    def __init__(self, config_dir=None, application_dirs=None, windows_preview=False):
        super().__init__()
        windows_preview = windows_preview or os.name == 'nt'
        if windows_preview:
            from .windows_support import PreviewCatalog, PreviewFiles, UnavailableService
            self._applications = PreviewCatalog(self)
            self._files = PreviewFiles(self)
            self._system = UnavailableService(self, 'Linux 系统指标在 Windows 预览中不可用')
            self._notifications = UnavailableService(self, 'Windows 预览不提供 freedesktop 通知服务')
            self._windows = UnavailableService(self, 'Windows 预览 · KWin 窗口管理仅支持 Linux')
            self._services = UnavailableService(self, 'Windows 预览不提供 Linux 锁屏或 Flatpak')
        else:
            from .system_status import SystemStatus
            from .notifications import NotificationCenter
            from .kwin_bridge import KWinBridge
            from .host_services import HostServices
            self._applications = ApplicationCatalog(self, directories=application_dirs)
            self._files = FileBrowser(self)
            self._system = SystemStatus(self)
            self._notifications = NotificationCenter(self)
            self._windows = KWinBridge(self)
            self._services = HostServices(self)
        self._windows_preview = windows_preview
        self._settings = Settings(self, directory=config_dir)
        self._services.worker.completed.connect(lambda result: self._applications.refresh() if isinstance(result, list) else None)
        self._notifications.notificationArrived.connect(self.feedback)
        self._files.changed.connect(self.changed)

    @Property(bool, constant=True)
    def windowsPreview(self):
        return self._windows_preview

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
