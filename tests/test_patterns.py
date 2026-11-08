"""Cell alphabet tests: mapping, distance and control alphabets."""

from __future__ import annotations

import pytest

from otl.codec.patterns import (
    alphabet_manifest,
    bits_per_cell,
    complement,
    decode_symbol,
    encode_symbol,
    min_distance,
    pattern_colors,
    pattern_distance,
    pattern_value,
    pattern_values,
    popcount,
)
from otl.errors import ProtocolError
from otl.types import PatternSet


def test_full16_is_identity_and_bijective() -> None:
    for value in range(16):
        colors = pattern_colors(value)
        assert pattern_value(colors) == value
        assert encode_symbol(value, PatternSet.FULL16) == value
        assert decode_symbol(value, PatternSet.FULL16) == (value, 0)


def test_complement_swaps_every_triangle() -> None:
    for value in range(16):
        assert complement(value) == value ^ 0xF
        assert complement(complement(value)) == value
        assert popcount(complement(value)) == 4 - popcount(value)


def test_distance_is_hamming_on_four_triangles() -> None:
    assert pattern_distance(0b0000, 0b1111) == 4
    assert pattern_distance(0b1010, 0b1000) == 1
    assert pattern_distance(7, 7) == 0


def test_control_alphabets() -> None:
    assert len(pattern_values(PatternSet.PARITY8)) == 8
    assert len(pattern_values(PatternSet.BALANCED6)) == 6
    assert bits_per_cell(PatternSet.FULL16) == 4
    assert bits_per_cell(PatternSet.PARITY8) == 3
    assert bits_per_cell(PatternSet.BALANCED6) == 0
    assert min_distance(PatternSet.FULL16) == 1
    assert min_distance(PatternSet.PARITY8) == 2
    assert min_distance(PatternSet.BALANCED6) == 2


def test_parity_symbol_roundtrip() -> None:
    for symbol in range(8):
        value = encode_symbol(symbol, PatternSet.PARITY8)
        assert popcount(value) % 2 == 0
        assert decode_symbol(value, PatternSet.PARITY8) == (symbol, 0)


def test_nearest_codeword_reports_distance() -> None:
    # 0b0001 has odd parity; nearest even-parity words are 0b0000 and 0b0011.
    symbol, distance = decode_symbol(0b0001, PatternSet.PARITY8)
    assert distance == 1
    assert encode_symbol(symbol, PatternSet.PARITY8) in (0b0000, 0b0011)


def test_out_of_range_and_unsupported() -> None:
    with pytest.raises(ProtocolError):
        pattern_colors(16)
    with pytest.raises(ProtocolError):
        encode_symbol(16, PatternSet.FULL16)
    with pytest.raises(ProtocolError):
        encode_symbol(0, PatternSet.BALANCED6)
    with pytest.raises(ProtocolError):
        bits_per_cell("nope")  # type: ignore[arg-type]


def test_manifest_is_stable() -> None:
    manifest = alphabet_manifest(PatternSet.FULL16)
    assert manifest["size"] == 16
    assert manifest["min_hamming_distance"] == 1
    assert len(manifest["table"]) == 16  # type: ignore[arg-type]
