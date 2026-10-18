import threading
import time
from PySide6.QtCore import QCoreApplication, QTimer
from matrix_shell.async_job import LatestWorker


def wait_until(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert predicate(), 'worker failed to finish'


def test_latest_result_and_gui_remains_responsive():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = LatestWorker()
    started, release = threading.Event(), threading.Event()
    seen, beats = [], []
    worker.completed.connect(seen.append)
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: beats.append(True))
    timer.start()
    def old():
        started.set()
        release.wait(5)
        return 'obsolete'
    try:
        worker.submit(old)
        wait_until(app, started.is_set)
        for i in range(100):
            worker.submit(lambda value=i: value)
        wait_until(app, lambda: len(beats) >= 3)
        release.set()
        wait_until(app, lambda: not worker.busy)
        assert seen == [99]
    finally:
        release.set()
        timer.stop()
        worker.shutdown()


def test_exception_can_be_recovered():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = LatestWorker()
    worker.submit(lambda: 1 / 0)
    wait_until(app, lambda: not worker.busy)
    assert worker.error
    worker.submit(lambda: 'recovered')
    wait_until(app, lambda: not worker.busy)
    assert not worker.error
