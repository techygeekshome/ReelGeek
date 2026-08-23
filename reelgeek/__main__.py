"""Command line entry point.

    python -m reelgeek                       # open the app in your browser
    python -m reelgeek ./photos -o out.mp4   # render straight from a folder
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def main(argv=None):
    from .presets import PACES, PRESET_ORDER

    ap = argparse.ArgumentParser(prog="reelgeek", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", help="folder of photos (omit to open the app)")
    ap.add_argument("-o", "--out", default=None,
                    help="output file (default: a dated name in your output folder)")
    ap.add_argument("-s", "--style", default="hype", choices=PRESET_ORDER)
    ap.add_argument("-p", "--pace", default="normal", choices=list(PACES))
    ap.add_argument("--hook", default="", help="text over the first 2 seconds")
    ap.add_argument("--endcard", default="")
    ap.add_argument("--seconds", type=float, default=None, help="target runtime")
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--seed", type=int, default=1, help="change for a different edit")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--wide", default="crop", choices=["crop", "blur"])
    ap.add_argument("--beat", action="store_true", help="add the synthesised scratch beat")
    ap.add_argument("--preview", action="store_true", help="fast, low-res draft")
    ap.add_argument("--shuffle", action="store_true")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)

    if not a.folder:
        from .server import serve
        return serve(None, a.port, not a.no_browser)

    folder = Path(a.folder).expanduser()
    photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)
    if a.shuffle:
        import random
        random.Random(a.seed).shuffle(photos)
    if len(photos) < 2:
        sys.exit(f"Need at least 2 photos in {folder}")

    from . import settings
    from .render import Config, render

    out = a.out
    if not out:
        import time
        out = str(settings.output_dir() /
                  f"reelgeek-{a.style}-{time.strftime('%Y%m%d-%H%M%S')}.mp4")
    kw = dict(style=a.style, pace=a.pace, hook=a.hook, endcard=a.endcard,
              seed=a.seed, target_seconds=a.seconds, bpm=a.bpm,
              landscape_mode=a.wide, scratch_beat=a.beat, fps=a.fps)
    cfg = Config.preview(**kw) if a.preview else Config(**kw)

    last = [""]
    def prog(stage, frac, msg):
        line = f"\r  {msg:<40}"
        if line != last[0]:
            sys.stdout.write(line); sys.stdout.flush(); last[0] = line

    print(f"  {len(photos)} photos · style={a.style} · seed={a.seed}")
    info = render(photos, out, cfg, progress=prog)
    print(f"\r  Done: {info['path']}  ({info['seconds']}s, {info['width']}x{info['height']}, "
          f"{info['shots']} shots, {info['bpm']} BPM, {info['render_seconds']}s to render)")


if __name__ == "__main__":
    main()
