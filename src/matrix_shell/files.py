"""Real filesystem operations, paged listing and cooperative copy cancellation."""
import os
from pathlib import Path
import subprocess
import threading
from datetime import datetime
from urllib.parse import quote
import uuid
from PySide6.QtCore import QObject, Signal, Slot, Property
from .async_job import LatestWorker
from .qt_runtime import client_environment
from .applications import launch_gio

PAGE_SIZE = 200


def child_path(directory, name):
    if not name or name in ('.', '..') or '/' in name or '\x00' in name:
        raise ValueError('名称不能包含路径分隔符或为空')
    return directory / name


def page(directory, offset=0):
    rows = []
    with os.scandir(directory) as iterator:
        for index, entry in enumerate(iterator):
            if index < offset:
                continue
            if len(rows) == PAGE_SIZE:
                return rows, True
            rows.append({'name': entry.name, 'directory': entry.is_dir(follow_symlinks=True)})
    return rows, False


def copy_file(source, destination, cancel):
    created = False
    try:
        with source.open('rb') as reader, destination.open('xb') as writer:
            created = True
            while True:
                if cancel.is_set():
                    raise InterruptedError('复制已取消')
                block = reader.read(1024 * 1024)
                if not block:
                    break
                writer.write(block)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def local_trash(source):
    """Home trash fallback for container mounts rejected by GIO. Never unlink data."""
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME 必须为绝对路径')
    trash = data / 'Trash'
    for directory in (trash, trash / 'files', trash / 'info'):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = directory.lstat()
        if directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PermissionError('回收站目录必须由当前用户独占')
    if source.lstat().st_dev != (trash / 'files').stat().st_dev:
        raise OSError('跨文件系统回收站不可用；未删除源文件')
    name = f'{source.name}.{uuid.uuid4().hex}'
    info_path = trash / 'info' / f'{name}.trashinfo'
    destination = trash / 'files' / name
    try:
        with info_path.open('x') as stream:
            stream.write('[Trash Info]\nPath=' + quote(str(source.absolute()), safe='/') +
                         '\nDeletionDate=' + datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        source.rename(destination)
    except BaseException:
        info_path.unlink(missing_ok=True)
        raise
    return destination


class FileBrowser(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._complete)
        self._path = str(Path.home())
        self._target_path = self._path
        self._rows = []
        self._visible = []
        self._more = False
        self._query = ''
        self._cancel = threading.Event()
        self._operation_error = ''

    @Property(str, notify=changed)
    def path(self):
        return self._path

    @Property('QStringList', notify=changed)
    def entries(self):
        return self._visible

    @Property(bool, notify=changed)
    def more(self):
        return self._more

    @Property(bool, notify=changed)
    def busy(self):
        return self.worker.busy

    @Property(str, notify=changed)
    def error(self):
        return self._operation_error or self.worker.error

    def _request(self, directory, offset=0, mutation=None):
        self._operation_error = ''
        query = self._query
        prior = self._rows[:] if offset else []

        def work():
            resolved = directory.resolve(strict=True)
            if mutation:
                mutation(resolved)
            rows, more = page(resolved, offset)
            combined = prior + rows
            names = sorted((row['name'] for row in combined if query in row['name'].casefold()), key=str.casefold)
            return str(resolved), combined, names, more

        self.worker.submit(work)

    @Slot(str)
    def navigate(self, path):
        self._target_path = path
        self._request(Path(path))

    @Slot()
    def parentDirectory(self):
        self.navigate(str(Path(self._path).parent))

    @Slot()
    def refresh(self):
        self.navigate(self._path)

    @Slot()
    def loadMore(self):
        if self._more and not self.busy:
            self._request(Path(self._path), len(self._rows))

    @Slot(str)
    def setQuery(self, query):
        self._query = query[:256].casefold()
        if self.busy:
            self._request(Path(self._target_path))
            return
        # Filter in the bounded worker, preserve already loaded pages.
        rows, path, more, query = self._rows[:], self._path, self._more, self._query
        self.worker.submit(lambda: (path, rows,
            sorted((row['name'] for row in rows if query in row['name'].casefold()), key=str.casefold), more))

    @Slot(object)
    def _complete(self, result):
        self._path, self._rows, self._visible, self._more = result
        self._target_path = self._path
        self.changed.emit()

    def _mutate(self, operation):
        if self.busy:
            self._operation_error = '请等待当前操作完成'
            self.changed.emit()
            return
        self._cancel = threading.Event()
        self._request(Path(self._path), mutation=operation)

    @Slot(str)
    def createFile(self, name):
        def create(directory):
            with child_path(directory, name).open('xb'):
                pass
        self._mutate(create)

    @Slot(str)
    def createFolder(self, name):
        self._mutate(lambda directory: child_path(directory, name).mkdir())

    @Slot(str, str)
    def copy(self, source, destination):
        self._mutate(lambda directory: copy_file(child_path(directory, source),
                     child_path(directory, destination), self._cancel))

    @Slot()
    def cancel(self):
        self._cancel.set()

    @Slot(str)
    def trash(self, name):
        def move(directory):
            result = subprocess.run(['gio', 'trash', '--', str(child_path(directory, name))],
                                    capture_output=True, text=True, timeout=15)
            if result.returncode:
                if 'not supported' in result.stderr.lower():
                    local_trash(child_path(directory, name))
                else:
                    raise RuntimeError(result.stderr.strip() or '无法移到回收站')
        self._mutate(move)

    @Slot(str)
    def open(self, name):
        # Both type check and launching occur in the worker.
        def activate(directory):
            target = child_path(directory, name)
            if target.is_dir():
                return target
            launch_gio('open', target)
            return directory
        if self.busy:
            return
        query = self._query
        directory = Path(self._path)

        def work():
            target = activate(directory)
            rows, more = page(target)
            return str(target), rows, sorted((r['name'] for r in rows if query in r['name'].casefold()), key=str.casefold), more
        self.worker.submit(work)
