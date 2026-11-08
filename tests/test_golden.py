"""Regression / golden tests for deterministic protocol artefacts.

These values are pure-Python or fixed-Pillow outputs.  A change here means the
on-screen format, packet layout, compressor or renderer changed; update the
constant only together with a protocol version bump and a note in
``docs/DECISIONS.md``.
"""

from __future__ import annotations

import hashlib

from otl.compress.dictionary import compress
from otl.config import ExperimentConfig
from otl.protocol.frame import pack_frame
from otl.protocol.packet import build_file
from otl.tx.renderer import render_frame
from otl.types import FrameHeader

GOLDEN_CELLS = (
    3, 0, 1, 1, 0, 0, 0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6, 0, 7,
    0, 8, 0, 9, 0, 10, 14, 10, 11, 14,
)
GOLDEN_FRAME0 = "4f00000000000000000000"
GOLDEN_FRAME17 = "ed00000000000000000000"
GOLDEN_COMPRESSED = "4f544c3101000000b40003616263020003b1"
GOLDEN_RENDER_SHA256 = "fb306fd6b2a3c281c5c344378abec246e1f823421837c36637c2b84672272413"


def test_frame_cells_golden() -> None:
    cfg = ExperimentConfig()
    cells = pack_frame(FrameHeader(3, 17), bytes(range(11)), cfg.protocol)
    assert cells == GOLDEN_CELLS


def test_packet_bytes_golden() -> None:
    _, packets = build_file(
        b"OTL golden payload " + bytes(range(32)),
        "golden.bin",
        compressed=False,
        original_len=48,
    )
    assert packets[0].frames[0].hex() == GOLDEN_FRAME0
    assert packets[0].frames[17].hex() == GOLDEN_FRAME17


def test_compressor_bytes_golden() -> None:
    cfg = ExperimentConfig()
    packed, stats = compress(b"abcabcabcabcabcabc" * 10, cfg.compression)
    assert packed.hex() == GOLDEN_COMPRESSED
    assert stats.ratio == 10.0


def test_rendered_frame_hash_golden() -> None:
    cfg = ExperimentConfig()
    image = render_frame(GOLDEN_CELLS, cfg.layout(), cfg.screen)
    assert hashlib.sha256(image.tobytes()).hexdigest() == GOLDEN_RENDER_SHA256
