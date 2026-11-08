#!/usr/bin/env python3
"""Generate or verify a deterministic checksum manifest for the project.

The manifest deliberately covers *source* artifacts only:

    otl/**.py, tests/**.py, experiments/**.py, docs/**.md, scripts/*.py,
    README.md, LICENSE, pyproject.toml, requirements.lock, Makefile,
    bootstrap.sh

Run directories (``experiments/*/runs/``), ``LATEST`` pointers, caches,
virtual environments and the derived ``results/`` index are excluded: they are
either append-only data or regenerated outputs, so hashing them would make the
manifest non-reproducible.

Usage::

    python3 scripts/checksums.py --write   # write CHECKSUMS.sha256
    python3 scripts/checksums.py --verify  # verify against CHECKSUMS.sha256

Exit status is 0 on success and 1 on a mismatch or missing file.  The output
format is the standard ``sha256sum`` format (``<hex>  <path>``), sorted by path,
so ``sha256sum -c CHECKSUMS.sha256`` also works on systems that provide it.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "CHECKSUMS.sha256"

EXPLICIT = (
    "README.md",
    "TODO.md",
    ".gitignore",
    "LICENSE",
    "pyproject.toml",
    "requirements.lock",
    "Makefile",
    "bootstrap.sh",
    "datasets/README.md",
    "datasets/physical/README.md",
)

GLOBS = (
    "otl/**/*.py",
    "tests/**/*.py",
    "experiments/*.py",
    "docs/*.md",
    "scripts/*.py",
    "datasets/*.md",
)

EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".mypy_cache",
    ".ruff_cache",
}


def _included(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    return path.is_file()


def collect() -> list[Path]:
    files: set[Path] = set()
    for name in EXPLICIT:
        path = ROOT / name
        if path.is_file():
            files.add(path)
    for pattern in GLOBS:
        for path in ROOT.glob(pattern):
            if _included(path):
                files.add(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def write() -> int:
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in collect()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST} ({len(lines)} files)")
    return 0


def verify() -> int:
    if not MANIFEST.is_file():
        print(f"missing manifest: {MANIFEST}", file=sys.stderr)
        return 1
    expected: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        checksum, _, rel = line.partition("  ")
        expected[rel] = checksum
    actual = {path.relative_to(ROOT).as_posix(): digest(path) for path in collect()}
    problems: list[str] = []
    for rel, checksum in sorted(expected.items()):
        if rel not in actual:
            problems.append(f"missing: {rel}")
        elif actual[rel] != checksum:
            problems.append(f"changed: {rel}")
    for rel in sorted(set(actual) - set(expected)):
        problems.append(f"untracked: {rel}")
    if problems:
        print("checksum verification FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"checksum verification OK ({len(expected)} files)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="write CHECKSUMS.sha256")
    group.add_argument("--verify", action="store_true", help="verify CHECKSUMS.sha256")
    args = parser.parse_args(argv)
    return write() if args.write else verify()


if __name__ == "__main__":
    raise SystemExit(main())
