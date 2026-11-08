"""Cell alphabet: four independently controlled black/white triangles.

A cell value is a 4-bit integer.  Bit 3 (MSB) is the top triangle, bit 2 the
right, bit 1 the bottom and bit 0 the left.  This ordering lets a serial bit
stream be packed MSB-first directly into cell values.

The full 16-pattern alphabet is the proposal under test.  ``PARITY8`` and
``BALANCED6`` are control alphabets used to measure the robustness/capacity
trade-off; they are not the main protocol.
"""

from __future__ import annotations

from typing import Iterable

from ..errors import ProtocolError
from ..types import PatternSet

TRIANGLE_ORDER: tuple[str, ...] = ("top", "right", "bottom", "left")


def pattern_colors(value: int) -> tuple[bool, bool, bool, bool]:
    """Return ``(top, right, bottom, left)``; True means white."""
    if not 0 <= value <= 0xF:
        raise ProtocolError(
            f"cell value out of range: {value}",
            component="codec",
            operation="pattern_colors",
        )
    return (bool(value & 0x8), bool(value & 0x4), bool(value & 0x2), bool(value & 0x1))


def pattern_value(colors: Iterable[bool]) -> int:
    top, right, bottom, left = tuple(colors)
    return (int(top) << 3) | (int(right) << 2) | (int(bottom) << 1) | int(left)


def complement(value: int) -> int:
    """Swap black and white in all four triangles."""
    return value ^ 0xF


def popcount(value: int) -> int:
    return bin(value & 0xF).count("1")


def pattern_distance(a: int, b: int) -> int:
    return popcount(a ^ b)


def pattern_values(pattern_set: PatternSet) -> tuple[int, ...]:
    if pattern_set is PatternSet.FULL16:
        return tuple(range(16))
    if pattern_set is PatternSet.PARITY8:
        return tuple(v for v in range(16) if popcount(v) % 2 == 0)
    if pattern_set is PatternSet.BALANCED6:
        return tuple(v for v in range(16) if popcount(v) == 2)
    raise ProtocolError(f"unknown pattern set: {pattern_set}", component="codec")


def bits_per_cell(pattern_set: PatternSet) -> int:
    if pattern_set is PatternSet.FULL16:
        return 4
    if pattern_set is PatternSet.PARITY8:
        return 3
    if pattern_set is PatternSet.BALANCED6:
        return 0  # not a power-of-two alphabet
    raise ProtocolError(f"unknown pattern set: {pattern_set}", component="codec")


def min_distance(pattern_set: PatternSet) -> int:
    vals = pattern_values(pattern_set)
    return min(pattern_distance(a, b) for i, a in enumerate(vals) for b in vals[i + 1 :])


def encode_symbol(symbol: int, pattern_set: PatternSet) -> int:
    """Map a data symbol to a cell value for a given alphabet."""
    vals = pattern_values(pattern_set)
    if pattern_set is PatternSet.FULL16:
        if not 0 <= symbol < 16:
            raise ProtocolError(f"symbol out of range: {symbol}", component="codec")
        return symbol
    if pattern_set is PatternSet.PARITY8:
        if not 0 <= symbol < 8:
            raise ProtocolError(f"symbol out of range: {symbol}", component="codec")
        return vals[symbol]
    raise ProtocolError(
        "BALANCED6 has no binary symbol mapping",
        component="codec",
        operation="encode_symbol",
    )


def decode_symbol(value: int, pattern_set: PatternSet) -> tuple[int, int]:
    """Return ``(symbol, hamming_distance_to_alphabet)``.

    For a value outside the alphabet the nearest codeword is returned together
    with its distance, so callers can flag low-confidence observations instead
    of silently accepting an invalid pattern.
    """
    vals = pattern_values(pattern_set)
    if pattern_set is PatternSet.FULL16:
        return value, 0
    best = min(vals, key=lambda v: (pattern_distance(value, v), v))
    return vals.index(best), pattern_distance(value, best)


def alphabet_manifest(pattern_set: PatternSet) -> dict[str, object]:
    vals = pattern_values(pattern_set)
    return {
        "pattern_set": pattern_set.value,
        "bits_per_cell": bits_per_cell(pattern_set),
        "min_hamming_distance": min_distance(pattern_set),
        "size": len(vals),
        "values": list(vals),
        "table": [
            {
                "value": v,
                "binary": f"{v:04b}",
                "colors_top_right_bottom_left": pattern_colors(v),
            }
            for v in vals
        ],
    }
