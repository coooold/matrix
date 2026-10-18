"""Planning gate rejects unsupported acceptance claims; no desktop scenarios here."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('acceptance_report', ROOT / 'tools/acceptance_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def plan():
    return json.loads((ROOT / 'docs/acceptance.json').read_text())


def test_current_plan_valid():
    assert module.validate(plan()) == []


def test_verified_cannot_omit_gate_evidence():
    data = plan()
    item = data['items'][1]
    item['status'] = 'verified'
    item['evidence'] = [{'gate': 'ci', 'result': 'passed', 'matrix_commit': 'a' * 40,
                         'report': 'https://example.org/ci/1', 'reviewer': 'reviewer'}]
    assert any('every gate' in error for error in module.validate(data))


def test_verified_needs_reviewer_and_full_sha():
    data = plan()
    item = data['items'][0]
    item['status'] = 'verified'
    item['evidence'] = [{'gate': 'visual', 'result': 'passed', 'matrix_commit': 'abc'}]
    assert any('Matrix SHA' in error for error in module.validate(data))
    item['evidence'][0]['matrix_commit'] = 'a' * 40
    assert any('report and reviewer' in error for error in module.validate(data))
    item['evidence'][0].update(report='https://example.org/report', reviewer='reviewer')
    assert module.validate(data) == []


def test_conflicting_gate_reports_rejected():
    data = plan()
    item = data['items'][0]
    item['evidence'] = [{'gate': 'visual', 'result': 'unrun'}, {'gate': 'visual', 'result': 'failed'}]
    assert any('duplicate evidence gate' in error for error in module.validate(data))


def test_reference_drift_duplicate_id_and_unknown_gate():
    data = plan()
    data['items'][1]['id'] = data['items'][0]['id']
    data['items'][0]['sources'] = ['https://github.com/omgupta117/OMEGA-OS/blob/main/README.md']
    data['items'][0]['gates'] = ['imaginary']
    errors = module.validate(data)
    assert any('duplicate ID' in error for error in errors)
    assert any('pinned reference' in error for error in errors)
    assert any('unknown or duplicate gate' in error for error in errors)
