"""Convert an image to the NOTE4C 400x300 BWRY 2bpp frame format (and shared palette helpers).

Output .bin matches the stock firmware's `/upload?format=bwry2bpp`:
30000 bytes, 4 px/byte, pixel 0 in bits 7..6, codes black=0 white=1 yellow=2 red=3.
The dashboard collector reuses fit_image/adjust/dither/to_png for the pet photo and heatmap.

Examples (from collector/):
  uv run eink-convert photo.jpg -o out.bin --preview out.png
  uv run eink-convert photo.jpg -o out.bin --focus 0.5,0.45 --upload <device-ip>
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

W, H = 400, 300

# Device color codes
BLACK, WHITE, YELLOW, RED = 0, 1, 2, 3
CODES = np.array([BLACK, WHITE, YELLOW, RED], dtype=np.uint8)

# Palettes used for color matching (order matches CODES).
# "ideal" = pure sRGB primaries (what the stock web page uses).
# "panel" = approximate real ink colors; matching against these makes the
#           ditherer use red/yellow only where the photo is actually warm.
PALETTES = {
    "ideal": [(0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 0)],
    "panel": [(25, 25, 30), (235, 235, 225), (225, 190, 20), (175, 35, 35)],
}

# Colors used to draw the on-screen preview (roughly what the panel looks like)
PREVIEW_RGB = np.array([(25, 25, 30), (235, 235, 225), (225, 190, 20), (175, 35, 35)], dtype=np.uint8)

# Error-diffusion kernels: (dx, dy, weight)
KERNELS = {
    "fs": [(1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)],
    "atkinson": [(1, 0, 1 / 8), (2, 0, 1 / 8), (-1, 1, 1 / 8), (0, 1, 1 / 8), (1, 1, 1 / 8), (0, 2, 1 / 8)],
    "jjn": [
        (1, 0, 7 / 48), (2, 0, 5 / 48),
        (-2, 1, 3 / 48), (-1, 1, 5 / 48), (0, 1, 7 / 48), (1, 1, 5 / 48), (2, 1, 3 / 48),
        (-2, 2, 1 / 48), (-1, 2, 3 / 48), (0, 2, 5 / 48), (1, 2, 3 / 48), (2, 2, 1 / 48),
    ],
}


def fit_image(img: Image.Image, mode: str, focus: tuple[float, float], rotate: int,
              size: tuple[int, int] = (W, H), zoom: float = 1.0) -> Image.Image:
    """zoom > 1 (cover mode) crops tighter around the focus point."""
    w, h = size
    img = ImageOps.exif_transpose(img).convert("RGB")
    if rotate:
        img = img.rotate(rotate, expand=True)
    if mode == "contain":
        canvas = Image.new("RGB", (w, h), (255, 255, 255))
        fitted = ImageOps.contain(img, (w, h), Image.Resampling.LANCZOS)
        canvas.paste(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
        return canvas
    # cover: scale to fill, then crop around the focus point
    scale = max(w / img.width, h / img.height) * max(zoom, 1.0)
    sw, sh = round(img.width * scale), round(img.height * scale)
    img = img.resize((sw, sh), Image.Resampling.LANCZOS)
    fx, fy = focus
    left = int(np.clip(fx * sw - w / 2, 0, sw - w))
    top = int(np.clip(fy * sh - h / 2, 0, sh - h))
    return img.crop((left, top, left + w, top + h))


def adjust(img: Image.Image, contrast: float, saturation: float, gamma: float, sharpen: float,
           autocontrast: float) -> Image.Image:
    if autocontrast > 0:
        img = ImageOps.autocontrast(img, cutoff=autocontrast)
    if gamma != 1.0:
        lut = [round(255 * (i / 255) ** (1 / gamma)) for i in range(256)]
        img = img.point(lut * 3)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)
    if sharpen > 0:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=int(sharpen * 100), threshold=2))
    return img


def dither(img: Image.Image, palette: list[tuple[int, int, int]], kernel: str, serpentine: bool,
           strength: float) -> np.ndarray:
    """Return an (h, w) array of palette indices (0..3, order of PALETTES) for an image of any size."""
    pal = np.array(palette, dtype=np.float32)
    # Perceptual-ish weights for the distance metric (luma-heavy)
    wts = np.array([0.30, 0.59, 0.11], dtype=np.float32) * 3
    work = np.asarray(img, dtype=np.float32).copy()
    h, w = work.shape[:2]
    out = np.zeros((h, w), dtype=np.uint8)
    taps = KERNELS[kernel]
    for y in range(h):
        rev = serpentine and (y % 2 == 1)
        xs = range(w - 1, -1, -1) if rev else range(w)
        for x in xs:
            px = np.clip(work[y, x], 0, 255)
            d = (((pal - px) ** 2) * wts).sum(axis=1)
            idx = int(d.argmin())
            out[y, x] = idx
            err = (px - pal[idx]) * strength
            for dx, dy, wgt in taps:
                nx = x - dx if rev else x + dx
                ny = y + dy
                if 0 <= nx < w and ny < h:
                    work[ny, nx] += err * wgt
    return out


# Exact panel colors for PNG output, indexed like PALETTES (black, white, yellow, red).
# A PNG using only these four colors maps 1:1 on the device (TRMNL GetBWYRPixel) and
# passes LaraPaper's palette colormap unchanged.
EXACT_RGB = [(0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 0)]


def to_png(indices: np.ndarray) -> bytes:
    """Encode palette indices as a 2-bit indexed PNG using the exact BWRY colors."""
    import io

    im = Image.fromarray(indices.astype(np.uint8), "P")
    im.putpalette([c for rgb in EXACT_RGB for c in rgb] + [0] * (768 - 12))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True, bits=2)
    return buf.getvalue()


def pack(indices: np.ndarray) -> bytes:
    codes = CODES[indices].reshape(H, W // 4, 4)
    packed = (codes[..., 0] << 6) | (codes[..., 1] << 4) | (codes[..., 2] << 2) | codes[..., 3]
    data = packed.astype(np.uint8).tobytes()
    assert len(data) == W * H // 4
    return data


def preview(indices: np.ndarray, path: str, scale: int = 2) -> None:
    rgb = PREVIEW_RGB[indices]
    h, w = indices.shape
    Image.fromarray(rgb, "RGB").resize((w * scale, h * scale), Image.Resampling.NEAREST).save(path)


def upload(host: str, data: bytes, show: bool) -> str:
    req = urllib.request.Request(f"http://{host}/upload?format=bwry2bpp", data=data, method="POST",
                                 headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    if not resp.get("success"):
        raise RuntimeError(f"upload failed: {resp}")
    photo_id = resp["id"]
    if show:
        body = json.dumps({"id": photo_id}).encode()
        req = urllib.request.Request(f"http://{host}/photo/show", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
    return photo_id


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("-o", "--output", help="write 30000-byte .bin here")
    p.add_argument("--preview", help="write a 2x PNG preview here")
    p.add_argument("--fit", choices=["cover", "contain"], default="cover",
                   help="cover = crop to fill (default), contain = letterbox")
    p.add_argument("--focus", default="0.5,0.5", help="crop center as x,y fractions (cover mode)")
    p.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                   help="rotate source counter-clockwise (90/270 for portrait viewing)")
    p.add_argument("--palette", choices=PALETTES, default="panel")
    p.add_argument("--dither", choices=KERNELS, default="fs")
    p.add_argument("--no-serpentine", action="store_true")
    p.add_argument("--strength", type=float, default=0.9, help="error diffusion strength 0..1")
    p.add_argument("--autocontrast", type=float, default=1.0, help="%% of histogram clipped at each end")
    p.add_argument("--contrast", type=float, default=1.15)
    p.add_argument("--saturation", type=float, default=1.0)
    p.add_argument("--gamma", type=float, default=1.0, help=">1 brightens midtones, <1 darkens")
    p.add_argument("--sharpen", type=float, default=0.8)
    p.add_argument("--upload", metavar="HOST", help="device IP; uploads and shows the frame")
    a = p.parse_args()

    fx, fy = (float(v) for v in a.focus.split(","))
    img = fit_image(Image.open(a.input), a.fit, (fx, fy), a.rotate)
    img = adjust(img, a.contrast, a.saturation, a.gamma, a.sharpen, a.autocontrast)
    idx = dither(img, PALETTES[a.palette], a.dither, not a.no_serpentine, a.strength)
    data = pack(idx)

    counts = np.bincount(idx.ravel(), minlength=4) / idx.size * 100
    print(f"black {counts[0]:.1f}%  white {counts[1]:.1f}%  yellow {counts[2]:.1f}%  red {counts[3]:.1f}%")

    if a.output:
        with open(a.output, "wb") as f:
            f.write(data)
        print(f"wrote {a.output} ({len(data)} bytes)")
    if a.preview:
        preview(idx, a.preview)
        print(f"wrote {a.preview}")
    if a.upload:
        photo_id = upload(a.upload, data, show=True)
        print(f"uploaded to {a.upload} as id={photo_id} and requested display")
    return 0


if __name__ == "__main__":
    sys.exit(main())
