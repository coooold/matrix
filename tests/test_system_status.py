import os
import subprocess
import pytest
from matrix_shell.system_status import sample, process_identity, terminate_process


def test_real_metrics_and_controlled_process():
    previous, values = sample(None)
    assert values['cpuPercent'] is None
    assert values['memoryTotalKiB'] > values['memoryUsedKiB'] >= 0
    again, values = sample(previous)
    if values['cpuPercent'] is not None:
        assert 0 <= values['cpuPercent'] <= 100
    with subprocess.Popen(['/bin/sleep', '30']) as child:
        try:
            identity = process_identity(child.pid)
            assert identity['uid'] == os.getuid()
            with pytest.raises(PermissionError):
                terminate_process(child.pid, 'wrong-start-token')
            assert child.poll() is None
            terminate_process(child.pid, identity['start'])
            assert child.wait(timeout=5) != 0
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)


def test_cannot_end_self():
    identity = process_identity(os.getpid())
    with pytest.raises(PermissionError):
        terminate_process(os.getpid(), identity['start'])
