"""Rolling-shutter model.

A rolling-shutter camera exposes rows sequentially.  If the screen changes
while the readout is in progress, different image rows contain different
display symbols.  The model here integrates each row's exposure window against
the display timeline and returns both the composite image and the exact
per-row symbol weights, so experiments can separate *model* error from
*decoder* error.

Critical physical limit: the number of display symbols visible in one frame is
``height * row_time / symbol_period``.  It is not multiplied by the camera's
frame rate.  :func:`timing_report` makes that explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import CameraConfig, Layout
from ..errors import ChannelError


@dataclass(frozen=True)
class RollingCapture:
    image: np.ndarray
    weights: np.ndarray          # (height, n_symbols), rows sum to 1
    dominant: np.ndarray         # (height,) symbol index per row
    phase_us: float
    symbol_period_us: float
    symbol_quality: np.ndarray   # (n_symbols,) total weight

    def bands(self) -> list[tuple[int, int, int]]:
        """Return contiguous ``(symbol, start_row, end_row_exclusive)`` runs."""
        runs: list[tuple[int, int, int]] = []
        start = 0
        for row in range(1, len(self.dominant)):
            if self.dominant[row] != self.dominant[start]:
                runs.append((int(self.dominant[start]), start, row))
                start = row
        if len(self.dominant):
            runs.append((int(self.dominant[start]), start, len(self.dominant)))
        return runs


def exposure_windows(camera: CameraConfig, phase_us: float) -> np.ndarray:
    """Start/end exposure time for every row, in microseconds."""
    rows = np.arange(camera.height, dtype=np.float64)
    if camera.readout_direction > 0:
        start = phase_us + rows * camera.row_time_us
    else:
        start = phase_us + (camera.height - 1 - rows) * camera.row_time_us
    return np.stack([start, start + camera.exposure_us], axis=1)


def row_weights(
    camera: CameraConfig,
    n_symbols: int,
    phase_us: float,
) -> np.ndarray:
    """Fraction of each row's exposure spent on each display symbol."""
    if n_symbols < 1:
        raise ChannelError("need at least one display symbol", component="rolling")
    windows = exposure_windows(camera, phase_us)
    period = camera.symbol_period_us
    weights = np.zeros((camera.height, n_symbols), dtype=np.float64)
    for symbol in range(n_symbols):
        low = symbol * period
        high = (symbol + 1) * period
        overlap = np.minimum(windows[:, 1], high) - np.maximum(windows[:, 0], low)
        weights[:, symbol] = np.clip(overlap, 0.0, None)
    totals = weights.sum(axis=1)
    empty = totals <= 0
    if empty.any():
        midpoint = windows[empty].mean(axis=1)
        nearest = np.clip(np.floor(midpoint / period).astype(int), 0, n_symbols - 1)
        weights[np.where(empty)[0], nearest] = 1.0
        totals = weights.sum(axis=1)
    weights /= totals[:, None]
    return weights


def simulate_rolling_shutter(
    frames: list[np.ndarray] | tuple[np.ndarray, ...],
    camera: CameraConfig,
    *,
    phase_us: float | None = None,
    seed: int | None = None,
) -> RollingCapture:
    """Compose one rolling-shutter image from a sequence of display frames."""
    if not frames:
        raise ChannelError("no display frames", component="rolling")
    shape = frames[0].shape
    if any(frame.shape != shape for frame in frames):
        raise ChannelError(
            "display frames must share one shape",
            component="rolling",
            operation="simulate_rolling_shutter",
        )
    if shape[0] != camera.height:
        raise ChannelError(
            "camera height does not match display frames",
            component="rolling",
            operation="simulate_rolling_shutter",
            camera_height=camera.height,
            frame_height=shape[0],
        )
    rng = np.random.default_rng(seed)
    if phase_us is None:
        phase_us = float(rng.uniform(0.0, camera.symbol_period_us)) if camera.random_phase else 0.0
    weights = row_weights(camera, len(frames), phase_us)
    stack = np.stack([frame.astype(np.float64) for frame in frames], axis=0)
    # Each camera row integrates its own exposure window across the symbol
    # stack, sampling the display frame at the same row:
    # result[row, x] = sum_s weights[row, s] * stack[s, row, x].
    image = np.einsum("rs,srw->rw", weights, stack)
    dominant = np.argmax(weights, axis=1)
    quality = weights.sum(axis=0)
    return RollingCapture(
        image=np.clip(image, 0.0, 255.0).astype(np.uint8),
        weights=weights,
        dominant=dominant,
        phase_us=phase_us,
        symbol_period_us=camera.symbol_period_us,
        symbol_quality=quality,
    )


def row_signal(image: np.ndarray, layout: Layout | None = None) -> np.ndarray:
    """Mean intensity per image row, optionally restricted to data columns.

    The returned array always has one entry per image row, so it can be aligned
    with :attr:`RollingCapture.dominant`.  When ``layout`` is supplied only the
    data-area columns are averaged.
    """
    if layout is not None:
        x0 = max(0, layout.origin_x)
        x1 = min(image.shape[1], layout.origin_x + layout.data_w)
        region = image[:, x0:x1]
    else:
        region = image
    if region.size == 0:
        raise ChannelError("empty sampling region", component="rolling")
    return region.astype(np.float64).mean(axis=1)


def chip_values(capture: RollingCapture, layout: Layout | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(symbol_indices, intensity)`` for symbols visible in a capture."""
    signal = row_signal(capture.image, layout)
    if len(signal) != len(capture.dominant):
        raise ChannelError(
            "row signal and symbol map disagree",
            component="rolling",
            operation="chip_values",
        )
    indices: list[int] = []
    values: list[float] = []
    for symbol in np.unique(capture.dominant):
        rows = np.where(capture.dominant == symbol)[0]
        if len(rows) == 0:
            continue
        indices.append(int(symbol))
        values.append(float(signal[rows].mean()))
    return np.asarray(indices, dtype=int), np.asarray(values, dtype=np.float64)


def timing_report(camera: CameraConfig, chips: int = 26) -> dict[str, object]:
    """Expose the rolling-shutter temporal budget as explicit arithmetic."""
    readout = camera.readout_us
    period = camera.symbol_period_us
    captured = readout / period
    exposure_ratio = camera.exposure_us / period if period else float("inf")
    fits = captured >= chips
    exposure_ok = exposure_ratio <= 1.0
    return {
        "rows": camera.height,
        "row_time_us": camera.row_time_us,
        "readout_us": readout,
        "display_fps": camera.display_fps,
        "symbol_period_us": period,
        "symbols_per_capture": captured,
        "word_chips": chips,
        "word_fits_in_one_capture": fits,
        "captures_needed_for_word": chips / captured if captured else None,
        "exposure_us": camera.exposure_us,
        "exposure_over_period": exposure_ratio,
        "exposure_within_symbol": exposure_ok,
        "temporal_budget_ok": fits and exposure_ok,
        "note": (
            "rolling shutter samples rows sequentially; it does not increase "
            "the display refresh rate.  A 26-chip word needs readout >= 26 "
            "symbol periods AND an exposure no longer than one symbol period; "
            "a longer exposure integrates several chips into each row."
        ),
    }
