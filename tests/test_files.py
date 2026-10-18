import threading
from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication
from matrix_shell.files import FileBrowser, copy_file
from test_backend import wait_until


def test_real_file_lifecycle_and_conflicts(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    browser = FileBrowser()
    def done():
        wait_until(app, lambda: not browser.busy)
    browser.navigate(str(tmp_path))
    done()
    browser.createFolder('documents')
    done()
    assert (tmp_path / 'documents').is_dir()
    browser.createFile('note.txt')
    done()
    (tmp_path / 'note.txt').write_text('keep this content')
    browser.copy('note.txt', 'copy.txt')
    done()
    assert (tmp_path / 'copy.txt').read_text() == 'keep this content'
    browser.createFile('copy.txt')
    done()
    assert browser.error
    assert (tmp_path / 'copy.txt').read_text() == 'keep this content'
    browser.createFolder('../escape')
    done()
    assert browser.error and not (tmp_path.parent / 'escape').exists()
    browser.open('documents')
    done()
    assert browser.path == str(tmp_path / 'documents')
    browser.parentDirectory()
    done()
    assert browser.path == str(tmp_path)


def test_pagination_search_and_missing_directory(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    for i in range(231):
        (tmp_path / f'file-{i:03d}').touch()
    browser = FileBrowser()
    browser.navigate(str(tmp_path))
    wait_until(app, lambda: not browser.busy)
    assert len(browser.entries) == 200 and browser.more
    browser.loadMore()
    wait_until(app, lambda: not browser.busy)
    assert len(browser.entries) == 231 and not browser.more
    browser.setQuery('FILE-230')
    wait_until(app, lambda: not browser.busy)
    assert browser.entries == ['file-230']
    browser.navigate(str(tmp_path / 'missing'))
    wait_until(app, lambda: not browser.busy)
    assert browser.error
    assert browser.path == str(tmp_path)


def test_cancelled_copy_removes_only_own_partial_file(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.write_bytes(b'x' * 1024)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        copy_file(source, target, cancel)
    assert not target.exists()
    target.write_text('original')
    with pytest.raises(FileExistsError):
        copy_file(source, target, threading.Event())
    assert target.read_text() == 'original'


def test_real_trash_has_recoverable_content(tmp_path, monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    data = tmp_path / 'data'
    monkeypatch.setenv('XDG_DATA_HOME', str(data))
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'recover.txt').write_text('recoverable')
    browser = FileBrowser()
    browser.navigate(str(work))
    wait_until(app, lambda: not browser.busy)
    browser.trash('recover.txt')
    wait_until(app, lambda: not browser.busy)
    assert not browser.error
    assert not (work / 'recover.txt').exists()
    trashed = list((data / 'Trash/files').glob('recover*'))
    assert len(trashed) == 1 and trashed[0].read_text() == 'recoverable'
    assert list((data / 'Trash/info').glob('*.trashinfo'))


def test_permission_failure_and_query_during_navigation(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    blocked = tmp_path / 'blocked'
    blocked.mkdir()
    blocked.chmod(0)
    browser = FileBrowser()
    try:
        browser.navigate(str(blocked))
        wait_until(app, lambda: not browser.busy)
        assert browser.error
    finally:
        blocked.chmod(0o700)
    (tmp_path / 'target.txt').touch()
    browser.navigate(str(tmp_path))
    browser.setQuery('target')
    wait_until(app, lambda: not browser.busy)
    assert browser.path == str(tmp_path)
    assert browser.entries == ['target.txt']


def test_disk_full_failure_cleans_partial_copy(tmp_path, monkeypatch):
    import errno
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.write_bytes(b'important bytes')
    original = Path.open
    class FailingWriter:
        def __enter__(self):
            self.stream = original(target, 'xb')
            return self
        def write(self, block):
            self.stream.write(block[:2])
            raise OSError(errno.ENOSPC, 'injected disk full')
        def __exit__(self, *args):
            self.stream.close()
    def open_path(path, mode='r', *args, **kwargs):
        if path == target and mode == 'xb':
            return FailingWriter()
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', open_path)
    with pytest.raises(OSError) as failure:
        copy_file(source, target, threading.Event())
    assert failure.value.errno == errno.ENOSPC
    assert source.read_bytes() == b'important bytes'
    assert not target.exists()
