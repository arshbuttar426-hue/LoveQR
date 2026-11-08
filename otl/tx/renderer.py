"""Screen renderer for the 30-cell spatial code.

The renderer is deterministic: given the same cell values and configuration it
produces byte-identical pixels.  It knows nothing about cameras or packets; it
only turns cell values into an image, which makes the transmitter testable
without a display.

Triangle bit convention (from :mod:`otl.codec.patterns`): bit 3 top, bit 2
right, bit 1 bottom, bit 0 left; ``1`` means white, ``0`` means black.

For throughput experiments thousands of frames are rendered.  A
:class:`FrameRenderer` therefore pre-renders the sixteen possible cell tiles
and the static background once, then composes each frame by pasting tiles.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from ..codec.patterns import pattern_colors
from ..config import TRIANGLE_UNIT, Layout, ScreenConfig
from ..errors import ConfigError, ProtocolError


class FrameRenderer:
    """Cached tile renderer for one layout and screen configuration."""

    def __init__(self, layout: Layout, screen: ScreenConfig | None = None) -> None:
        self.layout = layout
        self.screen = screen or ScreenConfig()
        if self.screen.supersample < 1:
            raise ConfigError("supersample must be >= 1", component="tx")
        self._background = self._make_background()
        self._tiles = {value: self._make_tile(value) for value in range(16)}

    def _make_background(self) -> Image.Image:
        layout = self.layout
        screen = self.screen
        ss = screen.supersample
        image = Image.new("L", (layout.canvas_w * ss, layout.canvas_h * ss), 255)
        draw = ImageDraw.Draw(image)
        for name, rect in layout.fiducial_rects().items():
            draw.rectangle(
                [
                    rect.x * ss,
                    rect.y * ss,
                    (rect.x + rect.w) * ss - 1,
                    (rect.y + rect.h) * ss - 1,
                ],
                fill=0,
            )
            if name == "tl":
                hole = max(2, int(rect.w * 0.4))
                cx = rect.x + rect.w // 2
                cy = rect.y + rect.h // 2
                draw.rectangle(
                    [
                        (cx - hole // 2) * ss,
                        (cy - hole // 2) * ss,
                        (cx + hole // 2) * ss - 1,
                        (cy + hole // 2) * ss - 1,
                    ],
                    fill=255,
                )
        if screen.border_px > 0:
            # A solid outer frame, placed outside the fiducials with a white
            # gap so that it never merges with them into one connected
            # component.  It is drawn as one thick outline in supersampled
            # coordinates; drawing many one-pixel outlines would alias into a
            # dashed grey ring after downsampling.
            width = max(1, screen.border_px)
            fid = layout.fiducial_rects()
            left = min(r.x for r in fid.values())
            top = min(r.y for r in fid.values())
            right = max(r.x + r.w for r in fid.values())
            bottom = max(r.y + r.h for r in fid.values())
            pad = layout.gap_px + width
            draw.rectangle(
                [
                    (left - pad) * ss,
                    (top - pad) * ss,
                    (right + pad) * ss - 1,
                    (bottom + pad) * ss - 1,
                ],
                outline=0,
                width=width * ss,
            )
        if ss > 1:
            image = image.resize((layout.canvas_w, layout.canvas_h), Image.LANCZOS)
        return image

    def _make_tile(self, value: int) -> Image.Image:
        layout = self.layout
        ss = self.screen.supersample
        size = layout.cell_px
        image = Image.new("L", (size * ss, size * ss), 255)
        draw = ImageDraw.Draw(image)
        for triangle, white in enumerate(pattern_colors(value)):
            if white:
                continue
            points = [
                (int(round(ux * size * ss)), int(round(uy * size * ss)))
                for ux, uy in TRIANGLE_UNIT[triangle]
            ]
            draw.polygon(points, fill=0)
        if ss > 1:
            image = image.resize((size, size), Image.LANCZOS)
        return image

    def render(self, cells: Sequence[int], *, invert: bool = False) -> np.ndarray:
        expected = self.layout.cols * self.layout.rows
        if len(cells) != expected:
            raise ProtocolError(
                "wrong number of cells for the screen layout",
                component="tx",
                operation="render",
                expected=expected,
                actual=len(cells),
            )
        values = tuple(int(c) for c in cells)
        if any(not 0 <= c <= 0xF for c in values):
            raise ProtocolError(
                "cell value outside the 4-bit alphabet",
                component="tx",
                operation="render",
            )
        image = self._background.copy()
        for index, value in enumerate(values):
            row, col = divmod(index, self.layout.cols)
            rect = self.layout.cell_rect(row, col)
            image.paste(self._tiles[value], (rect.x, rect.y))
        if invert:
            image = ImageOps.invert(image)
        return np.asarray(image, dtype=np.uint8).copy()


@lru_cache(maxsize=8)
def _cached_renderer(layout: Layout, screen: ScreenConfig) -> FrameRenderer:
    return FrameRenderer(layout, screen)


def renderer_for(layout: Layout, screen: ScreenConfig | None = None) -> FrameRenderer:
    return _cached_renderer(layout, screen or ScreenConfig())


def render_frame(
    cells: Sequence[int],
    layout: Layout,
    screen: ScreenConfig | None = None,
    *,
    invert: bool = False,
) -> np.ndarray:
    """Render one 30-cell frame to a grayscale ``uint8`` image."""
    return renderer_for(layout, screen).render(cells, invert=invert)


def render_inverted(
    cells: Sequence[int],
    layout: Layout,
    screen: ScreenConfig | None = None,
) -> np.ndarray:
    return render_frame(cells, layout, screen, invert=True)


def save_frame(path: str, image: np.ndarray) -> None:
    """Write a rendered frame as a lossless PNG."""
    Image.fromarray(image, mode="L").save(path)


def load_frame(path: str) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8).copy()


def render_sequence(
    frames: Sequence[Sequence[int]],
    layout: Layout,
    screen: ScreenConfig | None = None,
) -> list[np.ndarray]:
    renderer = renderer_for(layout, screen)
    return [renderer.render(cells) for cells in frames]


def render_blink_frames(
    cells: Sequence[int],
    bits: Sequence[int],
    layout: Layout,
    screen: ScreenConfig | None = None,
) -> list[np.ndarray]:
    """Render a temporal chip sequence for one static spatial frame.

    ``bit == 1`` renders the normal frame, ``bit == 0`` renders its inverse.
    """
    renderer = renderer_for(layout, screen)
    normal = renderer.render(cells)
    inverted = renderer.render(cells, invert=True)
    return [normal if bit else inverted for bit in bits]
