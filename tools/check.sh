#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export XDG_CACHE_HOME="$PWD/.cache"
mkdir -p "$XDG_CACHE_HOME"
mkdir -p artifacts
.venv/bin/python tools/acceptance_report.py --check
.venv/bin/python -m pytest -q --junitxml=artifacts/tests.xml
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m matrix_shell.app --smoke
