import io

import numpy as np
from PIL import Image

from zectrix_collector.render.heatmap import heatmap_pixels, heatmap_png


def test_heatmap_size_and_palette():
    grid = [[0, 1, 2, 3, 4, -1, -1]] * 3
    png, w, h = heatmap_png(grid)
    assert (w, h) == (3 * 13 - 2, 7 * 13 - 2)
    im = Image.open(io.BytesIO(png))
    assert im.size == (w, h)
    assert set(np.unique(np.asarray(im))) <= {0, 1}  # black / white palette indices only


def test_heatmap_fill_grows_with_level():
    for style in ("stripes", "dither"):
        img = heatmap_pixels([[0, 1, 2, 3, 4, -1, -1]], style=style)
        black = [int((img[y * 13 + 1:y * 13 + 10, 1:10] == 0).sum()) for y in range(5)]
        # level 0 = outline only (4 rounded-corner pixels inside the box), level 4 = solid
        assert black[0] == 4 and black[4] == 81, (style, black)
        assert all(a < b for a, b in zip(black, black[1:], strict=False)), (style, black)


def test_skipped_days_are_blank():
    img = heatmap_pixels([[-1] * 7])
    assert (img == 1).all()
