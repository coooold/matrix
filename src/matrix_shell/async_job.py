"""Single-flight worker queue: one running operation and one latest request."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Property


class Completion(QObject):
    finished = Signal(int, object, str)


class Work(QRunnable):
    def __init__(self, revision, operation):
        super().__init__()
        self.revision, self.operation = revision, operation
        self.signals = Completion()

    def run(self):
        try:
            value, error = self.operation(), ''
        except Exception as failure:
            value, error = None, str(failure)
        self.signals.finished.emit(self.revision, value, error)


class LatestWorker(QObject):
    changed = Signal()
    completed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._revision = 0
        self._active = None
        self._pending = None
        self._error = ''

    @Property(bool, notify=changed)
    def busy(self):
        return self._active is not None or self._pending is not None

    @Property(str, notify=changed)
    def error(self):
        return self._error

    def submit(self, operation):
        self._revision += 1
        self._pending = (self._revision, operation)
        self._error = ''
        if self._active is None:
            self._start()
        self.changed.emit()

    def _start(self):
        revision, operation = self._pending
        self._pending = None
        self._active = Work(revision, operation)
        self._active.signals.finished.connect(self._finish)
        self.pool.start(self._active)

    @Slot(int, object, str)
    def _finish(self, revision, value, error):
        self._active = None
        if revision == self._revision:
            self._error = error
            if not error:
                self.completed.emit(value)
        if self._pending is not None:
            self._start()
        self.changed.emit()

    def invalidate(self):
        self._revision += 1
        self._pending = None

    def shutdown(self):
        # At process exit, retain the latest queued write instead of dropping it.
        self.pool.waitForDone()
        if self._pending is not None:
            revision, operation = self._pending
            self._pending = None
            final = Work(revision, operation)
            self.pool.start(final)
            self.pool.waitForDone()
