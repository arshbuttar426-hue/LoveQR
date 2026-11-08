"""Deterministic M11 arm payloads and frame builders.

Each arm is a self-contained transmitter description: the application bytes,
the raw/compressed wire bytes, the packet codec parameters and the exact frames
that must be displayed.  The same function is used by the preparation script,
by E13 and by the tests, so a physical session can be reproduced byte-for-byte.

Arms (the reference is the frozen M9/M10 configuration):

``A0_reference``
    317-byte demo payload, always-on OTL1, M9 32-byte header, RS(255,223).
``A1_fill_adaptive``
    2,421-byte incompressible payload, adaptive raw, M9 header, RS(255,223).
``A2_bundle``
    four 570-byte logical payloads in one ``OTB1`` bundle, compact 15-byte
    header, adaptive raw, RS(255,223).
``A3_dictionary``
    145,745-byte repeated-instruction stream, OTL1, M9 header, RS(255,223).
``A4_always_on``
    the same 2,421-byte payload as A1 but always-on OTL1, M9 header.
``A5_rs24``
    2,526-byte incompressible payload, adaptive raw, compact 15-byte header,
    RS(255,231) with ``nsym=24``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from otl.compress.adaptive import EncodingChoice, choose_encoding
from otl.compress.dictionary import compress
from otl.errors import ProtocolError
from otl.protocol.m11 import (
    COMPACT_HEADER_SIZE,
    M9_HEADER_KIND,
    M11_HEADER_KIND,
    BundleEntry,
    CompactFileHeader,
    build_file_v2,
    bundle_manifest,
    pack_bundle,
    packet_manifest_v2,
    plan_total_packets_v2,
)
from otl.protocol.packet import (
    FRAMES_PER_PACKET,
    FileHeader,
    build_file,
    packet_manifest,
)
from otl.types import FrameHeader

ROOT = Path(__file__).resolve().parent.parent
DEMO_PAYLOAD = ROOT / "datasets" / "physical" / "demo" / "payload.txt"
BASELINE_SHA256 = "829a6e465f0be0a8ae2e5eee9adb783d84591f2bf1813a20153946edce9cab2d"

REFERENCE_BYTES = 317
PACKET0_M9 = 2421
PACKET0_COMPACT_32 = 2438
PACKET0_COMPACT_24 = 2526

FILL_BYTES = 2421
BUNDLE_ENTRY_BYTES = 570
BUNDLE_ENTRY_NAMES = ("alpha.bin", "beta.bin", "gamma.bin", "delta.bin")
DICTIONARY_BYTES = 145745
RS24_BYTES = 2526

REPEATED_INSTRUCTION = (
    b"REPEAT value=0x5A count=64; "
    b"COPY distance=0x0100 length=0xFF; "
    b"INVERT distance=0x0200 length=0x40; "
    b"SEQUENCE start=0x00 step=0x01 count=0x20;\n"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seeded_bytes(seed: int, size: int) -> bytes:
    rng = np.random.default_rng(seed)
    return bytes(int(value) for value in rng.integers(0, 256, size=size, dtype=np.uint8))


def repeated_instructions(size: int) -> bytes:
    if size < 0:
        raise ValueError("size must be non-negative")
    repeats = size // len(REPEATED_INSTRUCTION) + 1
    return (REPEATED_INSTRUCTION * repeats)[:size]


def reference_payload() -> bytes:
    if not DEMO_PAYLOAD.is_file():
        raise ProtocolError(
            "the frozen 317-byte demo payload is missing",
            component="experiments",
            operation="reference_payload",
            path=str(DEMO_PAYLOAD),
        )
    data = DEMO_PAYLOAD.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASELINE_SHA256:
        raise ProtocolError(
            "the frozen demo payload hash changed",
            component="experiments",
            operation="reference_payload",
            expected=BASELINE_SHA256,
            actual=hashlib.sha256(data).hexdigest(),
        )
    return data


@dataclass(frozen=True)
class ArmBuild:
    arm_id: str
    title: str
    description: str
    payload_name: str
    application_bytes: int
    original_len: int
    application_sha256: str
    application_payload: bytes | None
    wire: bytes
    wire_sha256: str
    compressed: bool
    nsym: int
    header_kind: str
    header_size: int
    total_packets: int
    frames: tuple[tuple[FrameHeader, bytes], ...]
    bundle: tuple[BundleEntry, ...] | None
    manifest: dict[str, object]

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def packet_data_bytes(self) -> int:
        if self.header_kind == M9_HEADER_KIND:
            return 2453
        return (255 - self.nsym) * 11

    @property
    def packet0_capacity(self) -> int:
        return self.packet_data_bytes - self.header_size

    @property
    def frames_sha256(self) -> str:
        digest = hashlib.sha256()
        for header, data in self.frames:
            digest.update(bytes((header.packet_id, header.frame_index % 256)))
            digest.update(data)
        return digest.hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "title": self.title,
            "description": self.description,
            "payload_name": self.payload_name,
            "application_bytes": self.application_bytes,
            "original_len": self.original_len,
            "application_sha256": self.application_sha256,
            "wire_bytes": len(self.wire),
            "wire_sha256": self.wire_sha256,
            "compressed": self.compressed,
            "nsym": self.nsym,
            "header_kind": self.header_kind,
            "header_size": self.header_size,
            "header_bytes": self.header_size,
            "total_packets": self.total_packets,
            "frame_count": self.frame_count,
            "frames_sha256": self.frames_sha256,
            "packet_data_bytes": self.packet_data_bytes,
            "packet0_capacity": self.packet0_capacity,
            "packet_fill_wire": (self.header_size + len(self.wire))
            / (self.total_packets * self.packet_data_bytes),
            "packet_fill_payload": len(self.wire)
            / (self.total_packets * self.packet_data_bytes),
            "bundle": (
                bundle_manifest(self.bundle) if self.bundle is not None else None
            ),
            "manifest": self.manifest,
        }


def _frames_m9(packets: list) -> tuple[tuple[FrameHeader, bytes], ...]:
    rows: list[tuple[FrameHeader, bytes]] = []
    for packet in packets:
        rows.extend(packet.iter_frames())
    return tuple(rows)


def _frames_v2(packets: list[tuple[bytes, ...]]) -> tuple[tuple[FrameHeader, bytes], ...]:
    rows: list[tuple[FrameHeader, bytes]] = []
    for packet_id, frames in enumerate(packets):
        rows.extend(
            (FrameHeader(packet_id, index), data)
            for index, data in enumerate(frames)
        )
    return tuple(rows)


def _m9_arm(
    *,
    arm_id: str,
    title: str,
    description: str,
    payload_name: str,
    original: bytes,
    wire: bytes,
    compressed: bool,
    nsym: int = 32,
) -> ArmBuild:
    header, packets = build_file(
        wire,
        payload_name,
        compressed=compressed,
        original_len=len(original),
        nsym=nsym,
    )
    frames = _frames_m9(packets)
    return ArmBuild(
        arm_id=arm_id,
        title=title,
        description=description,
        payload_name=payload_name,
        application_bytes=len(original),
        original_len=len(original),
        application_sha256=_sha256(original),
        application_payload=original,
        wire=wire,
        wire_sha256=_sha256(wire),
        compressed=compressed,
        nsym=nsym,
        header_kind=M9_HEADER_KIND,
        header_size=32,
        total_packets=header.total_packets,
        frames=frames,
        bundle=None,
        manifest={
            "codec": "m9-packet",
            "header": {
                "version": header.version,
                "flags": header.flags,
                "packet_id": header.packet_id,
                "total_packets": header.total_packets,
                "original_len": header.original_len,
                "payload_len": header.payload_len,
                "payload_crc32": header.payload_crc32,
                "name": header.name,
            },
            "packet_manifest": packet_manifest(),
        },
    )


def _v2_arm(
    *,
    arm_id: str,
    title: str,
    description: str,
    payload_name: str,
    original: bytes,
    wire: bytes,
    compressed: bool,
    nsym: int,
    bundle: tuple[BundleEntry, ...] | None = None,
) -> ArmBuild:
    header, packets = build_file_v2(
        wire,
        compressed=compressed,
        original_len=len(original),
        nsym=nsym,
        header_size=COMPACT_HEADER_SIZE,
    )
    frames = _frames_v2(packets)
    return ArmBuild(
        arm_id=arm_id,
        title=title,
        description=description,
        payload_name=payload_name,
        application_bytes=(
            sum(len(entry.data) for entry in bundle)
            if bundle is not None
            else len(original)
        ),
        original_len=len(original),
        application_sha256=(
            _sha256(
                "\n".join(
                    f"{entry.name}:{_sha256(entry.data)}" for entry in bundle
                ).encode("utf-8")
            )
            if bundle is not None
            else _sha256(original)
        ),
        application_payload=None if bundle is not None else original,
        wire=wire,
        wire_sha256=_sha256(wire),
        compressed=compressed,
        nsym=nsym,
        header_kind=M11_HEADER_KIND,
        header_size=COMPACT_HEADER_SIZE,
        total_packets=header.total_packets,
        frames=frames,
        bundle=bundle,
        manifest={
            "codec": "m11-v2",
            "header": {
                "version": header.version,
                "flags": header.flags,
                "total_packets": header.total_packets,
                "original_len": header.original_len,
                "payload_len": header.payload_len,
                "payload_crc32": header.payload_crc32,
            },
            "packet_manifest": packet_manifest_v2(
                nsym=nsym, header_size=COMPACT_HEADER_SIZE
            ),
        },
    )


def build_arm(arm_id: str) -> ArmBuild:
    """Build one arm deterministically."""
    if arm_id == "A0_reference":
        original = reference_payload()
        wire, _stats = compress(original)
        return _m9_arm(
            arm_id=arm_id,
            title="Frozen M9 reference",
            description=(
                "317-byte demo payload, always-on OTL1, 32-byte M9 header, "
                "RS(255,223), one 255-frame packet."
            ),
            payload_name="payload.txt",
            original=original,
            wire=wire,
            compressed=True,
        )

    if arm_id == "A1_fill_adaptive":
        original = seeded_bytes(1113, FILL_BYTES)
        choice: EncodingChoice = choose_encoding(original)
        return _m9_arm(
            arm_id=arm_id,
            title="Full packet with adaptive raw",
            description=(
                "2,421 incompressible bytes; adaptive encoding selects raw so "
                "the payload fills packet 0 instead of spilling to packet 1."
            ),
            payload_name="a1.bin",
            original=original,
            wire=choice.wire,
            compressed=choice.compressed,
        )

    if arm_id == "A2_bundle":
        entries = tuple(
            BundleEntry(
                name=name,
                data=seeded_bytes(1120 + index, BUNDLE_ENTRY_BYTES),
            )
            for index, name in enumerate(BUNDLE_ENTRY_NAMES)
        )
        wire = pack_bundle(entries, include_sha256=False)
        choice = choose_encoding(wire)
        return _v2_arm(
            arm_id=arm_id,
            title="Four logical payloads in one packet",
            description=(
                "An OTB1 bundle with four 570-byte entries, per-entry CRC-32, "
                "compact 15-byte header and adaptive raw encoding."
            ),
            payload_name="a2.otb",
            original=wire,
            wire=choice.wire,
            compressed=choice.compressed,
            nsym=32,
            bundle=entries,
        )

    if arm_id == "A3_dictionary":
        original = repeated_instructions(DICTIONARY_BYTES)
        wire, _stats = compress(original)
        return _m9_arm(
            arm_id=arm_id,
            title="Dictionary replaces repeated instructions",
            description=(
                "145,745 bytes of repeated OTL instruction records; OTL1 "
                "COPY operations reduce them to a single-packet wire payload."
            ),
            payload_name="a3.txt",
            original=original,
            wire=wire,
            compressed=True,
        )

    if arm_id == "A4_always_on":
        original = seeded_bytes(1113, FILL_BYTES)
        wire, _stats = compress(original)
        return _m9_arm(
            arm_id=arm_id,
            title="Always-on compression control",
            description=(
                "The same 2,421 incompressible bytes as A1, but OTL1 is always "
                "applied. The 29-byte growth forces a second packet."
            ),
            payload_name="a4.bin",
            original=original,
            wire=wire,
            compressed=True,
        )

    if arm_id == "A5_rs24":
        original = seeded_bytes(1120, RS24_BYTES)
        choice = choose_encoding(original)
        return _v2_arm(
            arm_id=arm_id,
            title="RS(255,231) with nsym=24",
            description=(
                "2,526 incompressible bytes fill the larger RS(255,231) data "
                "region; compact header and adaptive raw encoding."
            ),
            payload_name="a5.bin",
            original=original,
            wire=choice.wire,
            compressed=choice.compressed,
            nsym=24,
        )

    raise ProtocolError(
        f"unknown M11 arm {arm_id!r}",
        component="experiments",
        operation="build_arm",
        arm_id=arm_id,
    )


ARM_IDS = (
    "A0_reference",
    "A1_fill_adaptive",
    "A2_bundle",
    "A3_dictionary",
    "A4_always_on",
    "A5_rs24",
)


def all_arms() -> list[ArmBuild]:
    return [build_arm(arm_id) for arm_id in ARM_IDS]
