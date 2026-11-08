"""Synthetic optical channel.

Every parameter is a simulation knob, not a measurement.  The channel is
deterministic for a fixed seed and applies, in order: perspective warp,
brightness/gamma, ambient offset, vignette, blur (Gaussian and motion), sensor
noise, and JPEG compression.  Physical captures bypass this module entirely and
are loaded with :func:`load_capture`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from ..config import ChannelConfig
from ..errors import ChannelError

try:  # OpenCV is an optional accelerator; numpy/Pillow fallbacks keep tests usable.
    import cv2
except Exception:  # pragma: no cover - exercised only on minimal installs
    cv2 = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Capture:
    """One image plus the provenance needed to classify results honestly."""

    image: np.ndarray
    source: str  # "simulated" or "physical"
    device: str = ""
    notes: str = ""


def _perspective(image: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return image
    if cv2 is None:
        raise ChannelError(
            "perspective simulation requires OpenCV",
            component="channel",
            operation="perspective",
        )
    h, w = image.shape[:2]
    p = min(amount, 0.45)
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    dst = np.float32(
        [
            [p * w, p * h * 0.6],
            [w - 1 - p * w * 0.7, p * h * 0.2],
            [w - 1 - p * w * 0.5, h - 1 - p * h * 0.5],
            [p * w * 0.8, h - 1 - p * h * 0.7],
        ]
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def _motion_blur(image: np.ndarray, length: int, angle_deg: float) -> np.ndarray:
    if length <= 1:
        return image
    if cv2 is None:
        raise ChannelError(
            "motion blur requires OpenCV",
            component="channel",
            operation="motion_blur",
        )
    size = length if length % 2 == 1 else length + 1
    kernel = np.zeros((size, size), dtype=np.float32)
    kernel[size // 2, :] = 1.0
    rotation = cv2.getRotationMatrix2D((size / 2 - 0.5, size / 2 - 0.5), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, rotation, (size, size))
    total = kernel.sum()
    if total == 0:
        return image
    kernel /= total
    return cv2.filter2D(image, -1, kernel)


def _vignette(image: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return image
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    radius /= radius.max() or 1.0
    factor = np.clip(1.0 - amount * radius**2, 0.0, 1.0)
    return image * factor


def _jpeg(image: np.ndarray, quality: int) -> np.ndarray:
    if quality >= 100:
        return image
    if cv2 is None:
        raise ChannelError(
            "JPEG simulation requires OpenCV",
            component="channel",
            operation="jpeg",
        )
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ChannelError("JPEG encoding failed", component="channel")
    return cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)


def apply_channel(
    image: np.ndarray,
    cfg: ChannelConfig | None = None,
    *,
    seed: int | None = None,
) -> np.ndarray:
    """Apply the configured degradations and return ``uint8`` grayscale."""
    cfg = cfg or ChannelConfig()
    if image.ndim != 2:
        raise ChannelError(
            "channel expects a single-channel image",
            component="channel",
            operation="apply_channel",
            shape=image.shape,
        )
    rng = np.random.default_rng(cfg.seed if seed is None else seed)
    result = image.astype(np.float32, copy=True)

    result = _perspective(result, cfg.perspective)

    if cfg.brightness != 1.0 or cfg.gamma != 1.0:
        normalized = np.clip(result / 255.0, 0.0, 1.0)
        result = np.power(normalized, cfg.gamma) * 255.0 * cfg.brightness

    if cfg.ambient:
        result = result + cfg.ambient

    result = _vignette(result, cfg.vignette)

    if cfg.blur_sigma > 0:
        if cv2 is not None:
            result = cv2.GaussianBlur(result, (0, 0), cfg.blur_sigma)
        else:  # pragma: no cover
            from PIL import ImageFilter

            result = np.asarray(
                Image.fromarray(np.clip(result, 0, 255).astype(np.uint8)).filter(
                    ImageFilter.GaussianBlur(cfg.blur_sigma)
                ),
                dtype=np.float32,
            )

    if cfg.motion_blur_px > 1:
        result = _motion_blur(result, cfg.motion_blur_px, cfg.motion_angle_deg)

    if cfg.noise_sigma > 0:
        result = result + rng.normal(0.0, cfg.noise_sigma, size=result.shape)

    result = np.clip(result, 0.0, 255.0)
    if cfg.jpeg_quality < 100:
        result = _jpeg(result.astype(np.uint8), cfg.jpeg_quality).astype(np.float32)
    return result.astype(np.uint8)


def load_capture(path: str, *, device: str = "", notes: str = "") -> Capture:
    """Load a physical or prerecorded image without altering it."""
    try:
        with Image.open(path) as image:
            array = np.asarray(image.convert("L"), dtype=np.uint8).copy()
    except OSError as exc:
        raise ChannelError(
            "cannot read capture",
            component="channel",
            operation="load_capture",
            path=path,
        ) from exc
    source = "physical" if device else "simulated"
    return Capture(image=array, source=source, device=device, notes=notes)


def channel_manifest(cfg: ChannelConfig | None = None) -> dict[str, object]:
    cfg = cfg or ChannelConfig()
    return {
        "model": "perspective -> brightness/gamma -> ambient -> vignette -> blur -> noise -> jpeg",
        "simulation": True,
        "opencv": cv2 is not None,
        "config": {
            "blur_sigma": cfg.blur_sigma,
            "motion_blur_px": cfg.motion_blur_px,
            "motion_angle_deg": cfg.motion_angle_deg,
            "noise_sigma": cfg.noise_sigma,
            "ambient": cfg.ambient,
            "brightness": cfg.brightness,
            "gamma": cfg.gamma,
            "vignette": cfg.vignette,
            "perspective": cfg.perspective,
            "jpeg_quality": cfg.jpeg_quality,
            "seed": cfg.seed,
        },
    }
