import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('frame_report', Path(__file__).parents[1] / 'tools/frame_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_tail_and_late_intervals():
    report = module.summarize([8.0] * 98 + [12.0, 20.0], 120)
    assert report['p95_ms'] == 8
    assert report['p99_ms'] == 12
    assert report['late_interval_ratio'] == .02


@pytest.mark.parametrize('samples,hz', [([], 60), ([0], 60), ([float('nan')], 60), ([1], 0)])
def test_invalid_capture(samples, hz):
    with pytest.raises(ValueError):
        module.summarize(samples, hz)
