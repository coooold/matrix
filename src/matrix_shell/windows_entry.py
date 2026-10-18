"""Native Windows/frozen entry point, without the Linux Qt library re-exec."""
import os
from pathlib import Path
import sys


def main():
    if os.name == 'nt':
        os.environ.setdefault('QT_MEDIA_BACKEND', 'windows')
    if sys.stderr is None:
        directory = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MatrixPreview'
        directory.mkdir(parents=True, exist_ok=True)
        sys.stderr = (directory / 'runtime.log').open('a', encoding='utf-8')
    if sys.stdout is None:
        sys.stdout = sys.stderr
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--self-test', action='store_true')
        parser.add_argument('--report', type=Path, required=True)
        args = parser.parse_args()
        from .preview_checks import run
        run(args.report)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == '--app':
        del sys.argv[1]
        from .core_apps import main as run
    else:
        from .app import main as run
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
