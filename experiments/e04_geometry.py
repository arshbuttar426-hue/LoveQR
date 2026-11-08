"""E04 — Resolution (distance proxy) and perspective (angle proxy)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from otl.config import ChannelConfig, ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.errors import OTLError
from otl.metrics import Timer
from otl.rx.channel import apply_channel
from otl.tx.renderer import render_frame

from .common import cell_bit_error_rate, downsample_roundtrip, random_frame
from .harness import ExperimentSpec, RunContext

SCALES = (1.0, 0.75, 0.5, 0.35, 0.25, 0.15, 0.10, 0.06, 0.04, 0.03, 0.02)
PERSPECTIVES = (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.16, 0.20, 0.25)


def _trial(
    ctx: RunContext,
    *,
    kind: str,
    value: float,
    frames: int,
    cfg: ExperimentConfig,
    rng: np.random.Generator,
) -> None:
    layout = cfg.layout()
    crc_ok = 0
    cell_exact = 0
    cell_total = 0
    bit_rates: list[float] = []
    decode_ms: list[float] = []
    failures: list[dict[str, object]] = []
    fiducial_methods: list[str] = []
    for _ in range(frames):
        _, _, cells = random_frame(rng, cfg)
        image = render_frame(cells, layout, cfg.screen)
        if kind == "resolution":
            captured = downsample_roundtrip(image, value)
        else:
            captured = apply_channel(
                image, replace(ChannelConfig(), perspective=value), seed=int(rng.integers(0, 2**31))
            )
        with Timer() as timer:
            try:
                decoded = decode_image(captured, layout, cfg.receiver, cfg.protocol)
            except OTLError as exc:
                failures.append(exc.to_dict())
                decode_ms.append(timer.elapsed_s * 1000.0)
                continue
        decode_ms.append(timer.elapsed_s * 1000.0)
        fiducial_methods.append(decoded.fiducials.method)
        if decoded.crc_ok:
            crc_ok += 1
        observed = decoded.frame.cell_values
        cell_exact += sum(1 for a, b in zip(cells, observed) if a == b)
        cell_total += len(cells)
        bit_rates.append(cell_bit_error_rate(cells, observed))

    ctx.record(
        config={"kind": kind, "value": value, "frames": frames},
        inputs={"cell_px": layout.cell_px},
        outputs={
            "crc_ok_frames": crc_ok,
            "detection_failures": len(failures),
            "cell_accuracy": cell_exact / cell_total if cell_total else 0.0,
        },
        metrics={
            "kind": kind,
            "value": float(value),
            "effective_cell_px": layout.cell_px * value if kind == "resolution" else layout.cell_px,
            "success_rate": crc_ok / frames,
            "detection_failure_rate": len(failures) / frames,
            "cell_accuracy": cell_exact / cell_total if cell_total else 0.0,
            "mean_cell_bit_error_rate": float(np.mean(bit_rates)) if bit_rates else 1.0,
            "mean_decode_ms": float(np.mean(decode_ms)),
        },
        errors=failures[:2],
        notes=(
            "distance proxy: downscale then restore canvas size"
            if kind == "resolution"
            else "angle proxy: synthetic perspective warp; not a true rotation"
        ),
    )


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    rng = np.random.default_rng(404)
    frames = 4 if ctx.quick else 12
    for scale in SCALES:
        _trial(ctx, kind="resolution", value=scale, frames=frames, cfg=cfg, rng=rng)
    for amount in PERSPECTIVES:
        _trial(ctx, kind="perspective", value=amount, frames=frames, cfg=cfg, rng=rng)

    summary: dict[str, object] = {"frames_per_point": frames}
    for kind in ("resolution", "perspective"):
        rows = [t for t in ctx.trials if t["config"]["kind"] == kind]
        summary[kind] = [
            {
                "value": row["config"]["value"],
                "success_rate": row["metrics"]["success_rate"],
                "cell_accuracy": row["metrics"]["cell_accuracy"],
                "effective_cell_px": row["metrics"]["effective_cell_px"],
            }
            for row in rows
        ]
    ctx.summary = summary

    def _boundary(kind: str, *, lower_is_harder: bool) -> dict[str, object]:
        rows = sorted(
            (t for t in ctx.trials if t["config"]["kind"] == kind),
            key=lambda t: float(t["config"]["value"]),
        )
        failing = [t for t in rows if t["metrics"]["success_rate"] < 1.0]
        ok = [t for t in rows if t["metrics"]["success_rate"] >= 1.0]
        if lower_is_harder:
            hardest_ok = min(ok, key=lambda t: float(t["config"]["value"])) if ok else None
            first_fail = max(failing, key=lambda t: float(t["config"]["value"])) if failing else None
        else:
            hardest_ok = max(ok, key=lambda t: float(t["config"]["value"])) if ok else None
            first_fail = min(failing, key=lambda t: float(t["config"]["value"])) if failing else None
        return {
            "tested_values": [float(t["config"]["value"]) for t in rows],
            "last_full_success_value": (
                float(hardest_ok["config"]["value"]) if hardest_ok else None
            ),
            "last_full_success_cell_px": (
                float(hardest_ok["metrics"]["effective_cell_px"]) if hardest_ok else None
            ),
            "first_failing_value": (
                float(first_fail["config"]["value"]) if first_fail else None
            ),
            "first_failing_cell_px": (
                float(first_fail["metrics"]["effective_cell_px"]) if first_fail else None
            ),
        }

    resolution = _boundary("resolution", lower_is_harder=True)
    perspective = _boundary("perspective", lower_is_harder=False)
    ctx.summary["resolution_boundary"] = resolution
    ctx.summary["perspective_boundary"] = perspective
    if resolution["first_failing_value"] is None:
        res_text = (
            "Resolution did not reach a failure inside the tested range "
            f"(down to {min(SCALES):g} of canonical size, "
            f"{resolution['last_full_success_cell_px']:.1f} effective px per cell)."
        )
    else:
        res_text = (
            "The last fully successful downscale was "
            f"{resolution['last_full_success_value']:g} "
            f"({resolution['last_full_success_cell_px']:.1f} effective px per "
            f"cell) and the first failure was {resolution['first_failing_value']:g} "
            f"({resolution['first_failing_cell_px']:.1f} px per cell)."
        )
    if perspective["first_failing_value"] is None:
        persp_text = (
            "Perspective did not reach a failure inside the tested range "
            f"(up to {max(PERSPECTIVES):g})."
        )
    else:
        persp_text = (
            "Perspective stayed correct up to "
            f"{perspective['last_full_success_value']:g} and first failed at "
            f"{perspective['first_failing_value']:g}."
        )
    ctx.conclude(
        f"{res_text} {persp_text} Resolution loss makes triangle sampling windows "
        "overlap pattern boundaries; perspective is limited by the fiducial "
        "detector's fixed area/aspect gates and quadrant assumption, which are "
        "tuned for a cropped screen. The exact crossing points are in the "
        "per-trial CSV. The perspective sweep is an angle proxy, not a "
        "measurement of a real phone at a real angle."
    )


SPEC = ExperimentSpec(
    id="E04_geometry",
    title="Resolution (distance proxy) and perspective (angle proxy)",
    hypothesis=(
        "Spatial decoding tolerates moderate resolution loss and perspective, "
        "with a measurable boundary set by cell size and the fiducial detector."
    ),
    classification="OBSERVED (SIMULATED channel)",
    controlled=("clean optical channel", "canonical layout", "random frames", "decoder settings"),
    independent=("downscale factor", "perspective amount"),
    dependent=("CRC success rate", "cell accuracy", "cell bit error rate", "detection failures", "decode time"),
    procedure=(
        "Render random frames at the canonical 1080x1350 canvas.",
        "Apply either a downscale/upscale resolution proxy or a perspective warp.",
        "Decode and compare with ground truth, recording detection failures separately.",
        "Report success and accuracy against effective cell size / perspective amount.",
    ),
    run=run,
)
