"""Real /proc metrics and same-user process control without exposing argv/env."""
import os
from pathlib import Path
import signal
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from .async_job import LatestWorker


def process_identity(pid):
    root = Path('/proc') / str(pid)
    raw = (root / 'stat').read_text()
    # comm may include spaces and parentheses. Fields after the last ')' start at state.
    fields = raw[raw.rfind(')') + 2:].split()
    status = (root / 'status').read_text().splitlines()
    uid = int(next(line for line in status if line.startswith('Uid:')).split()[1])
    return {'pid': int(pid), 'name': (root / 'comm').read_text().strip(),
            'uid': uid, 'state': fields[0], 'start': fields[19], 'parent': int(fields[1]),
            'rssKiB': next((int(line.split()[1]) for line in status if line.startswith('VmRSS:')), 0)}


def protected_pids():
    protected = {1, os.getpid()}
    pid = os.getpid()
    while pid > 1:
        try:
            pid = process_identity(pid)['parent']
            if pid in protected:
                break
            protected.add(pid)
        except (OSError, ValueError):
            break
    return protected


def sample(previous):
    fields = [int(value) for value in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    total, idle = sum(fields), fields[3] + fields[4]
    cpu = None
    if previous and total > previous[0]:
        cpu = max(0, min(100, 100 * (1 - (idle - previous[1]) / (total - previous[0]))))
    memory = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    processes = []
    protected = protected_pids()
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            process = process_identity(int(directory.name))
            if process['uid'] == os.getuid():
                process['terminable'] = process['pid'] not in protected and process['state'] not in ('Z', 'X')
                processes.append(process)
        except (OSError, ValueError, IndexError, StopIteration):
            continue
    battery = None
    for supply in Path('/sys/class/power_supply').glob('*'):
        try:
            if (supply / 'type').read_text().strip() == 'Battery':
                battery = int((supply / 'capacity').read_text())
                break
        except (OSError, ValueError):
            pass
    default_routes = []
    try:
        for row in Path('/proc/net/route').read_text().splitlines()[1:]:
            parts = row.split()
            if parts[1] == '00000000' and int(parts[3], 16) & 1:
                default_routes.append(parts[0])
    except (OSError, ValueError, IndexError):
        pass
    values = {'cpuPercent': cpu, 'memoryUsedKiB': memory['MemTotal'] - memory['MemAvailable'],
              'memoryTotalKiB': memory['MemTotal'], 'batteryPercent': battery,
              'routeInterfaces': default_routes, 'volume': None,
              'processes': sorted(processes, key=lambda proc: proc['rssKiB'], reverse=True)}
    return (total, idle), values


def terminate_process(pid, start):
    identity = process_identity(pid)
    if identity['uid'] != os.getuid() or pid in protected_pids() or identity['start'] != start:
        raise PermissionError('进程身份已变化或不允许结束该进程')
    # pidfd pins the process identity, preventing PID reuse between check and signal.
    fd = os.pidfd_open(pid)
    try:
        if process_identity(pid)['start'] != start:
            raise PermissionError('进程身份已变化')
        signal.pidfd_send_signal(fd, signal.SIGTERM)
    finally:
        os.close(fd)


class SystemStatus(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._loaded)
        self._consumers = 0
        self._previous = None
        self._values = {}
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.refresh)
        self._error = ''

    @Property('QVariantMap', notify=changed)
    def values(self):
        return self._values

    @Property(str, notify=changed)
    def error(self):
        return self._error or self.worker.error

    @Slot()
    def acquire(self):
        self._consumers += 1
        if self._consumers == 1:
            self.refresh()
            self.timer.start()

    @Slot()
    def release(self):
        self._consumers = max(0, self._consumers - 1)
        if not self._consumers:
            self.timer.stop()

    @Slot()
    def refresh(self):
        if not self.worker.busy:
            self.worker.submit(lambda: sample(self._previous))

    @Slot(object)
    def _loaded(self, result):
        self._previous, self._values = result
        self.changed.emit()

    @Slot(int)
    def terminate(self, pid):
        if self.worker.busy:
            return
        current = next((process for process in self._values.get('processes', []) if process['pid'] == pid), None)
        if current is None or not current['terminable']:
            self._error = '只能结束列表中可操作的当前用户进程'
            self.changed.emit()
            return
        self._error = ''
        def operation():
            terminate_process(pid, current['start'])
            return sample(self._previous)
        self.worker.submit(operation)
