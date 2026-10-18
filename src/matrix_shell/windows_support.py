"""Real bundled clients and files; Linux services are explicitly unavailable."""
import os
import subprocess
import sys
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from .applications import ApplicationCatalog
from .files import FileBrowser
from .async_job import LatestWorker
from .qt_runtime import client_environment

CLIENTS = {'calculator': '计算器', 'notes': '笔记', 'image': '图片', 'music': '音频'}


def client_command(kind):
    if kind not in CLIENTS:
        raise ValueError('未知基础应用')
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--app', kind]
    return [sys.executable, '-m', 'matrix_shell.windows_entry', '--app', kind]


class PreviewCatalog(ApplicationCatalog):
    def __init__(self, parent=None):
        super().__init__(parent, directories=[])

    @Slot()
    def refresh(self):
        query = self._query
        self.worker.submit(lambda: [{'id': key, 'name': name, 'categories': 'Matrix 基础应用',
                                     'path': sys.executable, 'terminal': False}
                                    for key, name in CLIENTS.items()
                                    if query in (name + ' ' + key + ' Matrix 基础应用').casefold()])

    @Slot(str)
    def launch(self, ident):
        if self.launcher.busy:
            return
        if not any(entry['id'] == ident for entry in self._entries):
            self._launch_error = '应用不在当前列表中，请刷新'
            self.changed.emit()
            return
        self._launch_error = ''
        def execute():
            subprocess.Popen(client_command(ident), env=client_environment(),
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
            return ident
        self.launcher.submit(execute)


class PreviewFiles(FileBrowser):
    def _open_file(self, path):
        if os.name != 'nt':
            raise RuntimeError('Windows 文件关联仅在 Windows 可用')
        os.startfile(str(path.absolute()))

    @Slot(str)
    def trash(self, name):
        self._operation_error = 'Windows 预览尚未接入回收站；文件未删除，请使用资源管理器'
        self.changed.emit()


class UnavailableService(QObject):
    changed = Signal()
    notificationArrived = Signal()

    def __init__(self, parent, reason):
        super().__init__(parent)
        self.reason = reason
        self.worker = LatestWorker(self)
        self.timer = QTimer(self)

    @Property(str, constant=True)
    def error(self): return self.reason

    @Property(str, constant=True)
    def message(self): return self.reason

    @Property(bool, constant=True)
    def online(self): return False

    @Property(bool, constant=True)
    def busy(self): return False

    @Property(bool, constant=True)
    def doNotDisturb(self): return False

    @Property('QVariantList', constant=True)
    def entries(self): return []

    @Property('QVariantMap', constant=True)
    def values(self): return {}

    @Property('QVariantMap', constant=True)
    def latest(self): return {}

    @Slot()
    def start(self): pass

    @Slot()
    def clear(self): pass

    @Slot(bool)
    def setDoNotDisturb(self, value): pass

    @Slot(int, str)
    def invokeAction(self, ident, key): pass

    @Slot(str, str)
    def action(self, ident, operation): pass

    @Slot()
    def acquire(self): pass

    @Slot()
    def release(self): pass

    @Slot()
    def refreshPackages(self): pass

    @Slot(str, str)
    def install(self, remote, ident): pass

    @Slot(str)
    def uninstall(self, ident): pass

    @Slot()
    def lock(self): pass

    @Slot()
    def cancel(self): pass

    @Slot(int)
    def terminate(self, pid): pass

    def shutdown(self):
        self.worker.shutdown()
