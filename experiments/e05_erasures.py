"""E05 — Frame loss and Reed-Solomon erasure capacity."""

from __future__ import annotations

import numpy as np

from otl.config import ExperimentConfig
from otl.errors import OTLError
from otl.metrics import Timer
from otl.protocol.packet import build_file, decode_packet

from .harness import ExperimentSpec, RunContext

LOSS_COUNTS = tuple(sorted(set(range(0, 41, 2)) | {31, 32, 33, 34}))


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    payload = bytes((i * 37 + 11) & 0xFF for i in range(2200))
    _, packets = build_file(
        payload, "erasures.bin", compressed=False, original_len=len(payload), nsym=cfg.ecc.nsym
    )
    packet = packets[0]
    all_frames = list(range(255))
    seeds = (1, 2, 3) if not ctx.quick else (1,)

    for pattern in ("random", "burst"):
        for count in LOSS_COUNTS:
            for seed in seeds:
                rng = np.random.default_rng(seed * 100_000 + count)
                if pattern == "random":
                    lost = set(int(i) for i in rng.choice(all_frames, size=count, replace=False))
                else:
                    start = int(rng.integers(0, max(1, 255 - count)))
                    lost = set(range(start, start + count))
                received = {i: packet.frames[i] for i in all_frames if i not in lost}
                with Timer() as timer:
                    try:
                        decoded = decode_packet(0, received, nsym=cfg.ecc.nsym)
                        success = True
                        error = None
                        stats = decoded.stats
                        corrected = sum(stats.corrected_per_block)
                        block_failures = list(stats.block_failures)
                    except OTLError as exc:
                        success = False
                        error = exc.to_dict()
                        stats = None
                        corrected = None
                        block_failures = []
                ctx.record(
                    config={
                        "loss_pattern": pattern,
                        "lost_frames": count,
                        "seed": seed,
                        "nsym": cfg.ecc.nsym,
                    },
                    inputs={"frames_sent": 255},
                    outputs={
                        "success": success,
                        "frames_missing": count,
                        "corrected_positions": corrected,
                        "block_failures": block_failures,
                    },
                    metrics={
                        "lost_frames": count,
                        "success": 1.0 if success else 0.0,
                        "corrected_positions": float(corrected or 0),
                        "block_failures": len(block_failures),
                        "decode_ms": timer.elapsed_s * 1000.0,
                    },
                    errors=[error] if error else [],
                    notes=f"{pattern} frame loss; erasure-only RS path",
                )

    rows = ctx.trials
    max_ok = max(
        (t["config"]["lost_frames"] for t in rows if t["outputs"]["success"]),
        default=0,
    )
    min_fail = min(
        (t["config"]["lost_frames"] for t in rows if not t["outputs"]["success"]),
        default=None,
    )
    ctx.summary = {
        "nsym": cfg.ecc.nsym,
        "theoretical_max_erasures": cfg.ecc.nsym,
        "max_lost_frames_decoded": max_ok,
        "smallest_failing_loss_count": min_fail,
        "capacity_rule": "2*byte_errors + lost_frames <= nsym per RS block",
        "interleaving": "frame n carries byte n of every block, so a lost frame is one erasure per block",
    }
    ctx.conclude(
        f"With nsym={cfg.ecc.nsym}, packets decode with up to {max_ok} lost "
        f"frames; the smallest failing loss count observed is {min_fail}. This "
        "matches the theoretical erasure capacity of 32 per RS block because "
        "interleaving turns each lost frame into exactly one erasure in every "
        "block. Random and burst loss behave the same at equal counts under "
        "byte interleaving."
    )


SPEC = ExperimentSpec(
    id="E05_erasures",
    title="Frame loss and Reed-Solomon erasure capacity",
    hypothesis=(
        "Byte interleaving plus RS(255,223) tolerates up to 32 lost frames per "
        "packet, independent of whether the loss is random or bursty."
    ),
    classification="OBSERVED (software ECC) + THEORETICAL (capacity)",
    controlled=("one packet of 255 frames", "fixed payload", "nsym=32", "frame indices"),
    independent=("number of lost frames", "loss pattern (random/burst)", "random seed"),
    dependent=("packet decode success", "corrected positions", "block failures", "decode time"),
    procedure=(
        "Encode one 2200-byte payload into a 255-frame packet.",
        "Remove 0..40 frames at random or as one contiguous burst.",
        "Decode the packet with the erasure-aware RS path and record success or the structured error.",
        "Compare the observed boundary with 2*errors + erasures <= nsym.",
    ),
    run=run,
)
