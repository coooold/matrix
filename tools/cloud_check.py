"""Run the cloud KWin matrix, preserving separate results for every case."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, default=ROOT / '.cache/kwin/root')
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'tools/kwin_check.py'), '--cli-smoke', '--prefix', str(args.prefix), '--output', str(ROOT / 'artifacts/kwin/cli-startup')], check=True)
    cases = [('one-100', 1, 1, None), ('two-125', 2, 1.25, None),
             ('two-150', 2, 1.5, None), ('two-200', 2, 2, None), ('mixed-125-200', 2, 1.25, 2)]
    for name, outputs, scale, second in cases:
        command = [sys.executable, str(ROOT / 'tools/kwin_check.py'), '--session', '--prefix', str(args.prefix),
                   '--outputs', str(outputs), '--scale', str(scale), '--output', str(ROOT / 'artifacts/kwin' / name)]
        if second:
            command.extend(['--second-scale', str(second)])
        subprocess.run(command, check=True)
    print('Installed CLI plus 5 cloud KWin cases passed. Hardware, trusted lock and Flatpak sandbox are not covered.')


if __name__ == '__main__':
    main()
