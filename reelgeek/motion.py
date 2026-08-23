"""Camera moves. Each returns (scale, pan_x, pan_y, roll_degrees).

`scale` is magnification (1.0 = whole frame). `pan_x` / `pan_y` are in units of
available margin, so -1 is hard against one edge and +1 the other -- the crop
window can never fall off the photo no matter how far a move pushes.
"""
from __future__ import annotations
import math
from .imaging import lerp, ease_out_cubic, ease_in_out, ease_out_expo, ease_out_sine

MAX_SCALE = 1.55


def get(name: str, p: float, d: int = 1):
    p = 0.0 if p < 0 else (1.0 if p > 1 else p)

    if name == "push_in":
        return lerp(1.02, 1.21, ease_out_sine(p)), 0.0, -0.15 * p, 0.0
    if name == "pull_out":
        return lerp(1.26, 1.04, ease_out_sine(p)), 0.0, 0.10 * (1 - p), 0.0
    if name == "punch":
        return lerp(1.32, 1.07, ease_out_expo(p)), 0.0, 0.0, 0.0
    if name == "snap_in":
        # holds, then jumps on the half beat -- reads as a rhythmic hit
        return (1.04 if p < 0.5 else 1.19), 0.0, 0.0, 0.0
    if name == "pulse":
        return 1.09 + 0.07 * (1 - ease_out_expo(min(1.0, p * 3.2))), 0.0, 0.0, 0.0
    if name == "still":
        return 1.05, 0.0, 0.0, 0.0
    if name == "drift_l":
        return 1.15, lerp(0.85 * d, -0.85 * d, ease_in_out(p)), 0.0, 0.0
    if name == "drift_r":
        return 1.15, lerp(-0.85 * d, 0.85 * d, ease_in_out(p)), 0.0, 0.0
    if name == "drift_up":
        return 1.16, 0.0, lerp(0.8, -0.8, ease_in_out(p)), 0.0
    if name == "roll_in":
        return (lerp(1.24, 1.09, ease_out_cubic(p)), 0.0, 0.0,
                lerp(2.8 * d, 0.0, ease_out_cubic(p)))
    return 1.05, 0.0, 0.0, 0.0


def beat_pulse(t: float, bpm: float, amp: float) -> float:
    """A small scale bump landing on every beat, decaying over a quarter beat."""
    if amp <= 0:
        return 1.0
    phase = (t * bpm / 60.0) % 1.0
    return 1.0 + amp * (1.0 - ease_out_expo(min(1.0, phase * 4.0)))


def handheld(t: float, amp: float, phase: tuple) -> tuple:
    """Lazy two-frequency wobble so nothing sits perfectly locked off."""
    if amp <= 0:
        return 0.0, 0.0
    a, b, c, d = phase
    x = math.sin(2 * math.pi * 0.63 * t + a) + 0.55 * math.sin(2 * math.pi * 1.87 * t + b)
    y = math.sin(2 * math.pi * 0.51 * t + c) + 0.55 * math.sin(2 * math.pi * 2.13 * t + d)
    return x * amp, y * amp
