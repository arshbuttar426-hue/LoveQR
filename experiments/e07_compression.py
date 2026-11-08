"""E07 — Shared instruction dictionary (OTL1) compression effectiveness."""

from __future__ import annotations

import hashlib
import json
import zlib

import numpy as np

from otl.compress.dictionary import compress, decompress
from otl.config import ExperimentConfig
from otl.metrics import Timer
from otl.protocol.packet import plan_total_packets

from .harness import ExperimentSpec, RunContext

TEXT = (
    "Optical data transmission uses a screen as the transmitter and a camera as "
    "the receiver. Rolling shutter, spatial patterns, error correction and "
    "compression all interact. "
)


def _repeat_to(data: bytes, size: int) -> bytes:
    return (data * (size // max(1, len(data)) + 1))[:size]


def _corpus(size: int) -> dict[str, bytes]:
    """Build one corpus at exactly ``size`` bytes.

    ``random`` and ``sparse_binary`` are generated fresh for every size.  The
    earlier version generated one 4096-byte block and repeated it, which made
    the 16384-byte "random" sample compressible by block repetition and
    inflated its ratio.  Structured corpora are repeated deliberately: that is
    the kind of redundancy the shared dictionary is meant to exploit.
    """
    rng = np.random.default_rng(707 + size)
    text = _repeat_to(TEXT.encode("utf-8"), size)
    csv = _repeat_to(
        (
            "id,name,value,note\n"
            + "".join(f"{i},item_{i},{i * 17 % 997},row {i}\n" for i in range(400))
        ).encode("utf-8"),
        size,
    )
    code = _repeat_to(
        (
            "def f(x):\n"
            "    total = 0\n"
            "    for value in x:\n"
            "        total += value * 2\n"
            "    return total\n\n"
        ).encode("utf-8"),
        size,
    )
    doc = _repeat_to(
        json.dumps(
            {
                "protocol": "OTL",
                "cells": 30,
                "bits_per_cell": 4,
                "frames": 255,
                "rs": {"n": 255, "k": 223, "nsym": 32},
                "notes": ["spatial", "temporal", "compression"],
            },
            indent=2,
        ).encode("utf-8"),
        size,
    )
    sparse = bytearray(size)
    for index in rng.choice(size, size=min(120, size), replace=False):
        sparse[int(index)] = int(rng.integers(1, 256))
    return {
        "zeros": bytes(size),
        "repeat_abcd": _repeat_to(b"ABCD", size),
        "alternating": _repeat_to(b"\x00\xff", size),
        "text": text,
        "csv": csv,
        "source_code": code,
        "json": doc,
        "sparse_binary": bytes(sparse),
        "random": bytes(int(b) for b in rng.integers(0, 256, size=size)),
        "inverted_text": bytes(255 - b for b in text),
    }


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    sizes = (512, 4096) if ctx.quick else (512, 4096, 16384)
    try:
        import zstandard

        zstd_available = True
    except Exception:  # pragma: no cover
        zstandard = None
        zstd_available = False

    for size in sizes:
        corpus = _corpus(size)
        for name, sample in corpus.items():
            with Timer() as encode_timer:
                packed, stats = compress(sample, cfg.compression)
            with Timer() as decode_timer:
                restored = decompress(packed)
            assert restored == sample
            zlib_ratio = len(sample) / len(zlib.compress(sample, 9)) if sample else 1.0
            zstd_ratio = None
            if zstd_available:
                zstd_ratio = len(sample) / len(zstandard.ZstdCompressor(level=9).compress(sample))
            ctx.record(
                config={
                    "corpus": name,
                    "bytes": size,
                    "compression": cfg.compression.__dict__,
                    "zstd_available": zstd_available,
                },
                inputs={"sha256_prefix": hashlib.sha256(sample).hexdigest()[:16]},
                outputs={
                    "otl1_bytes": len(packed),
                    "roundtrip": restored == sample,
                    "opcodes": stats.to_dict()["ops"],
                    "packets_needed": plan_total_packets(len(packed)),
                },
                metrics={
                    "corpus": name,
                    "bytes": size,
                    "otl1_ratio": stats.ratio,
                    "zlib_ratio": zlib_ratio,
                    "zstd_ratio": zstd_ratio if zstd_ratio is not None else 0.0,
                    "encode_ms": encode_timer.elapsed_s * 1000.0,
                    "decode_ms": decode_timer.elapsed_s * 1000.0,
                    "packets_needed": plan_total_packets(len(packed)),
                },
                notes="deterministic OTL1 encoder; zlib/zstd are reference points only",
            )

    by_corpus: dict[str, list[float]] = {}
    for trial in ctx.trials:
        by_corpus.setdefault(str(trial["config"]["corpus"]), []).append(
            float(trial["metrics"]["otl1_ratio"])
        )
    random_ratios = [
        float(t["metrics"]["otl1_ratio"])
        for t in ctx.trials
        if t["config"]["corpus"] == "random"
    ]
    ctx.summary = {
        "container": "OTL1",
        "opcodes": ["LIT", "REPEAT", "COPY", "INVERT", "SEQUENCE"],
        "mean_ratio_by_corpus": {
            key: float(np.mean(values)) for key, values in sorted(by_corpus.items())
        },
        "random_ratio_mean": float(np.mean(random_ratios)) if random_ratios else None,
        "random_ratio_min": float(np.min(random_ratios)) if random_ratios else None,
        "random_ratio_max": float(np.max(random_ratios)) if random_ratios else None,
        "zstd_available": zstd_available,
        "note": (
            "OTL1 is a deterministic, dependency-free dictionary codec designed "
            "for the on-screen instruction set; zlib/zstd numbers are references, "
            "not part of the protocol. Each size is generated independently, so "
            "the random corpus is not compressible by block repetition."
        ),
    }
    random_text = (
        f"{ctx.summary['random_ratio_mean']:.3f} "
        f"(range {ctx.summary['random_ratio_min']:.3f}–{ctx.summary['random_ratio_max']:.3f})"
        if random_ratios
        else "not measured"
    )
    best = max(by_corpus.items(), key=lambda item: float(np.mean(item[1])))
    ctx.conclude(
        f"OTL1 compresses repetitive, textual and structured payloads strongly "
        f"(highest mean ratio: {best[0]} at {float(np.mean(best[1])):.1f}×), "
        f"leaves incompressible random data at roughly unit ratio "
        f"(mean {random_text}), and always round-trips byte-exactly. Because the "
        "compressed payload determines the number of packets, compression "
        "directly reduces screen time. OTL1 does not claim to beat zlib/zstd on "
        "general data; its purpose is a small, deterministic, inspectable "
        "instruction stream."
    )


SPEC = ExperimentSpec(
    id="E07_compression",
    title="Shared instruction dictionary (OTL1) compression effectiveness",
    hypothesis=(
        "A small deterministic LIT/REPEAT/COPY/INVERT/SEQUENCE codec reduces "
        "screen time for structured payloads while remaining byte-exact and "
        "cheap enough for the transmitter."
    ),
    classification="OBSERVED (software)",
    controlled=("OTL1 encoder settings", "corpus contents", "payload sizes"),
    independent=("corpus type", "payload size"),
    dependent=("compression ratio", "encode/decode time", "opcode counts", "packets needed"),
    procedure=(
        "Build a deterministic corpus of text, CSV, code, JSON, sparse, repeated, alternating and random bytes.",
        "Compress at 512, 4096 and 16384 bytes with the OTL1 encoder.",
        "Decompress and verify byte-exact round-trip.",
        "Record ratio, timings, opcode mix and the number of packets the compressed payload needs.",
    ),
    run=run,
)
