<div align="center">

<img src="icons/reelgeek.png" alt="ReelGeek logo" width="96" height="96">

# ReelGeek

**Turn a pile of photos into a vertical edit — cuts on the beat, real camera moves, ready for TikTok and Shorts.**

[![Status](https://img.shields.io/badge/status-in%20development-b7791f)](https://github.com/techygeekshome/ReelGeek)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078d4)](#getting-it-running)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3fca86)](https://www.python.org/downloads/)
[![Made by TechyGeeksHome](https://img.shields.io/badge/made%20by-TechyGeeksHome-b191f2)](https://techygeekshome.info)
[![Support on Ko-fi](https://img.shields.io/badge/support-Ko--fi-ff5e5b)](https://ko-fi.com/techygeekshome)

[Getting started](#getting-it-running) · [Using it](#using-it) · [The styles](#the-styles) · [Command line](#command-line) · [How it works](#how-it-works)

</div>

---

Turn a pile of photos into a vertical **edit** — not a slideshow. Cuts land on a
tempo grid, the camera moves on every shot, and the transitions are the ones
short-form editors actually use: whip pans with real motion blur, snap zooms,
flash frames, RGB-split glitches, hard cuts on the beat.

Output is **1080 × 1920 H.264 MP4**, which uploads as-is to TikTok and YouTube
Shorts.

---

## Getting it running

You need two things installed: **Python 3.9+** and **ffmpeg**.

| | Python | ffmpeg |
|---|---|---|
| **macOS** | [python.org/downloads](https://www.python.org/downloads/) | `brew install ffmpeg` |
| **Windows** | [python.org/downloads](https://www.python.org/downloads/) — tick *"Add Python to PATH"* | `winget install Gyan.FFmpeg` |
| **Linux** | usually already there | `sudo apt install ffmpeg` |

Then:

* **macOS / Linux** — double-click `run.command` (or `./run.sh` in a terminal)
* **Windows** — double-click `run.bat`

It installs the two Python libraries it needs, starts a small local server and
opens the app in your browser. Nothing is uploaded anywhere — the server binds
to `127.0.0.1`, so it is only reachable from your own machine.

**Finished videos go to your Downloads folder.** Change that any time with the
**Save videos to** box in the app — type or paste a path, hit Save, and it
sticks for future sessions. Clear the box and save to go back to Downloads. On
Windows the real Downloads location is read from the system, so a Downloads
folder you have moved to another drive is still found correctly.

---

## Using it

1. **Drop your photos in.** Any number. Drag the thumbnails to reorder — the
   order they sit in is the order they appear.
2. **Pick a style.** Five of them, described below.
3. **Type a hook.** The first second is the whole game on short-form. Something
   that has to be resolved — *"POV: you found the one"*, *"nobody tells you this
   about…"*, *"3 months of progress"*.
4. **Quick preview** renders a fast, low-res draft so you can judge the rhythm
   in a few seconds. **Render HD** does the real thing.
5. **Re-roll ⟳** keeps your photos and style but rolls a new edit — different
   motions, different transitions, different cut placement. Do this three or
   four times and keep the best one. It costs you nothing.

### The styles

| Style | What it is |
|---|---|
| **Hype** | Fast and aggressive. Flash and glitch hits, punch zooms, hard cuts. The default fashion/lifestyle look. |
| **Clean** | Modern and minimal. Crisp cuts, decisive slides, no gimmicks. Reads expensive rather than loud. |
| **Soft** | Dreamy. Long drifting pushes, gentle dissolves, faded film grade. Golden hour, portraits. |
| **VHS** | Retro camcorder. Heavy grain, colour bleed, glitch cuts, warm tape grade. |
| **Luxe** | Slow and cinematic. Big smooth pushes, deep contrast, letterbox bars. Fewer cuts, more weight per photo. |

### The settings that matter

* **Length** — *Auto* lets the style pick its own runtime. With 30 photos that's
  about 14s on Hype and closer to a minute on Luxe. Pin it to 15/20/30s if you
  want a specific length; the whole rhythm is scaled to fit.
* **Pace** — multiplies every shot length without changing the tempo grid.
* **Tempo (BPM)** — set this to match the track you plan to add in TikTok and
  the cuts will land on its beat. Leave blank to use the style's own tempo.
* **Wide photos** — *Fill frame* crops landscape shots to vertical and pans the
  camera across them, which is what an editor would do. *Show all* puts the
  whole photo on a blurred backdrop of itself, losing nothing but reading more
  like a slideshow.

---

## About the audio

**ReelGeek renders silent on purpose.**

On both TikTok and YouTube Shorts, attaching the platform's own trending audio
gets you better distribution than uploading a video with music already baked in
— and it is the only route that keeps you clear of copyright claims and muted
uploads. So: post the silent file, pick a sound in the app, done. Because the
cuts sit on a clean tempo grid, a track at a similar BPM lines up.

The **scratch beat** checkbox adds a drum pattern this app synthesises itself
from sine waves and noise. It exists so you can hear whether your cuts are
landing before you post. Nothing in it is sampled or licensed from anyone, so
it's yours to use — but trending audio will serve you better.

---

## Command line

The browser app is a wrapper around an engine you can also drive directly:

```bash
python -m reelgeek ./my-photos -o out.mp4 \
    --style hype --hook "POV: you found the one" --seconds 22 --seed 3
```

```
--style   hype | clean | soft | vhs | luxe
--pace    chill | normal | fast | frantic
--seconds target runtime          --bpm    tempo to cut against
--seed    change for a new edit   --preview  fast low-res draft
--wide    crop | blur             --beat   add the scratch beat
--shuffle randomise photo order   --fps    default 30
--out     output file (defaults to a dated name in your output folder)
```

Useful for batching: loop over seeds, render five drafts, watch them, keep one.

---

## How long a render takes

Roughly **4× the video length** on a normal laptop — a 20-second edit takes
about 90 seconds. Preview mode is about eight times faster. Prepared photos are
cached, so re-rolling the same set is quicker than the first render.

## How it works

Every frame is composed in Python — crop, camera move, transition, grade,
grain, text — and piped straight into ffmpeg as raw RGB. That's slower than an
ffmpeg filter chain but it's the reason the harder moves are possible at all:
you can't get a whip pan with genuine directional motion blur, or an RGB-split
glitch with displaced scanlines, out of stock filters.

```
reelgeek/
  settings.py  output folder and preferences, remembered between sessions
  presets.py   the five styles: rhythm, motion weights, transition odds, grade
  timeline.py  photos + style -> a beat-locked shot list
  motion.py    the camera moves
  imaging.py   easing, blurs, colour grading, framing, grain, vignette
  text.py      hook and end-card rendering
  audio.py     the synthesised scratch beat
  render.py    frame composition, transitions, encoding
  server.py    the local web app
  ui.html      the interface
```

Want a new style? Copy an entry in `presets.py`, change the numbers, and it
appears in the app automatically.

Settings and the prepped-photo cache live in a private app folder
(`%LOCALAPPDATA%\\ReelGeek` on Windows, `~/.reelgeek` on Linux,
`~/Library/Application Support/ReelGeek` on macOS). Deleting that folder resets
everything and costs you nothing but the cache.

---

## One honest note

This gives good photos their best shot: a competent, on-trend edit in the right
format with a hook in the right place. It cannot manufacture reach. What
actually moves the numbers is the strength of your photos, the hook, posting
consistently, and using sounds while they're still climbing. The edit is the
part you can automate — the rest is still on you.

## Support

Found a bug or have a request? [Open an issue](https://github.com/techygeekshome/ReelGeek/issues) or [get in touch](https://techygeekshome.info/contact/).

## Status and licence

ReelGeek is in development and has not had a public release yet, so there is no version number to quote and no download to point at. A licence file will be added before the first release.

---

<div align="center">

Made with ❤️ by [**TechyGeeksHome**](https://techygeekshome.info)

[Website](https://techygeekshome.info) · [YouTube](https://www.youtube.com/channel/UCtEuFj1SMLiuRoucD1hv8dA) · [X](https://x.com/TechyGeeks1) · [Facebook](https://www.facebook.com/techygeeks.home) · [Instagram](https://www.instagram.com/andrewarmstrongtgh/)

</div>
