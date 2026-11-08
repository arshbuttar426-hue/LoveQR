#!/usr/bin/env python3
"""Compare two experiment runs for reproducibility.

The comparison covers what a re-run must reproduce — the input payloads and the
trial outcomes — and deliberately ignores wall-clock and resource numbers,
which depend on the host and its load.

It is written for experiments that record the fingerprints produced by
``E09_end_to_end`` (``payload_manifest_sha256`` and ``outcome_sha256``);
experiments without them are rejected rather than compared superficially.

Usage::

    python3 scripts/verify_rerun.py --experiment E09_end_to_end
    python3 scripts/verify_rerun.py RUN_DIR_A RUN_DIR_B

``--experiment`` picks the two newest runs that have a ``processed/summary.json``
(an interrupted run has no summary and is skipped).  Exit status is 0 when the
payload set and the outcome set are identical, 1 when they differ, and 2 when
the runs cannot be compared.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ROOT / "experiments"

# Fields that legitimately differ between runs on the same host.
IGNORED_METRIC_PREFIXES = (
    "simulated_wall_s",
    "simulated_gross_bps",
    "simulated_net_bps",
    "decode_fps_simulated",
    "latency_",
    "reconstruction_ms",
    "ecc_ms",
    "compression_ms",
    "cpu_percent",
    "rss_kb",
    "max_rss_kb",
    "ber",  # derived from the recovered bytes; must match, but only for successes
)


def _load(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "processed" / "summary.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (run_dir / "raw" / "trials.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return manifest, summary, rows


def _key(row: dict[str, Any]) -> tuple:
    config = row["config"]
    return (
        config.get("payload_kind"),
        config.get("payload_bytes"),
        config.get("channel"),
        config.get("drop_probability"),
        config.get("compression"),
    )


def _outcome(row: dict[str, Any]) -> dict[str, Any]:
    outputs = row["outputs"]
    metrics = row["metrics"]
    return {
        "success": bool(outputs.get("success", False)),
        "frames_total": metrics.get("frames_total"),
        "frames_decoded": metrics.get("frames_decoded"),
        "frames_crc_ok": metrics.get("frames_crc_ok"),
        "frames_dropped": metrics.get("frames_dropped"),
        "error_stages": sorted(outputs.get("error_stages") or []),
        "payload_sha256": row["inputs"].get("payload_sha256"),
        "payload_len": outputs.get("payload_len"),
        "total_packets": outputs.get("total_packets"),
    }


def _latest_runs(experiment: str, count: int = 2) -> list[Path]:
    runs_dir = EXPERIMENTS / experiment / "runs"
    candidates = [
        path
        for path in runs_dir.iterdir()
        if path.is_dir() and (path / "processed" / "summary.json").is_file()
    ]
    candidates.sort(key=lambda p: p.name, reverse=True)
    if len(candidates) < count:
        raise SystemExit(
            f"need {count} complete runs for {experiment}, found {len(candidates)}"
        )
    return candidates[:count]


def _compare(a: Path, b: Path) -> int:
    manifest_a, summary_a, rows_a = _load(a)
    manifest_b, summary_b, rows_b = _load(b)

    problems: list[str] = []

    for run, summary in ((a, summary_a), (b, summary_b)):
        if summary.get("simulation_only") is not True:
            problems.append(f"{run.name}: summary.json does not say simulation_only")
        if summary.get("evidence_source") != "SIMULATED / SOFTWARE":
            problems.append(f"{run.name}: summary.json lacks the SIMULATED / SOFTWARE label")
        if "sha256_verification" not in summary.get("summary", {}):
            print(
                f"{run.name}: no sha256_verification block; this comparison only "
                "supports experiments that record payload and outcome fingerprints "
                "(E09_end_to_end)",
                file=sys.stderr,
            )
            return 2

    meta_a = manifest_a.get("experiment_metadata", {})
    meta_b = manifest_b.get("experiment_metadata", {})
    gen_a = meta_a.get("payload_generator")
    gen_b = meta_b.get("payload_generator")
    if gen_a != gen_b:
        problems.append("payload_generator specification differs")

    fp_a = meta_a.get("payload_manifest_sha256")
    fp_b = meta_b.get("payload_manifest_sha256")
    if fp_a != fp_b:
        problems.append(f"payload manifest fingerprint differs: {fp_a} != {fp_b}")

    if len(rows_a) != len(rows_b):
        problems.append(f"trial count differs: {len(rows_a)} != {len(rows_b)}")

    map_a = {_key(row): row for row in rows_a}
    map_b = {_key(row): row for row in rows_b}
    if set(map_a) != set(map_b):
        problems.append(
            f"trial configuration sets differ: {sorted(set(map_a) ^ set(map_b))}"
        )

    outcome_mismatches: list[str] = []
    payload_mismatches: list[str] = []
    for key in sorted(set(map_a) & set(map_b), key=str):
        out_a = _outcome(map_a[key])
        out_b = _outcome(map_b[key])
        if out_a["payload_sha256"] != out_b["payload_sha256"]:
            payload_mismatches.append(f"{key}: payload hash differs")
        for field, value_a in out_a.items():
            if field == "payload_sha256":
                continue
            if value_a != out_b[field]:
                outcome_mismatches.append(
                    f"{key}: {field} {value_a!r} != {out_b[field]!r}"
                )
    problems.extend(payload_mismatches)
    problems.extend(outcome_mismatches)

    outcome_fp_a = summary_a["summary"]["sha256_verification"]["outcome_sha256"]
    outcome_fp_b = summary_b["summary"]["sha256_verification"]["outcome_sha256"]
    if outcome_fp_a != outcome_fp_b:
        problems.append(f"outcome fingerprint differs: {outcome_fp_a} != {outcome_fp_b}")

    report = {
        "run_a": a.name,
        "run_b": b.name,
        "trials_a": len(rows_a),
        "trials_b": len(rows_b),
        "payload_manifest_sha256_a": fp_a,
        "payload_manifest_sha256_b": fp_b,
        "payloads_identical": not payload_mismatches,
        "outcome_sha256_a": outcome_fp_a,
        "outcome_sha256_b": outcome_fp_b,
        "outcomes_identical": not outcome_mismatches,
        "ignored_between_runs": sorted(IGNORED_METRIC_PREFIXES),
        "problems": problems,
        "verdict": "IDENTICAL" if not problems else "DIFFERENT",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not problems else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_a", nargs="?", type=Path)
    parser.add_argument("run_b", nargs="?", type=Path)
    parser.add_argument(
        "--experiment",
        help="compare the two newest complete runs of this experiment id",
    )
    args = parser.parse_args(argv)

    if args.experiment:
        runs = _latest_runs(args.experiment)
        return _compare(runs[1], runs[0])
    if not (args.run_a and args.run_b):
        parser.error("provide two run directories or --experiment ID")
    return _compare(args.run_a, args.run_b)


if __name__ == "__main__":
    raise SystemExit(main())
