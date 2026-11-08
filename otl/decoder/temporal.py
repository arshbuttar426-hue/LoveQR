"""Temporal decoding: blink words and rolling-shutter bands.

Two paths are provided:

* :func:`decode_values` classifies a sequence of per-symbol intensities into
  chips and searches for sync+ID words;
* :func:`bands_from_signal` segments a rolling-shutter row signal without
  knowing the display timeline, which is what a real receiver must do.

The rolling path reports how many display symbols were actually visible; it
never assumes that a full 26-chip word fits in one capture.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Layout
from ..errors import SyncError
from ..protocol.blink import BlinkDetection, find_blink_words
from ..rx.rolling import RollingCapture, chip_values, row_signal, timing_report


@dataclass(frozen=True)
class Band:
    start: int
    end: int
    value: float

    @property
    def height(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class TemporalResult:
    bits: tuple[int, ...]
    values: tuple[float, ...]
    detections: tuple[BlinkDetection, ...]
    contrast: float
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "bits": list(self.bits),
            "values": [round(v, 3) for v in self.values],
            "contrast": self.contrast,
            "detections": [d.to_dict() for d in self.detections],
            "note": self.note,
        }


def _moving_average(signal: np.ndarray, width: int) -> np.ndarray:
    if width <= 1 or len(signal) < width:
        return signal.astype(np.float64)
    kernel = np.ones(width, dtype=np.float64) / width
    padded = np.pad(signal.astype(np.float64), (width // 2, width - 1 - width // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def bits_from_values(
    values: np.ndarray | list[float],
    *,
    min_contrast: float = 0.02,
) -> tuple[tuple[int, ...], float]:
    """Threshold a chip-intensity sequence into bits.

    Returns ``(bits, contrast)`` where contrast is ``(max-min)/255``.  Raises
    :class:`SyncError` when the sequence is too flat to classify.
    """
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise SyncError("empty chip sequence", component="rx", operation="bits_from_values")
    low = float(np.percentile(array, 5))
    high = float(np.percentile(array, 95))
    contrast = (high - low) / 255.0
    if contrast < min_contrast:
        raise SyncError(
            "chip sequence contrast too low",
            component="rx",
            operation="bits_from_values",
            contrast=contrast,
            minimum=min_contrast,
        )
    threshold = (low + high) / 2.0
    return tuple(1 if value > threshold else 0 for value in array), contrast


def decode_values(
    values: np.ndarray | list[float],
    *,
    min_contrast: float = 0.02,
    sync_threshold: float = 0.6,
    id_threshold: float = 0.7,
) -> TemporalResult:
    """Decode a sequence of per-symbol intensities into blink detections."""
    bits, contrast = bits_from_values(values, min_contrast=min_contrast)
    detections = find_blink_words(
        [float(b) for b in bits],
        threshold=sync_threshold,
        id_threshold=id_threshold,
    )
    note = "" if detections else "no sync+ID word found"
    return TemporalResult(
        bits=bits,
        values=tuple(float(v) for v in np.asarray(values)),
        detections=tuple(detections),
        contrast=contrast,
        note=note,
    )


def bands_from_signal(
    signal: np.ndarray | list[float],
    *,
    smooth_width: int = 5,
    edge_factor: float = 0.1,
    min_height: int = 3,
) -> list[Band]:
    """Segment a row-intensity signal into contiguous bands.

    This is a blind heuristic: it smooths the signal, places boundaries where
    the absolute derivative exceeds a fraction of the dynamic range, and merges
    runs shorter than ``min_height``.  It is used for diagnostics and for
    experiments that compare blind segmentation with the known timeline.
    """
    array = np.asarray(signal, dtype=np.float64)
    if array.size == 0:
        return []
    smoothed = _moving_average(array, smooth_width)
    low = float(np.percentile(smoothed, 5))
    high = float(np.percentile(smoothed, 95))
    threshold = max(1.0, (high - low) * edge_factor)
    derivative = np.abs(np.diff(smoothed))
    raw_edges = np.where(derivative > threshold)[0]
    boundaries: list[int] = [0]
    for edge in raw_edges:
        boundary = int(edge) + 1
        if boundary - boundaries[-1] >= min_height:
            boundaries.append(boundary)
    if len(boundaries) == 1:
        return [Band(0, len(array), float(smoothed.mean()))]
    boundaries.append(len(array))
    bands: list[Band] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end - start < min_height:
            continue
        bands.append(Band(start, end, float(smoothed[start:end].mean())))
    return bands


def decode_rolling(
    capture: RollingCapture,
    layout: Layout | None = None,
    *,
    min_quality: float = 0.5,
    min_contrast: float = 0.02,
) -> TemporalResult:
    """Decode the display symbols visible in one rolling-shutter capture."""
    indices, values = chip_values(capture, layout)
    keep = capture.symbol_quality[indices] >= min_quality
    indices = indices[keep]
    values = values[keep]
    if values.size < 2:
        raise SyncError(
            "fewer than two usable display symbols in the capture",
            component="rx",
            operation="decode_rolling",
            symbols=int(values.size),
        )
    result = decode_values(values, min_contrast=min_contrast)
    note = (
        f"{len(indices)} display symbols visible; "
        f"indices {int(indices.min())}..{int(indices.max())}"
    )
    return TemporalResult(
        bits=result.bits,
        values=result.values,
        detections=result.detections,
        contrast=result.contrast,
        note=note,
    )


def temporal_manifest(capture: RollingCapture | None = None) -> dict[str, object]:
    info: dict[str, object] = {
        "word_chips": 26,
        "sync_chips": 13,
        "id_chips": 13,
        "classifier": "Pearson normalised cross-correlation, both polarities",
        "segmentation": "smoothed derivative threshold, blind to the timeline",
    }
    if capture is not None:
        info["visible_symbols"] = int(len(np.unique(capture.dominant)))
        info["bands"] = [
            {"symbol": symbol, "start": start, "end": end}
            for symbol, start, end in capture.bands()
        ]
    return info
