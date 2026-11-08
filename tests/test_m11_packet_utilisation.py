"""M11 packet-utilisation tests: header, capacity, bundle, adaptive, arms."""

from __future__ import annotations

import hashlib
import io

import pytest

from experiments import e13_packet_utilisation as e13
from experiments.harness import RunContext
from experiments.m11_payloads import (
    ARM_IDS,
    DICTIONARY_BYTES,
    all_arms,
    build_arm,
    repeated_instructions,
    seeded_bytes,
)
from otl.compress.adaptive import choose_encoding
from otl.compress.dictionary import compress, decompress
from otl.errors import ProtocolError, ReconstructionError
from otl.protocol.m11 import (
    COMPACT_HEADER_SIZE,
    CompactFileHeader,
    M11_FILE_VERSION,
    BundleEntry,
    data_bytes_per_block,
    decode_packet_v2,
    max_payload_bytes,
    packet_capacity,
    packet_data_bytes,
    pack_bundle,
    plan_total_packets_v2,
    reassemble_v2,
    unpack_bundle,
)
from otl.protocol.packet import plan_total_packets


def _group(frames):
    grouped: dict[int, dict[int, bytes]] = {}
    for header, data in frames:
        grouped.setdefault(header.packet_id, {})[header.frame_index] = data
    return grouped


def _recover(arm):
    grouped = _group(arm.frames)
    decoded = e13._decode_arm_frames(
        grouped, header_kind=arm.header_kind, nsym=arm.nsym
    )
    return e13._recover_arm(decoded, header_kind=arm.header_kind)


# ---------------------------------------------------------------------------
# Header and capacity arithmetic
# ---------------------------------------------------------------------------


def test_compact_header_roundtrip_and_limits() -> None:
    header = CompactFileHeader(
        version=M11_FILE_VERSION,
        flags=0,
        total_packets=3,
        original_len=145745,
        payload_len=2420,
        payload_crc32=0xDEADBEEF,
    )
    raw = header.to_bytes()
    assert len(raw) == COMPACT_HEADER_SIZE == 15
    restored = CompactFileHeader.from_bytes(raw)
    assert restored == header
    assert not restored.compressed
    with pytest.raises(ProtocolError):
        CompactFileHeader(
            version=1,
            flags=0,
            total_packets=1,
            original_len=1,
            payload_len=1,
            payload_crc32=0,
        )
    with pytest.raises(ProtocolError):
        CompactFileHeader(
            version=M11_FILE_VERSION,
            flags=0,
            total_packets=1,
            original_len=0x1000000,
            payload_len=1,
            payload_crc32=0,
        )


def test_capacity_arithmetic_tracks_nsym() -> None:
    assert data_bytes_per_block(32) == 223
    assert packet_data_bytes(32) == 2453
    assert packet_data_bytes(24) == 2541
    assert packet_data_bytes(16) == 2629
    assert packet_capacity(0, nsym=32, header_size=32) == 2421
    assert packet_capacity(0, nsym=32, header_size=15) == 2438
    assert packet_capacity(0, nsym=24, header_size=15) == 2526
    assert plan_total_packets_v2(2526, nsym=24, header_size=15) == 1
    assert plan_total_packets_v2(2527, nsym=24, header_size=15) == 2
    assert max_payload_bytes(nsym=24, header_size=15) == 2526 + 15 * 2541


# ---------------------------------------------------------------------------
# Packet codec
# ---------------------------------------------------------------------------


def test_capacity_aware_packet_survives_the_full_erasure_budget() -> None:
    arm = build_arm("A5_rs24")
    frames = _group(arm.frames)[0]
    for drop in (0, 1, 12, 24):
        damaged = {
            index: data
            for index, data in frames.items()
            if index < 255 - drop
        }
        decoded = decode_packet_v2(0, damaged, nsym=24)
        assert decoded.stats.frames_missing == drop
        assert decoded.stats.block_failures == []
        assert decoded.chunk[:50] == arm.wire[:50]
    too_many = {index: data for index, data in frames.items() if index < 230}
    with pytest.raises(ReconstructionError):
        decode_packet_v2(0, too_many, nsym=24)


def test_v2_file_roundtrip_with_compact_header() -> None:
    arm = build_arm("A5_rs24")
    header, wire, raw = _recover(arm)
    assert header.total_packets == 1
    assert header.original_len == len(raw)
    assert header.payload_len == len(wire)
    assert hashlib.sha256(wire).hexdigest() == arm.wire_sha256
    assert hashlib.sha256(raw).hexdigest() == arm.application_sha256


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------


def test_bundle_roundtrip_with_crc_and_sha() -> None:
    entries = [
        BundleEntry("one.bin", b"\x00\x01\x02" * 10),
        BundleEntry("two.txt", b"hello bundle" * 7),
    ]
    for include_sha in (False, True):
        blob = pack_bundle(entries, include_sha256=include_sha)
        recovered = unpack_bundle(blob)
        assert [entry.name for entry in recovered] == ["one.bin", "two.txt"]
        assert [entry.data for entry in recovered] == [entry.data for entry in entries]
        assert all(
            entry.sha256 == hashlib.sha256(entry.data).hexdigest()
            for entry in recovered
        ) if include_sha else True


