"""E02 — Separability of the 16 four-triangle cell patterns."""

from __future__ import annotations

import numpy as np

from otl.codec.patterns import alphabet_manifest, pattern_distance, pattern_values
from otl.config import ExperimentConfig
from otl.decoder.spatial import decode_image
from otl.metrics import Timer
from otl.rx.channel import apply_channel
from otl.tx.renderer import render_frame
from otl.types import PatternSet

from .common import CHANNELS, cell_bit_error_rate, cell_error_rate, random_frame
from .harness import ExperimentSpec, RunContext

SEVERITIES = ("clean", "mild", "harsh", "extreme", "brutal")
TARGET_POSITIONS = tuple(range(0, 30, 2))  # 15 target cells, 15 random distractors


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    layout = cfg.layout()
    rng = np.random.default_rng(20261108)
    alphabet = alphabet_manifest(PatternSet.FULL16)

    for pattern in pattern_values(PatternSet.FULL16):
        for severity in SEVERITIES:
            channel = CHANNELS[severity]
            repeats = 2 if ctx.quick else 4
            accuracies: list[float] = []
            bit_rates: list[float] = []
            confidences: list[float] = []
            margins: list[float] = []
            decode_ms: list[float] = []
            for _ in range(repeats):
                _, _, base = random_frame(rng, cfg)
                cells = list(base)
                for position in TARGET_POSITIONS:
                    cells[position] = pattern
                cells = tuple(cells)
                image = render_frame(cells, layout, cfg.screen)
                captured = apply_channel(image, channel, seed=int(rng.integers(0, 2**31 - 1)))
                with Timer() as timer:
                    decoded = decode_image(captured, layout, cfg.receiver, cfg.protocol)
                observed = decoded.frame.cell_values
                target_correct = sum(
                    1 for p in TARGET_POSITIONS if observed[p] == pattern
                ) / len(TARGET_POSITIONS)
                accuracies.append(target_correct)
                bit_rates.append(cell_bit_error_rate(cells, observed))
                confidences.append(decoded.observation.confidence)
                margins.append(decoded.observation.bit_margin)
                decode_ms.append(timer.elapsed_s * 1000.0)

            ctx.record(
                config={
                    "pattern": pattern,
                    "binary": f"{pattern:04b}",
                    "severity": severity,
                    "channel": channel.__dict__,
                    "repeats": repeats,
                },
                inputs={"target_positions": list(TARGET_POSITIONS)},
                outputs={
                    "mean_target_accuracy": float(np.mean(accuracies)),
                    "min_target_accuracy": float(np.min(accuracies)),
                    "mean_cell_bit_error_rate": float(np.mean(bit_rates)),
                    "mean_confidence": float(np.mean(confidences)),
                },
                metrics={
                    "pattern": pattern,
                    "mean_target_accuracy": float(np.mean(accuracies)),
                    "min_target_accuracy": float(np.min(accuracies)),
                    "mean_cell_bit_error_rate": float(np.mean(bit_rates)),
                    "mean_confidence": float(np.mean(confidences)),
                    "mean_bit_margin": float(np.mean(margins)),
                    "mean_decode_ms": float(np.mean(decode_ms)),
                },
                notes="target cells surrounded by random distractors; CRC not required",
            )

    distances = [
        pattern_distance(a, b)
        for i, a in enumerate(range(16))
        for b in range(i + 1, 16)
    ]
    ctx.summary = {
        "alphabet": alphabet,
        "min_pairwise_hamming_distance": min(distances),
        "max_pairwise_hamming_distance": max(distances),
        "distinct_patterns": 16,
        "bits_per_cell": 4,
        "note": (
            "FULL16 uses all 16 combinations, so the minimum symbol distance is "
            "one triangle (1 bit). There is no intra-cell error correction; "
            "detection and correction rely on the frame CRC and RS layer."
        ),
    }
    by_severity: dict[str, list[float]] = {}
    for trial in ctx.trials:
        key = trial["config"].get("severity")
        if key:
            by_severity.setdefault(str(key), []).append(
                float(trial["metrics"]["mean_target_accuracy"])
            )
    severity_accuracy = {
        key: float(np.mean(values)) for key, values in sorted(by_severity.items())
    }
    ctx.summary["mean_target_accuracy_by_severity"] = severity_accuracy
    measured = ", ".join(
        f"{key}={value:.3f}" for key, value in severity_accuracy.items()
    )
    perfect = [k for k, v in severity_accuracy.items() if v >= 1.0]
    degraded = [k for k, v in severity_accuracy.items() if v < 1.0]
    if degraded:
        outcome = (
            "The 16-way decision was perfect in "
            f"{', '.join(perfect) if perfect else 'no severity'}; it degraded in "
            f"{', '.join(degraded)} (figures above and per-pattern rows in the CSV)."
        )
    else:
        outcome = (
            "The 16-way decision was perfect at every severity tested here, so this "
            "sweep did not find a separating failure mode; a harsher or physical "
            "capture would be needed to probe the limit."
        )
    ctx.conclude(
        f"Measured mean target-cell accuracy by severity: {measured}. {outcome} "
        "FULL16 has minimum Hamming distance 1 between cell symbols, so a single "
        "misclassified triangle changes the decoded nibble. This is why the "
        "protocol adds a CRC-16 per frame and RS(255,223) per packet instead of "
        "relying on the cell alphabet for protection."
    )


SPEC = ExperimentSpec(
    id="E02_patterns",
    title="Separability of the 16 four-triangle cell patterns",
    hypothesis=(
        "Four independent black/white triangles give 16 visually distinct "
        "patterns, but the alphabet has minimum Hamming distance 1 and therefore "
        "needs CRC/RS protection."
    ),
    classification="OBSERVED (SIMULATED channel)",
    controlled=("30-cell layout", "FULL16 alphabet", "target cell positions", "distractor cells"),
    independent=("cell pattern 0..15", "channel severity"),
    dependent=("target-cell accuracy", "cell bit error rate", "confidence", "bit margin", "decode time"),
    procedure=(
        "Build a frame with 15 target cells set to one pattern and 15 random distractors.",
        "Render, apply the clean/mild/harsh synthetic channel, and decode the image.",
        "Compare decoded cell values with the ground truth; repeat per pattern and severity.",
        "Report per-pattern accuracy and the analytical pairwise Hamming distances.",
    ),
    run=run,
)
