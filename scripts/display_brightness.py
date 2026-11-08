#!/usr/bin/env python3
"""Read or set the built-in display brightness on macOS.

This is measurement instrumentation, not part of the optical protocol.  It
uses the private ``DisplayServices`` framework because macOS exposes no public
CLI for the numeric brightness level.  The value is a dimensionless fraction
(0.0..1.0) reported by the display controller; it is **not** a luminance
measurement in nits or cd/m² and it is not comparable across displays.

The command prints one JSON object and fails cleanly on non-macOS hosts or when
the framework/display is unavailable.  It never guesses a value.

Examples::

    python3 scripts/display_brightness.py --get
    python3 scripts/display_brightness.py --set 0.65
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from pathlib import Path


FRAMEWORK = Path(
    "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices"
)
COREGRAPHICS = Path("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")


def _load() -> tuple[ctypes.CDLL, int]:
    # ``Path.is_file()`` can report False for framework symlinks that the
    # dynamic loader resolves through the shared cache, so attempt the load.
    try:
        display_services = ctypes.CDLL(str(FRAMEWORK))
        core_graphics = ctypes.CDLL(str(COREGRAPHICS))
    except OSError as exc:
        raise RuntimeError("DisplayServices/CoreGraphics are unavailable") from exc
    core_graphics.CGMainDisplayID.restype = ctypes.c_uint32
    display_id = int(core_graphics.CGMainDisplayID())
    return display_services, display_id


def get_brightness() -> dict[str, object]:
    services, display_id = _load()
    value = ctypes.c_float(-1.0)
    result = services.DisplayServicesGetBrightness(display_id, ctypes.byref(value))
    if result != 0:
        raise RuntimeError(f"DisplayServicesGetBrightness failed with status {result}")
    return {
        "display_id": display_id,
        "brightness_fraction": round(float(value.value), 6),
        "unit": "fraction of controller range (0..1); not nits",
    }


def set_brightness(value: float) -> dict[str, object]:
    if not 0.0 <= value <= 1.0:
        raise ValueError("brightness must be in 0.0..1.0")
    services, display_id = _load()
    result = services.DisplayServicesSetBrightness(display_id, ctypes.c_float(value))
    if result != 0:
        raise RuntimeError(f"DisplayServicesSetBrightness failed with status {result}")
    time.sleep(0.2)
    observed = get_brightness()
    observed["requested_brightness_fraction"] = round(float(value), 6)
    return observed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--get", action="store_true", help="read current brightness")
    group.add_argument("--set", type=float, metavar="FRACTION", help="set brightness 0..1")
    args = parser.parse_args(argv)
    try:
        payload = get_brightness() if args.get else set_brightness(args.set)
    except Exception as exc:  # pragma: no cover - host/framework dependent
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
