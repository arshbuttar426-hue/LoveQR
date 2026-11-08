"""Command line interface for the optical transmission lab.

Subcommands are intentionally small and composable so that an experiment
harness (or another coding agent) can call the same code paths that a human
uses::

    otl manifest                       # protocol + pipeline constants
    otl render --text hello --out DIR  # PNG frames + frame manifest
    otl decode IMAGE --out result.json # decode a prerecorded capture
    otl transfer-sim --text hello      # end-to-end simulated transfer
    otl selftest                       # dependency-free smoke checks

Every command prints machine-readable JSON on stdout.  Expected OTL failures
are printed as a JSON object on stderr and exit with status 2.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from . import __version__
from .compress.dictionary import compress, decompress
from .config import (
    ChannelConfig,
    ExperimentConfig,
    config_to_dict,
    load_config,
    save_config,
)
from .decoder.spatial import decode_image
from .errors import OTLError
from .pipeline import pipeline_manifest, simulate_transfer
from .rx import capture as capture_mod
from .rx import session as session_mod
from .tx.player import PlayerConfig, build_player
from .protocol.blink import verify_codebook
from .protocol.frame import frame_manifest, pack_frame
from .protocol.packet import (
    build_file,
    decode_packet,
    packet_manifest,
    reassemble,
)
from .tx.renderer import load_frame, renderer_for, save_frame
from .types import FrameHeader

CHANNEL_PRESETS: dict[str, ChannelConfig] = {
    "clean": ChannelConfig(),
    "mild": ChannelConfig(
        blur_sigma=0.8,
        noise_sigma=2.0,
        ambient=12.0,
        brightness=0.92,
        gamma=1.05,
        vignette=0.12,
        perspective=0.01,
        jpeg_quality=92,
    ),
    "harsh": ChannelConfig(
        blur_sigma=1.4,
        noise_sigma=4.0,
        ambient=25.0,
        brightness=0.82,
        gamma=1.15,
        vignette=0.25,
        perspective=0.03,
        jpeg_quality=80,
    ),
}


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def _emit(payload: Any, *, stream: Any = None) -> None:
    target = sys.stdout if stream is None else stream
    json.dump(payload, target, indent=2, sort_keys=True, default=_json_default)
    target.write("\n")


def _read_payload(args: argparse.Namespace) -> tuple[bytes, str]:
    if args.text is not None:
        return args.text.encode("utf-8"), args.name or "message.txt"
    if args.input is None:
        raise OTLError(
            "provide --text or an input file",
            component="cli",
            operation="read_payload",
        )
    path = Path(args.input)
    return path.read_bytes(), args.name or path.name


def _load_cfg(args: argparse.Namespace) -> ExperimentConfig:
    if getattr(args, "config", None):
        return load_config(args.config)
    cfg = ExperimentConfig()
    preset = getattr(args, "channel", None)
    if preset:
        cfg = dataclasses.replace(cfg, channel=CHANNEL_PRESETS[preset])
    if getattr(args, "seed", None) is not None:
        cfg = dataclasses.replace(cfg, seed=args.seed)
    return cfg


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_manifest(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args)
    _emit(
        {
            "version": __version__,
            "frame": frame_manifest(),
            "packet": packet_manifest(),
            "blink": verify_codebook(),
            "pipeline": pipeline_manifest(),
            "layout": cfg.layout().to_dict(),
            "config": config_to_dict(cfg),
        }
    )
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    data, name = _read_payload(args)
    cfg = _load_cfg(args)
    layout = cfg.layout()

    payload = data
    if cfg.compression.enabled:
        payload, _ = compress(data, cfg.compression)
    header, packets = build_file(
        payload,
        name,
        compressed=cfg.compression.enabled,
        original_len=len(data),
        nsym=cfg.ecc.nsym,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    renderer = renderer_for(layout, cfg.screen)
    records: list[dict[str, Any]] = []
    written = 0
    for packet in packets:
        for frame_header, frame_data in packet.iter_frames():
            if args.limit is not None and written >= args.limit:
                break
            cells = pack_frame(frame_header, frame_data, cfg.protocol)
            image = renderer.render(cells)
            filename = f"p{packet.packet_id:02d}_f{frame_header.frame_index:03d}.png"
            save_frame(str(out / filename), image)
            record: dict[str, Any] = {
                "file": filename,
                "packet_id": packet.packet_id,
                "frame_index": frame_header.frame_index,
                "bytes": frame_data.hex(),
            }
            if args.include_cells:
                record["cells"] = list(cells)
            records.append(record)
            written += 1
        if args.limit is not None and written >= args.limit:
            break

    save_config(cfg, out / "config.json")
    _emit(
        {
            "out": str(out),
            "frames_written": written,
            "header": {
                "name": header.name,
                "total_packets": header.total_packets,
                "payload_len": header.payload_len,
                "original_len": header.original_len,
                "compressed": header.compressed,
            },
            "frames": records,
        }
    )
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args)
    image = load_frame(args.image)
    decoded = decode_image(image, cfg.layout(), cfg.receiver, cfg.protocol)
    result = decoded.to_dict()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(result, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )
    _emit(result)
    return 0 if decoded.crc_ok else 3


def cmd_transfer_sim(args: argparse.Namespace) -> int:
    data, name = _read_payload(args)
    cfg = _load_cfg(args)
    result = simulate_transfer(
        data,
        name,
        cfg,
        apply_optics=not args.no_optics,
        drop_probability=args.drop,
        seed=args.seed,
    )
    payload = result.to_dict()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )
    _emit(payload)
    return 0 if result.success else 3


def cmd_selftest(args: argparse.Namespace) -> int:
    """Fast deterministic checks that do not need pytest or a camera."""
    checks: list[dict[str, Any]] = []
    ok = True

    def check(name: str, fn: Any) -> None:
        nonlocal ok
        try:
            detail = fn()
            checks.append({"check": name, "ok": True, "detail": detail})
        except Exception as exc:  # selftest must report, not crash
            ok = False
            checks.append(
                {
                    "check": name,
                    "ok": False,
                    "error": (
                        exc.to_dict() if isinstance(exc, OTLError) else {"message": str(exc)}
                    ),
                }
            )

    cfg = ExperimentConfig()

    def roundtrip_compress() -> dict[str, Any]:
        raw = b"OTL selftest " * 100
        packed, stats = compress(raw, cfg.compression)
        assert decompress(packed) == raw
        return {"bytes_in": len(raw), "bytes_out": len(packed), "ratio": stats.ratio}

    def frame_roundtrip() -> dict[str, Any]:
        header = FrameHeader(3, 17)
        data = bytes(range(11))
        cells = pack_frame(header, data, cfg.protocol)
        decoded = decode_image(
            renderer_for(cfg.layout(), cfg.screen).render(cells),
            cfg.layout(),
            cfg.receiver,
            cfg.protocol,
        )
        assert decoded.crc_ok
        assert decoded.frame.header.packet_id == 3
        assert decoded.frame.header.frame_index == 17
        assert decoded.frame.data == data
        return {"cells": list(cells), "crc_ok": decoded.crc_ok}

    def packet_roundtrip() -> dict[str, Any]:
        raw = bytes(range(256)) * 7  # one packet (1792 < 2421 bytes)
        header, packets = build_file(
            raw, "selftest.bin", compressed=False, original_len=len(raw)
        )
        decoded = {
            packet.packet_id: decode_packet(
                packet.packet_id,
                {h.frame_index: d for h, d in packet.iter_frames()},
                nsym=cfg.ecc.nsym,
            )
            for packet in packets
        }
        recovered_header, payload = reassemble(decoded)
        assert payload == raw
        assert recovered_header.original_len == len(raw)
        return {"packets": len(packets), "payload_len": len(payload)}

    def simulated_transfer() -> dict[str, Any]:
        raw = b"end-to-end selftest " * 20
        result = simulate_transfer(raw, "selftest.txt", cfg, apply_optics=True)
        assert result.success, result.errors[:1]
        return {
            "frames": result.frames_total,
            "throughput": result.throughput.to_dict(),
        }

    check("compression", roundtrip_compress)
    check("frame", frame_roundtrip)
    check("packet", packet_roundtrip)
    check("pipeline", simulated_transfer)
    _emit({"ok": ok, "version": __version__, "checks": checks})
    return 0 if ok else 1


def cmd_info(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args)
    layout = cfg.layout()
    _emit(
        {
            "version": __version__,
            "canvas": {"width": layout.canvas_w, "height": layout.canvas_h},
            "cells": {"cols": layout.cols, "rows": layout.rows, "cell_px": layout.cell_px},
            "raw_bits_per_frame": cfg.protocol.total_bits,
            "data_bytes_per_frame": cfg.protocol.payload_bytes,
            "frames_per_packet": cfg.protocol.packet_frames,
            "rs": {"nsym": cfg.ecc.nsym, "block": 255, "data": 223},
            "packet_payload": packet_manifest(),
            "display": {
                "display_fps": cfg.camera.display_fps,
                "symbol_period_us": cfg.camera.symbol_period_us,
                "row_time_us": cfg.camera.row_time_us,
                "readout_us": cfg.camera.readout_us,
            },
        }
    )
    return 0


# ---------------------------------------------------------------------------
# Transmitter / receiver / session commands
# ---------------------------------------------------------------------------


def cmd_play(args: argparse.Namespace) -> int:
    frames_dir = Path(args.frames)
    frames = sorted(frames_dir.glob("p*_f*.png"))
    if not frames:
        raise OTLError(
            "no rendered frames found",
            component="cli",
            operation="play",
            directory=str(frames_dir),
        )
    cfg = PlayerConfig(
        fps=args.fps,
        loop=not args.no_loop,
        hold=args.hold,
        embed=not args.no_embed,
        title=args.title,
        start_delay_s=args.delay,
        show_hud=args.hud,
        autostart=args.autostart,
    )
    result = build_player(frames, args.out, cfg)
    if args.frame is not None:
        result["hold_frame"] = int(args.frame)
        result["hint"] = (
            f"open {args.out}?frame={int(args.frame)} to hold that frame"
        )
    _emit(result)
    return 0


def cmd_capture_list(args: argparse.Namespace) -> int:
    devices = capture_mod.list_cameras()
    _emit({"devices": [device.to_dict() for device in devices]})
    return 0


def cmd_capture_probe(args: argparse.Namespace) -> int:
    _emit({"device": args.device, "output": capture_mod.probe_device(args.device)})
    return 0


def cmd_capture_still(args: argparse.Namespace) -> int:
    result = capture_mod.capture_still(
        args.device, args.out, frames=args.frames, fps=args.fps, size=args.size
    )
    _emit(
        {
            "directory": result.directory,
            "device": result.device,
            "command": result.command,
            "frames": [record.to_dict() for record in result.frames],
            "selected": result.selected.to_dict() if result.selected else None,
            "notes": result.notes,
        }
    )
    return 0


def cmd_capture_video(args: argparse.Namespace) -> int:
    _emit(
        capture_mod.capture_video(
            args.device,
            args.out,
            duration_s=args.duration,
            fps=args.fps,
            size=args.size,
        )
    )
    return 0


def _parse_frame_spec(text: str | None) -> dict[str, int] | None:
    if not text:
        return None
    if ":" not in text:
        raise OTLError(
            "frame must be PACKET:INDEX",
            component="cli",
            operation="ingest",
            frame=text,
        )
    packet_text, index_text = text.split(":", 1)
    return {"packet_id": int(packet_text), "frame_index": int(index_text)}


def cmd_session_new(args: argparse.Namespace) -> int:
    target = session_mod.new_session(
        args.root,
        args.session_id,
        device=session_mod.DeviceInfo(
            model=args.device_model,
            os=args.device_os,
            camera=args.camera,
            notes=args.device_notes,
        ),
        display=session_mod.DisplayInfo(
            model=args.display_model,
            kind=args.display_kind,
            width_px=args.display_width,
            height_px=args.display_height,
            refresh_hz=args.refresh_hz,
            brightness=args.brightness,
            notes=args.display_notes,
        ),
        geometry=session_mod.GeometryInfo(
            distance_mm=args.distance_mm,
            angle_deg=args.angle_deg,
            ambient_lux=args.ambient_lux,
            lighting=args.lighting,
            hand_held=args.hand_held,
            notes=args.geometry_notes,
        ),
        capture=session_mod.CaptureSettings(
            mode=args.mode,
            resolution=args.resolution,
            fps=args.capture_fps,
            exposure=args.exposure,
            iso=args.iso,
            focus=args.focus,
            zoom=args.zoom,
            stabilization=args.stabilization,
            format=args.format,
            notes=args.capture_notes,
        ),
        capture_source=args.source,
        notes=args.notes,
    )
    _emit(
        {
            "session": str(target),
            "session_id": args.session_id,
            "capture_source": args.source,
            "next": (
                f"otl session attach {target} --frames FRAMES --player-manifest "
                f"FRAMES/player_manifest.json"
            ),
        }
    )
    return 0


def cmd_session_attach(args: argparse.Namespace) -> int:
    _emit(
        session_mod.attach_transmitter(
            args.session,
            args.frames,
            args.player_manifest,
            payload_name=args.payload_name,
            payload_sha256=args.payload_sha256,
        )
    )
    return 0


def cmd_session_ingest(args: argparse.Namespace) -> int:
    frame = _parse_frame_spec(args.frame)
    records: list[dict[str, Any]] = []
    for item in args.paths:
        path = Path(item)
        if args.kind == "video":
            video, extracted = capture_mod.ingest_video(
                args.session, path, max_frames=args.max_frames, stride=args.stride
            )
            records.append(video.to_dict())
            for row in extracted:
                records.append(
                    {
                        "path": row["path"],
                        "sha256": row["sha256"],
                        "bytes": Path(args.session, row["path"]).stat().st_size,
                        "width": row["width"],
                        "height": row["height"],
                        "kind": "video-frame",
                        "pos_msec": row["pos_msec"],
                        "source": "camera",
                        "notes": f"frame {row['index']} of {path.name}",
                    }
                )
        else:
            record = capture_mod.ingest_image(
                args.session, path, source=args.source, notes=args.notes
            )
            row = record.to_dict()
            row["kind"] = "still"
            if frame is not None:
                row["frame"] = frame
                row["display_file"] = (
                    args.display_file
                    or f"display/p{frame['packet_id']:02d}_f{frame['frame_index']:03d}.png"
                )
            records.append(row)
    added = session_mod.add_captures(args.session, records, kind=args.kind)
    _emit(
        {
            "session": str(args.session),
            "added": len(added),
            "captures": [
                {
                    "path": row["path"],
                    "kind": row["kind"],
                    "frame": row.get("frame"),
                    "sha256": row["sha256"],
                }
                for row in added
            ],
        }
    )
    return 0


def cmd_session_validate(args: argparse.Namespace) -> int:
    problems = session_mod.validate_session(args.session)
    session = session_mod.load_session(args.session)
    _emit(
        {
            "session": str(args.session),
            "valid": not problems,
            "problems": problems,
            "status": session.status,
            "capture_source": session.capture_source,
            "evidence_source": session.evidence_source,
            "captures": len(session_mod.load_captures(args.session)),
        }
    )
    return 0 if not problems else 3


def cmd_session_finalize(args: argparse.Namespace) -> int:
    lock = session_mod.finalize_session(args.session)
    _emit(lock)
    return 0


def cmd_session_list(args: argparse.Namespace) -> int:
    _emit({"root": str(args.root), "sessions": session_mod.list_sessions(args.root)})
    return 0


def cmd_session_show(args: argparse.Namespace) -> int:
    session = session_mod.load_session(args.session)
    payload = session.to_dict()
    payload["validation_problems"] = session_mod.validate_session(args.session)
    _emit(payload)
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="otl",
        description="Screen-to-camera optical data transmission lab",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser, *, channel: bool = True) -> None:
        p.add_argument("--config", help="JSON ExperimentConfig file")
        if channel:
            p.add_argument(
                "--channel",
                choices=sorted(CHANNEL_PRESETS),
                default="clean",
                help="synthetic channel preset (ignored with --config)",
            )
        p.add_argument("--seed", type=int, default=None, help="RNG seed")

    p = sub.add_parser("manifest", help="print protocol, pipeline and layout constants")
    add_common(p)
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("info", help="print a compact system summary")
    add_common(p)
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("render", help="render a payload to PNG frames")
    add_common(p)
    p.add_argument("--text", help="payload text (alternative to --input)")
    p.add_argument("--input", help="payload file")
    p.add_argument("--name", help="file name stored in the 32-byte header")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--limit", type=int, default=None, help="write at most N frames")
    p.add_argument("--include-cells", action="store_true", help="include cell values in JSON")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("decode", help="decode one prerecorded frame image")
    add_common(p)
    p.add_argument("image", help="PNG/JPEG frame captured or rendered")
    p.add_argument("--out", help="write the JSON result here as well")
    p.set_defaults(func=cmd_decode)

    p = sub.add_parser("transfer-sim", help="run the complete simulated transfer")
    add_common(p)
    p.add_argument("--text", help="payload text (alternative to --input)")
    p.add_argument("--input", help="payload file")
    p.add_argument("--name", help="file name stored in the 32-byte header")
    p.add_argument("--out", help="write the JSON result here as well")
    p.add_argument("--drop", type=float, default=0.0, help="independent frame loss probability")
    p.add_argument("--no-optics", action="store_true", help="skip channel degradations")
    p.set_defaults(func=cmd_transfer_sim)

    p = sub.add_parser("selftest", help="run fast internal smoke checks")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("play", help="build a full-screen HTML player for rendered frames")
    p.add_argument("frames", help="directory containing pNN_fNNN.png frames")
    p.add_argument("--out", required=True, help="output HTML file")
    p.add_argument("--fps", type=float, default=60.0, help="display rate")
    p.add_argument("--hold", action="store_true", help="start in hold mode")
    p.add_argument("--frame", type=int, default=None, help="hold this frame index")
    p.add_argument("--no-loop", action="store_true", help="stop at the last frame")
    p.add_argument("--no-embed", action="store_true", help="reference PNGs instead of embedding")
    p.add_argument("--delay", type=float, default=1.0, help="seconds before playback starts")
    p.add_argument("--hud", action="store_true", help="show frame counter")
    p.add_argument("--autostart", action="store_true", help="start without pressing Start")
    p.add_argument("--title", default="OTL transmitter", help="page title")
    p.set_defaults(func=cmd_play)

    cap = sub.add_parser("capture", help="drive a local camera with ffmpeg")
    cap_sub = cap.add_subparsers(dest="capture_command", required=True)
    cp = cap_sub.add_parser("list", help="list AVFoundation video devices")
    cp.set_defaults(func=cmd_capture_list)
    cp = cap_sub.add_parser("probe", help="show ffmpeg formats for one device")
    cp.add_argument("device", type=int)
    cp.set_defaults(func=cmd_capture_probe)
    cp = cap_sub.add_parser("still", help="capture a short burst of still frames")
    cp.add_argument("device", type=int)
    cp.add_argument("--out", required=True, help="capture root directory")
    cp.add_argument("--frames", type=int, default=8)
    cp.add_argument("--fps", type=int, default=30)
    cp.add_argument("--size", help="WxH (optional)")
    cp.set_defaults(func=cmd_capture_still)
    cp = cap_sub.add_parser("video", help="record a video clip")
    cp.add_argument("device", type=int)
    cp.add_argument("--out", required=True, help="output .mp4 path")
    cp.add_argument("--duration", type=float, required=True, help="seconds")
    cp.add_argument("--fps", type=int, default=30)
    cp.add_argument("--size", help="WxH (optional)")
    cp.set_defaults(func=cmd_capture_video)

    ses = sub.add_parser("session", help="create and inspect physical capture sessions")
    ses_sub = ses.add_subparsers(dest="session_command", required=True)
    sp = ses_sub.add_parser("new", help="create a new session directory")
    sp.add_argument("session_id")
    sp.add_argument("--root", default="datasets/physical", help="sessions root")
    sp.add_argument(
        "--source",
        choices=list(session_mod.CAPTURE_SOURCES),
        default="camera",
        help="camera/manual-import are physical; fixture is not",
    )
    sp.add_argument("--device-model", default="")
    sp.add_argument("--device-os", default="")
    sp.add_argument("--camera", default="")
    sp.add_argument("--device-notes", default="")
    sp.add_argument("--display-model", default="")
    sp.add_argument("--display-kind", default="phone")
    sp.add_argument("--display-width", type=int, default=None)
    sp.add_argument("--display-height", type=int, default=None)
    sp.add_argument("--refresh-hz", type=float, default=None)
    sp.add_argument("--brightness", default="")
    sp.add_argument("--display-notes", default="")
    sp.add_argument("--distance-mm", type=float, default=None)
    sp.add_argument("--angle-deg", type=float, default=None)
    sp.add_argument("--ambient-lux", type=float, default=None)
    sp.add_argument("--lighting", default="")
    sp.add_argument("--hand-held", action="store_true", default=None)
    sp.add_argument("--geometry-notes", default="")
    sp.add_argument("--mode", default="photo")
    sp.add_argument("--resolution", default="")
    sp.add_argument("--capture-fps", type=float, default=None)
    sp.add_argument("--exposure", default="")
    sp.add_argument("--iso", default="")
    sp.add_argument("--focus", default="")
    sp.add_argument("--zoom", default="")
    sp.add_argument("--stabilization", default="")
    sp.add_argument("--format", default="")
    sp.add_argument("--capture-notes", default="")
    sp.add_argument("--notes", default="")
    sp.set_defaults(func=cmd_session_new)

    sp = ses_sub.add_parser("attach", help="copy displayed frames + player manifest")
    sp.add_argument("session")
    sp.add_argument("--frames", required=True, help="directory with the displayed PNGs")
    sp.add_argument("--player-manifest", required=True)
    sp.add_argument("--payload-name", default="")
    sp.add_argument("--payload-sha256", default="")
    sp.set_defaults(func=cmd_session_attach)

    sp = ses_sub.add_parser("ingest", help="preserve camera images/videos in a session")
    sp.add_argument("session")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--kind", choices=("still", "video"), default="still")
    sp.add_argument(
        "--frame",
        default=None,
        help="ground-truth frame for stills as PACKET:INDEX",
    )
    sp.add_argument("--display-file", default=None)
    sp.add_argument("--source", default="camera")
    sp.add_argument("--notes", default="")
    sp.add_argument("--max-frames", type=int, default=None)
    sp.add_argument("--stride", type=int, default=1)
    sp.set_defaults(func=cmd_session_ingest)

    sp = ses_sub.add_parser("validate", help="check that a session is complete")
    sp.add_argument("session")
    sp.set_defaults(func=cmd_session_validate)

    sp = ses_sub.add_parser("finalize", help="lock and fingerprint a valid session")
    sp.add_argument("session")
    sp.set_defaults(func=cmd_session_finalize)

    sp = ses_sub.add_parser("list", help="list sessions under a root")
    sp.add_argument("--root", default="datasets/physical")
    sp.set_defaults(func=cmd_session_list)

    sp = ses_sub.add_parser("show", help="print a session manifest")
    sp.add_argument("session")
    sp.set_defaults(func=cmd_session_show)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except OTLError as exc:
        _emit(exc.to_dict(), stream=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _emit({"code": "E_IO", "message": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
