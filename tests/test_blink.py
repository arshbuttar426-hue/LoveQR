"""Blink codebook and detection tests."""

from __future__ import annotations

import random

import pytest

from otl.errors import SyncError
from otl.protocol.blink import (
    BARKER13,
    BLINK_IDS,
    ID_BITS,
    LENGTH,
    SYNC,
    aperiodic_autocorrelation,
    classify_id,
    cross_correlation,
    encode_word,
    find_blink_words,
    find_sync,
    max_sidelobe,
    normalized_correlation,
    search_codebook,
    verify_codebook,
)


def test_barker13_has_unit_sidelobes() -> None:
    assert max_sidelobe(BARKER13) == 1
    assert aperiodic_autocorrelation(BARKER13)[0] == LENGTH


def test_id_codebook_properties() -> None:
    for bits in ID_BITS:
        assert len(bits) == LENGTH
        assert max_sidelobe(bits) <= 2
    for i, a in enumerate(ID_BITS):
        for b in ID_BITS[i + 1 :]:
            assert cross_correlation(a, b) <= 5


def test_search_reproduces_hardcoded_codebook() -> None:
    assert search_codebook() == ID_BITS


def test_verify_codebook() -> None:
    report = verify_codebook()
    assert report["reproduced_by_search"] is True
    assert report["sync"]["max_sidelobe"] == 1  # type: ignore[index]
    assert report["max_pairwise_cross_correlation"] <= 5


def test_normalized_correlation_extremes() -> None:
    pattern = SYNC.bipolar()
    assert normalized_correlation(tuple(float(b) for b in SYNC.bits), pattern) == pytest.approx(1.0)
    assert normalized_correlation(tuple(1.0 - b for b in SYNC.bits), pattern) == pytest.approx(-1.0)
    assert normalized_correlation([0.5] * LENGTH, pattern) == 0.0
    with pytest.raises(SyncError):
        normalized_correlation([0.0] * 12, pattern)


def test_encode_word_and_detection_all_ids() -> None:
    for index in range(len(BLINK_IDS)):
        word = encode_word(index)
        assert len(word) == 2 * LENGTH
        signal = [0.1] * 4 + [float(b) for b in word] + [0.1] * 4
        detections = find_blink_words(signal)
        assert len(detections) == 1
        hit = detections[0]
        assert hit.offset == 4
        assert hit.id_index == index
        assert hit.sync_polarity == 1
        assert hit.sync_score == pytest.approx(1.0)
        assert hit.id_score == pytest.approx(1.0)


def test_inverted_detection() -> None:
    word = encode_word(1)
    signal = [1.0 - float(b) for b in word]
    detections = find_blink_words(signal)
    assert len(detections) == 1
    assert detections[0].id_index == 1
    assert detections[0].sync_polarity == -1


def test_detection_under_noise() -> None:
    rng = random.Random(99)
    for index in range(len(BLINK_IDS)):
        word = encode_word(index)
        signal = [0.1] * 3 + [float(b) + rng.gauss(0.0, 0.12) for b in word] + [0.1] * 3
        detections = find_blink_words(signal)
        assert detections, f"id {index} not detected"
        assert detections[0].id_index == index


def test_classify_id_validation() -> None:
    with pytest.raises(SyncError):
        classify_id([0.0] * 12)
    with pytest.raises(SyncError):
        encode_word(3)
    assert find_sync([0.0] * 5) == []


def test_no_false_positive_on_flat_signal() -> None:
    assert find_blink_words([0.5] * 100) == []
