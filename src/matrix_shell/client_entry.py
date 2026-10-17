"""Select the wheel's Qt libraries before importing Qt, then start the client."""
import importlib.util
import os
from pathlib import Path
import sys


def dispatch(module):
    spec = importlib.util.find_spec('PySide6')
    if spec is None:
        raise RuntimeError('PySide6 is not installed')
    libraries = str(Path(spec.origin).parent / 'Qt/lib')
    environment = dict(os.environ)
    existing = [path for path in environment.get('LD_LIBRARY_PATH', '').split(':') if path and path != libraries]
    environment['LD_LIBRARY_PATH'] = ':'.join([libraries, *existing])
    os.execvpe(sys.executable, [sys.executable, '-m', module, *sys.argv[1:]], environment)


def shell_main():
    dispatch('matrix_shell.app')


def app_main():
    dispatch('matrix_shell.core_apps')
