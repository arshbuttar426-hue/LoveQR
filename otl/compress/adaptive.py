"""Adaptive raw/OTL1 selection for the M11 payload path.

The frozen M9 transmitter always compresses.  That is harmless for structured
data, but OTL1 adds a 9-byte container plus opcode overhead, so incompressible
data can grow.  On a 2,421-byte packet-0 payload the 29-byte growth is enough to
spill into a second 255-frame packet.

``choose_encoding`` keeps the smaller representation and reports why.  The
decision is deterministic and byte-exact: decompression is performed only when
the compressed flag is set.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..config import CompressionConfig
from .dictionary import CompressionStats, compress, decompress


@dataclass(frozen=True)
class EncodingChoice:
    """The wire representation selected for one application payload."""

    original: bytes
    wire: bytes
    compressed: bool
    stats: CompressionStats | None
    reason: str

    @property
    def original_bytes(self) -> int:
        return len(self.original)

    @property
    def wire_bytes(self) -> int:
        return len(self.wire)

    @property
    def ratio(self) -> float:
        return self.original_bytes / self.wire_bytes if self.wire_bytes else 0.0

    def decode(self) -> bytes:
        """Return the original bytes, verifying the chosen representation."""
        if self.compressed:
            restored = decompress(self.wire)
        else:
            restored = self.wire
        if restored != self.original:
            raise AssertionError("adaptive encoding did not round-trip")
        return restored

    def to_dict(self) -> dict[str, object]:
        return {
            "original_bytes": self.original_bytes,
            "wire_bytes": self.wire_bytes,
            "compressed": self.compressed,
            "reason": self.reason,
            "ratio": self.ratio,
            "original_sha256": hashlib.sha256(self.original).hexdigest(),
            "wire_sha256": hashlib.sha256(self.wire).hexdigest(),
            "opcodes": self.stats.ops if self.stats else None,
        }


def choose_encoding(
    data: bytes,
    cfg: CompressionConfig | None = None,
) -> EncodingChoice:
    """Return OTL1-compressed bytes when they are strictly smaller, else raw."""
    compact, stats = compress(data, cfg)
    if len(compact) < len(data):
        return EncodingChoice(
            original=data,
            wire=compact,
            compressed=True,
            stats=stats,
            reason="OTL1 is smaller than raw",
        )
    return EncodingChoice(
        original=data,
        wire=data,
        compressed=False,
        stats=stats,
        reason=(
            "raw is smaller than OTL1"
            if len(data) < len(compact)
            else "raw and OTL1 are the same size; raw avoids the container"
        ),
    )
