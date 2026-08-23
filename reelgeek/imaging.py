"""Low level image maths: easing, blurs, grading, framing, grain, vignette."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageFilter

# --------------------------------------------------------------- easing ----

def _c(p):
    return 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)

def lerp(a, b, t):
    return a + (b - a) * t

def ease_out_cubic(p):
    p = _c(p); return 1 - (1 - p) ** 3

def ease_in_out(p):
    p = _c(p); return p * p * (3 - 2 * p)

def ease_out_expo(p):
    p = _c(p); return 1.0 if p >= 1 else 1 - 2 ** (-9 * p)

def ease_out_sine(p):
    return math.sin(_c(p) * math.pi / 2)

def ease_out_back(p):
    p = _c(p); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2

def ease_linear(p):
    return _c(p)

# ---------------------------------------------------------------- blurs ----

def box_blur_x(a: np.ndarray, r: int) -> np.ndarray:
    """Fast horizontal box blur via cumulative sums. `a` is HxWxC float32."""
    r = int(r)
    if r < 1:
        return a
    f = a if a.dtype == np.float32 else a.astype(np.float32)
    pad = np.pad(f, ((0, 0), (r + 1, r), (0, 0)), mode="edge")
    cs = np.cumsum(pad, axis=1, dtype=np.float32)
    w = 2 * r + 1
    return (cs[:, w:, :] - cs[:, :-w, :]) * (1.0 / w)

def box_blur_y(a: np.ndarray, r: int) -> np.ndarray:
    r = int(r)
    if r < 1:
        return a
    f = a if a.dtype == np.float32 else a.astype(np.float32)
    pad = np.pad(f, ((r + 1, r), (0, 0), (0, 0)), mode="edge")
    cs = np.cumsum(pad, axis=0, dtype=np.float32)
    w = 2 * r + 1
    return (cs[w:, :, :] - cs[:-w, :, :]) * (1.0 / w)

def box_blur(a: np.ndarray, r: int) -> np.ndarray:
    return box_blur_y(box_blur_x(a, r), r)

# --------------------------------------------------------------- grading ---

def build_lut(grade: dict) -> np.ndarray:
    """Return a 256x3 uint8 lookup table implementing the tone/split-tone grade."""
    contrast = grade.get("contrast", 1.0)
    lift = grade.get("lift", 0.0)
    gamma = grade.get("gamma", 1.0)
    sh = np.array(grade.get("shadow_tint", (0, 0, 0)), dtype=np.float32)
    hi = np.array(grade.get("high_tint", (0, 0, 0)), dtype=np.float32)

    x = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    y = (x - 0.5) * contrast + 0.5           # contrast about mid grey
    y = np.clip(y, 0.0, 1.0) ** gamma
    y = y * (1.0 - lift) + lift              # lifted blacks, film style
    y = np.clip(y, 0.0, 1.0)

    # split tone: shadow tint fades out as we go up, highlight tint fades in
    shw = (1.0 - y) ** 2
    hiw = y ** 2
    out = np.empty((256, 3), dtype=np.float32)
    for c in range(3):
        out[:, c] = y * 255.0 + sh[c] * shw + hi[c] * hiw
    return np.clip(out, 0, 255).astype(np.uint8)

def apply_grade(img: Image.Image, grade: dict, lut: np.ndarray) -> Image.Image:
    a = np.asarray(img, dtype=np.uint8)
    a = lut[a, [0, 1, 2]]          # per-channel LUT in one fancy-index pass
    sat = grade.get("sat", 1.0)
    if abs(sat - 1.0) > 1e-3:
        f = a.astype(np.float32)
        luma = (f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114)[..., None]
        f = luma + (f - luma) * sat
        a = np.clip(f, 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGB")

# --------------------------------------------------------------- framing ---

def frame_to_portrait(img: Image.Image, w: int, h: int, landscape_mode="crop",
                      head_bias=0.42, max_wide=2.0) -> Image.Image:
    """Fit an arbitrary photo onto the render canvas.

    Portrait and square sources are cropped full-bleed, biased upwards so heads
    are not sliced off. Landscape sources are the interesting case:

    * "crop" keeps the full height and lets the image stay WIDER than the
      canvas, so the renderer can pan the camera across it -- which is what an
      editor would actually do with a wide shot in a vertical edit.
    * "blur" lays the whole photo across a blurred copy of itself, so nothing
      is lost. Safer, but it reads more like a slideshow.
    """
    iw, ih = img.size
    src = iw / ih

    if src <= 1.15:
        return _cover(img, w, h, head_bias)

    if landscape_mode == "blur":
        bg = _cover(img, w, h, 0.5)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(w, h) * 0.022))
        bg = Image.fromarray(
            np.clip(np.asarray(bg, dtype=np.float32) * 0.62, 0, 255).astype(np.uint8), "RGB")
        fw = int(w * 0.98)
        fh = max(1, int(round(fw / src)))
        fg = img.resize((fw, fh), Image.LANCZOS)
        y = int(h * 0.44 - fh / 2)
        bg.paste(fg, ((w - fw) // 2, max(0, min(h - fh, y))))
        return bg

    # full height, extra width preserved for the camera to travel across
    cap = int(w * max_wide)
    cap_ar = cap / h
    if src > cap_ar:                        # absurdly wide: trim the extremes first
        need = int(round(ih * cap_ar))
        x = (iw - need) // 2
        img = img.crop((x, 0, x + need, ih))
        return img.resize((cap, h), Image.LANCZOS)
    return img.resize((int(round(h * src)), h), Image.LANCZOS)


def _cover(img: Image.Image, w: int, h: int, vbias: float) -> Image.Image:
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(math.ceil(iw * scale)), int(math.ceil(ih * scale))
    r = img.resize((nw, nh), Image.LANCZOS)
    x = (nw - w) / 2.0
    y = (nh - h) * vbias
    return r.crop((int(x), int(y), int(x) + w, int(y) + h))

# ------------------------------------------------------- grain & vignette --

def make_vignette(w: int, h: int, strength: float) -> np.ndarray:
    if strength <= 0:
        return None
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx = (xx - w / 2) / (w / 2)
    yy = (yy - h / 2) / (h / 2)
    d = np.sqrt(xx * xx + yy * yy * 0.62)      # softer vertically for 9:16
    m = 1.0 - strength * np.clip((d - 0.45) / 1.05, 0, 1) ** 1.7
    return m.astype(np.float32)[..., None]

def make_grain_tiles(w: int, h: int, strength: float, n: int = 6, seed: int = 0):
    if strength <= 0:
        return []
    rng = np.random.default_rng(seed)
    tiles = []
    for _ in range(n):
        # generated at 1/3 scale then expanded: reads like film grain, not noise
        small = rng.normal(0.0, strength, size=(h // 3 + 1, w // 3 + 1)).astype(np.float32)
        big = np.repeat(np.repeat(small, 3, axis=0), 3, axis=1)[:h, :w]
        tiles.append(np.clip(big, -120, 120).astype(np.int8)[..., None])
    return tiles
