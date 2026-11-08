"""CRC-16/CCITT-FALSE and CRC-32 helpers.

CRC-16 parameters: polynomial 0x1021, init 0xFFFF, no input/output reflection,
xorout 0x0000.  Check value for ``b"123456789"`` is 0x29B1.
"""

from __future__ import annotations

import zlib

from ..errors import CRCError

_POLY = 0x1021


def _make_table() -> tuple[int, ...]:
    table = []
    for byte in range(256):
        crc = byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ _POLY) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)


_TABLE = _make_table()


def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init & 0xFFFF
    for byte in data:
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ byte) & 0xFF]
    return crc & 0xFFFF


def crc16_bytes(data: bytes) -> bytes:
    return crc16_ccitt(data).to_bytes(2, "big")


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc16(data: bytes, expected: int) -> None:
    actual = crc16_ccitt(data)
    if actual != expected:
        raise CRCError(
            "CRC-16 mismatch",
            component="ecc",
            operation="verify_crc16",
            expected=expected,
            actual=actual,
        )
