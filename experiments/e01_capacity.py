"""E01 — Protocol arithmetic and raw capacity."""

from __future__ import annotations

import numpy as np

from otl.config import ExperimentConfig
from otl.metrics import Timer
from otl.protocol.frame import pack_frame, unpack_frame
from otl.protocol.packet import (
    PACKET_BYTES,
    PAYLOAD_0,
    build_file,
    decode_packet,
    packet_manifest,
)
from otl.types import FrameHeader

from .common import random_frame
from .harness import ExperimentSpec, RunContext

FRAME_RATES = (1, 5, 10, 15, 24, 30, 60, 120)
LOSS_RATES = (0.0, 0.01, 0.05, 0.10)


def run(ctx: RunContext) -> None:
    cfg = ExperimentConfig()
    protocol = cfg.protocol
    manifest = packet_manifest()
    rs_rate = 223.0 / 255.0
    raw_bits = protocol.total_bits
    data_bytes = protocol.data_bytes_per_frame
    packet_frames = protocol.packet_frames
    max_packets = int(manifest["max_packets"])
    max_payload = int(manifest["max_payload_bytes"])

    for fps in FRAME_RATES:
        for loss in LOSS_RATES:
            frames_per_s = fps * (1.0 - loss)
            raw_bps = frames_per_s * raw_bits
            framed_payload_bps = frames_per_s * data_bytes * 8
            rs_goodput_bps = framed_payload_bps * rs_rate
            ctx.record(
                config={
                    "display_fps": fps,
                    "frame_loss": loss,
                    "cells": protocol.cols * protocol.rows,
                    "bits_per_cell": protocol.bits_per_cell,
                },
                inputs={"packet_frames": packet_frames, "rs_nsym": cfg.ecc.nsym},
                outputs={
                    "raw_bps": raw_bps,
                    "framed_payload_bps": framed_payload_bps,
                    "rs_goodput_bps": rs_goodput_bps,
                    "rs_goodput_bytes_s": rs_goodput_bps / 8.0,
                    "packet_duration_s": packet_frames / fps if fps else None,
                },
                metrics={
                    "raw_bps": raw_bps,
                    "framed_payload_bps": framed_payload_bps,
                    "rs_goodput_bps": rs_goodput_bps,
                    "frame_loss": loss,
                },
                notes="analytical; no optics",
            )

    # Software cost of the pure protocol layer.
    rng = np.random.default_rng(1)
    frames = [random_frame(rng, cfg) for _ in range(2000)]

    with Timer() as pack_timer:
        packed = [pack_frame(h, d, protocol) for h, d, _ in frames]
    with Timer() as unpack_timer:
        decoded = [unpack_frame(c, protocol) for c in packed]
    assert all(frame.crc_ok for frame in decoded)

    raw = bytes(range(256)) * 8  # one packet
    with Timer() as encode_timer:
        _, packets = build_file(raw, "capacity.bin", compressed=False, original_len=len(raw))
    received = {h.frame_index: d for h, d in packets[0].iter_frames()}
    with Timer() as decode_timer:
        packet = decode_packet(0, received, nsym=cfg.ecc.nsym)
    assert packet.stats.frames_missing == 0

    ctx.record(
        config={"operation": "protocol_software", "frames": len(frames)},
        inputs={"payload_bytes": len(raw)},
        outputs={
            "pack_us_per_frame": pack_timer.elapsed_s / len(frames) * 1e6,
            "unpack_us_per_frame": unpack_timer.elapsed_s / len(frames) * 1e6,
            "rs_encode_ms": encode_timer.elapsed_s * 1000.0,
            "rs_decode_ms": decode_timer.elapsed_s * 1000.0,
        },
        metrics={
            "pack_us_per_frame": pack_timer.elapsed_s / len(frames) * 1e6,
            "unpack_us_per_frame": unpack_timer.elapsed_s / len(frames) * 1e6,
            "rs_encode_ms": encode_timer.elapsed_s * 1000.0,
            "rs_decode_ms": decode_timer.elapsed_s * 1000.0,
        },
        notes="OBSERVED software timings on this machine",
    )

    ctx.summary = {
        "frame_bits": raw_bits,
        "header_bits": protocol.header_bits,
        "crc_bits": protocol.crc_bits,
        "payload_bits": data_bytes * 8,
        "payload_bytes_per_frame": data_bytes,
        "frames_per_packet": packet_frames,
        "packet_payload_bytes": PACKET_BYTES,
        "packet0_payload_bytes": PAYLOAD_0,
        "max_packets": max_packets,
        "max_payload_bytes": max_payload,
        "rs_code_rate": rs_rate,
        "raw_bps_at_60fps": 60 * raw_bits,
        "framed_payload_bps_at_60fps": 60 * data_bytes * 8,
        "rs_goodput_bps_at_60fps": 60 * data_bytes * 8 * rs_rate,
        "max_payload_kib": max_payload / 1024.0,
        "packet_duration_s_at_60fps": packet_frames / 60.0,
        "software": {
            "pack_us_per_frame": pack_timer.elapsed_s / len(frames) * 1e6,
            "unpack_us_per_frame": unpack_timer.elapsed_s / len(frames) * 1e6,
        },
    }
    ctx.conclude(
        "The 30-cell FULL16 frame carries 120 raw bits, of which 88 are payload "
        f"({data_bytes} bytes). At 60 display frames/s the raw rate is "
        f"{60 * raw_bits} bps, the framed payload rate is "
        f"{60 * data_bytes * 8} bps, and the RS(255,223) goodput is "
        f"{60 * data_bytes * 8 * rs_rate:.0f} bps. A packet occupies "
        f"{packet_frames / 60.0:.2f} s at 60 fps and the 4-bit packet id caps a "
        f"transfer at {max_packets} packets ({max_payload} bytes before "
        "compression). These are THEORETICAL arithmetic values; software "
        "timings are OBSERVED on the run machine."
    )


SPEC = ExperimentSpec(
    id="E01_capacity",
    title="Protocol arithmetic and raw capacity",
    hypothesis=(
        "The proposed 30-cell, four-triangle alphabet yields 120 raw bits per "
        "screen frame, 88 payload bits after the 16-bit header and 16-bit CRC, "
        "and the 4-bit packet id limits a transfer to 16 packets."
    ),
    classification="THEORETICAL (arithmetic) + OBSERVED (software timings)",
    controlled=("cell alphabet FULL16", "header 16 bits", "CRC 16 bits", "RS(255,223)"),
    independent=("display frame rate", "frame loss rate"),
    dependent=("raw bit rate", "framed payload rate", "RS goodput", "packet duration"),
    procedure=(
        "Derive frame and packet arithmetic from the typed ProtocolConfig.",
        "Compute raw, framed-payload and RS-goodput rates for each frame rate and loss rate.",
        "Measure pack/unpack and RS encode/decode time on 2000 random frames and one packet.",
        "Record all values with explicit analytical/software provenance.",
    ),
    run=run,
)
