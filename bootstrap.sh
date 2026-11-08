#!/usr/bin/env bash
# Bootstrap a reproducible OPTICAL_TRANSMISSION_LAB environment.
#
# Creates a local virtual environment, installs the pinned dependencies from
# requirements.lock, installs the package in editable mode without touching
# dependency resolution, then runs the internal selftest.
#
# Usage:
#   ./bootstrap.sh            # create/reuse .venv
#   PYTHON=python3.12 ./bootstrap.sh
#
# The script is idempotent.  It never modifies experiment data.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "error: $PYTHON not found on PATH" >&2
    exit 1
fi

echo "== Python =="
"$PYTHON" --version

if [ ! -d "$VENV" ]; then
    echo "== Creating $VENV =="
    "$PYTHON" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "== Installing pinned dependencies =="
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.lock

echo "== Installing package (editable, no dependency resolution) =="
python -m pip install -e . --no-deps

echo "== Selftest =="
python -m otl selftest

echo
echo "Environment ready. Activate with:"
echo "    source $VENV/bin/activate"
echo "Then run:"
echo "    python -m pytest"
echo "    python -m experiments.run_all --all"
