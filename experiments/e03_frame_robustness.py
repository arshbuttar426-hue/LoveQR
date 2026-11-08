"""E03 — Single-frame decode robustness sweep."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from otl.config import ChannelConfig, ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.errors import OTLError
from otl.metrics import Timer
from otl.rx.channel import apply_channel
from otl.tx.renderer import render_frame

from .common import cell_bit_error_rate, cell_error_rate, random_frame
from .harness import ExperimentSpec, RunContext

SWEEPS: dict[str, tuple[float, ...]] = {
    "blur_sigma": (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0),
    "noise_sigma": (0.0, 2.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0),
    "jpeg_quality": (100, 90, 75, 60, 40, 25, 10, 5),
    "ambient": (0.0, 10.0, 25.0, 40.0, 60.0, 90.0, 120.0, 160.0, 200.0),
    "brightness": (1.0, 0.9, 0.8, 0.65, 0.5, 0.35, 0.25, 0.15, 0.08),
    "perspective": (0.0, 0.01, 0.02, 0.05, 0.08, 0.12, 0.18, 0.25),
    "vignette": (0.0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9),
    "gamma": (1.0, 1.1, 1.25, 1.5, 1.8, 2.2, 2.8),
}


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    layout = cfg.layout()
    rng = np.random.default_rng(303)
    per_level = 4 if ctx.quick else 12

    for parameter, values in SWEEPS.items():
        for value in values:
            channel = replace(ChannelConfig(), **{parameter: value})
            crc_ok = 0
            cell_exact = 0
            cell_total = 0
            bit_rates: list[float] = []
            confidences: list[float] = []
            contrasts: list[float] = []
            decode_ms: list[float] = []
            failures: list[dict[str, object]] = []
            for _ in range(per_level):
                _, _, cells = random_frame(rng, cfg)
                image = render_frame(cells, layout, cfg.screen)
                captured = apply_channel(image, channel, seed=int(rng.integers(0, 2**31 - 1)))
                with Timer() as timer:
                    try:
                        decoded = decode_image(captured, layout, cfg.receiver, cfg.protocol)
                    except OTLError as exc:
                        failures.append(exc.to_dict())
                        decode_ms.append(timer.elapsed_s * 1000.0)
                        continue
                decode_ms.append(timer.elapsed_s * 1000.0)
                if decoded.crc_ok:
                    crc_ok += 1
                observed = decoded.frame.cell_values
                cell_exact += sum(1 for a, b in zip(cells, observed) if a == b)
                cell_total += len(cells)
                bit_rates.append(cell_bit_error_rate(cells, observed))
                confidences.append(decoded.observation.confidence)
                contrasts.append(decoded.observation.contrast)

            success_rate = crc_ok / per_level
            ctx.record(
                config={"parameter": parameter, "value": value, "channel": channel.__dict__},
                inputs={"frames": per_level, "seed": cfg.seed},
                outputs={
                    "crc_ok_frames": crc_ok,
                    "detection_failures": len(failures),
                    "cell_accuracy": cell_exact / cell_total if cell_total else 0.0,
                },
                metrics={
                    "parameter": parameter,
                    "value": float(value),
                    "success_rate": success_rate,
                    "detection_failure_rate": len(failures) / per_level,
                    "cell_accuracy": cell_exact / cell_total if cell_total else 0.0,
                    "mean_cell_bit_error_rate": float(np.mean(bit_rates)) if bit_rates else 1.0,
                    "mean_confidence": float(np.mean(confidences)) if confidences else 0.0,
                    "mean_contrast": float(np.mean(contrasts)) if contrasts else 0.0,
                    "mean_decode_ms": float(np.mean(decode_ms)),
                },
                errors=failures[:2],
                notes="random frame per trial; CRC-16 is the success criterion",
            )

    by_parameter: dict[str, list[float]] = {}
    for trial in ctx.trials:
        by_parameter.setdefault(str(trial["config"]["parameter"]), []).append(
            float(trial["metrics"]["success_rate"])
        )
    ctx.summary = {
        "frames_per_level": per_level,
        "parameters": {
            key: {"mean_success_rate": float(np.mean(vals)), "min_success_rate": float(np.min(vals))}
            for key, vals in sorted(by_parameter.items())
        },
        "success_rule": "frame CRC-16 matches after spatial decode",
    }
    # Report only what the sweep actually measured: which parameters reached a
    # failure boundary, and at which level the first failure appeared.
    # For JPEG quality and brightness a *lower* value is harder; every other
    # parameter gets harder as it increases.  The boundary is the failing level
    # closest to the successful region.
    lower_is_harder = {"jpeg_quality", "brightness"}
    boundaries: dict[str, dict[str, object]] = {}
    for parameter in SWEEPS:
        rows = sorted(
            (t for t in ctx.trials if t["config"]["parameter"] == parameter),
            key=lambda t: float(t["config"]["value"]),
        )
        failing = [t for t in rows if t["metrics"]["success_rate"] < 1.0]
        ok = [t for t in rows if t["metrics"]["success_rate"] >= 1.0]
        if failing:
            first = (
                max(failing, key=lambda t: float(t["config"]["value"]))
                if parameter in lower_is_harder
                else min(failing, key=lambda t: float(t["config"]["value"]))
            )
            boundary = {
                "first_failing_value": float(first["config"]["value"]),
                "success_rate_at_first_failure": float(first["metrics"]["success_rate"]),
                "min_success_rate": float(min(t["metrics"]["success_rate"] for t in rows)),
            }
        else:
            boundary = {
                "first_failing_value": None,
                "success_rate_at_first_failure": None,
                "min_success_rate": 1.0,
            }
        if ok:
            hardest_ok = (
                min(ok, key=lambda t: float(t["config"]["value"]))
                if parameter in lower_is_harder
                else max(ok, key=lambda t: float(t["config"]["value"]))
            )
            boundary["last_full_success_value"] = float(hardest_ok["config"]["value"])
        else:
            boundary["last_full_success_value"] = None
        boundaries[parameter] = boundary
    ctx.summary["failure_boundaries"] = boundaries
    found = [k for k, v in boundaries.items() if v["first_failing_value"] is not None]
    not_found = [k for k in boundaries if k not in found]
    if found:
        detail = "; ".join(
            f"{k} first failed at {boundaries[k]['first_failing_value']:g}"
            for k in found
        )
        outcome = (
            f"A failure boundary was measured for {len(found)} of "
            f"{len(boundaries)} parameters ({detail})."
        )
        if not_found:
            outcome += (
                " No failure was reached within the tested range for "
                f"{', '.join(not_found)}; the per-frame photometric calibration "
                "makes global brightness, gamma and ambient offset largely "
                "irrelevant until contrast is destroyed."
            )
    else:
        outcome = (
            "No parameter reached a CRC failure within the tested range, so this "
            "sweep did not locate a single-frame failure boundary; the values "
            "tested are still upper bounds on tolerated degradation."
        )
    ctx.conclude(
        f"{outcome} Blur mixes triangle interiors, noise perturbs the per-cell "
        "threshold, JPEG creates block artefacts, perspective stresses fiducial "
        "detection, and vignetting reduces corner contrast. These are SIMULATED "
        "observations, not physical camera results; the exact crossing points "
        "are in processed/summary.csv."
    )


SPEC = ExperimentSpec(
    id="E03_frame_robustness",
    title="Single-frame decode robustness sweep",
    hypothesis=(
        "One 120-bit frame can be recovered under moderate blur, noise, JPEG, "
        "ambient light, brightness, perspective and vignetting, with a "
        "parameter-dependent failure boundary."
    ),
    classification="OBSERVED (SIMULATED channel)",
    controlled=("random frame contents", "layout", "decoder settings", "frame count per level"),
    independent=(
        "blur sigma",
        "noise sigma",
        "JPEG quality",
        "ambient offset",
        "brightness",
        "perspective",
        "vignette",
        "gamma",
    ),
    dependent=("CRC success rate", "cell accuracy", "cell bit error rate", "confidence", "decode time"),
    procedure=(
        "Generate random valid frames and render each to the canonical screen.",
        "Apply one channel parameter at a time over a fixed sweep, with seeded noise.",
        "Decode every capture and compare header/data/CRC and cell values with ground truth.",
        "Aggregate success and error rates per parameter level.",
    ),
    run=run,
)
