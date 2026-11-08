"""End-to-end software pipeline.

file bytes -> optional OTL1 compression -> packet/RS encoding -> frame packing
-> rendering -> synthetic channel -> detection/spatial decode -> RS packet
decode -> reassembly -> decompression.

Every stage is timed and every failure is recorded as structured data.  The
pipeline never hides a failed packet: ``success`` is true only when the
original bytes are recovered and all CRCs agree.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .compress.dictionary import compress, decompress
from .config import ExperimentConfig, ProtocolConfig
from .decoder.spatial import decode_image
from .errors import OTLError
from .metrics import Throughput, Timer, bit_error_rate
from .protocol.frame import pack_frame
from .protocol.packet import (
    DecodedPacket,
    FileHeader,
    build_file,
    decode_packet,
    reassemble,
)
from .rx.channel import apply_channel
from .tx.renderer import renderer_for


@dataclass
class PipelineResult:
    success: bool
    original: bytes | None
    header: FileHeader | None
    throughput: Throughput
    compression_ratio: float
    frames_total: int
    frames_decoded: int
    frames_crc_ok: int
    frames_dropped: int
    ber: float | None
    per_packet: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "header": (
                {
                    "name": self.header.name,
                    "original_len": self.header.original_len,
                    "payload_len": self.header.payload_len,
                    "payload_crc32": self.header.payload_crc32,
                    "total_packets": self.header.total_packets,
                    "compressed": self.header.compressed,
                }
                if self.header
                else None
            ),
            "throughput": self.throughput.to_dict(),
            "compression_ratio": self.compression_ratio,
            "frames_total": self.frames_total,
            "frames_decoded": self.frames_decoded,
            "frames_crc_ok": self.frames_crc_ok,
            "frames_dropped": self.frames_dropped,
            "ber": self.ber,
            "per_packet": self.per_packet,
            "errors": self.errors,
            "timings_ms": self.timings_ms,
            "notes": self.notes,
        }


def simulate_transfer(
    data: bytes,
    name: str,
    cfg: ExperimentConfig | None = None,
    *,
    apply_optics: bool = True,
    drop_probability: float = 0.0,
    seed: int | None = None,
) -> PipelineResult:
    """Run the complete simulated transfer and return measured results."""
    cfg = cfg or ExperimentConfig()
    protocol: ProtocolConfig = cfg.protocol
    layout = cfg.layout()
    rng = np.random.default_rng(cfg.seed if seed is None else seed)
    total_timer = Timer()

    timings: dict[str, float] = {}
    errors: list[dict[str, Any]] = []

    with Timer() as compression_timer:
        if cfg.compression.enabled:
            compressed, compression_stats = compress(data, cfg.compression)
        else:
            compressed, compression_stats = data, None
    timings["compression"] = compression_timer.elapsed_s * 1000.0

    header, packets = build_file(
        compressed,
        name,
        compressed=cfg.compression.enabled,
        original_len=len(data),
        nsym=cfg.ecc.nsym,
    )
    renderer = renderer_for(layout, cfg.screen)

    decoded_packets: dict[int, DecodedPacket] = {}
    per_packet: list[dict[str, Any]] = []
    frames_total = 0
    frames_decoded = 0
    frames_crc_ok = 0
    frames_dropped = 0
    render_s = 0.0
    channel_s = 0.0
    spatial_s = 0.0
    ecc_s = 0.0

    with total_timer:
        for packet in packets:
            received: dict[int, bytes] = {}
            packet_record: dict[str, Any] = {
                "packet_id": packet.packet_id,
                "frames": len(packet.frames),
            }
            for frame_header, frame_data in packet.iter_frames():
                frames_total += 1
                if drop_probability > 0 and rng.random() < drop_probability:
                    frames_dropped += 1
                    continue
                cells = pack_frame(frame_header, frame_data, protocol)

                start = time.perf_counter()
                image = renderer.render(cells)
                render_s += time.perf_counter() - start

                if apply_optics:
                    start = time.perf_counter()
                    image = apply_channel(
                        image,
                        cfg.channel,
                        seed=int(rng.integers(0, 2**31 - 1)),
                    )
                    channel_s += time.perf_counter() - start

                start = time.perf_counter()
                try:
                    decoded = decode_image(image, layout, cfg.receiver, protocol)
                except OTLError as exc:
                    errors.append(
                        {
                            "stage": "spatial",
                            "packet_id": packet.packet_id,
                            "frame_index": frame_header.frame_index,
                            **exc.to_dict(),
                        }
                    )
                    spatial_s += time.perf_counter() - start
                    continue
                spatial_s += time.perf_counter() - start
                frames_decoded += 1
                if decoded.crc_ok and decoded.frame.header.packet_id == packet.packet_id:
                    frames_crc_ok += 1
                    received[decoded.frame.header.frame_index] = decoded.frame.data
                else:
                    errors.append(
                        {
                            "stage": "frame_crc",
                            "packet_id": packet.packet_id,
                            "frame_index": frame_header.frame_index,
                            "crc_ok": decoded.crc_ok,
                            "decoded_packet_id": decoded.frame.header.packet_id,
                            "decoded_frame_index": decoded.frame.header.frame_index,
                        }
                    )

            start = time.perf_counter()
            try:
                decoded_packet = decode_packet(packet.packet_id, received, nsym=cfg.ecc.nsym)
                decoded_packets[packet.packet_id] = decoded_packet
                packet_record.update(decoded_packet.stats.to_dict())
                packet_record["decoded"] = True
            except OTLError as exc:
                packet_record["decoded"] = False
                packet_record["error"] = exc.to_dict()
                errors.append(
                    {
                        "stage": "packet",
                        "packet_id": packet.packet_id,
                        **exc.to_dict(),
                    }
                )
            ecc_s += time.perf_counter() - start
            per_packet.append(packet_record)

    duration_s = total_timer.elapsed_s
    timings.update(
        {
            "render": render_s * 1000.0,
            "channel": channel_s * 1000.0,
            "spatial_decode": spatial_s * 1000.0,
            "ecc": ecc_s * 1000.0,
            "total": duration_s * 1000.0,
        }
    )

    recovered: bytes | None = None
    recovered_header: FileHeader | None = None
    success = False
    with Timer() as reassembly_timer:
        try:
            recovered_header, payload = reassemble(decoded_packets)
            if recovered_header.compressed:
                recovered = decompress(payload)
            else:
                recovered = payload
            success = recovered == data
            if not success:
                errors.append(
                    {
                        "stage": "verify",
                        "code": "E_VERIFY",
                        "message": "reassembled bytes differ from the input",
                    }
                )
        except OTLError as exc:
            errors.append({"stage": "reassembly", **exc.to_dict()})
    timings["reassembly"] = reassembly_timer.elapsed_s * 1000.0

    ber: float | None = None
    if recovered is not None and len(recovered) == len(data):
        ber = bit_error_rate(data, recovered)

    corrected_positions = sum(
        sum(record.get("corrected_per_block", [])) for record in per_packet
    )
    throughput = Throughput(
        payload_bytes=len(compressed),
        original_bytes=len(data),
        duration_s=duration_s,
        frames=frames_total,
        packets=len(packets),
        lost_frames=frames_dropped + (frames_total - frames_decoded),
        corrected_frames=corrected_positions,
    )
    ratio = (
        compression_stats.ratio
        if compression_stats is not None
        else (len(data) / len(compressed) if compressed else 1.0)
    )
    return PipelineResult(
        success=success,
        original=recovered,
        header=recovered_header,
        throughput=throughput,
        compression_ratio=ratio,
        frames_total=frames_total,
        frames_decoded=frames_decoded,
        frames_crc_ok=frames_crc_ok,
        frames_dropped=frames_dropped,
        ber=ber,
        per_packet=per_packet,
        errors=errors,
        timings_ms=timings,
        notes=(
            "simulated optical channel"
            if apply_optics
            else "clean render, no channel degradations"
        ),
    )


def pipeline_manifest() -> dict[str, object]:
    return {
        "stages": [
            "compress",
            "build_file",
            "render",
            "channel",
            "spatial_decode",
            "packet_decode",
            "reassemble",
            "decompress",
        ],
        "success_rule": "recovered bytes equal input and every CRC agrees",
        "simulation": True,
    }
