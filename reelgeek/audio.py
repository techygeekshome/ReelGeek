"""A synthesised scratch beat, generated from scratch by this app.

It exists so you can check your cuts land on the beat before you post. It is
not a music bed: on TikTok and Shorts you get better distribution attaching the
platform's own trending audio, and that is also the only copyright-safe route.
Because these samples are generated numerically here, nothing is licensed from
anyone and the file is yours.
"""
from __future__ import annotations
import math
import wave
import numpy as np

SR = 44100


def _env(n, attack, decay):
    a = max(1, int(attack * SR))
    e = np.ones(n, dtype=np.float32)
    e[:a] = np.linspace(0, 1, a, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SR
    return e * np.exp(-t / max(1e-4, decay))


def _kick(dur=0.30):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 118.0 * np.exp(-t * 34.0) + 44.0
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * _env(n, 0.001, 0.085)
    click = np.random.default_rng(1).normal(0, 1, n).astype(np.float32) * _env(n, 0.0002, 0.004)
    return np.tanh((body * 1.5 + click * 0.35)) * 0.95


def _hat(dur=0.055, seed=2):
    n = int(dur * SR)
    x = np.random.default_rng(seed).normal(0, 1, n).astype(np.float32)
    x = np.diff(np.concatenate([[0.0], x]))            # crude high-pass
    return x * _env(n, 0.0005, 0.011) * 0.34


def _clap(dur=0.24, seed=3):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n).astype(np.float32)
    x = np.diff(np.concatenate([[0.0], x])) * 0.6 + x * 0.4
    out = np.zeros(n, dtype=np.float32)
    for i, off in enumerate((0.0, 0.011, 0.023)):      # three slaps = a clap
        s = int(off * SR)
        out[s:] += x[: n - s] * _env(n - s, 0.0004, 0.035) * (0.9 ** i)
    out += x * _env(n, 0.004, 0.10) * 0.35
    return out * 0.55


def _sub(dur, freq):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    return np.sin(2 * np.pi * freq * t) * _env(n, 0.006, dur * 0.45) * 0.42


def write_scratch_beat(path: str, bpm: float, seconds: float, seed: int = 0) -> str:
    spb = 60.0 / bpm
    n = int((seconds + 0.6) * SR)
    buf = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(seed)

    kick, clap = _kick(), _clap()
    hats = [_hat(seed=10 + i) for i in range(4)]
    notes = [41.2, 41.2, 55.0, 49.0, 43.65, 41.2, 36.71, 49.0]   # simple minor loop

    def put(sample, at):
        s = int(at * SR)
        if s >= n:
            return
        e = min(n, s + len(sample))
        buf[s:e] += sample[: e - s]

    beat = 0
    t = 0.0
    while t < seconds:
        bar_pos = beat % 4
        put(kick, t)
        if bar_pos in (1, 3):
            put(clap, t)
        if bar_pos == 3 and (beat // 4) % 2 == 1:
            put(kick, t + spb * 0.75)                  # little turnaround
        for k in range(2):
            put(hats[rng.integers(0, 4)], t + spb * 0.5 * k)
        if bar_pos in (0, 2):
            put(_sub(spb * 1.9, notes[(beat // 2) % len(notes)]), t)
        beat += 1
        t += spb

    peak = float(np.max(np.abs(buf))) or 1.0
    buf = np.tanh(buf / peak * 1.25) * 0.82
    buf = buf[: int(seconds * SR)]
    # short fade so it never clicks at the top or tail
    f = int(0.01 * SR)
    buf[:f] *= np.linspace(0, 1, f, dtype=np.float32)
    buf[-f:] *= np.linspace(1, 0, f, dtype=np.float32)

    pcm = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1).tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo)
    return path
