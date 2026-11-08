"""Spatial frame format: 30 cells x 4 bits = 120 bits.

Layout (MSB first, big-endian)::

    header   16 bits   4-bit packet id + 12-bit frame index
    data     88 bits   11 bytes of packet payload
    crc      16 bits   CRC-16/CCITT-FALSE over header + data (13 bytes)

Each byte becomes two consecutive cell values (high nibble, then low nibble),
so a frame is exactly 15 bytes / 30 cells.  This module is deliberately free of
any camera or drawing code: it is the contract between transmitter, channel and
decoder and can be unit-tested on prerecorded cell values.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..config import ProtocolConfig
from ..ecc.crc import crc16_ccitt
from ..errors import FrameFormatError
from ..types import DecodedFrame, FrameHeader

FRAME_BYTES = 15
HEADER_BYTES = 2
CRC_BYTES = 2


def _validate_config(cfg: ProtocolConfig) -> None:
    if cfg.bits_per_cell != 4:
        raise FrameFormatError(
            "spatial frame module implements the 4-bit FULL16 format only",
            component="protocol",
            operation="frame",
            bits_per_cell=cfg.bits_per_cell,
        )


def pack_frame(
    header: FrameHeader,
    data: bytes,
    cfg: ProtocolConfig | None = None,
) -> tuple[int, ...]:
    """Pack a header and 11 data bytes into 30 cell values."""
    cfg = cfg or ProtocolConfig()
    _validate_config(cfg)
    if len(data) != cfg.data_bytes_per_frame:
        raise FrameFormatError(
            "wrong data length for one frame",
            component="protocol",
            operation="pack_frame",
            expected=cfg.data_bytes_per_frame,
            actual=len(data),
        )
    payload = header.to_int().to_bytes(HEADER_BYTES, "big") + bytes(data)
    raw = payload + crc16_ccitt(payload).to_bytes(CRC_BYTES, "big")
    cells: list[int] = []
    for byte in raw:
        cells.append((byte >> 4) & 0xF)
        cells.append(byte & 0xF)
    return tuple(cells)


def unpack_frame(
    cells: Sequence[int],
    cfg: ProtocolConfig | None = None,
    *,
    confidence: float = 1.0,
) -> DecodedFrame:
    """Unpack 30 cell values.  A bad CRC is reported, not raised."""
    cfg = cfg or ProtocolConfig()
    _validate_config(cfg)
    expected_cells = cfg.total_bits // cfg.bits_per_cell
    if len(cells) != expected_cells:
        raise FrameFormatError(
            "wrong number of cells for one frame",
            component="protocol",
            operation="unpack_frame",
            expected=expected_cells,
            actual=len(cells),
        )
    values = tuple(int(c) for c in cells)
    if any(not 0 <= c <= 0xF for c in values):
        raise FrameFormatError(
            "cell value outside the 4-bit alphabet",
            component="protocol",
            operation="unpack_frame",
            cells=values,
        )
    raw = bytes(((values[2 * i] << 4) | values[2 * i + 1]) for i in range(FRAME_BYTES))
    payload = raw[: HEADER_BYTES + cfg.data_bytes_per_frame]
    crc = int.from_bytes(raw[HEADER_BYTES + cfg.data_bytes_per_frame :], "big")
    header = FrameHeader.from_int(int.from_bytes(payload[:HEADER_BYTES], "big"))
    return DecodedFrame(
        header=header,
        data=payload[HEADER_BYTES:],
        crc=crc,
        crc_ok=crc16_ccitt(payload) == crc,
        confidence=float(confidence),
        cell_values=values,
    )


def cells_to_bits(cells: Sequence[int]) -> tuple[int, ...]:
    """Expand cell values into a 120-bit MSB-first stream."""
    bits: list[int] = []
    for cell in cells:
        if not 0 <= cell <= 0xF:
            raise FrameFormatError(
                "cell value outside the 4-bit alphabet",
                component="protocol",
                operation="cells_to_bits",
                cell=cell,
            )
        bits.extend((cell >> shift) & 1 for shift in (3, 2, 1, 0))
    return tuple(bits)


def bits_to_cells(bits: Sequence[int]) -> tuple[int, ...]:
    """Pack a 120-bit MSB-first stream into 30 cell values."""
    if len(bits) % 4 != 0:
        raise FrameFormatError(
            "bit stream length must be a multiple of four",
            component="protocol",
            operation="bits_to_cells",
            length=len(bits),
        )
    cells: list[int] = []
    for i in range(0, len(bits), 4):
        value = 0
        for bit in bits[i : i + 4]:
            value = (value << 1) | (1 if bit else 0)
        cells.append(value)
    return tuple(cells)


def frame_manifest(cfg: ProtocolConfig | None = None) -> dict[str, object]:
    cfg = cfg or ProtocolConfig()
    return {
        "cells": cfg.cols * cfg.rows,
        "bits_per_cell": cfg.bits_per_cell,
        "total_bits": cfg.total_bits,
        "header_bits": cfg.header_bits,
        "data_bits": cfg.data_bytes_per_frame * 8,
        "crc_bits": cfg.crc_bits,
        "bytes_per_frame": FRAME_BYTES,
        "byte_order": "big-endian; header, data, crc",
        "cell_order": "row-major, high nibble before low nibble",
        "crc": "CRC-16/CCITT-FALSE over header+data",
    }
