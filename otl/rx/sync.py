"""Synchronisation helpers.

Two independent locks are needed before data can be decoded:

* spatial/geometry lock: locate the four fiducials and rectify the screen;
* temporal lock: find the 13-chip Barker sync followed by a blink ID.

This module is a thin, typed facade so experiments can record each lock
separately instead of collapsing both into one success/failure bit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Layout, ReceiverConfig
from ..decoder.temporal import TemporalResult, decode_values
from ..errors import SyncError
from ..rx.detect import Fiducials, detect_geometry


@dataclass(frozen=True)
class SpatialSync:
    rectified: np.ndarray
    fiducials: Fiducials
    matrix: np.ndarray
    confidence: float
    locked: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.fiducials.method,
            "fiducial_confidence": self.fiducials.confidence,
            "confidence": self.confidence,
            "locked": self.locked,
            "centers": {k: list(v) for k, v in self.fiducials.centers.items()},
        }


@dataclass(frozen=True)
class TemporalSync:
    result: TemporalResult
    id_index: int | None
    id_name: str | None
    score: float
    locked: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "locked": self.locked,
            "id_index": self.id_index,
            "id_name": self.id_name,
            "score": self.score,
            "result": self.result.to_dict(),
        }


def spatial_sync(
    image: np.ndarray,
    layout: Layout,
    cfg: ReceiverConfig | None = None,
    *,
    min_confidence: float = 0.0,
) -> SpatialSync:
    rectified, fiducials, matrix = detect_geometry(image, layout, cfg)
    confidence = fiducials.confidence
    return SpatialSync(
        rectified=rectified,
        fiducials=fiducials,
        matrix=matrix,
        confidence=confidence,
        locked=confidence >= min_confidence and fiducials.method != "none",
    )


def temporal_sync(
    values: np.ndarray | list[float],
    *,
    min_contrast: float = 0.02,
    sync_threshold: float = 0.6,
    id_threshold: float = 0.7,
) -> TemporalSync:
    try:
        result = decode_values(
            values,
            min_contrast=min_contrast,
            sync_threshold=sync_threshold,
            id_threshold=id_threshold,
        )
    except SyncError:
        # No lock is a normal receiver state, not an exception for the caller.
        return TemporalSync(
            result=TemporalResult(
                bits=(),
                values=tuple(float(v) for v in values),
                detections=(),
                contrast=0.0,
                note="insufficient contrast for a temporal lock",
            ),
            id_index=None,
            id_name=None,
            score=0.0,
            locked=False,
        )
    if result.detections:
        best = max(result.detections, key=lambda d: d.id_score)
        return TemporalSync(
            result=result,
            id_index=best.id_index,
            id_name=best.id_name,
            score=best.id_score,
            locked=True,
        )
    return TemporalSync(result=result, id_index=None, id_name=None, score=0.0, locked=False)


def sync_manifest() -> dict[str, object]:
    return {
        "spatial": "four corner fiducials, Otsu threshold, homography to canonical layout",
        "temporal": "Barker-13 sync + one of three 13-chip IDs",
        "spatial_lock": "fiducials found in four quadrants and homography solved",
        "temporal_lock": "Pearson correlation above threshold for sync and ID",
    }
