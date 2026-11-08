"""Camera capture and ingestion for physical OTL sessions.

This module is the *receiver interface*.  It does not decode anything; it only
gets real camera bytes into a session directory without altering them.  Two
paths are supported:

* :func:`capture_still` / :func:`capture_video` drive a local AVFoundation
  device through ``ffmpeg`` (macOS).  The exact command is recorded.
* :func:`ingest_image` / :func:`ingest_video` import files produced by a phone
  or another camera.  Original bytes are copied verbatim and hashed; if the
  format cannot be read by Pillow (for example HEIC), a derived PNG is written
  next to it and both hashes are recorded.  The original is never modified.

Every file operation is non-destructive: an existing file is never overwritten,
and a capture session directory is never reused.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..errors import CaptureError

try:  # Pillow is a hard dependency, but keep the import explicit for tests.
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore[assignment]

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CameraDevice:
    index: int
    name: str
    kind: str = "video"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaptureFile:
    """One preserved image or video plus the path the decoder should read."""

    path: str
    sha256: str
    bytes: int
    width: int | None = None
    height: int | None = None
    format: str = ""
    original_path: str | None = None
    original_sha256: str | None = None
    derived_path: str | None = None
    derived_sha256: str | None = None
    source: str = "camera"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StillCapture:
    directory: str
    device: int
    command: list[str]
    frames: list[CaptureFile] = field(default_factory=list)
    selected: CaptureFile | None = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _unique_path(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    for counter in range(1, 10000):
        candidate = directory / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
    raise CaptureError(
        "could not find a free file name",
        component="rx",
        operation="unique_path",
        name=name,
    )


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _dimensions(path: Path) -> tuple[int | None, int | None]:
    if Image is not None:
        try:
            with Image.open(path) as image:
                return int(image.width), int(image.height)
        except Exception:
            pass
    if cv2 is not None:
        array = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if array is not None:
            return int(array.shape[1]), int(array.shape[0])
    return None, None


def _is_readable(path: Path) -> bool:
    if Image is not None:
        try:
            with Image.open(path) as image:
                image.verify()
            return True
        except Exception:
            pass
    if cv2 is not None:
        return cv2.imread(str(path), cv2.IMREAD_UNCHANGED) is not None
    return False


def _derive_png(path: Path, out_dir: Path) -> Path:
    """Convert an unreadable camera format (for example HEIC) to PNG."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_path(out_dir, path.stem + ".png")
    sips = shutil.which("sips")
    if sips:
        proc = subprocess.run(
            [sips, "-s", "format", "png", str(path), "--out", str(target)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and target.is_file():
            return target
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
             "-frames:v", "1", "-y", str(target)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and target.is_file():
            return target
    raise CaptureError(
        "cannot read capture and no converter is available",
        component="rx",
        operation="derive_png",
        path=str(path),
        hint="convert the file to PNG/JPEG with sips, ffmpeg or the Photos app",
    )


def _record(path: Path, root: Path, *, source: str = "camera", notes: str = "") -> CaptureFile:
    width, height = _dimensions(path)
    return CaptureFile(
        path=_relative(path, root),
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        width=width,
        height=height,
        format=path.suffix.lower().lstrip("."),
        source=source,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Local camera control (ffmpeg / AVFoundation)
# ---------------------------------------------------------------------------


def list_cameras() -> list[CameraDevice]:
    """Enumerate AVFoundation video devices without opening one."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return []
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
    )
    devices: list[CameraDevice] = []
    in_video = False
    for line in (proc.stderr + proc.stdout).splitlines():
        if "AVFoundation video devices:" in line:
            in_video = True
            continue
        if "AVFoundation audio devices:" in line:
            in_video = False
            continue
        if not in_video:
            continue
        marker = line.split("] [")
        if len(marker) != 2 or "] " not in marker[1]:
            continue
        index_text, name = marker[1].split("] ", 1)
        try:
            index = int(index_text)
        except ValueError:
            continue
        kind = "screen" if "screen" in name.lower() else "video"
        devices.append(CameraDevice(index=index, name=name.strip(), kind=kind))
    return devices


def _run_ffmpeg(command: list[str], *, timeout_s: float = 120.0) -> None:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s)
    except FileNotFoundError as exc:  # pragma: no cover - depends on host
        raise CaptureError(
            "ffmpeg is not installed",
            component="rx",
            operation="capture",
            hint="install ffmpeg or import images with `otl session ingest`",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CaptureError(
            "camera capture timed out",
            component="rx",
            operation="capture",
            timeout_s=timeout_s,
        ) from exc
    if proc.returncode != 0:
        raise CaptureError(
            "ffmpeg capture failed",
            component="rx",
            operation="capture",
            stderr=proc.stderr[-1200:],
            command=command,
        )


def capture_still(
    device: int,
    out_dir: Path | str,
    *,
    frames: int = 8,
    fps: int = 30,
    size: str | None = None,
) -> StillCapture:
    """Capture a short burst of frames and keep every raw frame.

    The first frames from a consumer camera are often black while exposure and
    white balance settle.  All frames are preserved; ``selected`` points at the
    last frame that is not essentially black, so the caller can decide.
    """
    if frames < 1:
        raise CaptureError(
            "frames must be >= 1", component="rx", operation="capture_still"
        )
    root = Path(out_dir)
    target = root / f"still_{_utc_stamp()}"
    target.mkdir(parents=True, exist_ok=False)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "avfoundation", "-framerate", str(fps),
    ]
    if size:
        command += ["-video_size", size]
    command += ["-i", str(device), "-frames:v", str(frames),
                str(target / "raw_%03d.png")]
    _run_ffmpeg(command, timeout_s=max(30.0, frames / max(fps, 1) * 4 + 15))
    paths = sorted(target.glob("raw_*.png"))
    if not paths:
        raise CaptureError(
            "camera produced no frames",
            component="rx",
            operation="capture_still",
            device=device,
        )
    records = [_record(path, root) for path in paths]
    selected = None
    for record, path in zip(reversed(records), reversed(paths)):
        if Image is not None:
            with Image.open(path) as image:
                array = np.asarray(image.convert("L"), dtype=np.uint8)
            if int(array.max()) > 10 and float(array.std()) > 1.0:
                selected = record
                break
    if selected is None:
        selected = records[-1]
    log = {
        "kind": "still",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "device": device,
        "command": command,
        "frames": [rec.to_dict() for rec in records],
        "selected": selected.to_dict() if selected else None,
    }
    (target / "capture_log.json").write_text(
        json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return StillCapture(
        directory=_relative(target, root),
        device=device,
        command=command,
        frames=records,
        selected=selected,
        notes="all raw frames preserved; selected is the last non-black frame",
    )


def capture_video(
    device: int,
    out: Path | str,
    *,
    duration_s: float,
    fps: int = 30,
    size: str | None = None,
    crf: int = 0,
) -> dict[str, Any]:
    """Record a video with the camera, preserving it as the raw artifact."""
    if duration_s <= 0:
        raise CaptureError(
            "duration_s must be positive", component="rx", operation="capture_video"
        )
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise CaptureError(
            "refusing to overwrite an existing video",
            component="rx",
            operation="capture_video",
            path=str(path),
        )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "avfoundation", "-framerate", str(fps),
    ]
    if size:
        command += ["-video_size", size]
    command += [
        "-i", str(device), "-t", f"{duration_s:.3f}",
        "-c:v", "libx264", "-qp", str(crf), "-pix_fmt", "yuv420p",
        str(path),
    ]
    _run_ffmpeg(command, timeout_s=duration_s + 60.0)
    log = {
        "kind": "video",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "device": device,
        "command": command,
        "file": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "duration_s": duration_s,
        "fps": fps,
    }
    path.with_suffix(path.suffix + ".capture_log.json").write_text(
        json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return log


def probe_device(device: int) -> str:
    """Return ffmpeg's supported-format listing for a device."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "ffmpeg not installed"
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-f", "avfoundation", "-i", str(device)],
        capture_output=True,
        text=True,
    )
    return (proc.stderr or proc.stdout).strip()


# ---------------------------------------------------------------------------
# Ingestion (manual import, video extraction)
# ---------------------------------------------------------------------------


def ingest_image(
    session_dir: Path | str,
    path: Path | str,
    *,
    copy: bool = True,
    source: str = "camera",
    notes: str = "",
) -> CaptureFile:
    """Preserve one image and return the record the decoder should use."""
    root = Path(session_dir)
    original = Path(path)
    if not original.is_file():
        raise CaptureError(
            "capture file does not exist",
            component="rx",
            operation="ingest_image",
            path=str(original),
        )

    try:
        inside = original.resolve().is_relative_to(root.resolve())
    except AttributeError:  # pragma: no cover - Python < 3.9
        inside = str(original.resolve()).startswith(str(root.resolve()))
    preserved = original
    if not inside:
        if not copy:
            raise CaptureError(
                "file is outside the session and copy=False",
                component="rx",
                operation="ingest_image",
                path=str(original),
            )
        originals = root / "captures" / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        preserved = _unique_path(originals, original.name)
        shutil.copy2(original, preserved)

    original_sha = sha256_file(preserved)
    record = _record(preserved, root, source=source, notes=notes)
    decode_path = preserved
    derived: Path | None = None
    if not _is_readable(preserved):
        derived = _derive_png(preserved, root / "captures" / "derived")
        decode_path = derived
        record = CaptureFile(
            **{
                **record.to_dict(),
                "path": _relative(decode_path, root),
                "sha256": sha256_file(decode_path),
                "bytes": decode_path.stat().st_size,
                "format": "png",
                "width": _dimensions(decode_path)[0],
                "height": _dimensions(decode_path)[1],
                "original_path": _relative(preserved, root),
                "original_sha256": original_sha,
                "derived_path": _relative(derived, root),
                "derived_sha256": sha256_file(derived),
            }
        )
    return record


def ingest_video(
    session_dir: Path | str,
    video: Path | str,
    *,
    max_frames: int | None = None,
    stride: int = 1,
) -> tuple[CaptureFile, list[dict[str, Any]]]:
    """Preserve a video and extract lossless PNG frames with timestamps."""
    if cv2 is None:  # pragma: no cover - OpenCV is a declared dependency
        raise CaptureError(
            "video ingestion requires OpenCV",
            component="rx",
            operation="ingest_video",
        )
    root = Path(session_dir)
    source = Path(video)
    if not source.is_file():
        raise CaptureError(
            "video does not exist",
            component="rx",
            operation="ingest_video",
            path=str(source),
        )
    try:
        inside = source.resolve().is_relative_to(root.resolve())
    except AttributeError:  # pragma: no cover
        inside = str(source.resolve()).startswith(str(root.resolve()))
    preserved = source
    if not inside:
        originals = root / "captures" / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        preserved = _unique_path(originals, source.name)
        shutil.copy2(source, preserved)

    video_record = _record(preserved, root, source="camera", notes="original video")
    frames_dir = root / "captures" / "frames" / preserved.stem
    frames_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(preserved))
    if not capture.isOpened():
        raise CaptureError(
            "cannot open video",
            component="rx",
            operation="ingest_video",
            path=str(preserved),
        )
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    records: list[dict[str, Any]] = []
    index = 0
    kept = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % max(stride, 1) == 0:
            pos_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            target = frames_dir / f"frame_{index:06d}.png"
            if not cv2.imwrite(str(target), frame):
                raise CaptureError(
                    "could not write extracted frame",
                    component="rx",
                    operation="ingest_video",
                    path=str(target),
                )
            records.append(
                {
                    "index": index,
                    "pos_msec": pos_msec,
                    "path": _relative(target, root),
                    "sha256": sha256_file(target),
                    "width": int(frame.shape[1]),
                    "height": int(frame.shape[0]),
                }
            )
            kept += 1
            if max_frames is not None and kept >= max_frames:
                break
        index += 1
    capture.release()
    (frames_dir / "frames.json").write_text(
        json.dumps(
            {
                "video": video_record.to_dict(),
                "fps": fps,
                "reported_frames": total,
                "extracted": len(records),
                "stride": stride,
                "frames": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return video_record, records
