# OPTICAL_TRANSMISSION_LAB — reproducible commands
#
# Every target is a thin wrapper around a command documented in README.md and
# docs/REPRODUCE.md.  Nothing here writes to an existing experiment run: the
# harness creates a new timestamped run directory on every invocation.
#
# Usage:
#   make bootstrap     create .venv, install the pinned environment, run selftest
#   make test          full pytest suite
#   make selftest      dependency-free internal smoke checks
#   make quick         run E01–E10 in quick mode (new runs, append-only)
#   make experiments   run E01–E10 in full mode (new runs, append-only)
#   make manifest      print protocol and pipeline constants as JSON
#   make checksums     regenerate CHECKSUMS.sha256
#   make verify        verify CHECKSUMS.sha256 and run the test suite
#   make clean         remove caches only (never experiment data)

PYTHON ?= python3
VENV ?= .venv
PY := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,$(PYTHON))

.PHONY: all bootstrap install test selftest quick experiments manifest checksums verify clean help

all: test

help:
	@sed -n '1,20p' Makefile

bootstrap:
	./bootstrap.sh

install:
	$(PY) -m pip install -r requirements.lock
	$(PY) -m pip install -e . --no-deps

test:
	$(PY) -m pytest

selftest:
	$(PY) -m otl selftest

quick:
	$(PY) -m experiments.run_all --all --quick

experiments:
	$(PY) -m experiments.run_all --all

manifest:
	$(PY) -m otl manifest

checksums:
	$(PY) scripts/checksums.py --write

verify:
	$(PY) scripts/checksums.py --verify
	$(PY) -m pytest

clean:
	rm -rf .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
