"""E09 — End-to-end simulated transfer.

Every number produced here is **SIMULATED / SOFTWARE**.  There is no screen,
camera or physical optical link in this experiment: the "optics" are
``otl/rx/channel.py`` and the wall-clock numbers are Python execution time.

Reproducibility contract
------------------------
* Payloads are generated from a recorded, seeded generator.  ``text`` payloads
  are a repeated UTF-8 template truncated to the requested length; ``random``
  payloads use ``numpy.random.default_rng(PAYLOAD_SEED_BASE + size)``.  The
  generator specification, every seed and every payload SHA-256 are written to
  ``manifest.json`` under ``experiment_metadata``.
* ``payload_manifest_sha256`` fingerprints all payloads; ``outcome_sha256``
  fingerprints every trial's outcome (configuration, success flag, frame
  counters and error stages).  A re-run with the same code produces the same
  two fingerprints, which is how the rerun check in ``docs/EXPERIMENTS.md`` was
  verified.
* All 64 full-mode trials — successes and failures — are written to
  ``raw/trials.jsonl``.  Nothing is filtered out of the raw data.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

import numpy as np

from otl.config import ExperimentConfig
from otl.metrics import Aggregate, ResourceMeter
from otl.pipeline import simulate_transfer

from .common import CHANNELS, cfg_with
from .harness import ExperimentSpec, RunContext

SIZES = (100, 1000, 2400, 6000)
CHANNEL_NAMES = ("clean", "mild", "harsh", "brutal")
DROPS = (0.0, 0.03)
KINDS = ("text", "random")

PAYLOAD_SEED_BASE = 7000
RNG_FACTORY = "numpy.random.default_rng"
RNG_BIT_GENERATOR = "PCG64 (numpy default)"
RANDOM_DRAW = "integers(0, 256, size=payload_bytes, dtype=uint8).tobytes()"
PIPELINE_SEED_RULE = "9000 + payload_bytes + int(drop_probability * 1000)"

TEXT = (
    "Screen-to-camera optical transmission carries bytes through a spatial "
    "code, a rolling shutter and a noisy image sensor. "
)


def _text_payload(size: int) -> bytes:
    raw = (TEXT * (size // len(TEXT) + 1)).encode("utf-8")
    return raw[:size]


def _payload_seed(kind: str, size: int) -> int | None:
    return None if kind == "text" else PAYLOAD_SEED_BASE + size


def _payload(kind: str, size: int) -> bytes:
    """Deterministic payload for a given kind and size (see module docstring)."""
    if kind == "text":
        return _text_payload(size)
    seed = _payload_seed(kind, size)
    assert seed is not None
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=size, dtype=np.uint8).tobytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fingerprint(rows: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8")).hexdigest()


def _aggregate(values: list[float]) -> dict[str, float]:
    agg = Aggregate()
    for value in values:
        agg.add(value)
    return agg.to_dict()


def run(ctx: RunContext) -> None:
    base = ExperimentConfig()
    sizes = (100, 1000) if ctx.quick else SIZES
    channels = ("clean", "mild") if ctx.quick else CHANNEL_NAMES
    drops = (0.0,) if ctx.quick else DROPS
    kinds = KINDS

    # -- deterministic payloads, hashed before any pipeline runs ------------
    payloads: dict[tuple[str, int], bytes] = {}
    payload_hashes: dict[tuple[str, int], str] = {}
    payload_records: list[dict[str, object]] = []
    for kind in kinds:
        for size in sizes:
            data = _payload(kind, size)
            digest = _sha256(data)
            payloads[(kind, size)] = data
            payload_hashes[(kind, size)] = digest
            payload_records.append(
                {
                    "kind": kind,
                    "payload_bytes": size,
                    "seed": _payload_seed(kind, size),
                    "sha256": digest,
                }
            )
    payload_manifest_sha256 = _fingerprint(
        [f"{rec['kind']}:{rec['payload_bytes']}:{rec['sha256']}" for rec in payload_records]
    )

    ctx.metadata = {
        "evidence_source": "SIMULATED / SOFTWARE",
        "physical_device": None,
        "simulation_only": True,
        "payload_generator": {
            "text": {
                "method": "UTF-8 template repeated then truncated to payload_bytes",
                "template_sha256": _sha256(TEXT.encode("utf-8")),
                "template_bytes": len(TEXT.encode("utf-8")),
                "seed": None,
            },
            "random": {
                "factory": RNG_FACTORY,
                "bit_generator": RNG_BIT_GENERATOR,
                "draw": RANDOM_DRAW,
                "seed_rule": f"PAYLOAD_SEED_BASE + payload_bytes (PAYLOAD_SEED_BASE={PAYLOAD_SEED_BASE})",
            },
        },
        "pipeline_seed_rule": PIPELINE_SEED_RULE,
        "matrix": {
            "kinds": list(kinds),
            "sizes": list(sizes),
            "channels": list(channels),
            "drop_probabilities": list(drops),
            "trials": len(kinds) * len(sizes) * len(channels) * len(drops),
        },
        "channels": {name: dataclasses.asdict(CHANNELS[name]) for name in channels},
        "payloads": payload_records,
        "payload_manifest_sha256": payload_manifest_sha256,
    }

    # -- trials -------------------------------------------------------------
    for kind in kinds:
        for size in sizes:
            data = payloads[(kind, size)]
            digest = payload_hashes[(kind, size)]
            for channel_name in channels:
                for drop in drops:
                    pipeline_seed = 9000 + size + int(drop * 1000)
                    cfg = cfg_with(
                        base,
                        channel=CHANNELS[channel_name],
                        compression=(kind == "text"),
                        seed=pipeline_seed,
                    )
                    meter = ResourceMeter()
                    result = simulate_transfer(
                        data,
                        f"{kind[0]}{size}.bin",
                        cfg,
                        apply_optics=True,
                        drop_probability=drop,
                        seed=pipeline_seed,
                    )
                    resource = meter.sample()

                    timings = result.timings_ms
                    frames_decoded = max(1, result.frames_decoded)
                    projected_s = result.frames_total / cfg.camera.display_fps
                    projected_net_bps = (
                        len(data) * 8.0 / projected_s if projected_s > 0 else 0.0
                    )
                    error_stages = sorted(
                        {str(err.get("stage", "unknown")) for err in result.errors}
                    )

                    ctx.record(
                        config={
                            "payload_kind": kind,
                            "payload_bytes": size,
                            "payload_seed": _payload_seed(kind, size),
                            "channel": channel_name,
                            "drop_probability": drop,
                            "compression": kind == "text",
                            "pipeline_seed": pipeline_seed,
                        },
                        inputs={
                            "payload_sha256": digest,
                            "payload_sha256_matches_manifest": digest
                            == payload_hashes[(kind, size)],
                            "payload_bytes": len(data),
                        },
                        outputs={
                            "success": result.success,
                            "payload_len": result.header.payload_len
                            if result.header
                            else None,
                            "total_packets": result.header.total_packets
                            if result.header
                            else None,
                            "per_packet": result.per_packet,
                            "error_stages": error_stages,
                            "errors": result.errors[:3],
                        },
                        metrics={
                            "success": 1.0 if result.success else 0.0,
                            "payload_bytes": size,
                            "compressed_bytes": result.throughput.payload_bytes,
                            "compression_ratio": result.compression_ratio,
                            "frames_total": result.frames_total,
                            "frames_decoded": result.frames_decoded,
                            "frames_crc_ok": result.frames_crc_ok,
                            "frames_dropped": result.frames_dropped,
                            "frame_loss_rate": result.throughput.frame_loss_rate,
                            "ber": result.ber if result.ber is not None else 1.0,
                            # Throughput (simulated execution and projected screen time)
                            "simulated_wall_s": result.throughput.duration_s,
                            "simulated_net_bps": result.throughput.net_bps,
                            "simulated_gross_bps": result.throughput.gross_bps,
                            "decode_fps_simulated": result.throughput.fps,
                            "projected_screen_s_at_60fps": projected_s,
                            "projected_net_bps_at_60fps": projected_net_bps,
                            # Latency (per decoded frame, from pipeline timings)
                            "latency_spatial_decode_ms_per_frame": timings.get(
                                "spatial_decode", 0.0
                            )
                            / frames_decoded,
                            "latency_total_pipeline_ms": timings.get("total", 0.0),
                            # Reconstruction (reassemble + decompress) and ECC
                            "reconstruction_ms": timings.get("reassembly", 0.0),
                            "ecc_ms": timings.get("ecc", 0.0),
                            "compression_ms": timings.get("compression", 0.0),
                            # Resources for this trial's interval
                            "cpu_percent": resource.cpu_percent,
                            "max_rss_kb": resource.max_rss_kb,
                            "rss_kb": resource.rss_kb,
                            "errors": len(result.errors),
                        },
                        errors=result.errors[:3],
                        notes=(
                            "SIMULATED / SOFTWARE. Simulated wall time is Python "
                            "execution time, not screen time. projected_* assumes "
                            "60 display frames/s. latency_* is measured decode "
                            "latency, reconstruction_ms is reassembly+decompress."
                        ),
                    )

    # -- success and failure accounting ------------------------------------
    rows = ctx.trials
    successes = [t for t in rows if t["outputs"]["success"]]
    failures = [t for t in rows if not t["outputs"]["success"]]

    def _count_by(source: list[dict], key: str, values: tuple) -> dict[str, dict[str, int]]:
        return {
            str(value): {
                "trials": sum(1 for t in rows if t["config"][key] == value),
                "successes": sum(1 for t in source if t["config"][key] == value),
                "failures": sum(
                    1 for t in rows if t["config"][key] == value
                )
                - sum(1 for t in source if t["config"][key] == value),
            }
            for value in values
        }

    failed_trials = [
        {
            "config": t["config"],
            "error_stages": t["outputs"].get("error_stages", []),
            "first_error": t["errors"][0] if t["errors"] else None,
        }
        for t in failures
    ]
    failure_stage_counts: dict[str, int] = {}
    for t in failures:
        for stage in t["outputs"].get("error_stages", []) or ["unknown"]:
            failure_stage_counts[stage] = failure_stage_counts.get(stage, 0) + 1

    verified_hashes = sum(
        1
        for t in rows
        if t["inputs"].get("payload_sha256")
        == payload_hashes[
            (t["config"]["payload_kind"], t["config"]["payload_bytes"])
        ]
    )
    # Independent re-derivation from the recorded generator specification, run
    # after every trial, must reproduce the same bytes.
    recomputed_hashes = sum(
        1
        for t in rows
        if _sha256(
            _payload(t["config"]["payload_kind"], t["config"]["payload_bytes"])
        )
        == t["inputs"].get("payload_sha256")
    )
    outcome_rows = [
        json.dumps(
            {
                "kind": t["config"]["payload_kind"],
                "bytes": t["config"]["payload_bytes"],
                "channel": t["config"]["channel"],
                "drop": t["config"]["drop_probability"],
                "success": bool(t["outputs"]["success"]),
                "frames_total": t["metrics"]["frames_total"],
                "frames_decoded": t["metrics"]["frames_decoded"],
                "frames_crc_ok": t["metrics"]["frames_crc_ok"],
                "frames_dropped": t["metrics"]["frames_dropped"],
                "error_stages": t["outputs"].get("error_stages", []),
            },
            sort_keys=True,
        )
        for t in rows
    ]
    outcome_sha256 = _fingerprint(outcome_rows)

    throughput_rows = [t for t in successes]  # only verified transfers
    ctx.summary = {
        "evidence_source": "SIMULATED / SOFTWARE",
        "simulation_only": True,
        "trials": len(rows),
        "success_rate": len(successes) / len(rows) if rows else 0.0,
        "successes": {
            "count": len(successes),
            "rate": len(successes) / len(rows) if rows else 0.0,
            "by_channel": _count_by(successes, "channel", channels),
            "by_kind": _count_by(successes, "payload_kind", kinds),
            "by_size": _count_by(successes, "payload_bytes", sizes),
        },
        "failures": {
            "count": len(failures),
            "rate": len(failures) / len(rows) if rows else 0.0,
            "by_channel": {
                name: {
                    "trials": sum(1 for t in rows if t["config"]["channel"] == name),
                    "failures": sum(
                        1 for t in failures if t["config"]["channel"] == name
                    ),
                }
                for name in channels
            },
            "by_stage": failure_stage_counts,
            "trials": failed_trials,
        },
        "max_payload_decoded": max(
            (t["config"]["payload_bytes"] for t in successes), default=0
        ),
        "sha256_verification": {
            "trials_hashed": len(rows),
            "verified_against_manifest": verified_hashes,
            "recomputed_from_generator": recomputed_hashes,
            "mismatches": [
                t["config"]
                for t in rows
                if t["inputs"].get("payload_sha256")
                != payload_hashes[
                    (t["config"]["payload_kind"], t["config"]["payload_bytes"])
                ]
            ],
            "payload_manifest_sha256": payload_manifest_sha256,
            "outcome_sha256": outcome_sha256,
        },
        "throughput": {
            "basis": "successful trials only; simulated execution and projected 60 fps screen time",
            "simulated_gross_bps": _aggregate(
                [t["metrics"]["simulated_gross_bps"] for t in throughput_rows]
            ),
            "simulated_net_bps": _aggregate(
                [t["metrics"]["simulated_net_bps"] for t in throughput_rows]
            ),
            "projected_net_bps_at_60fps": _aggregate(
                [t["metrics"]["projected_net_bps_at_60fps"] for t in throughput_rows]
            ),
            "decode_fps_simulated": _aggregate(
                [t["metrics"]["decode_fps_simulated"] for t in throughput_rows]
            ),
            "projected_screen_s_at_60fps": _aggregate(
                [t["metrics"]["projected_screen_s_at_60fps"] for t in throughput_rows]
            ),
        },
        "latency": {
            "basis": "all trials; per-decoded-frame spatial decode time and total pipeline time",
            "spatial_decode_ms_per_frame": _aggregate(
                [t["metrics"]["latency_spatial_decode_ms_per_frame"] for t in rows]
            ),
            "total_pipeline_ms": _aggregate(
                [t["metrics"]["latency_total_pipeline_ms"] for t in rows]
            ),
        },
        "reconstruction_time": {
            "basis": "all trials; reassembly + decompression, and Reed-Solomon ECC",
            "reassembly_plus_decompress_ms": _aggregate(
                [t["metrics"]["reconstruction_ms"] for t in rows]
            ),
            "ecc_ms": _aggregate([t["metrics"]["ecc_ms"] for t in rows]),
            "compression_ms": _aggregate([t["metrics"]["compression_ms"] for t in rows]),
        },
        "resource": {
            "cpu_percent": _aggregate([t["metrics"]["cpu_percent"] for t in rows]),
            "rss_kb_max": max((t["metrics"]["rss_kb"] for t in rows), default=0),
            "peak_rss_kb_max": max((t["metrics"]["max_rss_kb"] for t in rows), default=0),
        },
        "note": (
            "SIMULATED / SOFTWARE. Simulated wall time is Python execution time; "
            "projected screen time = frames / 60 fps. Neither is a physical camera "
            "measurement. All trials, including failures, are retained in "
            "raw/trials.jsonl."
        ),
    }

    by_channel = ctx.summary["successes"]["by_channel"]
    channel_text = ", ".join(
        f"{name} {stats['successes']}/{stats['trials']}" for name, stats in by_channel.items()
    )
    failure_text = (
        "Failures: "
        + ", ".join(
            f"{name} {stats['failures']}/{stats['trials']}"
            for name, stats in ctx.summary["failures"]["by_channel"].items()
            if stats["failures"]
        )
        + (
            f"; stages {', '.join(f'{k}×{v}' for k, v in sorted(failure_stage_counts.items()))}"
            if failure_stage_counts
            else ""
        )
        + "."
        if failures
        else "No failures occurred inside the tested matrix."
    )
    tp = ctx.summary["throughput"]
    lat = ctx.summary["latency"]
    rec = ctx.summary["reconstruction_time"]
    res = ctx.summary["resource"]
    ctx.conclude(
        f"{len(successes)} of {len(rows)} simulated transfers succeeded "
        f"({ctx.summary['success_rate']:.1%}); {len(failures)} failed. "
        f"Successes by channel: {channel_text}. {failure_text} "
        f"All {len(rows)} payload SHA-256 values were checked against the pre-run "
        f"manifest ({verified_hashes}/{len(rows)} matched) and re-derived from the "
        f"recorded generator specification ({recomputed_hashes}/{len(rows)} "
        f"identical); payload manifest {payload_manifest_sha256[:12]}…, outcome "
        f"fingerprint {outcome_sha256[:12]}…. "
        f"Throughput (successful trials only): simulated net "
        f"{tp['simulated_net_bps']['mean']:.1f} bps and projected 60 fps net "
        f"{tp['projected_net_bps_at_60fps']['mean']:.1f} bps. "
        f"Latency: spatial decode {lat['spatial_decode_ms_per_frame']['mean']:.2f} ms "
        f"per decoded frame, total pipeline {lat['total_pipeline_ms']['mean']:.0f} ms "
        f"per trial. Reconstruction: reassembly+decompress "
        f"{rec['reassembly_plus_decompress_ms']['mean']:.2f} ms, RS ECC "
        f"{rec['ecc_ms']['mean']:.2f} ms per trial. Resources: "
        f"{res['cpu_percent']['mean']:.0f}% CPU of one core, peak RSS "
        f"{res['peak_rss_kb_max']} KiB. These are SIMULATED / SOFTWARE results, "
        "not a physical optical transmission benchmark."
    )


SPEC = ExperimentSpec(
    id="E09_end_to_end",
    title="End-to-end simulated transfer",
    hypothesis=(
        "The full pipeline (compression, packetisation, RS, rendering, simulated "
        "channel, spatial decode, reassembly) recovers files under clean/mild/"
        "harsh channels and moderate frame loss, with a measurable failure limit "
        "on a deliberately brutal stress channel."
    ),
    classification="OBSERVED (SIMULATED channel) + THEORETICAL (projected screen time)",
    controlled=("protocol", "layout", "renderer", "decoder", "RS settings", "seed"),
    independent=("payload type/size", "channel severity", "frame-drop probability"),
    dependent=(
        "transfer success",
        "compression ratio",
        "frames decoded/dropped",
        "BER",
        "simulated throughput",
        "projected screen throughput",
        "decode latency",
        "reconstruction time",
        "CPU/memory",
    ),
    procedure=(
        "Generate text and seeded-random payloads at several sizes and hash each one.",
        "Record the payload generator, every seed and every SHA-256 in the run manifest.",
        "Run the complete simulate_transfer pipeline with clean/mild/harsh/brutal channels and 0/3% frame loss.",
        "Record success, per-packet RS statistics, errors, throughput, latency, reconstruction time and resource use for every trial, including failures.",
        "Re-derive each payload hash and fingerprint the payload set and the outcome set.",
        "Separate simulated wall-clock throughput, projected 60 fps screen throughput, decode latency and reconstruction time.",
    ),
    run=run,
)
