"""Turn the repo's PNG app icon into a multi-size .ico for the build.

Run from the repo root. Silent no-op if there is no source icon, so the build
still produces an installer rather than failing over an icon.
"""
from pathlib import Path

SRC = Path("icons/reelgeek.png")
OUT = Path("packaging/reelgeek.ico")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

if SRC.exists():
    from PIL import Image

    Image.open(SRC).convert("RGBA").save(OUT, sizes=SIZES)
    print(f"icon written to {OUT}")
else:
    print(f"no {SRC}, the build will use the default icon")
