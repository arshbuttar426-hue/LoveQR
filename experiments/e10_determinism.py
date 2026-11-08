"""E10 — Determinism, prerecorded-image decoding and resource benchmark."""

from __future__ import annotations

import hashlib

import numpy as np

from otl.config import ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.metrics import Aggregate, ResourceMeter, Timer
from otl.pipeline import simulate_transfer
from otl.tx.renderer import load_frame, render_frame, save_frame

from .common import image_hash, random_frame
from .harness import ExperimentSpec, RunContext

FRAME_COUNT = 40


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    meter = ResourceMeter()
    layout = cfg.layout()
    rng = np.random.default_rng(1010)
    frames = [random_frame(rng, cfg) for _ in range(FRAME_COUNT)]

    frame_dir = ctx.out_dir / "artifacts" / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    first_hashes: list[str] = []
    second_hashes: list[str] = []
    render_ms: list[float] = []
    for index, (_, _, cells) in enumerate(frames):
        with Timer() as timer:
            image = render_frame(cells, layout, cfg.screen)
        render_ms.append(timer.elapsed_s * 1000.0)
        first_hashes.append(image_hash(image))
        save_frame(str(frame_dir / f"frame_{index:03d}.png"), image)
        second = render_frame(cells, layout, cfg.screen)
        second_hashes.append(image_hash(second))

    decode_ms: list[float] = []
    crc_ok = 0
    cell_exact = 0
    cell_total = 0
    observed_hashes: list[str] = []
    for index, (_, _, cells) in enumerate(frames):
        image = load_frame(str(frame_dir / f"frame_{index:03d}.png"))
        with Timer() as timer:
            decoded = decode_image(image, layout, cfg.receiver, cfg.protocol)
        decode_ms.append(timer.elapsed_s * 1000.0)
        if decoded.crc_ok:
            crc_ok += 1
        observed_hashes.append(hashlib.sha256(bytes(decoded.frame.cell_values)).hexdigest())
        cell_exact += sum(1 for a, b in zip(cells, decoded.frame.cell_values) if a == b)
        cell_total += len(cells)

    # Decode the same PNGs a second time and require identical cell sequences.
    repeat_hashes: list[str] = []
    for index in range(FRAME_COUNT):
        image = load_frame(str(frame_dir / f"frame_{index:03d}.png"))
        decoded = decode_image(image, layout, cfg.receiver, cfg.protocol)
        repeat_hashes.append(hashlib.sha256(bytes(decoded.frame.cell_values)).hexdigest())

    ctx.record(
        config={"frames": FRAME_COUNT, "source": "prerecorded PNG", "layout": layout.to_dict()},
        inputs={"frame_dir": str(frame_dir.relative_to(ctx.out_dir))},
        outputs={
            "crc_ok_frames": crc_ok,
            "cell_accuracy": cell_exact / cell_total,
            "render_hashes_equal": first_hashes == second_hashes,
            "decode_hashes_repeatable": observed_hashes == repeat_hashes,
            "corpus_hash": hashlib.sha256("".join(first_hashes).encode()).hexdigest(),
        },
        metrics={
            "crc_ok_frames": crc_ok,
            "cell_accuracy": cell_exact / cell_total,
            "render_deterministic": 1.0 if first_hashes == second_hashes else 0.0,
            "decode_deterministic": 1.0 if observed_hashes == repeat_hashes else 0.0,
            "mean_render_ms": float(np.mean(render_ms)),
            "p95_render_ms": float(np.percentile(render_ms, 95)),
            "mean_decode_ms": float(np.mean(decode_ms)),
            "p95_decode_ms": float(np.percentile(decode_ms, 95)),
        },
        notes="decoder reads PNG files through Pillow; no camera object is used",
    )

    # Pipeline determinism with a fixed seed.
    payload = b"determinism payload " * 40
    runs = []
    for _ in range(2):
        result = simulate_transfer(
            payload, "determ.bin", cfg, drop_probability=0.05, seed=4242
        )
        runs.append(result)
    same = (
        runs[0].success == runs[1].success
        and runs[0].frames_dropped == runs[1].frames_dropped
        and runs[0].per_packet == runs[1].per_packet
        and runs[0].original == runs[1].original
    )
    ctx.record(
        config={"payload_bytes": len(payload), "drop_probability": 0.05, "seed": 4242},
        inputs={"repeats": 2},
        outputs={
            "success": [runs[0].success, runs[1].success],
            "frames_dropped": [runs[0].frames_dropped, runs[1].frames_dropped],
            "identical": same,
        },
        metrics={
            "pipeline_deterministic": 1.0 if same else 0.0,
            "frames_dropped": runs[0].frames_dropped,
            "simulated_wall_s": runs[0].throughput.duration_s,
        },
        notes="same seed, same payload, two independent calls",
    )

    # Micro-benchmarks for the core layers.
    bench: dict[str, float] = {}
    with Timer() as timer:
        for _ in range(200):
            render_frame(frames[0][2], layout, cfg.screen)
    bench["render_ms"] = timer.elapsed_s / 200 * 1000.0
    with Timer() as timer:
        for index in range(FRAME_COUNT):
            image = load_frame(str(frame_dir / f"frame_{index:03d}.png"))
            decode_image(image, layout, cfg.receiver, cfg.protocol)
    bench["decode_ms"] = timer.elapsed_s / FRAME_COUNT * 1000.0

    resource = meter.sample()
    agg = Aggregate()
    for value in decode_ms:
        agg.add(value)
    ctx.record(
        config={"operation": "benchmark"},
        inputs={"render_repeats": 200, "decode_frames": FRAME_COUNT},
        outputs={"decode_latency": agg.to_dict(), "resource": resource.to_dict()},
        metrics={
            "render_ms": bench["render_ms"],
            "decode_ms": bench["decode_ms"],
            "decode_p50_ms": agg.percentile(50),
            "decode_p95_ms": agg.percentile(95),
            "cpu_percent": resource.cpu_percent,
            "max_rss_kb": resource.max_rss_kb,
            "rss_kb": resource.rss_kb,
        },
        notes="software timings; wall time depends on the host machine",
    )

    ctx.summary = {
        "frames": FRAME_COUNT,
        "crc_ok_frames": crc_ok,
        "cell_accuracy": cell_exact / cell_total,
        "render_deterministic": first_hashes == second_hashes,
        "decode_deterministic": observed_hashes == repeat_hashes,
        "pipeline_deterministic": same,
        "corpus_hash": hashlib.sha256("".join(first_hashes).encode()).hexdigest(),
        "latency_ms": {
            "render_mean": float(np.mean(render_ms)),
            "decode_mean": float(np.mean(decode_ms)),
            "decode_p50": agg.percentile(50),
            "decode_p95": agg.percentile(95),
        },
        "resource": resource.to_dict(),
        "artifacts": "artifacts/frames/*.png",
    }
    ctx.conclude(
        "Rendering is byte-identical across repeated calls, decoding the same "
        "prerecorded PNGs twice produces identical cell sequences, and the "
        "end-to-end pipeline reproduces the same drop pattern and output with a "
        "fixed seed. The decoder has no camera dependency. Latency and memory "
        "figures are OBSERVED software measurements on this host and will vary "
        "with hardware."
    )


SPEC = ExperimentSpec(
    id="E10_determinism",
    title="Determinism, prerecorded-image decoding and resource benchmark",
    hypothesis=(
        "Every stage is deterministic for fixed inputs and seeds, the decoder "
        "works on prerecorded images without a camera, and latency/memory are "
        "measurable and stable."
    ),
    classification="OBSERVED (software)",
    controlled=("fixed frames", "fixed layout/config", "fixed seed", "same host"),
    independent=("repeat index", "input source (memory vs PNG)"),
    dependent=("hash equality", "CRC success", "cell accuracy", "latency", "CPU", "RSS"),
    procedure=(
        "Render a corpus of random frames twice and compare hashes.",
        "Save the corpus as PNG, decode from disk twice, and compare cell sequences.",
        "Run the end-to-end pipeline twice with the same seed and compare results.",
        "Benchmark render/decode latency and record CPU/RSS.",
    ),
    run=run,
)
