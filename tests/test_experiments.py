"""Regression tests for experiment definitions.

These do not run an experiment; they lock the properties that make a recorded
run reproducible: the payload generator is deterministic, the full-mode matrix
has the documented size, and the payload fingerprint is order-independent.
"""

from __future__ import annotations

from experiments.e09_end_to_end import (
    CHANNEL_NAMES,
    DROPS,
    KINDS,
    SIZES,
    _fingerprint,
    _payload,
    _payload_seed,
    _sha256,
)


def test_full_mode_matrix_is_64_trials() -> None:
    # The user-facing claim is "64 full-mode trials"; keep it tied to the code.
    assert len(KINDS) * len(SIZES) * len(CHANNEL_NAMES) * len(DROPS) == 64


def test_random_payloads_are_seeded_and_stable() -> None:
    first = _payload("random", 100)
    second = _payload("random", 100)
    assert first == second
    assert _sha256(first) == _sha256(second)
    assert _payload_seed("random", 100) == 7100
    # Golden hashes: a change here means recorded E09 runs no longer reproduce.
    assert _sha256(first) == (
        "9c32e072fc4ae9f6a38a6795f08ea6e8ebd3a737550bcab2a61be7eab8e2bfdf"
    )
    assert first != _payload("random", 1000)
    assert _payload("text", 100) != first


def test_text_payload_is_the_documented_template() -> None:
    data = _payload("text", 100)
    assert len(data) == 100
    assert _payload_seed("text", 100) is None
    assert _sha256(data) == (
        "982e9a33c8a4f51171b39d2fbd21f1e16bf0416b1a241f114980717670c5a715"
    )


def test_fingerprint_is_order_independent_and_sensitive() -> None:
    a = _fingerprint(["x", "y"])
    b = _fingerprint(["y", "x"])
    assert a == b
    assert a != _fingerprint(["x", "z"])
