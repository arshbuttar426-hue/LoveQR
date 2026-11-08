"""Temporal blink codebook: one 13-chip Barker sync plus three IDs.

The temporal layer is independent of the spatial layer.  A *blink word* is 26
chips: the 13-chip sync followed by one 13-chip ID.  Chips are transmitted as
whole-screen polarity changes and are observed by the camera as a temporal
intensity sequence (or, under rolling shutter, as bands in a single frame).

The codebook is fixed and versioned.  :func:`search_codebook` reproduces the
IDs from first principles; :func:`verify_codebook` reports the correlation
metrics that justify the choice.  The search criterion is:

* length 13, aperiodic autocorrelation sidelobe <= 2;
* minimise the largest absolute cross-correlation against the sync and the
  already-selected IDs, then minimise the imbalance.

No third-party sequence table is used.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import SyncError

LENGTH = 13

#: Barker-13: aperiodic autocorrelation sidelobes are exactly +/-1.
BARKER13: tuple[int, ...] = (1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1)

#: Deterministically selected low-cross-correlation IDs (see search_codebook).
ID_BITS: tuple[tuple[int, ...], ...] = (
    (0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0),
    (0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0),
    (0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0),
)


def _check_bits(bits: Sequence[int], name: str) -> tuple[int, ...]:
    values = tuple(int(b) for b in bits)
    if len(values) != LENGTH:
        raise SyncError(
            "blink code must have 13 chips",
            component="protocol",
            operation="blink",
            name=name,
            length=len(values),
        )
    if any(b not in (0, 1) for b in values):
        raise SyncError(
            "blink code chips must be 0 or 1",
            component="protocol",
            operation="blink",
            name=name,
        )
    return values


@dataclass(frozen=True)
class BlinkCode:
    name: str
    bits: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "bits", _check_bits(self.bits, self.name))

    def bipolar(self) -> tuple[int, ...]:
        return tuple(1 if b else -1 for b in self.bits)

    def waveform(
        self,
        *,
        on: float = 1.0,
        off: float = 0.0,
        repeat: int = 1,
    ) -> tuple[float, ...]:
        if repeat < 1:
            raise SyncError("repeat must be >= 1", component="protocol")
        levels = (off, on)
        return tuple(levels[b] for b in self.bits for _ in range(repeat))


SYNC = BlinkCode("sync", BARKER13)
BLINK_IDS: tuple[BlinkCode, ...] = tuple(
    BlinkCode(f"id{index}", bits) for index, bits in enumerate(ID_BITS)
)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in a))


def normalized_correlation(signal: Sequence[float], pattern: Sequence[float]) -> float:
    """Pearson normalised cross-correlation in [-1, 1].

    Both vectors are mean-centred, so a 0/1 observation of a bipolar pattern
    scores 1.0 and its inversion scores -1.0 regardless of absolute brightness.
    """
    if len(signal) != len(pattern) or not signal:
        raise SyncError(
            "correlation requires equally sized non-empty windows",
            component="protocol",
            operation="normalized_correlation",
            signal=len(signal),
            pattern=len(pattern),
        )
    n = len(signal)
    mean_signal = sum(float(x) for x in signal) / n
    mean_pattern = sum(float(x) for x in pattern) / n
    centred_signal = [float(x) - mean_signal for x in signal]
    centred_pattern = [float(x) - mean_pattern for x in pattern]
    denominator = _norm(centred_signal) * _norm(centred_pattern)
    if denominator == 0:
        return 0.0
    return _dot(centred_signal, centred_pattern) / denominator


def aperiodic_autocorrelation(bits: Sequence[int]) -> tuple[int, ...]:
    values = _check_bits(bits, "autocorrelation")
    bipolar = [1 if b else -1 for b in values]
    return tuple(
        sum(bipolar[i] * bipolar[i + lag] for i in range(LENGTH - lag))
        for lag in range(LENGTH)
    )


def max_sidelobe(bits: Sequence[int]) -> int:
    return max(abs(value) for value in aperiodic_autocorrelation(bits)[1:])


def cross_correlation(a: Sequence[int], b: Sequence[int]) -> int:
    """Largest absolute aperiodic cross-correlation over all shifts."""
    va = [1 if x else -1 for x in _check_bits(a, "cross")]
    vb = [1 if x else -1 for x in _check_bits(b, "cross")]
    scores: list[int] = []
    for lag in range(LENGTH):
        scores.append(sum(va[i] * vb[i + lag] for i in range(LENGTH - lag)))
        scores.append(sum(va[i + lag] * vb[i] for i in range(LENGTH - lag)))
    return max(abs(s) for s in scores)


@dataclass(frozen=True)
class SyncHit:
    offset: int
    score: float
    polarity: int  # +1 normal, -1 inverted

    def to_dict(self) -> dict[str, object]:
        return {"offset": self.offset, "score": self.score, "polarity": self.polarity}


@dataclass(frozen=True)
class BlinkDetection:
    offset: int
    sync_score: float
    sync_polarity: int
    id_index: int
    id_name: str
    id_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "offset": self.offset,
            "sync_score": self.sync_score,
            "sync_polarity": self.sync_polarity,
            "id_index": self.id_index,
            "id_name": self.id_name,
            "id_score": self.id_score,
        }


def find_sync(
    signal: Sequence[float],
    *,
    threshold: float = 0.6,
    min_separation: int = LENGTH // 2,
) -> list[SyncHit]:
    """Locate sync chips with non-maximum suppression.

    Both polarities are searched because the display may be inverted.
    """
    if len(signal) < LENGTH:
        return []
    pattern = SYNC.bipolar()
    hits: list[SyncHit] = []
    for offset in range(len(signal) - LENGTH + 1):
        window = signal[offset : offset + LENGTH]
        positive = normalized_correlation(window, pattern)
        negative = normalized_correlation(window, tuple(-p for p in pattern))
        if positive >= negative:
            score, polarity = positive, 1
        else:
            score, polarity = negative, -1
        if score >= threshold:
            hits.append(SyncHit(offset, score, polarity))
    accepted: list[SyncHit] = []
    for hit in sorted(hits, key=lambda h: (-h.score, h.offset)):
        if all(abs(hit.offset - other.offset) >= min_separation for other in accepted):
            accepted.append(hit)
    return sorted(accepted, key=lambda h: h.offset)


def classify_id(
    window: Sequence[float],
    *,
    polarity: int = 1,
) -> tuple[int, str, float]:
    """Return ``(index, name, score)`` for the best matching blink ID."""
    if len(window) != LENGTH:
        raise SyncError(
            "ID window must be 13 chips",
            component="protocol",
            operation="classify_id",
            length=len(window),
        )
    best: tuple[int, str, float] | None = None
    for index, code in enumerate(BLINK_IDS):
        pattern = tuple(polarity * p for p in code.bipolar())
        score = normalized_correlation(window, pattern)
        if best is None or score > best[2]:
            best = (index, code.name, score)
    assert best is not None
    return best


def find_blink_words(
    signal: Sequence[float],
    *,
    threshold: float = 0.6,
    id_threshold: float = 0.7,
) -> list[BlinkDetection]:
    """Find sync+ID words in a temporal signal."""
    detections: list[BlinkDetection] = []
    for hit in find_sync(signal, threshold=threshold):
        start = hit.offset + LENGTH
        if start + LENGTH > len(signal):
            continue
        index, name, score = classify_id(signal[start : start + LENGTH], polarity=hit.polarity)
        if score >= id_threshold:
            detections.append(
                BlinkDetection(
                    offset=hit.offset,
                    sync_score=hit.score,
                    sync_polarity=hit.polarity,
                    id_index=index,
                    id_name=name,
                    id_score=score,
                )
            )
    return detections


def encode_word(id_index: int) -> tuple[int, ...]:
    """Return the 26-chip sync+ID word for one blink ID."""
    if not 0 <= id_index < len(BLINK_IDS):
        raise SyncError(
            "blink id out of range",
            component="protocol",
            operation="encode_word",
            id_index=id_index,
        )
    return SYNC.bits + BLINK_IDS[id_index].bits


def search_codebook(max_sidelobe_bound: int = 2) -> tuple[tuple[int, ...], ...]:
    """Reproduce the ID codebook deterministically.

    Exhaustively enumerates all 13-bit sequences whose aperiodic
    autocorrelation sidelobe is within ``max_sidelobe_bound``, then greedily
    minimises the maximum cross-correlation against the sync and the IDs
    already chosen.  Ties are broken lexicographically, so the result is stable
    across Python versions.
    """
    if not 1 <= max_sidelobe_bound <= LENGTH:
        raise SyncError("invalid sidelobe bound", component="protocol")
    candidates = [
        bits
        for bits in itertools.product((0, 1), repeat=LENGTH)
        if max_sidelobe(bits) <= max_sidelobe_bound
    ]
    chosen: list[tuple[int, ...]] = []
    while len(chosen) < len(BLINK_IDS):
        best: tuple[tuple[int, int, int, tuple[int, ...]], tuple[int, ...]] | None = None
        for candidate in candidates:
            if candidate in chosen:
                continue
            peers = [BARKER13, *chosen]
            worst = max(cross_correlation(candidate, peer) for peer in peers)
            key = (worst, max_sidelobe(candidate), abs(sum(candidate) - 6.5), candidate)
            if best is None or key < best[0]:
                best = (key, candidate)
        assert best is not None
        chosen.append(best[1])
    return tuple(chosen)


def verify_codebook() -> dict[str, object]:
    """Correlation metrics for documentation and regression tests."""
    codes = (SYNC, *BLINK_IDS)
    pairwise = [
        {
            "a": codes[i].name,
            "b": codes[j].name,
            "max_abs_cross_correlation": cross_correlation(codes[i].bits, codes[j].bits),
        }
        for i in range(len(codes))
        for j in range(i + 1, len(codes))
    ]
    return {
        "length": LENGTH,
        "sync": {
            "bits": list(SYNC.bits),
            "autocorrelation": list(aperiodic_autocorrelation(SYNC.bits)),
            "max_sidelobe": max_sidelobe(SYNC.bits),
            "weight": sum(SYNC.bits),
        },
        "ids": [
            {
                "name": code.name,
                "bits": list(code.bits),
                "max_sidelobe": max_sidelobe(code.bits),
                "weight": sum(code.bits),
            }
            for code in BLINK_IDS
        ],
        "pairwise": pairwise,
        "max_pairwise_cross_correlation": max(
            entry["max_abs_cross_correlation"] for entry in pairwise  # type: ignore[index]
        ),
        "reproduced_by_search": search_codebook() == ID_BITS,
        "search_criterion": (
            "length 13; sidelobe <= 2; greedy minimum max cross-correlation "
            "against sync and previously chosen IDs; lexical tie-break"
        ),
    }
