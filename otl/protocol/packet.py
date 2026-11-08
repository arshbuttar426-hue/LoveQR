"""Packet layer: RS(255,223) blocks, byte interleaving and file framing.

A packet is exactly 255 spatial frames.  Every frame carries one byte from
each of 11 RS blocks (byte interleaving), so losing a whole frame costs one
erasure in every block instead of destroying a single block.  With
``nsym = 32`` a packet survives up to 32 lost frames, or a mix satisfying
``2 * byte_errors + lost_frames <= 32`` per block.

The first packet starts with a fixed 32-byte file header.  Packet ids are the
4-bit field of the on-screen frame header, therefore a transfer can span at
most 16 packets (about 38 KiB before compression).  This limit is a protocol
property, not an implementation detail, and is reported by
:func:`packet_manifest`.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Mapping
from dataclasses import dataclass, field

from ..ecc.crc import crc32
from ..ecc.rs import decode as rs_decode
from ..ecc.rs import encode as rs_encode
from ..errors import ECCError, ProtocolError, ReconstructionError
from ..types import FrameHeader
from .frame import pack_frame

FILE_MAGIC = b"OT"
FILE_VERSION = 1
FILE_HEADER_STRUCT = struct.Struct(">2sBBBBIIIB13s")
FILE_HEADER_SIZE = FILE_HEADER_STRUCT.size  # 32
NAME_MAX = 13

BLOCK_DATA_BYTES = 223
BLOCKS_PER_PACKET = 11
PACKET_BYTES = BLOCK_DATA_BYTES * BLOCKS_PER_PACKET  # 2453
FRAMES_PER_PACKET = 255
DATA_BYTES_PER_FRAME = BLOCKS_PER_PACKET  # 11
MAX_PACKETS = 0x10  # 4-bit packet id
PAYLOAD_0 = PACKET_BYTES - FILE_HEADER_SIZE  # 2421

FLAG_COMPRESSED = 0x01


@dataclass(frozen=True)
class FileHeader:
    """32-byte file header carried at the start of packet 0."""

    version: int
    flags: int
    packet_id: int
    total_packets: int
    original_len: int
    payload_len: int
    payload_crc32: int
    name: str

    def __post_init__(self) -> None:
        if self.version != FILE_VERSION:
            raise ProtocolError(
                "unsupported file header version",
                component="protocol",
                operation="FileHeader",
                version=self.version,
            )
        if not 0 <= self.packet_id < MAX_PACKETS:
            raise ProtocolError(
                "packet id must fit the 4-bit frame header",
                component="protocol",
                operation="FileHeader",
                packet_id=self.packet_id,
            )
        if not 1 <= self.total_packets <= MAX_PACKETS:
            raise ProtocolError(
                "total_packets out of range",
                component="protocol",
                operation="FileHeader",
                total_packets=self.total_packets,
            )
        if len(self.name.encode("utf-8")) > NAME_MAX:
            raise ProtocolError(
                "file name too long for the header",
                component="protocol",
                operation="FileHeader",
                name=self.name,
                max_bytes=NAME_MAX,
            )
        for value in (self.original_len, self.payload_len, self.payload_crc32):
            if not 0 <= value <= 0xFFFFFFFF:
                raise ProtocolError(
                    "header field outside uint32",
                    component="protocol",
                    operation="FileHeader",
                    value=value,
                )

    @property
    def compressed(self) -> bool:
        return bool(self.flags & FLAG_COMPRESSED)

    def to_bytes(self) -> bytes:
        name = self.name.encode("utf-8")
        return FILE_HEADER_STRUCT.pack(
            FILE_MAGIC,
            self.version,
            self.flags,
            self.packet_id,
            self.total_packets,
            self.original_len,
            self.payload_len,
            self.payload_crc32,
            len(name),
            name.ljust(NAME_MAX, b"\x00"),
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "FileHeader":
        if len(raw) != FILE_HEADER_SIZE:
            raise ProtocolError(
                "wrong file header size",
                component="protocol",
                operation="FileHeader.from_bytes",
                expected=FILE_HEADER_SIZE,
                actual=len(raw),
            )
        (
            magic,
            version,
            flags,
            packet_id,
            total_packets,
            original_len,
            payload_len,
            payload_crc32,
            name_len,
            name_raw,
        ) = FILE_HEADER_STRUCT.unpack(raw)
        if magic != FILE_MAGIC:
            raise ProtocolError(
                "bad file magic",
                component="protocol",
                operation="FileHeader.from_bytes",
                magic=magic.hex(),
            )
        if name_len > NAME_MAX:
            raise ProtocolError(
                "name length outside header field",
                component="protocol",
                operation="FileHeader.from_bytes",
                name_len=name_len,
            )
        try:
            name = name_raw[:name_len].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError(
                "file name is not valid UTF-8",
                component="protocol",
                operation="FileHeader.from_bytes",
            ) from exc
        return cls(
            version=version,
            flags=flags,
            packet_id=packet_id,
            total_packets=total_packets,
            original_len=original_len,
            payload_len=payload_len,
            payload_crc32=payload_crc32,
            name=name,
        )


@dataclass(frozen=True)
class Packet:
    """Encoded packet: 255 frames of 11 bytes each."""

    packet_id: int
    header: FileHeader | None
    frames: tuple[bytes, ...]

    def __post_init__(self) -> None:
        if len(self.frames) != FRAMES_PER_PACKET:
            raise ProtocolError(
                "packet must contain 255 frames",
                component="protocol",
                operation="Packet",
                frames=len(self.frames),
            )
        if any(len(f) != DATA_BYTES_PER_FRAME for f in self.frames):
            raise ProtocolError(
                "each frame must carry 11 bytes",
                component="protocol",
                operation="Packet",
            )

    def iter_frames(self) -> tuple[tuple[FrameHeader, bytes], ...]:
        return tuple(
            (FrameHeader(self.packet_id, i), frame) for i, frame in enumerate(self.frames)
        )

    def to_cells(self) -> tuple[tuple[int, ...], ...]:
        """Render every frame to its 30 cell values."""
        return tuple(pack_frame(h, data) for h, data in self.iter_frames())


@dataclass
class PacketStats:
    frames_present: int = 0
    frames_missing: int = 0
    erasures: list[int] = field(default_factory=list)
    corrected_per_block: list[int] = field(default_factory=list)
    block_failures: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "frames_present": self.frames_present,
            "frames_missing": self.frames_missing,
            "erasures": list(self.erasures),
            "corrected_per_block": list(self.corrected_per_block),
            "block_failures": list(self.block_failures),
        }


@dataclass(frozen=True)
class DecodedPacket:
    packet_id: int
    header: FileHeader | None
    chunk: bytes
    stats: PacketStats


def plan_total_packets(payload_len: int) -> int:
    if payload_len < 0:
        raise ProtocolError("payload length must be >= 0", component="protocol")
    if payload_len <= PAYLOAD_0:
        return 1
    return 1 + math.ceil((payload_len - PAYLOAD_0) / PACKET_BYTES)


def encode_packet(
    packet_id: int,
    chunk: bytes,
    *,
    header: FileHeader | None = None,
    nsym: int = 32,
) -> Packet:
    """Encode one packet's payload chunk into 255 interleaved frames."""
    if not 0 <= packet_id < MAX_PACKETS:
        raise ProtocolError(
            "packet id out of range",
            component="protocol",
            operation="encode_packet",
            packet_id=packet_id,
        )
    capacity = PAYLOAD_0 if packet_id == 0 else PACKET_BYTES
    if len(chunk) > capacity:
        raise ProtocolError(
            "payload chunk exceeds packet capacity",
            component="protocol",
            operation="encode_packet",
            packet_id=packet_id,
            capacity=capacity,
            actual=len(chunk),
        )
    if packet_id == 0 and header is None:
        raise ProtocolError(
            "packet 0 requires a file header",
            component="protocol",
            operation="encode_packet",
        )
    region = bytearray(PACKET_BYTES)
    offset = 0
    if packet_id == 0:
        assert header is not None
        region[:FILE_HEADER_SIZE] = header.to_bytes()
        offset = FILE_HEADER_SIZE
    region[offset : offset + len(chunk)] = chunk

    blocks = [
        rs_encode(bytes(region[b * BLOCK_DATA_BYTES : (b + 1) * BLOCK_DATA_BYTES]), nsym)
        for b in range(BLOCKS_PER_PACKET)
    ]
    frames = tuple(
        bytes(blocks[b][n] for b in range(BLOCKS_PER_PACKET))
        for n in range(FRAMES_PER_PACKET)
    )
    return Packet(packet_id=packet_id, header=header, frames=frames)


