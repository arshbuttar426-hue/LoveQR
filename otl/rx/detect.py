"""Fiducial detection, rectification and cell sampling.

The detector works on prerecorded images; no camera object is required.  It
finds the four corner fiducials, computes a homography to the canonical screen
geometry, rectifies the image, and samples the four triangle centroids of each
cell.  Classification is a separate step so that raw samples can be stored and
re-analysed offline.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import Layout, ReceiverConfig
from ..errors import DetectionError

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Fiducials:
    centers: dict[str, tuple[float, float]]
    confidence: float
    method: str

    def ordered(self) -> list[tuple[float, float]]:
        return [self.centers[name] for name in ("tl", "tr", "br", "bl")]


@dataclass(frozen=True)
class CellObservation:
    cells: tuple[int, ...]
    samples: np.ndarray
    confidence: float
    contrast: float
    threshold: float
    bit_margin: float


def _canonical_centers(layout: Layout) -> dict[str, tuple[float, float]]:
    return {name: (rect.cx, rect.cy) for name, rect in layout.fiducial_rects().items()}


def _order_corners(points: np.ndarray) -> dict[str, tuple[float, float]]:
    sums = points[:, 0] + points[:, 1]
    diffs = points[:, 0] - points[:, 1]
    tl = points[int(np.argmin(sums))]
    br = points[int(np.argmax(sums))]
    tr = points[int(np.argmax(diffs))]
    bl = points[int(np.argmin(diffs))]
    return {
        "tl": (float(tl[0]), float(tl[1])),
        "tr": (float(tr[0]), float(tr[1])),
        "br": (float(br[0]), float(br[1])),
        "bl": (float(bl[0]), float(bl[1])),
    }


def find_fiducials(
    image: np.ndarray,
    layout: Layout,
    cfg: ReceiverConfig | None = None,
) -> Fiducials:
    """Find the four corner squares using thresholded connected components."""
    cfg = cfg or ReceiverConfig()
    if image.ndim != 2:
        raise DetectionError(
            "detector expects a grayscale image",
            component="rx",
            operation="find_fiducials",
        )
    if cv2 is None:
        raise DetectionError(
            "fiducial detection requires OpenCV",
            component="rx",
            operation="find_fiducials",
        )
    expected_area = float(layout.fiducial_px**2)
    blurred = cv2.GaussianBlur(image, (3, 3), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[tuple[float, tuple[float, float]]] = []
    for label in range(1, count):
        x, y, w, h, area = stats[label]
        if w == 0 or h == 0:
            continue
        aspect = w / h
        fill = area / float(w * h)
        area_ratio = area / expected_area
        if not (0.6 <= aspect <= 1.7):
            continue
        if not (0.4 <= area_ratio <= 2.0):
            continue
        if fill < 0.45:
            continue
        candidates.append((float(area), (float(centroids[label][0]), float(centroids[label][1]))))
    if len(candidates) < 4:
        if cfg.assume_cropped and image.shape[:2] == (layout.canvas_h, layout.canvas_w):
            return Fiducials(_canonical_centers(layout), 0.0, "assumed")
        raise DetectionError(
            "could not find four fiducials",
            component="rx",
            operation="find_fiducials",
            found=len(candidates),
        )

    # Pick one candidate per image quadrant.  The quadrants are relative to the
    # *captured image*, not the canonical canvas: a phone photo usually contains
    # a screen surrounded by background, so the canvas only occupies part of the
    # frame.  The score combines distance to the image corner with deviation from
    # the expected fiducial area, so large cell blobs are rejected even when they
    # are closer to the centre.
    width, height = float(image.shape[1]), float(image.shape[0])
    diagonal = float(np.hypot(width, height))
    targets = {
        "tl": (0.0, 0.0),
        "tr": (width, 0.0),
        "br": (width, height),
        "bl": (0.0, height),
    }
    quadrant_test = {
        "tl": lambda p: p[0] < width / 2 and p[1] < height / 2,
        "tr": lambda p: p[0] >= width / 2 and p[1] < height / 2,
        "br": lambda p: p[0] >= width / 2 and p[1] >= height / 2,
        "bl": lambda p: p[0] < width / 2 and p[1] >= height / 2,
    }
    chosen: dict[str, tuple[float, float]] = {}
    areas: list[float] = []
    for name, predicate in quadrant_test.items():
        target = targets[name]
        best: tuple[float, float, tuple[float, float]] | None = None
        for area, center in candidates:
            if not predicate(center):
                continue
            distance = float(np.hypot(center[0] - target[0], center[1] - target[1])) / diagonal
            area_penalty = abs(float(np.log(area / expected_area)))
            score = distance + area_penalty
            if best is None or score < best[0]:
                best = (score, area, center)
        if best is not None:
            chosen[name] = best[2]
            areas.append(best[1])
    if len(chosen) < 4:
        if cfg.assume_cropped and image.shape[:2] == (layout.canvas_h, layout.canvas_w):
            return Fiducials(_canonical_centers(layout), 0.0, "assumed")
        raise DetectionError(
            "fiducials did not occupy four distinct quadrants",
            component="rx",
            operation="find_fiducials",
            found=len(chosen),
        )
    spread = (max(areas) - min(areas)) / max(areas) if max(areas) else 1.0
    confidence = float(max(0.0, min(1.0, 1.0 - spread)))
    return Fiducials(chosen, confidence, "components")


def rectify(
    image: np.ndarray,
    fiducials: Fiducials,
    layout: Layout,
) -> tuple[np.ndarray, np.ndarray]:
    """Warp the detected quadrilateral onto the canonical canvas."""
    if cv2 is None:
        raise DetectionError(
            "rectification requires OpenCV",
            component="rx",
            operation="rectify",
        )
    canonical = _canonical_centers(layout)
    source = np.float32(fiducials.ordered())
    target = np.float32([canonical[name] for name in ("tl", "tr", "br", "bl")])
    matrix = cv2.getPerspectiveTransform(source, target)
    warped = cv2.warpPerspective(
        image,
        matrix,
        (layout.canvas_w, layout.canvas_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return warped, matrix


def _disk_mean(image: np.ndarray, cx: float, cy: float, radius: int) -> float:
    h, w = image.shape[:2]
    x0 = max(0, int(round(cx)) - radius)
    x1 = min(w, int(round(cx)) + radius + 1)
    y0 = max(0, int(round(cy)) - radius)
    y1 = min(h, int(round(cy)) + radius + 1)
    if x0 >= x1 or y0 >= y1:
        raise DetectionError(
            "sampling window outside image",
            component="rx",
            operation="sample_cells",
            cx=cx,
            cy=cy,
        )
    patch = image[y0:y1, x0:x1].astype(np.float64)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
    if not mask.any():
        return float(patch.mean())
    return float(patch[mask].mean())


def sample_cells(
    image: np.ndarray,
    layout: Layout,
    cfg: ReceiverConfig | None = None,
) -> np.ndarray:
    """Return a ``(30, 4)`` array of mean intensities per triangle."""
    cfg = cfg or ReceiverConfig()
    samples = np.zeros((layout.rows * layout.cols, 4), dtype=np.float64)
    for index in range(layout.rows * layout.cols):
        row, col = divmod(index, layout.cols)
        for triangle in range(4):
            cx, cy = layout.triangle_centroid(row, col, triangle)
            samples[index, triangle] = _disk_mean(image, cx, cy, cfg.sample_radius_px)
    return samples


def _patch(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(image.shape[1], int(x + w))
    y1 = min(image.shape[0], int(y + h))
    return image[y0:y1, x0:x1].astype(np.float64).reshape(-1)


def reference_levels(
    image: np.ndarray,
    layout: Layout,
) -> tuple[float, float]:
    """Photometric black/white references that exist in *every* frame.

    The four fiducials are always black (the top-left one has a white
    orientation hole), and the gaps between cells are always white.  Together
    they give the receiver a black and a white level even when all 120 data
    triangles are identical — an all-black or all-white payload frame, or the
    zero padding at the end of a short packet.

    Both the fiducials and the data area are sampled, and the extrema are
    combined, so the same function also works on an inverted frame.  The
    constant warp fill outside the drawn screen is never used.
    """
    fid_lo: list[float] = []
    fid_hi: list[float] = []
    for rect in layout.fiducial_rects().values():
        flat = _patch(image, rect.x, rect.y, rect.w, rect.h)
        if flat.size:
            fid_lo.append(float(np.percentile(flat, 10.0)))
            fid_hi.append(float(np.percentile(flat, 90.0)))

    data = _patch(image, layout.origin_x, layout.origin_y, layout.data_w, layout.data_h)
    if data.size == 0:
        data = image.astype(np.float64).reshape(-1)
    lows = [float(np.percentile(data, 1.0)), *fid_lo]
    highs = [float(np.percentile(data, 99.0)), *fid_hi]
    return min(lows), max(highs)


def classify_samples(
    samples: np.ndarray,
    cfg: ReceiverConfig | None = None,
    *,
    reference: tuple[float, float] | None = None,
) -> CellObservation:
    """Threshold triangle samples into 4-bit cell values.

    ``reference`` supplies externally measured black/white levels (normally
    from :func:`reference_levels`).  Without it the decision threshold is
    derived from the triangle samples alone, which fails on frames whose 120
    triangles are all the same colour.
    """
    cfg = cfg or ReceiverConfig()
    if samples.ndim != 2 or samples.shape[1] != 4:
        raise DetectionError(
            "expected a (n, 4) sample array",
            component="rx",
            operation="classify_samples",
            shape=samples.shape,
        )
    flat = samples.reshape(-1)
    lo = float(np.percentile(flat, 5))
    hi = float(np.percentile(flat, 95))
    if reference is not None:
        lo = min(lo, float(reference[0]))
        hi = max(hi, float(reference[1]))
    contrast = (hi - lo) / 255.0
    if contrast < cfg.min_contrast:
        raise DetectionError(
            "insufficient contrast to classify cells",
            component="rx",
            operation="classify_samples",
            contrast=contrast,
            minimum=cfg.min_contrast,
        )
    global_threshold = (lo + hi) / 2.0
    frame_span = max(hi - lo, 1.0)
    values: list[int] = []
    margins: list[float] = []
    for cell in samples:
        local_lo = float(cell.min())
        local_hi = float(cell.max())
        local_span = local_hi - local_lo
        # A cell's own threshold only makes sense when the cell actually
        # contains both triangle colours.  A solid cell still has sensor
        # noise and display mottling; if that noise is bigger than
        # ``min_contrast`` the old rule split the noise and decoded a
        # triangle that is not there.  Requiring the cell span to be a
        # fraction of the frame's black-to-white span keeps the noise
        # below threshold on solid cells while still adapting to a real
        # illumination gradient across a patterned cell.
        if (
            local_span >= cfg.local_threshold_fraction * frame_span
            and local_span / 255.0 >= cfg.min_contrast
        ):
            threshold = (local_lo + local_hi) / 2.0
        else:
            threshold = global_threshold
        value = 0
        for triangle, sample in enumerate(cell):
            if sample > threshold:
                value |= 1 << (3 - triangle)
            margins.append(abs(float(sample) - threshold))
        values.append(value)
    bit_margin = float(np.mean(margins) / (frame_span / 2.0))
    confidence = float(np.clip(bit_margin, 0.0, 1.0))
    return CellObservation(
        cells=tuple(values),
        samples=samples.copy(),
        confidence=confidence,
        contrast=contrast,
        threshold=global_threshold,
        bit_margin=bit_margin,
    )


def detect_geometry(
    image: np.ndarray,
    layout: Layout,
    cfg: ReceiverConfig | None = None,
) -> tuple[np.ndarray, Fiducials, np.ndarray]:
    """Convenience: find fiducials and rectify."""
    cfg = cfg or ReceiverConfig()
    fiducials = find_fiducials(image, layout, cfg)
    rectified, matrix = rectify(image, fiducials, layout)
    return rectified, fiducials, matrix
