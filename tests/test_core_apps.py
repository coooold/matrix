from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication
from matrix_shell.core_apps import calculate, CoreModel
from test_backend import wait_until


def test_calculator_arithmetic_errors_and_no_code_execution():
    assert calculate('(2+3)*4/2') == '10'
    assert calculate('-(3-5)') == '2'
    assert calculate('.1+.2') == '0.3'
    assert calculate('9007199254740993+1') == '9007199254740994'
    for expression in ('1/0', '__import__("os")', '2**10000', '[1]', '1e999'):
        with pytest.raises((ValueError, ZeroDivisionError)):
            calculate(expression)


def test_note_survives_process_model_restart_and_exit(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    path = tmp_path / 'note.txt'
    model = CoreModel('notes', path)
    wait_until(app, lambda: not model.worker.busy)
    assert model.ready
    model.setText('真实笔记\n保存后重启')
    model.shutdown()
    again = CoreModel('notes', path)
    wait_until(app, lambda: not again.worker.busy)
    assert again.text == '真实笔记\n保存后重启'
    again.shutdown()
