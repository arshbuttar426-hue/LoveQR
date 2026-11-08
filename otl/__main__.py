"""Allow ``python -m otl`` to run the command line interface."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
