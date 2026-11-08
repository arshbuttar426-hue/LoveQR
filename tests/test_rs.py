"""Reed-Solomon tests: errors, erasures, mixed errata and rejection."""

from __future__ import annotations

import random

import pytest

from otl.ecc.rs import (
    decode,
    encode,
    generator_poly,
    max_erasures,
    max_errors,
)
from otl.errors import ECCError


def _codeword(nsym: int, rng: random.Random) -> tuple[bytes, bytes]:
    msg = bytes(rng.randrange(256) for _ in range(255 - nsym))
    return msg, encode(msg, nsym)


def _corrupt(
    cw: bytearray,
    rng: random.Random,
    *,
    n_errors: int,
    n_erasures: int,
) -> tuple[list[int], list[int]]:
    positions = rng.sample(range(255), n_errors + n_erasures)
    error_positions = positions[:n_errors]
    erasure_positions = positions[n_errors:]
    for position in error_positions:
        cw[position] ^= rng.randrange(1, 256)
    for position in erasure_positions:
        cw[position] = rng.randrange(256)
    return error_positions, erasure_positions


def test_generator_degree_and_roots() -> None:
    from otl.ecc.rs import GF_EXP, poly_eval

    for nsym in (1, 8, 16, 32):
        generator = generator_poly(nsym)
        assert len(generator) == nsym + 1
        assert generator[0] == 1
        for root_exponent in range(nsym):
            assert poly_eval(generator, GF_EXP[root_exponent]) == 0


@pytest.mark.parametrize("nsym", [16, 32])
def test_errors_only_up_to_capacity(nsym: int) -> None:
    rng = random.Random(1000 + nsym)
    for n_errors in range(max_errors(nsym) + 1):
        for _ in range(8):
            msg, codeword = _codeword(nsym, rng)
            corrupted = bytearray(codeword)
            _corrupt(corrupted, rng, n_errors=n_errors, n_erasures=0)
            corrected, count = decode(bytes(corrupted), nsym)
            assert corrected == codeword
            assert count == n_errors


@pytest.mark.parametrize("nsym", [16, 32])
def test_erasures_only_up_to_capacity(nsym: int) -> None:
    rng = random.Random(2000 + nsym)
    for n_erasures in (1, 2, 4, 8, nsym):
        for _ in range(6):
            msg, codeword = _codeword(nsym, rng)
            corrupted = bytearray(codeword)
            _, erasures = _corrupt(corrupted, rng, n_errors=0, n_erasures=n_erasures)
            corrected, count = decode(bytes(corrupted), nsym, erasures=erasures)
            assert corrected == codeword
            assert count == n_erasures


@pytest.mark.parametrize("nsym", [16, 32])
def test_mixed_errata_inside_capacity(nsym: int) -> None:
    rng = random.Random(3000 + nsym)
    cases = [(e, r) for e in range(1, max_errors(nsym) + 1) for r in (1, 2, 4, 8)]
    for n_errors, n_erasures in cases:
        if 2 * n_errors + n_erasures > nsym:
            continue
        for _ in range(3):
            msg, codeword = _codeword(nsym, rng)
            corrupted = bytearray(codeword)
            _, erasures = _corrupt(
                corrupted, rng, n_errors=n_errors, n_erasures=n_erasures
            )
            corrected, _ = decode(bytes(corrupted), nsym, erasures=erasures)
            assert corrected == codeword


def test_no_error_is_unchanged() -> None:
    rng = random.Random(4)
    _, codeword = _codeword(32, rng)
    assert decode(codeword, 32) == (codeword, 0)


def test_over_capacity_is_rejected_not_miscorrected() -> None:
    rng = random.Random(5)
    nsym = 32
    for _ in range(40):
        _, codeword = _codeword(nsym, rng)
        corrupted = bytearray(codeword)
        _corrupt(corrupted, rng, n_errors=max_errors(nsym) + 1, n_erasures=0)
        with pytest.raises(ECCError):
            decode(bytes(corrupted), nsym)
    for _ in range(40):
        _, codeword = _codeword(nsym, rng)
        corrupted = bytearray(codeword)
        _, erasures = _corrupt(corrupted, rng, n_errors=0, n_erasures=nsym + 1)
        with pytest.raises(ECCError):
            decode(bytes(corrupted), nsym, erasures=erasures)


def test_input_validation() -> None:
    with pytest.raises(ECCError):
        encode(b"x" * 224, 32)
    with pytest.raises(ECCError):
        decode(b"x" * 254, 32)
    with pytest.raises(ECCError):
        decode(bytes(255), 32, erasures=list(range(33)))
    with pytest.raises(ECCError):
        decode(bytes(255), 32, erasures=[-1])


def test_capacity_helpers() -> None:
    assert max_errors(32) == 16
    assert max_erasures(32) == 32
