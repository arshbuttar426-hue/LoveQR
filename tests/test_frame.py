"""Spatial frame format tests."""

from __future__ import annotations

import pytest

from otl.config import ProtocolConfig
from otl.errors import FrameFormatError
from otl.protocol.frame import (
    bits_to_cells,
    cells_to_bits,
    frame_manifest,
    pack_frame,
    unpack_frame,
)
from otl.types import FrameHeader


def test_pack_unpack_roundtrip() -> None:
    data = bytes(range(11))
    for packet_id in (0, 1, 15):
        for frame_index in (0, 1, 254, 4095):
            header = FrameHeader(packet_id, frame_index)
            cells = pack_frame(header, data)
            assert len(cells) == 30
            decoded = unpack_frame(cells)
            assert decoded.header == header
            assert decoded.data == data
            assert decoded.crc_ok
            assert decoded.cell_values == cells


def test_all_cell_values_survive() -> None:
    # 30 cells; force every nibble 0..15 by choosing bytes accordingly.
    header = FrameHeader(5, 100)
    data = bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0x10, 0x32, 0x54])
    cells = pack_frame(header, data)
    assert set(cells) == set(range(16))
    assert unpack_frame(cells).data == data


def test_crc_failure_is_reported_not_raised() -> None:
    cells = list(pack_frame(FrameHeader(1, 2), bytes(11)))
    cells[0] ^= 0xF
    decoded = unpack_frame(cells)
    assert not decoded.crc_ok


def test_bits_roundtrip() -> None:
    cells = pack_frame(FrameHeader(7, 300), bytes(range(11)))
    bits = cells_to_bits(cells)
    assert len(bits) == 120
    assert bits_to_cells(bits) == cells
    assert set(bits) <= {0, 1}


def test_length_and_range_validation() -> None:
    with pytest.raises(FrameFormatError):
        pack_frame(FrameHeader(0, 0), bytes(10))
    with pytest.raises(FrameFormatError):
        pack_frame(FrameHeader(0, 0), bytes(12))
    with pytest.raises(FrameFormatError):
        unpack_frame([0] * 29)
    with pytest.raises(FrameFormatError):
        unpack_frame([0] * 29 + [16])
    with pytest.raises(FrameFormatError):
        cells_to_bits([16] + [0] * 29)
    with pytest.raises(FrameFormatError):
        bits_to_cells([0] * 121)


def test_header_field_boundaries() -> None:
    with pytest.raises(ValueError):
        FrameHeader(16, 0)
    with pytest.raises(ValueError):
        FrameHeader(0, 4096)
    assert FrameHeader.from_int(FrameHeader(9, 4095).to_int()) == FrameHeader(9, 4095)


def test_manifest() -> None:
    info = frame_manifest(ProtocolConfig())
    assert info["cells"] == 30
    assert info["total_bits"] == 120
    assert info["bytes_per_frame"] == 15
