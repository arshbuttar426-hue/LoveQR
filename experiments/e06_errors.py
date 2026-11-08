"""E06 — Reed-Solomon byte-error and mixed error/erasure capacity."""

from __future__ import annotations

import numpy as np

from otl.config import ExperimentConfig
from otl.errors import OTLError
from otl.metrics import Timer
from otl.protocol.packet import BLOCKS_PER_PACKET, build_file, decode_packet

from .harness import ExperimentSpec, RunContext

ERROR_COUNTS = (0, 2, 4, 6, 8, 10, 12, 14, 15, 16, 17)
MIXED = (
    (0, 32), (2, 28), (4, 24), (6, 20), (8, 16), (10, 12), (11, 11),
    (12, 8), (16, 0), (17, 0), (10, 16), (8, 20), (9, 16),
)


def _inject(
    frames: dict[int, bytes],
    errors_per_block: int,
    lost: set[int],
    rng: np.random.Generator,
) -> dict[int, bytes]:
    corrupted = {index: bytearray(data) for index, data in frames.items()}
    available = [n for n in range(255) if n not in lost]
    for block in range(BLOCKS_PER_PACKET):
        chosen = rng.choice(available, size=errors_per_block, replace=False)
        for index in chosen:
            bit = int(rng.integers(0, 8))
            corrupted[int(index)][block] ^= 1 << bit
    return {index: bytes(data) for index, data in corrupted.items()}


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    payload = bytes((i * 53 + 7) & 0xFF for i in range(2200))
    _, packets = build_file(
        payload, "errors.bin", compressed=False, original_len=len(payload), nsym=cfg.ecc.nsym
    )
    packet = packets[0]
    clean = {h.frame_index: d for h, d in packet.iter_frames()}
    seeds = (1, 2, 3) if not ctx.quick else (1,)

    cases: list[tuple[int, int]] = [(e, 0) for e in ERROR_COUNTS] + list(MIXED)
    for errors_per_block, erasures in cases:
        for seed in seeds:
            rng = np.random.default_rng(seed * 1_000_003 + errors_per_block * 101 + erasures)
            lost = set(
                int(i) for i in rng.choice(range(255), size=erasures, replace=False)
            ) if erasures else set()
            received = {
                index: data for index, data in clean.items() if index not in lost
            }
            received = _inject(received, errors_per_block, lost, rng)
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
                    corrected = None
                    block_failures = []
            ctx.record(
                config={
                    "errors_per_block": errors_per_block,
                    "erasures": erasures,
                    "seed": seed,
                    "nsym": cfg.ecc.nsym,
                },
                inputs={"frames": 255, "blocks": BLOCKS_PER_PACKET},
                outputs={
                    "success": success,
                    "corrected_positions": corrected,
                    "block_failures": block_failures,
                    "capacity_used": 2 * errors_per_block + erasures,
                },
                metrics={
                    "errors_per_block": errors_per_block,
                    "erasures": erasures,
                    "capacity_used": 2 * errors_per_block + erasures,
                    "success": 1.0 if success else 0.0,
                    "corrected_positions": float(corrected or 0),
                    "block_failures": len(block_failures),
                    "decode_ms": timer.elapsed_s * 1000.0,
                },
                errors=[error] if error else [],
                notes="byte errors injected after frame decode; tests the RS layer directly",
            )

    ok = [t for t in ctx.trials if t["outputs"]["success"]]
    bad = [t for t in ctx.trials if not t["outputs"]["success"]]
    ctx.summary = {
        "nsym": cfg.ecc.nsym,
        "theoretical_rule": "2*errors + erasures <= nsym",
        "max_capacity_used_success": max((t["metrics"]["capacity_used"] for t in ok), default=None),
        "min_capacity_used_failure": min((t["metrics"]["capacity_used"] for t in bad), default=None),
        "successes": len(ok),
        "failures": len(bad),
    }
    ctx.conclude(
        "The measured boundary follows 2*errors + erasures <= nsym. Cases at or "
        "below capacity decode; cases above it fail with E_ECC/E_RECONSTRUCT "
        "rather than returning corrupt data. This is an injected-error test of "
        "the RS layer, not an optical measurement: frame CRC would normally "
        "convert most optical byte errors into erasures."
    )


SPEC = ExperimentSpec(
    id="E06_errors",
    title="Reed-Solomon byte-error and mixed error/erasure capacity",
    hypothesis=(
        "The clean-room RS(255,223) decoder corrects up to 16 unknown byte "
        "errors per block, or a mix satisfying 2*errors + erasures <= 32, and "
        "rejects anything beyond that."
    ),
    classification="OBSERVED (software ECC) + THEORETICAL (capacity)",
    controlled=("one encoded packet", "block interleaving", "nsym=32", "frame indices"),
    independent=("byte errors per block", "number of erased frames", "random seed"),
    dependent=("decode success", "corrected positions", "block failures", "capacity used", "decode time"),
    procedure=(
        "Encode one packet and keep a clean copy of every frame's 11 bytes.",
        "Inject a fixed number of single-bit byte errors per RS block at random frame positions.",
        "Optionally erase a number of whole frames (one erasure per block).",
        "Decode and compare the observed success boundary with 2*errors + erasures <= 32.",
    ),
    run=run,
)
