"""The renderer: shot list in, vertical video out.

Every frame is composed in Python (crop, move, transition, grade, grain, text)
and piped straight into ffmpeg as raw RGB. Doing it this way rather than as an
ffmpeg filter chain is what makes the harder moves -- whip pans with real motion
blur, RGB-split glitches, snap zooms -- possible at all.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from . import audio as audio_mod
from . import motion as mo
from . import text as tx
from . import timeline as tl
from .imaging import (apply_grade, box_blur, box_blur_x, build_lut, ease_in_out,
                      ease_out_back, ease_out_expo, frame_to_portrait,
                      make_grain_tiles, make_vignette)
from .presets import GRADES, PACES, PRESETS

SRC_OVERSCAN = 1.6          # photos prepped 1.6x larger so zooms never soften
WHIP_TRAVEL = 0.30          # whip pan distance, as a fraction of source width


@dataclass
class Config:
    style: str = "hype"
    pace: str = "normal"
    fps: int = 30
    width: int = 1080
    height: int = 1920
    bpm: float | None = None
    target_seconds: float | None = None      # None = let the preset decide
    seed: int = 1
    hook: str = ""
    endcard: str = ""
    accent: tuple = (255, 46, 90)
    landscape_mode: str = "crop"             # crop (pan across) | blur (show all)
    scratch_beat: bool = False
    crf: int = 20
    x264_preset: str = "faster"
    maxrate: str = "12M"          # grain eats bitrate; both platforms re-encode anyway

    @classmethod
    def preview(cls, **kw):
        kw.setdefault("width", 540)
        kw.setdefault("height", 960)
        kw.setdefault("fps", 24)
        kw.setdefault("crf", 28)
        kw.setdefault("x264_preset", "veryfast")
        kw.setdefault("maxrate", "4M")
        return cls(**kw)


# --------------------------------------------------------------- preparing --

def prepare(photos, cfg: Config, workdir: Path, progress=None) -> list:
    """Frame, grade and cache every photo at render resolution."""
    preset = PRESETS[cfg.style]
    grade = GRADES[preset["grade"]]
    sw = int(cfg.width * SRC_OVERSCAN) // 2 * 2
    sh = int(cfg.height * SRC_OVERSCAN) // 2 * 2

    key = hashlib.sha1(json.dumps([
        [str(p), os.path.getmtime(p), os.path.getsize(p)] for p in photos
    ] + [sw, sh, preset["grade"], cfg.landscape_mode]).encode()).hexdigest()[:16]
    out = workdir / f"prep_{key}"
    manifest = out / "manifest.json"
    if manifest.is_file():
        try:
            rec = json.loads(manifest.read_text())
            return [(out / n, w, h) for n, w, h in rec]
        except Exception:
            shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    lut = build_lut(grade)
    names = []
    for i, p in enumerate(photos):
        with Image.open(p) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")
            im = frame_to_portrait(im, sw, sh, cfg.landscape_mode)
            im = apply_grade(im, grade, lut)
            name = f"{i:04d}.jpg"
            im.save(out / name, quality=95, subsampling=0, optimize=False)
            names.append([name, im.width, im.height])
        if progress:
            progress("prep", (i + 1) / len(photos), f"Preparing photo {i+1}/{len(photos)}")
    manifest.write_text(json.dumps(names))
    return [(out / n, w, h) for n, w, h in names]


class _Cache:
    """Keeps only the handful of prepped photos the current cut needs in RAM."""

    def __init__(self, paths, size=4):
        self.paths, self.size, self.d = paths, size, {}

    def get(self, i):
        im = self.d.get(i)
        if im is None:
            im = Image.open(self.paths[i]).convert("RGB")
            self.d[i] = im
            while len(self.d) > self.size:      # drop whatever is furthest away
                self.d.pop(max(self.d, key=lambda k: abs(k - i)), None)
        return im


# ---------------------------------------------------------------- composing --

def _compose(cache, shot, frame, cfg, preset, shake_amp, extra_scale=1.0,
             off=(0.0, 0.0), rot_extra=0.0):
    img = cache.get(shot.photo)
    sw, sh = img.size
    p = (frame - shot.start) / max(1, shot.frames)
    scale, panx, pany, roll = mo.get(shot.motion, p, shot.direction)

    t = frame / cfg.fps
    scale *= extra_scale * mo.beat_pulse(t, preset["_bpm"], preset["beat_pulse"])
    scale = min(mo.MAX_SCALE, max(1.001, scale))
    roll += rot_extra

    rng_phase = shot.seed
    hx, hy = mo.handheld(t, shake_amp, (
        (rng_phase % 628) / 100.0, (rng_phase // 7 % 628) / 100.0,
        (rng_phase // 13 % 628) / 100.0, (rng_phase // 29 % 628) / 100.0))

    pad = 1.075 if abs(roll) > 0.05 else 1.0
    scale = min(mo.MAX_SCALE, scale * pad)

    ar = cfg.width / cfg.height
    if sw / sh > ar:                     # wider than the canvas: full height
        bh, bw = float(sh), sh * ar
    else:
        bw, bh = float(sw), sw / ar
    cw, ch = bw / scale, bh / scale
    mx, my = (sw - cw) / 2.0, (sh - ch) / 2.0
    cx = sw / 2.0 + panx * mx + off[0] + hx
    cy = sh / 2.0 + pany * my + off[1] + hy
    cx = min(sw - cw / 2, max(cw / 2, cx))
    cy = min(sh - ch / 2, max(ch / 2, cy))
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)

    ow, oh = cfg.width, cfg.height
    if pad > 1.0:
        big = img.resize((int(ow * pad), int(oh * pad)), Image.BICUBIC, box)
        big = big.rotate(roll, resample=Image.BICUBIC)
        l, u = (big.width - ow) // 2, (big.height - oh) // 2
        return big.crop((l, u, l + ow, u + oh))
    return img.resize((ow, oh), Image.BICUBIC, box)


def _glitch(a, amt, rng):
    h, w, _ = a.shape
    dx = int(round(24 * amt))
    if dx:
        a[..., 0] = np.roll(a[..., 0], dx, axis=1)
        a[..., 2] = np.roll(a[..., 2], -dx, axis=1)
    for _ in range(int(3 + 6 * amt)):
        y0 = int(rng.integers(0, max(1, h - 10)))
        hh = int(rng.integers(5, 80))
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(rng.integers(-80, 80) * amt), axis=1)
    if rng.random() < 0.5 * amt:
        y0 = int(rng.integers(0, max(1, h - 4)))
        a[y0:y0 + 3] = np.minimum(255.0, a[y0:y0 + 3] * 1.9 + 40)
    return a


def _push(prev, cur, u, direction):
    """Slide: the incoming shot shoves the outgoing one off frame."""
    h, w, _ = cur.shape
    e = ease_out_expo(u)
    if direction in (0, 1):                       # horizontal
        s = int(round((1 - e) * w))
        if s <= 0:
            return cur
        out = np.empty_like(cur)
        if direction == 1:
            out[:, s:] = cur[:, :w - s]
            out[:, :s] = prev[:, w - s:]
        else:
            out[:, :w - s] = cur[:, s:]
            out[:, w - s:] = prev[:, :s]
        return out
    s = int(round((1 - e) * h))                   # vertical (up)
    if s <= 0:
        return cur
    out = np.empty_like(cur)
    out[:h - s] = cur[s:]
    out[h - s:] = prev[:s]
    return out


# ----------------------------------------------------------------- rendering --

def check_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    raise RuntimeError(
        "ffmpeg is not installed (or not on your PATH), and ReelGeek needs it "
        "to write the video.\n"
        "  macOS:    brew install ffmpeg\n"
        "  Windows:  winget install Gyan.FFmpeg   (then reopen the terminal)\n"
        "  Linux:    sudo apt install ffmpeg")


def render(photos, out_path, cfg: Config, workdir=None, progress=None) -> dict:
    check_ffmpeg()
    photos = [str(p) for p in photos]
    if len(photos) < 2:
        raise ValueError("Give me at least 2 photos.")
    t_start = time.time()
    workdir = Path(workdir or Path(out_path).parent / ".reelgeek")
    workdir.mkdir(parents=True, exist_ok=True)

    preset = dict(PRESETS[cfg.style])
    prep = prepare(photos, cfg, workdir, progress)
    prepped = [p for p, _, _ in prep]
    wide = [w / h > (cfg.width / cfg.height) * 1.25 for _, w, h in prep]

    tline = tl.build(len(photos), preset, fps=cfg.fps,
                     pace=PACES.get(cfg.pace, 1.0), bpm=cfg.bpm, seed=cfg.seed,
                     target_seconds=cfg.target_seconds, wide=wide)
    preset["_bpm"] = tline.bpm
    shots, total, fps = tline.shots, tline.total_frames, cfg.fps
    W, Hh = cfg.width, cfg.height

    cache = _Cache(prepped)
    rng = np.random.default_rng(cfg.seed * 7919 + 13)
    shake_amp = preset["shake"] * (W / 1080.0) * 5.0
    vign = make_vignette(W, Hh, preset["vignette"])
    grains = make_grain_tiles(W, Hh, preset["grain"] * (W / 1080.0), 6, cfg.seed)
    bars = int(Hh * preset.get("bars", 0.0))
    travel = WHIP_TRAVEL * (W * SRC_OVERSCAN)

    hook_img = tx.render_caption(cfg.hook, W, preset["hook_style"], tuple(cfg.accent))
    end_img = tx.render_caption(cfg.endcard, W, preset["hook_style"], tuple(cfg.accent))
    hook_len = min(total, int(fps * 2.4))
    end_len = min(total, int(fps * 2.0))

    # audio bed
    wav = None
    if cfg.scratch_beat:
        wav = str(workdir / f"beat_{cfg.seed}_{int(tline.bpm)}.wav")
        audio_mod.write_scratch_beat(wav, tline.bpm, tline.seconds, cfg.seed)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{Hh}",
           "-r", str(fps), "-i", "-"]
    cmd += (["-i", wav] if wav else
            ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
    cmd += ["-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", cfg.x264_preset, "-crf", str(cfg.crf),
            "-maxrate", cfg.maxrate, "-bufsize", f"{int(float(cfg.maxrate.rstrip(chr(77))) * 1.6)}M",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
            "-g", str(fps * 2), "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    si = 0
    try:
        for i in range(total):
            while si + 1 < len(shots) and i >= shots[si].end:
                si += 1
            shot = shots[si]
            nxt = shots[si + 1] if si + 1 < len(shots) else None

            extra_scale, off, rot_extra = 1.0, [0.0, 0.0], 0.0
            blur_x = 0.0
            flash = 0.0
            glitch_amt = 0.0
            blend = None          # (kind, u) needing the outgoing shot too

            # --- transition landing on this shot -------------------------
            k = i - shot.start
            tname = shot.trans_in
            spec = tl.TRANSITIONS[tname]
            if tname != "hardcut" and k < spec["post"]:
                u = k / spec["post"]
                if tname == "zoom_punch":
                    extra_scale *= 1.0 + 0.34 * (1 - ease_out_expo(u))
                elif tname == "flash":
                    flash = 0.88 * (1 - u) ** 1.5
                elif tname == "glitch":
                    glitch_amt = (1 - u) ** 0.8
                elif tname == "shake_cut":
                    m = (1 - u) ** 1.4 * 46 * (W / 1080.0)
                    off[0] += float(rng.normal(0, m))
                    off[1] += float(rng.normal(0, m))
                    rot_extra += float(rng.normal(0, 0.9 * (1 - u)))
                elif tname == "whip":
                    extra_scale *= 1.16
                    off[0] += -shot.direction * travel * (1 - u) ** 1.7
                    blur_x = 40 * (W / 1080.0) * (1 - u) ** 1.2
                elif tname in ("slide", "dissolve", "blur_dissolve"):
                    blend = (tname, u)

            # --- transition leaving this shot (the frames before the cut) -
            if nxt is not None:
                nspec = tl.TRANSITIONS[nxt.trans_in]
                dist = nxt.start - i
                if nspec["pre"] and 0 < dist <= nspec["pre"]:
                    v = 1.0 - (dist - 1) / max(1, nspec["pre"])
                    if nxt.trans_in == "whip":
                        extra_scale *= 1.16
                        off[0] += nxt.direction * travel * v ** 1.7
                        blur_x = max(blur_x, 40 * (W / 1080.0) * v ** 1.2)
                    elif nxt.trans_in == "flash":
                        flash = max(flash, 0.45 * v ** 2)
                    elif nxt.trans_in == "glitch":
                        glitch_amt = max(glitch_amt, 0.5 * v)

            frame = _compose(cache, shot, i, cfg, preset, shake_amp,
                             extra_scale, off, rot_extra)
            a = np.asarray(frame, dtype=np.float32)

            if blend is not None and si > 0:
                kind, u = blend
                prev_shot = shots[si - 1]
                b = np.asarray(_compose(cache, prev_shot, i, cfg, preset, shake_amp),
                               dtype=np.float32)
                if kind == "slide":
                    a = _push(b, a, u, si % 3)
                elif kind == "dissolve":
                    w_ = ease_in_out(u)
                    a = b * (1 - w_) + a * w_
                else:
                    r = int(round(16 * (W / 1080.0)))
                    a = (box_blur(b, int(r * (1 - u))) * (1 - ease_in_out(u))
                         + box_blur(a, int(r * u)) * ease_in_out(u))

            if blur_x >= 1:
                a = box_blur_x(a, int(blur_x))
            if glitch_amt > 0.02:
                a = _glitch(a, glitch_amt, rng)
            if flash > 0.004:
                a = a * (1 - flash) + 255.0 * flash
            if vign is not None:
                a *= vign
            if grains:
                a += grains[i % len(grains)]
            np.clip(a, 0, 255, out=a)
            out = a.astype(np.uint8)
            if bars:
                out[:bars] = 0
                out[-bars:] = 0

            # --- captions ------------------------------------------------
            cap = None
            if hook_img is not None and i < hook_len:
                cap = _cap_anim(hook_img, i, hook_len, fps, 0.30)
            elif end_img is not None and i >= total - end_len:
                cap = _cap_anim(end_img, i - (total - end_len), end_len, fps, 0.50)
            if cap:
                img, sc, al, yf, rot = cap
                pil = Image.fromarray(out, "RGB").convert("RGBA")
                tx.composite(pil, img, sc, al, yf, rot)
                out = np.asarray(pil.convert("RGB"), dtype=np.uint8)

            proc.stdin.write(out.tobytes())
            if progress and (i % 6 == 0 or i == total - 1):
                progress("render", (i + 1) / total,
                         f"Rendering frame {i+1}/{total}")
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
    err = proc.stderr.read().decode("utf8", "replace")
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{err.strip()[:2000]}")

    return dict(path=str(out_path), seconds=round(tline.seconds, 2),
                frames=total, fps=fps, bpm=round(tline.bpm, 1),
                shots=len(shots), width=W, height=Hh,
                render_seconds=round(time.time() - t_start, 1),
                cuts=[round(s.start / fps, 3) for s in shots])


def _cap_anim(img, k, span, fps, y_frac):
    """Bounce in, hold, lift out."""
    ain = max(4, int(fps * 0.30))
    aout = max(4, int(fps * 0.22))
    if k < ain:
        p = k / ain
        return img, 0.74 + 0.26 * ease_out_back(p), min(1.0, p * 2.2), y_frac, -2.2
    if k > span - aout:
        p = (k - (span - aout)) / aout
        return img, 1.0 + 0.07 * p, max(0.0, 1 - p * 1.15), y_frac - 0.012 * p, -2.2
    return img, 1.0, 1.0, y_frac, -2.2