def test_bundle_detects_corruption() -> None:
    blob = bytearray(pack_bundle([BundleEntry("a.bin", b"abcdef" * 20)]))
    blob[-1] ^= 0xFF
    with pytest.raises(ProtocolError):
        unpack_bundle(bytes(blob))


def test_bundle_arms_verify_every_entry() -> None:
    arm = build_arm("A2_bundle")
    assert arm.bundle is not None
    _header, wire, raw = _recover(arm)
    recovered = unpack_bundle(raw)
    assert len(recovered) == len(arm.bundle)
    assert sum(len(entry.data) for entry in recovered) == arm.application_bytes
    for actual, expected in zip(recovered, arm.bundle):
        assert actual.name == expected.name
        assert hashlib.sha256(actual.data).hexdigest() == hashlib.sha256(
            expected.data
        ).hexdigest()


# ---------------------------------------------------------------------------
# Adaptive compression
# ---------------------------------------------------------------------------


def test_adaptive_choice_keeps_raw_when_compression_expands() -> None:
    data = seeded_bytes(1113, 2421)
    choice = choose_encoding(data)
    assert choice.compressed is False
    assert choice.wire == data
    assert choice.decode() == data
    packed, _stats = compress(data)
    assert len(packed) > len(data)


def test_adaptive_choice_uses_compression_when_smaller() -> None:
    data = repeated_instructions(8192)
    choice = choose_encoding(data)
    assert choice.compressed is True
    assert len(choice.wire) < len(data)
    assert decompress(choice.wire) == data


# ---------------------------------------------------------------------------
# All arms
# ---------------------------------------------------------------------------


def test_every_m11_arm_roundtrips_and_matches_sha256() -> None:
    for arm in all_arms():
        header, wire, raw = _recover(arm)
        assert header.total_packets == arm.total_packets
        assert len(wire) == len(arm.wire)
        assert hashlib.sha256(wire).hexdigest() == arm.wire_sha256
        if arm.bundle is not None:
            recovered = unpack_bundle(raw)
            assert len(recovered) == len(arm.bundle)
            for actual, expected in zip(recovered, arm.bundle):
                assert hashlib.sha256(actual.data).hexdigest() == hashlib.sha256(
                    expected.data
                ).hexdigest()
        else:
            assert hashlib.sha256(raw).hexdigest() == arm.application_sha256


def test_dictionary_arm_fits_one_packet_and_raw_would_not() -> None:
    arm = build_arm("A3_dictionary")
    assert arm.application_bytes == DICTIONARY_BYTES == 145745
    assert arm.total_packets == 1
    assert arm.compressed is True
    assert len(arm.wire) <= 2421
    # The same bytes without the dictionary cannot fit the 16-packet limit.
    assert plan_total_packets(DICTIONARY_BYTES) > 16


def test_always_on_compression_costs_a_second_packet() -> None:
    adaptive = build_arm("A1_fill_adaptive")
    always = build_arm("A4_always_on")
    assert adaptive.wire == always.application_payload
    assert adaptive.total_packets == 1
    assert always.total_packets == 2
    assert always.frame_count == 2 * 255


# ---------------------------------------------------------------------------
# Accounting and discovery
# ---------------------------------------------------------------------------


def test_utilisation_identity_and_frozen_root_cause() -> None:
    cfg = e13
    frozen = cfg.utilisation_budget(
        display_fps=10.0,
        expected_frames=255,
        application_bytes=317,
        wire_bytes=294,
        compressed=True,
        nsym=32,
        header_bytes=32,
        total_packets=1,
        packet_data_bytes=2453,
    )
    assert frozen["packet_fill_payload"] == pytest.approx(294 / 2453)
    assert frozen["packet_fill_incl_header"] == pytest.approx(326 / 2453)
    assert frozen["application_bytes_per_frame"] == pytest.approx(317 / 255)
    assert frozen["padding_bps"] + frozen["file_header_bps"] == pytest.approx(
        2453 * 8 / 25.5 - 294 * 8 / 25.5
    )
    assert frozen["residual_bps"] == pytest.approx(0.0, abs=1e-9)
    assert frozen["dominant_loss"]["stage"] == "unused_packet_padding"

    filled = cfg.utilisation_budget(
        display_fps=10.0,
        expected_frames=255,
        application_bytes=2421,
        wire_bytes=2421,
        compressed=False,
        nsym=32,
        header_bytes=32,
        total_packets=1,
        packet_data_bytes=2453,
    )
    assert filled["packet_fill_incl_header"] == pytest.approx(1.0)
    assert filled["residual_bps"] == pytest.approx(0.0, abs=1e-9)


def _context(tmp_path, sessions=None) -> RunContext:
    ctx = RunContext(
        spec=e13.SPEC,
        run_id="test-run",
        out_dir=tmp_path,
        options={"sessions": [str(item) for item in sessions]} if sessions else {},
    )
    ctx._raw = io.StringIO()
    return ctx


def test_m11_discovery_ignores_m9_and_m10_sessions(tmp_path, monkeypatch) -> None:
    root = tmp_path / "physical"
    root.mkdir()
    for name in ("m9-old", "m10-old", "m11-new"):
        child = root / name
        child.mkdir()
        (child / "session.json").write_text("{}", encoding="utf-8")
        (child / "session.lock.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(e13, "SESSIONS_ROOT", root)
    paths = e13._session_paths(_context(tmp_path))
    assert [path.name for path in paths] == ["m11-new"]
