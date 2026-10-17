import time
from PySide6.QtCore import QCoreApplication
from matrix_shell.backend import DesktopBackend


def wait_until(app, predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert predicate(), 'worker failed to finish'


def test_scan_and_error(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    (tmp_path / 'hello.txt').write_text('hello')
    backend = DesktopBackend()
    backend.scan(str(tmp_path))
    assert backend.busy
    wait_until(app, lambda: not backend.busy and not backend.filtering)
    assert backend.entries == ['hello.txt']
    assert not backend.error
    backend.scan(str(tmp_path / 'missing'))
    wait_until(app, lambda: not backend.busy and not backend.filtering)
    assert backend.entries == []
    assert backend.error


def test_scan_bounded_and_single_flight(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    for i in range(220):
        (tmp_path / str(i)).touch()
    backend = DesktopBackend()
    backend.scan(str(tmp_path))
    backend.scan('/nonexistent-must-not-replace-active-job')
    wait_until(app, lambda: not backend.busy and not backend.filtering)
    assert len(backend.entries) == 200
    assert not backend.error


def test_filter_latest_query_casefold_and_clear(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    for name in ['Alpha.txt', 'beta.txt', 'ALPINE.md']:
        (tmp_path / name).touch()
    backend = DesktopBackend()
    backend.scan(str(tmp_path))
    backend.setQuery('does-not-match')
    backend.setQuery('ALP')
    wait_until(app, lambda: not backend.busy and not backend.filtering)
    assert backend.entries == ['Alpha.txt', 'ALPINE.md']
    backend.setQuery('missing')
    wait_until(app, lambda: not backend.filtering)
    assert backend.entries == []
    backend.setQuery('')
    wait_until(app, lambda: not backend.filtering)
    assert len(backend.entries) == 3


def test_stale_filter_never_overwrites_new_query(tmp_path, monkeypatch):
    import threading
    from PySide6.QtCore import QTimer
    from matrix_shell.backend import Filter
    app = QCoreApplication.instance() or QCoreApplication([])
    (tmp_path / 'alpha').touch()
    (tmp_path / 'beta').touch()
    backend = DesktopBackend()
    backend.scan(str(tmp_path))
    wait_until(app, lambda: not backend.busy and not backend.filtering)
    started, release = threading.Event(), threading.Event()
    original_run = Filter.run

    def delayed_run(task):
        if task.query == 'alpha':
            started.set()
            release.wait(5)
        original_run(task)

    monkeypatch.setattr(Filter, 'run', delayed_run)
    seen = []
    backend.changed.connect(lambda: seen.append(backend.entries[:]))
    beats = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: beats.append(True))
    timer.start()
    try:
        backend.setQuery('alpha')
        wait_until(app, started.is_set)
        backend.setQuery('beta')
        wait_until(app, lambda: len(beats) >= 3)
        release.set()
        wait_until(app, lambda: not backend.filtering)
        assert backend.entries == ['beta']
        assert ['alpha'] not in seen
    finally:
        release.set()
        timer.stop()
        backend.pool.waitForDone()
