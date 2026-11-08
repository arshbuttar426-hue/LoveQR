"""Run one or all experiments.

Examples::

    python3 -m experiments.run_all --list
    python3 -m experiments.run_all --only E01_capacity
    python3 -m experiments.run_all --only E01_capacity,E05_erasures --quick
    python3 -m experiments.run_all --only E12_channel_efficiency \
        --sessions datasets/physical/m10-baseline-01-20261108T112241Z
    python3 -m experiments.run_all --all
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .harness import RESULTS, run_experiment
from .registry import BY_ID, EXPERIMENTS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list experiment ids")
    parser.add_argument("--only", help="comma-separated experiment ids")
    parser.add_argument("--all", action="store_true", help="run every experiment")
    parser.add_argument("--quick", action="store_true", help="reduced trial counts")
    parser.add_argument(
        "--session",
        help="physical capture session directory (used by E11_physical)",
    )
    parser.add_argument(
        "--sessions",
        help=(
            "comma-separated physical capture session directories "
            "(used by E12_channel_efficiency)"
        ),
    )
    args = parser.parse_args(argv)

    if args.list:
        for spec in EXPERIMENTS:
            print(f"{spec.id:24s} {spec.classification:45s} {spec.title}")
        return 0

    if args.all:
        selected = list(EXPERIMENTS)
    elif args.only:
        ids = [item.strip() for item in args.only.split(",") if item.strip()]
        unknown = [item for item in ids if item not in BY_ID]
        if unknown:
            print(f"unknown experiment(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        selected = [BY_ID[item] for item in ids]
    else:
        parser.print_help()
        return 2

    log: list[dict[str, object]] = []
    options: dict[str, object] = {}
    if args.session:
        options["session"] = args.session
    if args.sessions:
        options["sessions"] = [
            item.strip() for item in args.sessions.split(",") if item.strip()
        ]
    for spec in selected:
        print(f"== {spec.id}: {spec.title}", flush=True)
        out_dir = run_experiment(spec, quick=args.quick, options=options)
        log.append(
            {
                "id": spec.id,
                "run_dir": str(out_dir),
                "run_id": out_dir.name,
                "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "quick": args.quick,
            }
        )
        print(f"   -> {out_dir}", flush=True)

    RESULTS.mkdir(parents=True, exist_ok=True)
    log_path = RESULTS / "runs.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in log:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
