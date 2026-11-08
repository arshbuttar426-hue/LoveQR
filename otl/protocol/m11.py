"""M11 packet-utilisation extensions.

M11 does **not** change the frozen M9/M10 frame format, renderer, player or
``otl.protocol.packet`` defaults.  It adds three opt-in pieces on top of the
same 255-frame / 11-block physical layout:

1. A **capacity-aware packet codec** parameterised by ``nsym``.  An RS(255,k)
   block has ``255 - nsym`` data bytes, so a packet carries
   ``11 * (255 - nsym)`` data bytes instead of the hard-coded 2,453.
2. A **compact 15-byte file header** (version 2).  It keeps the CRC-32 and all
   reconstruction fields, drops the redundant packet id and the 13-byte file
   name, and saves 17 bytes versus the frozen 32-byte M9 header.
3. A **bundle container** (``OTB1``) so several logical payloads can share one
   packet.  Each entry carries its own CRC-32 and, optionally, a SHA-256.

Nothing in this module is required by M9/M10.  The frozen packet helpers in
:mod:`otl.protocol.packet` keep their exact behaviour.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ..ecc.crc import crc32
from ..ecc.rs import decode as rs_decode
from ..ecc.rs import encode as rs_encode
from ..errors import ECCError, ProtocolError, ReconstructionError
from .packet import (
    FLAG_COMPRESSED,
    FRAMES_PER_PACKET,
    MAX_PACKETS,
    PacketStats,
)

BLOCKS_PER_PACKET = 11
DATA_BYTES_PER_FRAME = 11
M11_FILE_MAGIC = b"OT"
M11_FILE_VERSION = 2
COMPACT_HEADER_STRUCT = struct.Struct(">2sBBBI3s3s")
COMPACT_HEADER_SIZE = COMPACT_HEADER_STRUCT.size  # 15
MAX_COMPACT_LEN = 0xFFFFFF  # three-byte length field
M11_HEADER_KIND = "compact15"
M9_HEADER_KIND = "m9-32"

BUNDLE_MAGIC = b"OTB1"
BUNDLE_VERSION = 1
BUNDLE_FLAG_SHA256 = 0x01
BUNDLE_HEADER_STRUCT = struct.Struct(">4sBBI")
BUNDLE_HEADER_SIZE = BUNDLE_HEADER_STRUCT.size  # 10
ENTRY_HEADER_STRUCT = struct.Struct(">BII")
ENTRY_HEADER_SIZE = ENTRY_HEADER_STRUCT.size  # 9
SHA256_BYTES = 32


# ---------------------------------------------------------------------------
# Capacity arithmetic
# ---------------------------------------------------------------------------


def data_bytes_per_block(nsym: int) -> int:
    """RS data bytes in one 255-byte codeword."""
    if not 0 < nsym < 255:
        raise ProtocolError(
            "nsym must be in 1..254",
            component="protocol",
            operation="data_bytes_per_block",
            nsym=nsym,
        )
    return 255 - nsym


def packet_data_bytes(nsym: int) -> int:
    """Data region of a whole packet (11 interleaved RS blocks)."""
    return data_bytes_per_block(nsym) * BLOCKS_PER_PACKET


def packet_capacity(
    packet_id: int,
    *,
    nsym: int = 32,
    header_size: int = 0,
) -> int:
    """Application bytes that fit in one packet."""
    if not 0 <= packet_id < MAX_PACKETS:
        raise ProtocolError(
            "packet id out of range",
            component="protocol",
            operation="packet_capacity",
            packet_id=packet_id,
        )
    capacity = packet_data_bytes(nsym)
    if packet_id == 0:
        if header_size < 0:
            raise ProtocolError(
                "header size must be non-negative",
                component="protocol",
                operation="packet_capacity",
                header_size=header_size,
            )
        capacity -= header_size
    if capacity < 0:
        raise ProtocolError(
            "file header is larger than the packet data region",
            component="protocol",
            operation="packet_capacity",
            header_size=header_size,
            packet_data=packet_data_bytes(nsym),
        )
    return capacity


def plan_total_packets_v2(
    payload_len: int,
    *,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> int:
    if payload_len < 0:
        raise ProtocolError("payload length must be >= 0", component="protocol")
    first = packet_capacity(0, nsym=nsym, header_size=header_size)
    if payload_len <= first:
        return 1
    rest = packet_data_bytes(nsym)
    return 1 + math.ceil((payload_len - first) / rest)


def max_payload_bytes(
    *,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> int:
    return packet_capacity(0, nsym=nsym, header_size=header_size) + (
        MAX_PACKETS - 1
    ) * packet_data_bytes(nsym)


# ---------------------------------------------------------------------------
# Compact file header
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactFileHeader:
    """15-byte M11 file header.

    The packet id is already in every on-screen frame header and the file name
    is not needed for reconstruction, so both are omitted.  The CRC-32, the
    original length, the wire length and the packet count are retained.
    """

    version: int
    flags: int
    total_packets: int
    original_len: int
    payload_len: int
    payload_crc32: int

    def __post_init__(self) -> None:
        if self.version != M11_FILE_VERSION:
            raise ProtocolError(
                "unsupported compact file header version",
                component="protocol",
                operation="CompactFileHeader",
                version=self.version,
            )
        if not 1 <= self.total_packets <= MAX_PACKETS:
            raise ProtocolError(
                "total_packets out of range",
                component="protocol",
                operation="CompactFileHeader",
                total_packets=self.total_packets,
            )
        for name, value in (
            ("original_len", self.original_len),
            ("payload_len", self.payload_len),
        ):
            if not 0 <= value <= MAX_COMPACT_LEN:
                raise ProtocolError(
                    "compact header length outside the 24-bit field",
                    component="protocol",
                    operation="CompactFileHeader",
                    field=name,
                    value=value,
                )
        if not 0 <= self.payload_crc32 <= 0xFFFFFFFF:
            raise ProtocolError(
                "payload CRC-32 outside uint32",
                component="protocol",
                operation="CompactFileHeader",
                value=self.payload_crc32,
            )

    @property
    def compressed(self) -> bool:
        return bool(self.flags & FLAG_COMPRESSED)

    def to_bytes(self) -> bytes:
        return COMPACT_HEADER_STRUCT.pack(
            M11_FILE_MAGIC,
            self.version,
            self.flags,
            self.total_packets,
            self.payload_crc32,
            self.original_len.to_bytes(3, "big"),
            self.payload_len.to_bytes(3, "big"),
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "CompactFileHeader":
        if len(raw) != COMPACT_HEADER_SIZE:
            raise ProtocolError(
                "wrong compact header size",
                component="protocol",
                operation="CompactFileHeader.from_bytes",
                expected=COMPACT_HEADER_SIZE,
                actual=len(raw),
            )
        (
            magic,
            version,
            flags,
            total_packets,
            payload_crc32,
            original_raw,
            payload_raw,
        ) = COMPACT_HEADER_STRUCT.unpack(raw)
        if magic != M11_FILE_MAGIC:
            raise ProtocolError(
                "bad compact header magic",
                component="protocol",
                operation="CompactFileHeader.from_bytes",
                magic=magic.hex(),
            )
        return cls(
            version=version,
            flags=flags,
            total_packets=total_packets,
            original_len=int.from_bytes(original_raw, "big"),
            payload_len=int.from_bytes(payload_raw, "big"),
            payload_crc32=payload_crc32,
        )


@dataclass(frozen=True)
class DecodedPacketV2:
    packet_id: int
    header: CompactFileHeader | None
    chunk: bytes
    stats: PacketStats


# ---------------------------------------------------------------------------
# Capacity-aware packet codec
# ---------------------------------------------------------------------------


def encode_packet_v2(
    packet_id: int,
    chunk: bytes,
    *,
    header: CompactFileHeader | None = None,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> tuple[bytes, ...]:
    """Encode one packet whose RS data width follows ``nsym``."""
    if not 0 <= packet_id < MAX_PACKETS:
        raise ProtocolError(
            "packet id out of range",
            component="protocol",
            operation="encode_packet_v2",
            packet_id=packet_id,
        )
    capacity = packet_capacity(packet_id, nsym=nsym, header_size=header_size)
    if len(chunk) > capacity:
        raise ProtocolError(
            "payload chunk exceeds packet capacity",
            component="protocol",
            operation="encode_packet_v2",
            packet_id=packet_id,
            capacity=capacity,
            actual=len(chunk),
        )
    if packet_id == 0 and header is None:
        raise ProtocolError(
            "packet 0 requires a file header",
            component="protocol",
            operation="encode_packet_v2",
        )

    width = data_bytes_per_block(nsym)
    region = bytearray(packet_data_bytes(nsym))
    offset = 0
    if packet_id == 0:
        assert header is not None
        encoded = header.to_bytes()
        if len(encoded) != header_size:
            raise ProtocolError(
                "header encoding does not match header_size",
                component="protocol",
                operation="encode_packet_v2",
                header_size=header_size,
                actual=len(encoded),
            )
        region[:header_size] = encoded
        offset = header_size
    region[offset : offset + len(chunk)] = chunk

    blocks = [
        rs_encode(bytes(region[b * width : (b + 1) * width]), nsym)
        for b in range(BLOCKS_PER_PACKET)
    ]
    return tuple(
        bytes(blocks[b][n] for b in range(BLOCKS_PER_PACKET))
        for n in range(FRAMES_PER_PACKET)
    )


def decode_packet_v2(
    packet_id: int,
    frames: Mapping[int, bytes],
    *,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> DecodedPacketV2:
    """De-interleave and RS-decode one capacity-aware packet."""
    if not 0 <= packet_id < MAX_PACKETS:
        raise ProtocolError(
            "packet id out of range",
            component="protocol",
            operation="decode_packet_v2",
            packet_id=packet_id,
        )
    clean: dict[int, bytes] = {}
    for index, data in frames.items():
        if not 0 <= index < FRAMES_PER_PACKET:
            raise ProtocolError(
                "frame index out of range",
                component="protocol",
                operation="decode_packet_v2",
                frame_index=index,
            )
        if len(data) != DATA_BYTES_PER_FRAME:
            raise ProtocolError(
                "frame must carry 11 bytes",
                component="protocol",
                operation="decode_packet_v2",
                frame_index=index,
                length=len(data),
            )
        clean[index] = bytes(data)

    stats = PacketStats(
        frames_present=len(clean),
        frames_missing=FRAMES_PER_PACKET - len(clean),
        erasures=sorted(set(range(FRAMES_PER_PACKET)) - set(clean)),
    )
    width = data_bytes_per_block(nsym)
    region = bytearray()
    for b in range(BLOCKS_PER_PACKET):
        codeword = bytearray(FRAMES_PER_PACKET)
        for n in range(FRAMES_PER_PACKET):
            data = clean.get(n)
            if data is not None:
                codeword[n] = data[b]
        try:
            corrected, n_corrected = rs_decode(
                bytes(codeword), nsym, stats.erasures
            )
        except ECCError as exc:
            stats.block_failures.append(b)
            raise ReconstructionError(
                "RS block could not be corrected",
                component="protocol",
                operation="decode_packet_v2",
                packet_id=packet_id,
                block=b,
                erasures=len(stats.erasures),
                cause=exc.to_dict(),
            ) from exc
        stats.corrected_per_block.append(n_corrected)
        region.extend(corrected[:width])

    header: CompactFileHeader | None = None
    if packet_id == 0:
        header = CompactFileHeader.from_bytes(bytes(region[:header_size]))
        chunk = bytes(region[header_size:])
    else:
        chunk = bytes(region)
    return DecodedPacketV2(
        packet_id=packet_id, header=header, chunk=chunk, stats=stats
    )


def build_file_v2(
    payload: bytes,
    *,
    compressed: bool,
    original_len: int,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> tuple[CompactFileHeader, list[tuple[bytes, ...]]]:
    """Split a payload into capacity-aware packets and encode every frame."""
    total = plan_total_packets_v2(
        len(payload), nsym=nsym, header_size=header_size
    )
    if total > MAX_PACKETS:
        raise ProtocolError(
            "payload needs more packets than the 4-bit packet id allows",
            component="protocol",
            operation="build_file_v2",
            payload_len=len(payload),
            total_packets=total,
            max_packets=MAX_PACKETS,
        )
    if original_len > MAX_COMPACT_LEN:
        raise ProtocolError(
            "original length exceeds the compact header field",
            component="protocol",
            operation="build_file_v2",
            original_len=original_len,
            max=MAX_COMPACT_LEN,
        )
    header = CompactFileHeader(
        version=M11_FILE_VERSION,
        flags=FLAG_COMPRESSED if compressed else 0,
        total_packets=total,
        original_len=original_len,
        payload_len=len(payload),
        payload_crc32=crc32(payload),
    )
    packets: list[tuple[bytes, ...]] = []
    cursor = 0
    for packet_id in range(total):
        capacity = packet_capacity(
            packet_id, nsym=nsym, header_size=header_size
        )
        chunk = payload[cursor : cursor + capacity]
        cursor += len(chunk)
        packets.append(
            encode_packet_v2(
                packet_id,
                chunk,
                header=header if packet_id == 0 else None,
                nsym=nsym,
                header_size=header_size,
            )
        )
    return header, packets


def reassemble_v2(
    packets: Mapping[int, DecodedPacketV2],
    *,
    verify_crc: bool = True,
) -> tuple[CompactFileHeader, bytes]:
    if 0 not in packets:
        raise ReconstructionError(
            "packet 0 is required to recover the file header",
            component="protocol",
            operation="reassemble_v2",
        )
    header = packets[0].header
    if header is None:
        raise ReconstructionError(
            "packet 0 did not contain a file header",
            component="protocol",
            operation="reassemble_v2",
        )
    missing = [i for i in range(header.total_packets) if i not in packets]
    if missing:
        raise ReconstructionError(
            "one or more packets are missing",
            component="protocol",
            operation="reassemble_v2",
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
            operation="reassemble_v2",
            declared=header.payload_len,
            actual=len(payload),
        )
    if verify_crc:
        actual_crc = crc32(bytes(payload))
        if actual_crc != header.payload_crc32:
            raise ReconstructionError(
                "payload CRC-32 mismatch",
                component="protocol",
                operation="reassemble_v2",
                expected=header.payload_crc32,
                actual=actual_crc,
            )
    return header, bytes(payload)


def packet_manifest_v2(
    *,
    nsym: int = 32,
    header_size: int = COMPACT_HEADER_SIZE,
) -> dict[str, object]:
    return {
        "frames_per_packet": FRAMES_PER_PACKET,
        "blocks_per_packet": BLOCKS_PER_PACKET,
        "rs_nsym": nsym,
        "block_data_bytes": data_bytes_per_block(nsym),
        "packet_data_bytes": packet_data_bytes(nsym),
        "file_header_bytes": header_size,
        "header_kind": M11_HEADER_KIND if header_size == COMPACT_HEADER_SIZE else "custom",
        "payload_packet0": packet_capacity(0, nsym=nsym, header_size=header_size),
        "payload_other": packet_data_bytes(nsym),
        "max_packets": MAX_PACKETS,
        "max_payload_bytes": max_payload_bytes(nsym=nsym, header_size=header_size),
        "interleave": "frame n carries block b byte n for b=0..10",
    }


# ---------------------------------------------------------------------------
# Multi-payload bundle container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BundleEntry:
    name: str
    data: bytes
    sha256: str | None = None

    def __post_init__(self) -> None:
        try:
            encoded = self.name.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ProtocolError(
                "bundle entry name is not valid UTF-8",
                component="protocol",
                operation="BundleEntry",
            ) from exc
        if not encoded:
            raise ProtocolError(
                "bundle entry name must not be empty",
                component="protocol",
                operation="BundleEntry",
            )
        if len(encoded) > 255:
            raise ProtocolError(
                "bundle entry name is longer than 255 bytes",
                component="protocol",
                operation="BundleEntry",
                bytes=len(encoded),
            )
        if len(self.data) > 0xFFFFFFFF:
            raise ProtocolError(
                "bundle entry is too large for a uint32 length",
                component="protocol",
                operation="BundleEntry",
                bytes=len(self.data),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "bytes": len(self.data),
            "sha256": self.sha256,
            "crc32": f"{crc32(self.data):08x}",
        }


def pack_bundle(
    entries: Sequence[BundleEntry | tuple[str, bytes]],
    *,
    include_sha256: bool = False,
) -> bytes:
    """Pack logical payloads into one deterministic ``OTB1`` blob.

    Entry layout (big-endian)::

        u8  name length
        u32 data length
        u32 CRC-32 of data
        [32-byte SHA-256 when the bundle SHA flag is set]
        name bytes
        data bytes
    """
    normalised: list[BundleEntry] = []
    for item in entries:
        if isinstance(item, BundleEntry):
            normalised.append(item)
        else:
            normalised.append(BundleEntry(name=item[0], data=item[1]))
    if not normalised:
        raise ProtocolError(
            "a bundle needs at least one entry",
            component="protocol",
            operation="pack_bundle",
        )
    if len(normalised) > 255:
        raise ProtocolError(
            "bundle entry count exceeds the one-byte field",
            component="protocol",
            operation="pack_bundle",
            count=len(normalised),
        )
    flags = BUNDLE_FLAG_SHA256 if include_sha256 else 0
    body = bytearray()
    for entry in normalised:
        name = entry.name.encode("utf-8")
        body.extend(
            ENTRY_HEADER_STRUCT.pack(len(name), len(entry.data), crc32(entry.data))
        )
        if include_sha256:
            import hashlib

            body.extend(hashlib.sha256(entry.data).digest())
        body.extend(name)
        body.extend(entry.data)
    total = BUNDLE_HEADER_SIZE + len(body)
    blob = bytearray(
        BUNDLE_HEADER_STRUCT.pack(BUNDLE_MAGIC, BUNDLE_VERSION, flags, total)
    )
    blob.extend(body)
    return bytes(blob)


def unpack_bundle(blob: bytes) -> list[BundleEntry]:
    """Parse and verify a bundle, including per-entry CRC-32 (and SHA-256)."""
    if len(blob) < BUNDLE_HEADER_SIZE:
        raise ProtocolError(
            "bundle is shorter than its header",
            component="protocol",
            operation="unpack_bundle",
            bytes=len(blob),
        )
    magic, version, flags, total = BUNDLE_HEADER_STRUCT.unpack(
        blob[:BUNDLE_HEADER_SIZE]
    )
    if magic != BUNDLE_MAGIC:
        raise ProtocolError(
            "bad bundle magic",
            component="protocol",
            operation="unpack_bundle",
            magic=magic.hex(),
        )
    if version != BUNDLE_VERSION:
        raise ProtocolError(
            "unsupported bundle version",
            component="protocol",
            operation="unpack_bundle",
            version=version,
        )
    if total != len(blob):
        raise ProtocolError(
            "bundle length field does not match the blob",
            component="protocol",
            operation="unpack_bundle",
            declared=total,
            actual=len(blob),
        )
    has_sha = bool(flags & BUNDLE_FLAG_SHA256)
    cursor = BUNDLE_HEADER_SIZE
    entries: list[BundleEntry] = []
    while cursor < len(blob):
        if cursor + ENTRY_HEADER_SIZE > len(blob):
            raise ProtocolError(
                "bundle entry header is truncated",
                component="protocol",
                operation="unpack_bundle",
                cursor=cursor,
            )
        name_len, data_len, expected_crc = ENTRY_HEADER_STRUCT.unpack(
            blob[cursor : cursor + ENTRY_HEADER_SIZE]
        )
        cursor += ENTRY_HEADER_SIZE
        expected_sha = None
        if has_sha:
            if cursor + SHA256_BYTES > len(blob):
                raise ProtocolError(
                    "bundle entry SHA-256 is truncated",
                    component="protocol",
                    operation="unpack_bundle",
                    cursor=cursor,
                )
            expected_sha = blob[cursor : cursor + SHA256_BYTES].hex()
            cursor += SHA256_BYTES
        if cursor + name_len + data_len > len(blob):
            raise ProtocolError(
                "bundle entry exceeds the blob",
                component="protocol",
                operation="unpack_bundle",
                cursor=cursor,
                name_len=name_len,
                data_len=data_len,
            )
        try:
            name = blob[cursor : cursor + name_len].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError(
                "bundle entry name is not valid UTF-8",
                component="protocol",
                operation="unpack_bundle",
            ) from exc
        cursor += name_len
        data = bytes(blob[cursor : cursor + data_len])
        cursor += data_len
        actual_crc = crc32(data)
        if actual_crc != expected_crc:
            raise ProtocolError(
                "bundle entry CRC-32 mismatch",
                component="protocol",
                operation="unpack_bundle",
                name=name,
                expected=expected_crc,
                actual=actual_crc,
            )
        if expected_sha is not None:
            import hashlib

            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                raise ProtocolError(
                    "bundle entry SHA-256 mismatch",
                    component="protocol",
                    operation="unpack_bundle",
                    name=name,
                    expected=expected_sha,
                    actual=actual_sha,
                )
        entries.append(BundleEntry(name=name, data=data, sha256=expected_sha))
    if not entries:
        raise ProtocolError(
            "bundle contains no entries",
            component="protocol",
            operation="unpack_bundle",
        )
    return entries


def bundle_manifest(entries: Iterable[BundleEntry]) -> dict[str, object]:
    import hashlib

    rows = []
    total = 0
    for entry in entries:
        total += len(entry.data)
        rows.append(
            {
                "name": entry.name,
                "bytes": len(entry.data),
                "sha256": hashlib.sha256(entry.data).hexdigest(),
                "crc32": f"{crc32(entry.data):08x}",
            }
        )
    return {
        "container": BUNDLE_MAGIC.decode("ascii"),
        "version": BUNDLE_VERSION,
        "entry_count": len(rows),
        "entries_bytes": total,
        "entries": rows,
    }
