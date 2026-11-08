"""Shared helpers for experiment implementations.

Nothing here measures anything by itself; it only builds deterministic inputs
and applies transformations whose parameters are recorded in trial configs.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any

import numpy as np

from otl.config import ChannelConfig, ExperimentConfig
from otl.protocol.frame import pack_frame
from otl.tx.renderer import render_frame
from otl.types import FrameHeader

CHANNELS: dict[str, ChannelConfig] = {
    "clean": ChannelConfig(),
    "mild": ChannelConfig(
        blur_sigma=0.8,
        noise_sigma=2.0,
        ambient=12.0,
        brightness=0.92,
        gamma=1.05,
        vignette=0.12,
        perspective=0.01,
        jpeg_quality=92,
    ),
    "harsh": ChannelConfig(
        blur_sigma=1.4,
        noise_sigma=4.0,
        ambient=25.0,
        brightness=0.82,
        gamma=1.15,
        vignette=0.25,
        perspective=0.03,
        jpeg_quality=80,
    ),
    "extreme": ChannelConfig(
        blur_sigma=2.0,
        noise_sigma=8.0,
        ambient=35.0,
        brightness=0.7,
        gamma=1.3,
        vignette=0.4,
        perspective=0.05,
        jpeg_quality=60,
    ),
    # Deliberately beyond a plausible handheld capture. It exists so the
    # experiments can locate a separating failure mode instead of only
    # confirming that easy channels work.
    "brutal": ChannelConfig(
        blur_sigma=3.5,
        noise_sigma=20.0,
        ambient=60.0,
        brightness=0.5,
        gamma=1.6,
        vignette=0.6,
        perspective=0.08,
        jpeg_quality=35,
    ),
}


def cfg_with(
    cfg: ExperimentConfig,
    *,
    channel: ChannelConfig | None = None,
    compression: bool | None = None,
    seed: int | None = None,
) -> ExperimentConfig:
    updates: dict[str, Any] = {}
    if channel is not None:
        updates["channel"] = channel
    if compression is not None:
        updates["compression"] = replace(cfg.compression, enabled=compression)
    if seed is not None:
        updates["seed"] = seed
    return replace(cfg, **updates)


def random_frame(
    rng: np.random.Generator,
    cfg: ExperimentConfig,
    *,
    packet_id: int | None = None,
    frame_index: int | None = None,
) -> tuple[FrameHeader, bytes, tuple[int, ...]]:
    header = FrameHeader(
        int(rng.integers(0, 16)) if packet_id is None else packet_id,
        int(rng.integers(0, 4096)) if frame_index is None else frame_index,
    )
    data = bytes(int(b) for b in rng.integers(0, 256, size=cfg.protocol.payload_bytes))
    cells = pack_frame(header, data, cfg.protocol)
    return header, data, cells


def cell_error_rate(expected: tuple[int, ...], actual: tuple[int, ...]) -> float:
    if len(expected) != len(actual):
        raise ValueError("cell sequences differ in length")
    return sum(1 for a, b in zip(expected, actual) if a != b) / len(expected)


def cell_bit_error_rate(expected: tuple[int, ...], actual: tuple[int, ...]) -> float:
    return sum((a ^ b).bit_count() for a, b in zip(expected, actual)) / (4.0 * len(expected))


def corrupt_cells(
    cells: tuple[int, ...],
    count: int,
    rng: np.random.Generator,
) -> tuple[int, ...]:
    """Replace ``count`` random cells with a different 4-bit value."""
    values = list(cells)
    for index in rng.choice(len(values), size=min(count, len(values)), replace=False):
        current = values[int(index)]
        replacement = int(rng.integers(0, 15))
        values[int(index)] = replacement if replacement < current else replacement + 1
    return tuple(values)


def corrupt_bytes(
    data: bytes,
    count: int,
    rng: np.random.Generator,
) -> bytes:
    values = bytearray(data)
    for index in rng.choice(len(values), size=min(count, len(values)), replace=False):
        values[int(index)] ^= 1 << int(rng.integers(0, 8))
    return bytes(values)


def downsample_roundtrip(image: np.ndarray, scale: float) -> np.ndarray:
    """Reduce effective resolution and restore the canonical canvas size."""
    if scale >= 1.0:
        return image
    try:
        import cv2

        h, w = image.shape[:2]
        small = cv2.resize(
            image, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
        )
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    except Exception:  # pragma: no cover
        from PIL import Image

        h, w = image.shape[:2]
        pil = Image.fromarray(image)
        small = pil.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
        return np.asarray(small.resize((w, h), Image.NEAREST), dtype=np.uint8)


def image_hash(image: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(image).tobytes()).hexdigest()


def summarize_success(values: list[bool]) -> dict[str, Any]:
    n = len(values)
    successes = sum(1 for v in values if v)
    return {
        "n": n,
        "successes": successes,
        "success_rate": successes / n if n else 0.0,
    }


def load_rendered(path: str) -> np.ndarray:
    from otl.tx.renderer import load_frame

    return load_frame(path)


def render_cells(cells: tuple[int, ...], cfg: ExperimentConfig) -> np.ndarray:
    return render_frame(cells, cfg.layout(), cfg.screen)
