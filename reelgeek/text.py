"""Hook and end-card text -- the thing that actually stops the scroll."""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Punchier display faces first; the last two are on virtually every machine.
FONT_CANDIDATES = [
    "Anton-Regular.ttf", "BebasNeue-Regular.ttf", "Montserrat-ExtraBold.ttf",
    "Montserrat-Bold.ttf", "Oswald-Bold.ttf", "Archivo-Black.ttf",
    "Poppins-Bold.ttf", "Inter-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf",
    "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf",
]
FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), "fonts"),
    "/usr/share/fonts/truetype/google-fonts", "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation", "/usr/share/fonts",
    "/Library/Fonts", "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/Library/Fonts"), "C:/Windows/Fonts",
]


def find_font() -> str | None:
    for name in FONT_CANDIDATES:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    for d in FONT_DIRS:                       # last resort: any bold ttf
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".ttf", ".otf")) and "bold" in f.lower():
                    return os.path.join(d, f)
    return None


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_caption(text: str, width: int, style: str = "block",
                   accent=(255, 46, 90), size_frac=0.088, upper=True) -> Image.Image | None:
    """Draw a caption to a tight RGBA image, ready to be scaled and composited."""
    text = (text or "").strip()
    if not text:
        return None
    if upper:
        text = text.upper()

    path = find_font()
    size = int(width * size_frac)
    font = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)

    scratch = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    max_w = int(width * 0.78)
    lines = _wrap(scratch, text, font, max_w)

    asc, desc = font.getmetrics()
    lh = int((asc + desc) * 1.02)
    pad_x, pad_y = int(size * 0.42), int(size * 0.24)
    tw = max(int(scratch.textlength(l, font=font)) for l in lines)
    box_w = tw + pad_x * 2
    box_h = lh * len(lines) + pad_y * 2

    margin = int(size * 0.9)                  # room for shadow / glow
    img = Image.new("RGBA", (box_w + margin * 2, box_h + margin * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = margin, margin
    radius = int(size * 0.16)

    if style == "block":
        d.rounded_rectangle([ox, oy, ox + box_w, oy + box_h], radius=radius,
                            fill=accent + (255,))
        fill, stroke_w, stroke_fill = (255, 255, 255, 255), 0, None
    elif style == "bar":
        d.rounded_rectangle([ox, oy, ox + box_w, oy + box_h], radius=radius,
                            fill=(0, 0, 0, 165))
        fill, stroke_w, stroke_fill = (255, 255, 255, 255), 0, None
    else:                                     # plain: white text, soft shadow
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for i, line in enumerate(lines):
            lw = sd.textlength(line, font=font)
            sd.text((ox + (box_w - lw) / 2, oy + pad_y + i * lh + 4),
                    line, font=font, fill=(0, 0, 0, 190))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.10)))
        fill, stroke_w, stroke_fill = (255, 255, 255, 255), max(2, size // 26), (0, 0, 0, 120)

    for i, line in enumerate(lines):
        lw = d.textlength(line, font=font)
        d.text((ox + (box_w - lw) / 2, oy + pad_y + i * lh), line, font=font,
               fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)
    return img


def composite(frame: Image.Image, cap: Image.Image, scale: float, alpha: float,
              y_frac: float, rotate: float = 0.0) -> Image.Image:
    """Paste an animated caption onto a frame. `frame` is modified and returned."""
    if cap is None or alpha <= 0.004 or scale <= 0.01:
        return frame
    w, h = cap.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    layer = cap.resize((nw, nh), Image.LANCZOS)
    if abs(rotate) > 0.05:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
        nw, nh = layer.size
    if alpha < 0.996:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer.putalpha(a)
    frame.alpha_composite(layer, (int((frame.width - nw) / 2),
                                  int(frame.height * y_frac - nh / 2)))
    return frame
