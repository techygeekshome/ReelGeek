"""Turns a pile of photos into a beat-locked shot list.

This is the part that decides the *edit*: how long each photo is on screen,
how the camera moves on it, and what happens at each cut.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field

# how many frames either side of a cut each transition needs
TRANSITIONS = {
    "hardcut":       dict(pre=0, post=0, both=False),
    "flash":         dict(pre=2, post=5, both=False),
    "zoom_punch":    dict(pre=0, post=7, both=False),
    "glitch":        dict(pre=1, post=4, both=False),
    "shake_cut":     dict(pre=0, post=6, both=False),
    "whip":          dict(pre=4, post=5, both=False),
    "slide":         dict(pre=0, post=6, both=True),
    "dissolve":      dict(pre=0, post=7, both=True),
    "blur_dissolve": dict(pre=0, post=8, both=True),
}

# motions that need room to breathe -- never put them on a quarter-beat cut
SLOW_MOTIONS = {"push_in", "pull_out", "drift_l", "drift_r", "drift_up", "roll_in"}
FAST_MOTIONS = {"punch", "snap_in", "pulse", "still"}


@dataclass
class Shot:
    photo: int
    start: int              # first frame, inclusive
    end: int                # last frame, exclusive
    motion: str
    direction: int          # +1 / -1, flips pans and rolls
    trans_in: str           # transition landing on this shot's first frame
    seed: int
    beats: float

    @property
    def frames(self) -> int:
        return self.end - self.start


@dataclass
class Timeline:
    shots: list
    fps: int
    total_frames: int
    bpm: float
    seconds: float


def _weighted(rng, pairs, exclude=()):
    pool = [(n, w) for n, w in pairs if n not in exclude]
    if not pool:
        pool = list(pairs)
    total = sum(w for _, w in pool)
    r = rng.random() * total
    for n, w in pool:
        r -= w
        if r <= 0:
            return n
    return pool[-1][0]


def build_beats(n_photos: int, preset: dict, pace: float, seed: int) -> list:
    """Beat length for every photo, tiling the preset's rhythm phrase."""
    phrase = list(preset["phrase"])
    burst = list(preset.get("burst") or [])
    every = int(preset.get("burst_every") or 0)

    beats, cycle = [], 0
    while len(beats) < n_photos:
        beats.extend(phrase)
        cycle += 1
        if burst and every and cycle % every == 0:
            beats.extend(burst)
    beats = beats[:n_photos]

    # the hook holds a beat longer, the last shot lands and settles
    beats[0] = max(beats[0], 2.0)
    if len(beats) > 1:
        beats[-1] = max(beats[-1], 2.5)
    return [b * pace for b in beats]


def build(n_photos: int, preset: dict, *, fps: int = 30, pace: float = 1.0,
          bpm: float | None = None, seed: int = 0,
          target_seconds: float | None = None, wide=None) -> Timeline:
    rng = random.Random(seed)
    bpm = float(bpm or preset["bpm"])
    beats = build_beats(n_photos, preset, pace, seed)

    spb = 60.0 / bpm
    raw = sum(beats) * spb
    if target_seconds:
        # squeeze or stretch the whole rhythm onto the requested runtime
        scale = target_seconds / raw
        beats = [b * scale for b in beats]
        raw = target_seconds

    shots, frame, prev_motion, prev_trans = [], 0, None, None
    for i, b in enumerate(beats):
        dur = max(2, int(round(b * spb * fps)))
        short = b <= 0.55

        # motion: keep slow moves off the very short cuts, never repeat back to back
        pool = preset["motions"]
        if short:
            pool = [(m, w) for m, w in pool if m in FAST_MOTIONS] or pool
        elif wide and i < len(wide) and wide[i] and rng.random() < 0.72:
            # a wide photo wants the camera to travel across it, not sit still
            pool = [(m, w) for m, w in pool if m in ("drift_l", "drift_r")] or pool
        motion = _weighted(rng, pool, exclude={prev_motion})

        if i == 0:
            trans = "hardcut"
        else:
            tpool = preset["transitions"]
            if short:
                # bursts stay clean; only cheap one-frame hits allowed
                tpool = [(t, w) for t, w in tpool
                         if t in ("hardcut", "flash", "zoom_punch", "shake_cut")] or tpool
            trans = _weighted(rng, tpool, exclude={prev_trans} if prev_trans != "hardcut" else ())
            # a transition can never be longer than the shot it lands on
            need = TRANSITIONS[trans]["post"]
            if need >= dur:
                trans = "hardcut"

        shots.append(Shot(photo=i, start=frame, end=frame + dur, motion=motion,
                          direction=1 if rng.random() < 0.5 else -1,
                          trans_in=trans, seed=rng.randrange(1 << 30), beats=b))
        frame += dur
        prev_motion, prev_trans = motion, trans

    return Timeline(shots=shots, fps=fps, total_frames=frame, bpm=bpm,
                    seconds=frame / fps)
