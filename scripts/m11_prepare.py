#!/usr/bin/env python3
"""Prepare one M11 arm: PNG frames, player HTML and an exact manifest.

Example::

    python3 scripts/m11_prepare.py --arm A1_fill_adaptive \
        --out datasets/physical/m11-staging/A1 --fps 10

The script writes:

``frames/pNN_fNNN.png``
    the exact frames to display, using the frozen M9 renderer.
``player.html`` / ``player_manifest.json``
    the frozen M9 player, generated from those frames.
``payload.bin`` or ``payloads/``
    the original application bytes that must be recovered.
``wire.bin``
    the bytes actually encoded into the packet (compressed or bundle form).
``m11_manifest.json``
    arm metadata, SHA-256 of every artefact and the bundle entry manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.m11_payloads import ARM_IDS, build_arm  # noqa: E402
from otl.config import ExperimentConfig  # noqa: E402
from otl.protocol.frame import pack_frame  # noqa: E402
from otl.tx.player import PlayerConfig, build_player  # noqa: E402
from otl.tx.renderer import renderer_for, save_frame  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(arm_id: str, out: Path, *, fps: float, embed: bool) -> dict[str, object]:
    arm = build_arm(arm_id)
    out.mkdir(parents=True, exist_ok=True)
    frames_dir = out / "frames"
    frames_dir.mkdir(exist_ok=True)

    cfg = ExperimentConfig()
    renderer = renderer_for(cfg.layout(), cfg.screen)
    frame_paths: list[Path] = []
    for header, data in arm.frames:
        cells = pack_frame(header, data, cfg.protocol)
        image = renderer.render(cells)
        path = frames_dir / f"p{header.packet_id:02d}_f{header.frame_index:03d}.png"
        save_frame(str(path), image)
        frame_paths.append(path)

    player = out / "player.html"
    player_result = build_player(
        frame_paths,
        player,
        PlayerConfig(
            fps=fps,
            loop=True,
            hold=False,
            embed=embed,
            title=f"M11 {arm.arm_id}",
            start_delay_s=3.0,
            show_hud=False,
            autostart=True,
        ),
    )

    payloads_dir = out / "payloads"
    payloads_dir.mkdir(exist_ok=True)
    entry_files: list[dict[str, object]] = []
    if arm.bundle is not None:
        for entry in arm.bundle:
            path = payloads_dir / entry.name
            path.write_bytes(entry.data)
            entry_files.append(
                {
                    "name": entry.name,
                    "file": str(path.relative_to(out)),
                    "bytes": len(entry.data),
                    "sha256": _sha256(entry.data),
                }
            )
    else:
        if arm.application_payload is None:
            raise AssertionError("non-bundle arm has no application payload")
        path = out / "payload.bin"
        path.write_bytes(arm.application_payload)
        entry_files.append(
            {
                "name": path.name,
                "file": str(path.relative_to(out)),
                "bytes": len(arm.application_payload),
                "sha256": _sha256(arm.application_payload),
            }
        )

    wire_path = out / "wire.bin"
    wire_path.write_bytes(arm.wire)

    manifest = arm.to_dict()
    manifest.update(
        {
            "schema": "otl-m11-arm/1",
            "fps": fps,
            "embed": embed,
            "frames_dir": "frames",
            "player_html": str(player.relative_to(out)),
            "player_manifest": str(Path(player_result["manifest"]).relative_to(out)),
            "player_manifest_sha256": _sha256(
                Path(player_result["manifest"]).read_bytes()
            ),
            "player_html_sha256": player_result["player_html_sha256"],
            "wire_file": "wire.bin",
            "entries": entry_files,
        }
    )
    _write_json(out / "m11_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=ARM_IDS)
    parser.add_argument("--out", required=True)
    parser.add_argument("--fps", type=float, default=10.0)
    parser.add_argument("--no-embed", action="store_true")
    args = parser.parse_args(argv)
    manifest = prepare(
        args.arm,
        Path(args.out),
        fps=args.fps,
        embed=not args.no_embed,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