def decode_packet(
    packet_id: int,
    frames: Mapping[int, bytes],
    *,
    nsym: int = 32,
) -> DecodedPacket:
    """De-interleave and RS-decode one packet from received frames.

    ``frames`` maps frame index (0..254) to the 11 bytes recovered from that
    frame.  Missing indices are treated as erasures at the corresponding byte
    position in every RS block.
    """
    if not 0 <= packet_id < MAX_PACKETS:
        raise ProtocolError(
            "packet id out of range",
            component="protocol",
            operation="decode_packet",
            packet_id=packet_id,
        )
    clean: dict[int, bytes] = {}
    for index, data in frames.items():
        if not 0 <= index < FRAMES_PER_PACKET:
            raise ProtocolError(
                "frame index out of range",
                component="protocol",
                operation="decode_packet",
                frame_index=index,
            )
        if len(data) != DATA_BYTES_PER_FRAME:
            raise ProtocolError(
                "frame must carry 11 bytes",
                component="protocol",
                operation="decode_packet",
                frame_index=index,
                length=len(data),
            )
        clean[index] = bytes(data)

    stats = PacketStats(
        frames_present=len(clean),
        frames_missing=FRAMES_PER_PACKET - len(clean),
        erasures=sorted(set(range(FRAMES_PER_PACKET)) - set(clean)),
    )
    region = bytearray()
    for b in range(BLOCKS_PER_PACKET):
        codeword = bytearray(FRAMES_PER_PACKET)
        for n in range(FRAMES_PER_PACKET):
            data = clean.get(n)
            if data is not None:
                codeword[n] = data[b]
        try:
            corrected, n_corrected = rs_decode(bytes(codeword), nsym, stats.erasures)
        except ECCError as exc:
            stats.block_failures.append(b)
            raise ReconstructionError(
                "RS block could not be corrected",
                component="protocol",
                operation="decode_packet",
                packet_id=packet_id,
                block=b,
                erasures=len(stats.erasures),
                cause=exc.to_dict(),
            ) from exc
        stats.corrected_per_block.append(n_corrected)
        region.extend(corrected[:BLOCK_DATA_BYTES])

    header: FileHeader | None = None
    if packet_id == 0:
        header = FileHeader.from_bytes(bytes(region[:FILE_HEADER_SIZE]))
        chunk = bytes(region[FILE_HEADER_SIZE:])
    else:
        chunk = bytes(region)
    return DecodedPacket(packet_id=packet_id, header=header, chunk=chunk, stats=stats)


