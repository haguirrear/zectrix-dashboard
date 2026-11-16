"""Pet photo, cropped and pre-dithered to the four panel colors, embedded as a data: URI.
The photo stays on your PC (PET_PHOTO); it is never committed."""

from __future__ import annotations

import base64
import os

from PIL import Image

from ..render import eink


def collect(cfg: dict) -> dict:
    src = os.path.expanduser(cfg["PET_PHOTO"])
    if not cfg["PET_PHOTO"] or not os.path.exists(src):
        raise FileNotFoundError(f"PET_PHOTO not set or missing: {cfg['PET_PHOTO']!r}")
    w, h = (int(v) for v in cfg["PET_SIZE"].lower().split("x"))
    fx, fy = (float(v) for v in cfg["PET_FOCUS"].split(","))
    img = eink.fit_image(Image.open(src), "cover", (fx, fy), 0, size=(w, h), zoom=float(cfg["PET_ZOOM"]))
    img = eink.adjust(img, contrast=1.1, saturation=1.0, gamma=1.25, sharpen=0.8, autocontrast=1.0)
    idx = eink.dither(img, eink.PALETTES["panel"], "fs", serpentine=True, strength=0.9)
    png = eink.to_png(idx)
    return {"available": True, "width": w, "height": h,
            "src": "data:image/png;base64," + base64.b64encode(png).decode()}


def summary(p: dict) -> str:
    return f"{p['width']}x{p['height']}, {len(p['src'])} chars"
