"""Packet layer tests: file header, interleaving, loss and rejection."""

from __future__ import annotations

import random

import pytest

from otl.errors import ProtocolError, ReconstructionError
from otl.protocol.packet import (
    FILE_HEADER_SIZE,
    FRAMES_PER_PACKET,
    MAX_PACKETS,
    PACKET_BYTES,
    PAYLOAD_0,
    FileHeader,
    build_file,
    decode_packet,
    encode_packet,
    packet_manifest,
    plan_total_packets,
    reassemble,
)


def _file(payload: bytes, name: str = "payload.bin") -> tuple[FileHeader, list]:
    return build_file(payload, name, compressed=False, original_len=len(payload))


def _decode_with_loss(packet, lost: set[int]):
    received = {i: frame for i, frame in enumerate(packet.frames) if i not in lost}
    return decode_packet(packet.packet_id, received)


def test_file_header_roundtrip() -> None:
    header = FileHeader(
        version=1,
        flags=0,
        packet_id=0,
        total_packets=3,
        original_len=10000,
        payload_len=9000,
        payload_crc32=0xDEADBEEF,
        name="report.pdf",
    )
    raw = header.to_bytes()
    assert len(raw) == FILE_HEADER_SIZE == 32
    assert FileHeader.from_bytes(raw) == header


def test_file_header_validation() -> None:
    base = dict(
        version=1,
        flags=0,
        packet_id=0,
        total_packets=1,
        original_len=1,
        payload_len=1,
        payload_crc32=0,
        name="a",
    )
    with pytest.raises(ProtocolError):
        FileHeader(**{**base, "version": 2})
    with pytest.raises(ProtocolError):
        FileHeader(**{**base, "packet_id": 16})
    with pytest.raises(ProtocolError):
        FileHeader(**{**base, "total_packets": 17})
    with pytest.raises(ProtocolError):
        FileHeader(**{**base, "name": "x" * 14})
    with pytest.raises(ProtocolError):
        FileHeader.from_bytes(b"\x00" * 32)


def test_plan_total_packets() -> None:
    assert plan_total_packets(0) == 1
    assert plan_total_packets(PAYLOAD_0) == 1
    assert plan_total_packets(PAYLOAD_0 + 1) == 2
    assert plan_total_packets(PAYLOAD_0 + PACKET_BYTES) == 2
    assert plan_total_packets(PAYLOAD_0 + PACKET_BYTES + 1) == 3


@pytest.mark.parametrize("size", [0, 1, 11, 1000, PAYLOAD_0, PAYLOAD_0 + 1, 6000, 20000])
def test_full_file_roundtrip(size: int) -> None:
    payload = random.Random(size).randbytes(size)
    header, packets = _file(payload)
    decoded = {}
    for packet in packets:
        decoded[packet.packet_id] = _decode_with_loss(packet, set())
    recovered_header, recovered = reassemble(decoded)
    assert recovered == payload
    assert recovered_header == header


def test_interleaving_spreads_frames_across_blocks() -> None:
    payload = bytes(range(256)) * 20
    _, packets = _file(payload)
    packet = packets[0]
    assert len(packet.frames) == FRAMES_PER_PACKET
    assert all(len(frame) == 11 for frame in packet.frames)
    # Frame n carries byte n of every block, so frames differ in every lane.
    for lane in range(11):
        column = bytes(frame[lane] for frame in packet.frames)
        assert len(column) == FRAMES_PER_PACKET


def test_survives_32_lost_frames() -> None:
    payload = random.Random(11).randbytes(5000)
    _, packets = _file(payload)
    decoded = {}
    for packet in packets:
        lost = set(random.Random(100 + packet.packet_id).sample(range(255), 32))
        decoded[packet.packet_id] = _decode_with_loss(packet, lost)
        assert decoded[packet.packet_id].stats.frames_missing == 32
    _, recovered = reassemble(decoded)
    assert recovered == payload


def test_33_lost_frames_is_rejected() -> None:
    _, packets = _file(random.Random(12).randbytes(3000))
    packet = packets[0]
    lost = set(range(33))
    with pytest.raises(ReconstructionError):
        _decode_with_loss(packet, lost)


def test_byte_errors_consume_capacity() -> None:
    payload = random.Random(13).randbytes(3000)
    _, packets = _file(payload)
    packet = packets[0]
    received = {i: bytearray(frame) for i, frame in enumerate(packet.frames)}
    # 16 byte errors per block + 0 erasures is exactly capacity.
    rng = random.Random(14)
    for lane in range(11):
        for frame_index in rng.sample(range(255), 16):
            received[frame_index][lane] ^= rng.randrange(1, 256)
    decoded = decode_packet(0, {i: bytes(v) for i, v in received.items()})
    assert decoded.header is not None


def test_manifest() -> None:
    info = packet_manifest()
    assert info["frames_per_packet"] == 255
    assert info["packet_bytes"] == 2453
    assert info["max_packets"] == MAX_PACKETS
    assert info["max_payload_bytes"] == PAYLOAD_0 + (MAX_PACKETS - 1) * PACKET_BYTES


def test_too_many_packets_rejected() -> None:
    huge = bytes(PAYLOAD_0 + (MAX_PACKETS - 1) * PACKET_BYTES + 1)
    with pytest.raises(ProtocolError):
        build_file(huge, "x", compressed=False, original_len=len(huge))


def test_encode_packet_validation() -> None:
    with pytest.raises(ProtocolError):
        encode_packet(0, b"x")  # missing header
    with pytest.raises(ProtocolError):
        encode_packet(16, b"")
    with pytest.raises(ProtocolError):
        encode_packet(1, bytes(PACKET_BYTES + 1))
