"""CRC tests, including the published check value."""

from __future__ import annotations

import pytest

from otl.ecc.crc import crc16_ccitt, crc16_bytes, crc32, verify_crc16
from otl.errors import CRCError


def test_crc16_ccitt_check_value() -> None:
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_crc16_empty_and_bytes() -> None:
    assert crc16_ccitt(b"") == 0xFFFF
    assert crc16_bytes(b"123456789") == b"\x29\xb1"


def test_crc16_detects_single_bit_flips() -> None:
    payload = bytes(range(32))
    reference = crc16_ccitt(payload)
    for bit in range(len(payload) * 8):
        corrupted = bytearray(payload)
        corrupted[bit // 8] ^= 1 << (bit % 8)
        assert crc16_ccitt(bytes(corrupted)) != reference


def test_crc32_matches_zlib() -> None:
    import zlib

    for payload in (b"", b"a", b"123456789", bytes(range(256))):
        assert crc32(payload) == zlib.crc32(payload) & 0xFFFFFFFF


def test_verify_crc16_raises_structured_error() -> None:
    with pytest.raises(CRCError) as excinfo:
        verify_crc16(b"data", 0)
    assert excinfo.value.code == "E_CRC"
    assert excinfo.value.details["actual"] == crc16_ccitt(b"data")
