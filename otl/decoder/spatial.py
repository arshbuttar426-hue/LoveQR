"""Spatial decoder: image -> cells -> 120-bit frame.

This is the only place that combines geometry and the frame format.  It works
on any grayscale image, including prerecorded PNGs, so the decoder can be
tested without a camera.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Layout, ProtocolConfig, ReceiverConfig
from ..protocol.frame import unpack_frame
from ..rx.detect import (
    CellObservation,
    Fiducials,
    classify_samples,
    detect_geometry,
    reference_levels,
    sample_cells,
)
from ..types import DecodedFrame


@dataclass(frozen=True)
class SpatialDecode:
    frame: DecodedFrame
    observation: CellObservation
    fiducials: Fiducials
    rectified: np.ndarray
    rectification: np.ndarray

    @property
    def crc_ok(self) -> bool:
        return self.frame.crc_ok

    def to_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame.to_dict(),
            "confidence": self.observation.confidence,
            "contrast": self.observation.contrast,
            "threshold": self.observation.threshold,
            "bit_margin": self.observation.bit_margin,
            "fiducial_method": self.fiducials.method,
            "fiducial_confidence": self.fiducials.confidence,
        }


def decode_image(
    image: np.ndarray,
    layout: Layout,
    receiver: ReceiverConfig | None = None,
    protocol: ProtocolConfig | None = None,
) -> SpatialDecode:
    """Detect, rectify, sample, classify and unpack one image."""
    receiver = receiver or ReceiverConfig()
    protocol = protocol or ProtocolConfig()
    rectified, fiducials, matrix = detect_geometry(image, layout, receiver)
    samples = sample_cells(rectified, layout, receiver)
    reference = reference_levels(rectified, layout)
    observation = classify_samples(samples, receiver, reference=reference)
    frame = unpack_frame(observation.cells, protocol, confidence=observation.confidence)
    return SpatialDecode(
        frame=frame,
        observation=observation,
        fiducials=fiducials,
        rectified=rectified,
        rectification=matrix,
    )


def decode_cells(
    cells: tuple[int, ...] | list[int],
    protocol: ProtocolConfig | None = None,
) -> DecodedFrame:
    """Decode already-classified cell values (no optics)."""
    return unpack_frame(cells, protocol)