def build_file(
    payload: bytes,
    name: str,
    *,
    compressed: bool,
    original_len: int,
    nsym: int = 32,
) -> tuple[FileHeader, list[Packet]]:
    """Split a payload into packets and encode all of them."""
    total = plan_total_packets(len(payload))
    if total > MAX_PACKETS:
        raise ProtocolError(
            "payload needs more packets than the 4-bit packet id allows",
            component="protocol",
            operation="build_file",
            payload_len=len(payload),
            total_packets=total,
            max_packets=MAX_PACKETS,
        )
    flags = FLAG_COMPRESSED if compressed else 0
    header = FileHeader(
        version=FILE_VERSION,
        flags=flags,
        packet_id=0,
        total_packets=total,
        original_len=original_len,
        payload_len=len(payload),
        payload_crc32=crc32(payload),
        name=name,
    )
    packets: list[Packet] = []
    cursor = 0
    for packet_id in range(total):
        capacity = PAYLOAD_0 if packet_id == 0 else PACKET_BYTES
        chunk = payload[cursor : cursor + capacity]
        cursor += len(chunk)
        packets.append(
            encode_packet(
                packet_id,
                chunk,
                header=header if packet_id == 0 else None,
                nsym=nsym,
            )
        )
    return header, packets


def reassemble(
    packets: Mapping[int, DecodedPacket],
    *,
    verify_crc: bool = True,
) -> tuple[FileHeader, bytes]:
    """Reassemble a file from decoded packets and verify its CRC-32."""
    if 0 not in packets:
        raise ReconstructionError(
            "packet 0 is required to recover the file header",
            component="protocol",
            operation="reassemble",
        )
    header = packets[0].header
    if header is None:
        raise ReconstructionError(
            "packet 0 did not contain a file header",
            component="protocol",
            operation="reassemble",
        )
    missing = [i for i in range(header.total_packets) if i not in packets]
    if missing:
        raise ReconstructionError(
            "one or more packets are missing",
            component="protocol",
            operation="reassemble",
            missing=missing,
            total=header.total_packets,
        )
    payload = bytearray()
    for packet_id in range(header.total_packets):
        payload.extend(packets[packet_id].chunk)
    payload = payload[: header.payload_len]
    if len(payload) != header.payload_len:
        raise ReconstructionError(
            "reassembled payload shorter than declared",
            component="protocol",
            operation="reassemble",
            declared=header.payload_len,
            actual=len(payload),
        )
    if verify_crc:
        actual_crc = crc32(bytes(payload))
        if actual_crc != header.payload_crc32:
            raise ReconstructionError(
                "payload CRC-32 mismatch",
                component="protocol",
                operation="reassemble",
                expected=header.payload_crc32,
                actual=actual_crc,
            )
    return header, bytes(payload)


def packet_manifest() -> dict[str, object]:
    return {
        "frames_per_packet": FRAMES_PER_PACKET,
        "blocks_per_packet": BLOCKS_PER_PACKET,
        "block_data_bytes": BLOCK_DATA_BYTES,
        "packet_bytes": PACKET_BYTES,
        "file_header_bytes": FILE_HEADER_SIZE,
        "payload_packet0": PAYLOAD_0,
        "payload_other": PACKET_BYTES,
        "max_packets": MAX_PACKETS,
        "max_payload_bytes": PAYLOAD_0 + (MAX_PACKETS - 1) * PACKET_BYTES,
        "interleave": "frame n carries block b byte n for b=0..10",
    }
