"""Bounded background I/O; GUI updates are delivered through queued signals."""
import os
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Property, QTimer


class ScanSignals(QObject):
    finished = Signal(list, str)


class Scan(QRunnable):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.signals = ScanSignals()

    def run(self):
        try:
            # Bound both enumeration and payload; full indexing belongs in a service.
            entries = []
            with os.scandir(self.path) as iterator:
                for entry in iterator:
                    entries.append(entry.name)
                    if len(entries) == 200:
                        break
            self.signals.finished.emit(sorted(entries, key=str.casefold), '')
        except OSError as error:
            self.signals.finished.emit([], str(error))


class FilterSignals(QObject):
    finished = Signal(int, list)


class Filter(QRunnable):
    def __init__(self, revision, entries, query):
        super().__init__()
        self.revision, self.entries, self.query = revision, entries, query.casefold()
        self.signals = FilterSignals()

    def run(self):
        self.signals.finished.emit(
            self.revision, [name for name in self.entries if self.query in name.casefold()])


class DesktopBackend(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._entries = []
        self._busy = False
        self._error = ''
        self._scan = None
        self._all_entries = []
        self._query = ''
        self._revision = 0
        self._filtering = False
        self._filter_task = None
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(100)
        self._filter_timer.timeout.connect(self._start_filter)

    @Property('QStringList', notify=changed)
    def entries(self):
        return self._entries

    @Property(bool, notify=changed)
    def filtering(self):
        return self._filtering

    @Slot(str)
    def setQuery(self, query):
        if query == self._query:
            return
        self._query = query
        self._request_filter()

    def _request_filter(self):
        # One active task plus the latest desired query; never queue every keystroke.
        self._revision += 1
        self._filtering = True
        self._filter_timer.start()
        self.changed.emit()

    @Slot()
    def _start_filter(self):
        if self._filter_task is not None:
            return
        self._filter_task = Filter(self._revision, self._all_entries[:], self._query)
        self._filter_task.signals.finished.connect(self._filtered)
        self.pool.start(self._filter_task)

    @Slot(int, list)
    def _filtered(self, revision, entries):
        self._filter_task = None
        if revision == self._revision:
            self._entries = entries
            self._filtering = False
            self.changed.emit()
        elif not self._filter_timer.isActive():
            self._start_filter()

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Slot()
    def scanHome(self):
        self.scan(str(Path.home()))

    @Slot(str)
    def scan(self, path):
        if self._busy:
            return
        self._busy = True
        self._error = ''
        self.changed.emit()
        self._scan = Scan(path)
        self._scan.signals.finished.connect(self._complete)
        self.pool.start(self._scan)

    @Slot(list, str)
    def _complete(self, entries, error):
        self._all_entries, self._error, self._busy = entries, error, False
        self._scan = None
        self._request_filter()
