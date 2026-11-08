#!/usr/bin/env python3
"""Capture one prepared M11 arm into a locked physical session.

The script is the M11 analogue of the manual M9/M10 capture procedure:

1. create a fresh ``m11-*`` session with explicit device/display metadata,
2. attach the exact displayed frames and player manifest,
3. merge the arm manifest into ``transmitter.m11``,
4. point the existing Safari window at ``player.html?fps=10``,
5. record a video with the Continuity Camera,
6. ingest every video frame, then validate and finalize the session.

Nothing existing is modified: sessions are new directories and the M9/M10
baselines are never touched.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from otl.rx import capture as capture_mod  # noqa: E402
from otl.rx import session as session_mod  # noqa: E402

ARM_SLUGS = {
    "A0_reference": "a0-reference",
    "A1_fill_adaptive": "a1-fill-adaptive",
    "A2_bundle": "a2-bundle",
    "A3_dictionary": "a3-dictionary",
    "A4_always_on": "a4-always-on",
    "A5_rs24": "a5-rs24",
}


def _utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _osa(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _safari_player(url: str, window_id: int) -> None:
    _osa(
        f'tell application "Safari"\n'
        f"  activate\n"
        f"  set bounds of window id {window_id} to {{250, 120, 700, 700}}\n"
        f'  set URL of current tab of window id {window_id} to "{url}"\n'
        f"end tell"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", required=True, choices=sorted(ARM_SLUGS))
    parser.add_argument(
        "--staging", default=str(ROOT / "datasets" / "physical" / "m11-staging")
    )
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--window-id", type=int, required=True)
    parser.add_argument("--device", type=int, default=1)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--size", default="1920x1440")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument(
        "--root", default=str(ROOT / "datasets" / "physical")
    )
    parser.add_argument("--start-delay", type=float, default=3.0)
    parser.add_argument("--brightness", default="0.354058")
    args = parser.parse_args(argv)

    staging = Path(args.staging) / args.arm
    manifest = json.loads(
        (staging / "m11_manifest.json").read_text(encoding="utf-8")
    )
    fps = float(manifest["fps"])
    session_id = f"m11-{ARM_SLUGS[args.arm]}-{_utc_stamp()}"
    root = Path(args.root)

    created = session_mod.new_session(
        root,
        session_id,
        capture_source="camera",
        device=session_mod.DeviceInfo(
            model="iPhone14,2 (Continuity Camera, 'Arsh Camera')",
            os="iOS (Continuity Camera via macOS)",
            camera="rear camera, Continuity Camera, AVFoundation index 1",
        ),
        display=session_mod.DisplayInfo(
            model="Apple M5 built-in Liquid Retina (MacBook Air)",
            kind="computer",
            width_px=2560,
            height_px=1664,
            refresh_hz=60.0,
            brightness=(
                f"fraction {args.brightness} of controller range (0..1); "
                "not nits"
            ),
            notes="brightness held at the M10 restored fraction",
        ),
        geometry=session_mod.GeometryInfo(
            lighting="indoor, unchanged from M10; illuminance not measured",
            notes=(
                "phone position not instrumented; distance, angle and ambient "
                "lux not measured"
            ),
        ),
        capture=session_mod.CaptureSettings(
            mode="video",
            resolution=args.size,
            fps=float(args.fps),
            exposure="auto",
            iso="auto",
            focus="auto (Continuity Camera)",
            zoom="1x (camera default; not independently measured)",
            stabilization="not instrumented (Continuity Camera)",
            format="H.264 MP4 via AVFoundation",
            notes=(
                f"Safari window {{250,120,700,700}} points; "
                f"player.html?fps={fps:g}; {args.arm}"
            ),
        ),
        notes=(
            f"M11 arm {args.arm}: {manifest['title']}. Frozen M9 frame format, "
            "renderer, player and decoder. Physical factor values remain "
            "unmeasured."
        ),
    )
    print(f"session: {created}")

    session_mod.attach_transmitter(
        created,
        staging / "frames",
        staging / "player_manifest.json",
        payload_name=str(manifest.get("payload_name") or ""),
        payload_sha256=str(manifest.get("application_sha256") or ""),
    )
    session = session_mod.load_session(created)
    transmitter = dict(session.transmitter)
    transmitter["m11"] = manifest
    session.transmitter = transmitter
    session_mod.save_session(created, session)

    url = (
        (staging / "player.html").resolve().as_uri()
        + f"?fps={fps:g}"
    )
    _safari_player(url, args.window_id)
    print(f"player: {url}")
    time.sleep(args.start_delay + 1.0)

    video = created / "captures" / "originals" / (
        f"{args.arm}_{fps:g}fps.mp4"
    )
    log = capture_mod.capture_video(
        args.device,
        video,
        duration_s=args.duration,
        fps=args.fps,
        size=args.size,
    )
    print(f"video: {video} ({log['bytes']} bytes)")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "otl",
            "session",
            "ingest",
            str(created),
            str(video),
            "--kind",
            "video",
            "--stride",
            str(args.stride),
            "--source",
            "camera",
            "--notes",
            f"{args.arm} player capture",
        ],
        check=True,
        cwd=str(ROOT),
    )

    problems = session_mod.validate_session(created)
    if problems:
        print(json.dumps({"status": "invalid", "problems": problems}, indent=2))
        return 1
    lock = session_mod.finalize_session(created)
    print(
        json.dumps(
            {
                "status": "final",
                "session": str(created),
                "captures": lock["capture_count"],
                "lock": lock,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
