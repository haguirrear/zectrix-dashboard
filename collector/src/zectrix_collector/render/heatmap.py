"""GitHub contribution heatmap drawn as an exact-palette (black/white) PNG."""

from __future__ import annotations

import numpy as np

from .eink import to_png

# 4x4 Bayer matrix: a pixel is black when BAYER < density * 16 (ordered dither, no noise)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
DENSITY = {0: 0.0, 1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}  # GitHub's 5 shades -> black coverage


def _fill_dither(lv: int, y: int, x: int) -> bool:
    """Style "dither" (option A, 2026-11-15): ordered dither at 25/50/75% black."""
    return BAYER[y % 4][x % 4] < DENSITY.get(lv, 1.0) * 16


def _fill_stripes(lv: int, y: int, x: int) -> bool:
    """Style "stripes" (option E): diagonal hatching that thickens with activity -
    thin lines (1 of 4), checkerboard (1 of 2), thick lines (3 of 4), then solid."""
    if lv >= 4:
        return True
    return (x + y) % {1: 4, 2: 2, 3: 4}[lv] < {1: 1, 2: 1, 3: 3}[lv]


STYLES = {"dither": _fill_dither, "stripes": _fill_stripes}


def heatmap_pixels(grid: list[list[int]], cell: int = 11, gap: int = 2, style: str = "stripes") -> np.ndarray:
    """Palette-index image of the grid (columns = weeks, rows = Mon..Sun, values 0-4, -1 = skip).
    Each day is a rounded box (1px black outline with clipped corners) whose interior is filled
    by level with the chosen style; empty days are just the outline."""
    black, white = 0, 1  # palette indices (eink.EXACT_RGB order)
    pitch = cell + gap
    w, h = len(grid) * pitch - gap, 7 * pitch - gap
    img = np.full((h, w), white, dtype=np.uint8)
    last = cell - 1
    fill = STYLES.get(style, _fill_stripes)
    for cx, col in enumerate(grid):
        for cy, lv in enumerate(col):
            if lv < 0:
                continue
            x0, y0 = cx * pitch, cy * pitch
            box = img[y0:y0 + cell, x0:x0 + cell]
            for y in range(1, last):  # interior, phase-locked to the box so every day looks alike
                for x in range(1, last):
                    box[y, x] = black if lv > 0 and fill(lv, y - 1, x - 1) else white
            box[0, 1:last] = box[last, 1:last] = black  # straight edges, corners left white...
            box[1:last, 0] = box[1:last, last] = black
            for y, x in ((1, 1), (1, last - 1), (last - 1, 1), (last - 1, last - 1)):
                box[y, x] = black  # ...and a diagonal pixel inside each corner rounds it
    return img


def heatmap_png(grid: list[list[int]], cell: int = 11, gap: int = 2, style: str = "stripes") -> tuple[bytes, int, int]:
    img = heatmap_pixels(grid, cell, gap, style)
    return to_png(img), img.shape[1], img.shape[0]
