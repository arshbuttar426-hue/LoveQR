"""Shared-dictionary compression tests."""

from __future__ import annotations

import os
import random

import pytest

from otl.compress.dictionary import (
    HEADER,
    MAGIC,
    OP_NAMES,
    compress,
    decompress,
    manifest,
)
from otl.config import CompressionConfig
from otl.errors import CompressionError


CORPORA = {
    "empty": b"",
    "single": b"A",
    "repeat": b"\x00" * 5000,
    "sequence": bytes(range(256)) * 20,
    "inverted": bytes([0, 255]) * 1000,
    "text": b"the quick brown fox jumps over the lazy dog. " * 100,
    "random": random.Random(1).randbytes(4096),
    "mixed": b"A" * 1000 + random.Random(2).randbytes(500) + bytes(range(200)) * 3,
}


@pytest.mark.parametrize("name", sorted(CORPORA))
def test_roundtrip(name: str) -> None:
    data = CORPORA[name]
    blob, stats = compress(data)
    assert decompress(blob) == data
    assert stats.original == len(data)
    assert stats.compressed == len(blob)
    assert blob[:4] == MAGIC


def test_compression_is_deterministic() -> None:
    data = CORPORA["mixed"]
    assert compress(data)[0] == compress(data)[0]


def test_repetitive_data_compresses() -> None:
    blob, stats = compress(CORPORA["repeat"])
    assert stats.ratio > 10.0
    assert stats.ops["REPEAT"] > 0


def test_random_data_does_not_expand_much() -> None:
    data = CORPORA["random"]
    blob, _ = compress(data)
    assert len(blob) <= len(data) + len(data) // 50 + HEADER.size + 16


def test_invert_opcode_is_used() -> None:
    data = CORPORA["inverted"]
    _, stats = compress(data, CompressionConfig(use_invert_op=True))
    assert stats.ops["INVERT"] > 0


def test_invert_can_be_disabled() -> None:
    data = CORPORA["inverted"]
    blob, stats = compress(data, CompressionConfig(use_invert_op=False))
    assert stats.ops["INVERT"] == 0
    assert decompress(blob) == data


def test_bad_magic_and_version() -> None:
    with pytest.raises(CompressionError):
        decompress(b"XXXX\x01\x00\x00\x00\x00")
    with pytest.raises(CompressionError):
        decompress(b"OTL1\x02\x00\x00\x00\x00")


def test_truncated_and_overrun_blobs() -> None:
    blob, _ = compress(b"hello world")
    with pytest.raises(CompressionError):
        decompress(blob[:-1])
    with pytest.raises(CompressionError):
        decompress(blob[:5])


def test_unknown_opcode() -> None:
    blob = HEADER.pack(MAGIC, 1, 1) + bytes([0xFF])
    with pytest.raises(CompressionError):
        decompress(blob)


def test_manifest() -> None:
    info = manifest()
    assert info["magic"] == "OTL1"
    assert info["version"] == 1
    assert set(info["opcodes"].values()) == set(OP_NAMES.values())  # type: ignore[arg-type]
