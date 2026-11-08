"""Shared enums and immutable value objects.

The central epistemic rule of the project lives here: every reported number
carries a :class:`Classification`.  ``VERIFIED`` is reserved for a measurement
that has a raw capture, device identity and reproduction command.  Software
measurements on a simulated channel are ``OBSERVED`` and must say so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Classification(str, Enum):
    """Evidence level for a claim or measurement."""

    VERIFIED = "VERIFIED"          # physical device, raw data retained, reproducible
    OBSERVED = "OBSERVED"          # measured in this project (may be simulated channel)
    THEORETICAL = "THEORETICAL"    # derived from mathematics / protocol arithmetic
    HYPOTHESIS = "HYPOTHESIS"      # proposed, not yet tested
    REJECTED = "REJECTED"          # tested and failed


class Polarity(str, Enum):
    NORMAL = "normal"
    INVERTED = "inverted"


class PatternSet(str, Enum):
    """Cell alphabet under test."""

    FULL16 = "full16"        # all 4-triangle patterns, 4 bits/cell (proposed)
    PARITY8 = "parity8"      # even-parity patterns, 3 bits/cell
    BALANCED6 = "balanced6"  # exactly two white triangles, 6 patterns


class MeasurementSource(str, Enum):
    PHYSICAL = "physical"          # real screen + real camera
    SIMULATED = "simulated"        # synthetic channel in software
    SOFTWARE = "software"          # codec/ECC/compression timing, no optics
    ANALYTICAL = "analytical"      # arithmetic / information theory


@dataclass(frozen=True)
class Measurement:
    name: str
    value: float
    unit: str
    classification: Classification
    source: MeasurementSource
    notes: str = ""
    device: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "classification": self.classification.value,
            "source": self.source.value,
            "notes": self.notes,
            "device": self.device,
        }


@dataclass(frozen=True)
class FrameHeader:
    """16-bit on-screen frame header: 4-bit packet id + 12-bit frame index."""

    packet_id: int
    frame_index: int

    def __post_init__(self) -> None:
        if not 0 <= self.packet_id <= 0xF:
            raise ValueError(f"packet_id out of range: {self.packet_id}")
        if not 0 <= self.frame_index <= 0xFFF:
            raise ValueError(f"frame_index out of range: {self.frame_index}")

    def to_int(self) -> int:
        return (self.packet_id << 12) | self.frame_index

    @classmethod
    def from_int(cls, value: int) -> "FrameHeader":
        return cls(packet_id=(value >> 12) & 0xF, frame_index=value & 0xFFF)


@dataclass(frozen=True)
class DecodedFrame:
    """Result of decoding one spatial frame."""

    header: FrameHeader
    data: bytes
    crc: int
    crc_ok: bool
    confidence: float
    cell_values: tuple[int, ...]
    bit_errors: int | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.header.packet_id,
            "frame_index": self.header.frame_index,
            "data_hex": self.data.hex(),
            "crc": self.crc,
            "crc_ok": self.crc_ok,
            "confidence": self.confidence,
            "cell_values": list(self.cell_values),
            "bit_errors": self.bit_errors,
            "error_code": self.error_code,
        }


@dataclass
class TrialRecord:
    """One raw measurement trial, serialised verbatim to ``raw/trials.jsonl``."""

    experiment: str
    trial: int
    config: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment": self.experiment,
            "trial": self.trial,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "errors": self.errors,
            "notes": self.notes,
        }
