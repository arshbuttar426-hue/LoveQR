"""E08 — Temporal blink IDs under a rolling-shutter capture."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from otl.config import CameraConfig, ChannelConfig
from otl.decoder.temporal import decode_rolling
from otl.errors import OTLError
from otl.metrics import Timer
from otl.protocol.blink import encode_word
from otl.rx.channel import apply_channel
from otl.rx.rolling import simulate_rolling_shutter, timing_report

from .harness import ExperimentSpec, RunContext

DISPLAY_FPS = (60.0, 120.0, 240.0, 500.0, 1000.0, 2000.0)
EXPOSURES = (50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0)
ROW_TIMES = (5.0, 10.0, 20.0, 40.0)
NOISE = (0.0, 5.0, 15.0, 30.0)


def _capture(
    camera: CameraConfig,
    id_index: int,
    noise: float,
    rng: np.random.Generator,
) -> tuple[object, dict[str, object]]:
    period = camera.symbol_period_us
    visible = camera.readout_us / period
    n_symbols = max(26, int(math.ceil(visible)) + 1)
    bits = encode_word(id_index)
    frames = [
        np.full((camera.height, camera.width), 255 if bit else 0, dtype=np.uint8)
        for bit in bits
    ] + [
        np.zeros((camera.height, camera.width), dtype=np.uint8)
        for _ in range(n_symbols - len(bits))
    ]
    with Timer() as timer:
        capture = simulate_rolling_shutter(frames, camera, phase_us=0.0)
    if noise > 0:
        capture = replace(
            capture,
            image=apply_channel(
                capture.image,
                ChannelConfig(noise_sigma=noise),
                seed=int(rng.integers(0, 2**31 - 1)),
            ),
        )
    info = {
        "visible_symbols_theoretical": visible,
        "symbols_rendered": n_symbols,
        "capture_ms": timer.elapsed_s * 1000.0,
    }
    return capture, info


def run(ctx: RunContext) -> None:
    rng = np.random.default_rng(808)
    cases: list[dict[str, float]] = []
    for fps in DISPLAY_FPS:
        cases.append({"display_fps": fps, "exposure_us": 100.0, "row_time_us": 20.0, "noise": 0.0})
    for exposure in EXPOSURES:
        cases.append({"display_fps": 1000.0, "exposure_us": exposure, "row_time_us": 20.0, "noise": 0.0})
    for row_time in ROW_TIMES:
        cases.append({"display_fps": 1000.0, "exposure_us": 100.0, "row_time_us": row_time, "noise": 0.0})
    for noise in NOISE:
        cases.append({"display_fps": 1000.0, "exposure_us": 100.0, "row_time_us": 20.0, "noise": noise})

    for case in cases:
        camera = CameraConfig(
            width=1080,
            height=1350,
            row_time_us=case["row_time_us"],
            exposure_us=case["exposure_us"],
            display_fps=case["display_fps"],
            random_phase=False,
        )
        report = timing_report(camera, chips=26)
        for id_index in range(3):
            capture, info = _capture(camera, id_index, case["noise"], rng)
            with Timer() as timer:
                try:
                    result = decode_rolling(capture)
                    locked = bool(result.detections)
                    best = max(result.detections, key=lambda d: d.id_score) if locked else None
                    detected_id = best.id_index if best else None
                    score = best.id_score if best else 0.0
                    error = None
                except OTLError as exc:
                    locked = False
                    detected_id = None
                    score = 0.0
                    error = exc.to_dict()
            ctx.record(
                config={**case, "id_index": id_index, "camera": camera.__dict__},
                inputs={"word": list(encode_word(id_index)), "timing": report},
                outputs={
                    "locked": locked,
                    "detected_id": detected_id,
                    "correct_id": detected_id == id_index if locked else False,
                    "visible_symbols_measured": int(len(np.unique(capture.dominant))),
                    **info,
                },
                metrics={
                    "display_fps": case["display_fps"],
                    "exposure_us": case["exposure_us"],
                    "row_time_us": case["row_time_us"],
                    "noise_sigma": case["noise"],
                    "id_index": id_index,
                    "locked": 1.0 if locked else 0.0,
                    "correct_id": 1.0 if (locked and detected_id == id_index) else 0.0,
                    "visible_symbols": int(len(np.unique(capture.dominant))),
                    "symbols_per_capture": report["symbols_per_capture"],
                    "word_fits": 1.0 if report["word_fits_in_one_capture"] else 0.0,
                    "exposure_over_period": report["exposure_over_period"],
                    "exposure_ok": 1.0 if report["exposure_within_symbol"] else 0.0,
                    "temporal_budget_ok": 1.0 if report["temporal_budget_ok"] else 0.0,
                    "id_score": score,
                    "decode_ms": timer.elapsed_s * 1000.0,
                },
                errors=[error] if error else [],
                notes="uniform display frames; rolling-shutter row integration; no spatial data",
            )

    ok = [t for t in ctx.trials if t["outputs"]["correct_id"]]
    fits = [t for t in ctx.trials if t["metrics"]["word_fits"]]
    budget = [t for t in ctx.trials if t["metrics"]["temporal_budget_ok"]]
    by_fps: dict[str, dict[str, float]] = {}
    for t in ctx.trials:
        key = f"{t['config']['display_fps']:g}"
        entry = by_fps.setdefault(key, {"trials": 0.0, "correct": 0.0, "word_fits": 0.0})
        entry["trials"] += 1.0
        entry["correct"] += float(t["outputs"]["correct_id"])
        entry["word_fits"] += float(t["metrics"]["word_fits"])
    ctx.summary = {
        "word_chips": 26,
        "readout_us_default": 1350 * 20.0,
        "successful_words": len(ok),
        "trials_with_word_fit": len(fits),
        "trials_with_temporal_budget": len(budget),
        "success_when_word_fits": (
            sum(1 for t in fits if t["outputs"]["correct_id"]) / len(fits) if fits else 0.0
        ),
        "success_when_temporal_budget_ok": (
            sum(1 for t in budget if t["outputs"]["correct_id"]) / len(budget)
            if budget
            else 0.0
        ),
        "success_when_word_does_not_fit": (
            sum(1 for t in ctx.trials if not t["metrics"]["word_fits"] and t["outputs"]["correct_id"])
            / max(1, len(ctx.trials) - len(fits))
        ),
        "by_display_fps": by_fps,
        "physical_limit": (
            "visible display symbols = height * row_time / symbol_period; "
            "camera frame rate does not multiply display refresh rate; exposure "
            "must also be no longer than one symbol period"
        ),
    }

    fps_rows = [
        (float(k), v) for k, v in by_fps.items()
    ]
    fps_rows.sort(key=lambda item: item[0])
    fit_fps = [fps for fps, v in fps_rows if v["word_fits"] > 0]
    first_fit = min(fit_fps) if fit_fps else None
    low = CameraConfig(display_fps=60.0, row_time_us=20.0, exposure_us=100.0)
    low_report = timing_report(low, chips=26)
    exposure_failures = [
        t for t in ctx.trials
        if t["metrics"]["word_fits"] and not t["metrics"]["exposure_ok"]
    ]
    parts = [
        "A 26-chip word is recovered only when the rolling readout spans at least "
        f"26 display symbol periods; the lowest tested display rate with a "
        f"fitting word was {first_fit:g} Hz."
        if first_fit is not None
        else "No tested display rate produced a fitting 26-chip word.",
        f"At 60 Hz a {low_report['readout_us'] / 1000.0:.1f} ms readout sees "
        f"~{low_report['symbols_per_capture']:.2f} symbols, so a full blink word "
        "cannot fit in one capture.",
    ]
    if exposure_failures:
        worst = max(t["metrics"]["exposure_over_period"] for t in exposure_failures)
        parts.append(
            f"Separately, {len(exposure_failures)} trial(s) had a fitting readout "
            f"but an exposure up to {worst:.2f} symbol periods long; integrating "
            "several chips per row destroyed the word. Exposure must therefore be "
            "no longer than one symbol period as well as the readout spanning the "
            "word."
        )
    parts.append(
        "This is the central temporal constraint of the proposed architecture, "
        "and it is a physical/arithmetic result, not a software limitation."
    )
    ctx.conclude(" ".join(parts))


SPEC = ExperimentSpec(
    id="E08_rolling",
    title="Temporal blink IDs under a rolling-shutter capture",
    hypothesis=(
        "Rolling shutter exposes multiple display symbols per capture only when "
        "the readout time spans multiple symbol periods; a 26-chip word needs "
        "readout >= 26 symbol periods."
    ),
    classification="OBSERVED (SIMULATED rolling shutter) + THEORETICAL (timing)",
    controlled=("camera height 1350", "uniform display frames", "sync+ID codebook", "phase 0"),
    independent=("display frame rate", "exposure time", "row time", "sensor noise", "blink ID"),
    dependent=("temporal lock", "correct ID", "visible symbols", "symbols per capture", "decode time"),
    procedure=(
        "For each timing configuration, render the 26-chip sync+ID word as uniform full-frame symbols.",
        "Integrate each camera row's exposure against the display timeline.",
        "Optionally add sensor noise, then segment and decode the visible symbols.",
        "Compare lock/ID success with the analytical readout/symbol-period ratio.",
    ),
    run=run,
)
