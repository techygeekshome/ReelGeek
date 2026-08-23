"""Edit styles for ReelGeek.

Each preset describes HOW an edit feels: its rhythm, how the camera moves,
which transitions it favours, and how the colour is graded.

`phrase` is the rhythm, in beats per photo. It is tiled to cover however many
photos you give it, so 12 photos and 60 photos both stay musical. Values like
0.5 and 0.25 are half- and quarter-beat cuts (the rapid-fire bursts).
"""

# --- colour grade -----------------------------------------------------------
# contrast: 1.0 = untouched.  lift: raises blacks (film look) when positive.
# sat: saturation multiplier.  temp: >0 warmer, <0 cooler.
# shadow_tint / high_tint: RGB pushes applied to darks and lights (split tone).

GRADES = {
    "punchy": dict(contrast=1.16, lift=0.005, sat=1.14, gamma=0.98,
                   shadow_tint=(-6, 0, 10), high_tint=(10, 4, -6)),
    "faded": dict(contrast=0.94, lift=0.055, sat=0.92, gamma=1.04,
                  shadow_tint=(4, 2, 12), high_tint=(12, 8, 0)),
    "crisp": dict(contrast=1.10, lift=0.0, sat=1.06, gamma=1.0,
                  shadow_tint=(0, 0, 4), high_tint=(4, 2, 0)),
    "retro": dict(contrast=1.05, lift=0.07, sat=1.10, gamma=1.02,
                  shadow_tint=(10, -2, 6), high_tint=(16, 6, -10)),
    "moody": dict(contrast=1.24, lift=0.012, sat=0.90, gamma=0.95,
                  shadow_tint=(-8, -2, 8), high_tint=(6, 4, 0)),
}

PRESETS = {
    # ---------------------------------------------------------------- hype --
    "hype": dict(
        label="Hype",
        blurb="Fast, punchy, aggressive. Flash and glitch hits, hard cuts on "
              "the beat. The default TikTok fashion/lifestyle edit.",
        bpm=128,
        phrase=[2, 1, 1, 1, 0.5, 0.5, 2, 1, 1, 0.5, 0.5, 0.5, 0.5, 2, 1, 1],
        burst=[0.25, 0.25, 0.25, 0.25, 0.5, 0.5],   # fired at phrase ends
        burst_every=2,          # inject a burst every N phrases
        grade="punchy",
        motions=[("punch", 4), ("push_in", 3), ("snap_in", 3), ("pull_out", 2),
                 ("drift_l", 1), ("drift_r", 1), ("pulse", 2), ("still", 1)],
        transitions=[("hardcut", 46), ("zoom_punch", 16), ("flash", 12),
                     ("whip", 12), ("glitch", 8), ("shake_cut", 6)],
        beat_pulse=0.030,
        shake=0.7,
        grain=5,
        vignette=0.30,
        bars=0.0,
        hook_style="block",
    ),
    # ---------------------------------------------------------------- soft --
    "soft": dict(
        label="Soft",
        blurb="Dreamy and slow. Long drifting pushes, gentle dissolves, faded "
              "film grade. Good for golden-hour and portrait sets.",
        bpm=92,
        phrase=[3, 2, 2, 3, 2, 2, 2, 3, 2, 2],
        burst=[1, 1, 1, 1],
        burst_every=3,
        grade="faded",
        motions=[("push_in", 4), ("drift_l", 3), ("drift_r", 3), ("drift_up", 3),
                 ("pull_out", 3), ("still", 1)],
        transitions=[("hardcut", 30), ("dissolve", 40), ("blur_dissolve", 18),
                     ("flash", 6), ("whip", 6)],
        beat_pulse=0.0,
        shake=0.0,
        grain=9,
        vignette=0.42,
        bars=0.0,
        hook_style="plain",
    ),
    # --------------------------------------------------------------- clean --
    "clean": dict(
        label="Clean",
        blurb="Modern and minimal. Crisp hard cuts, decisive slides, no gimmicks. "
              "Reads as expensive rather than loud.",
        bpm=110,
        phrase=[2, 1, 1, 2, 1, 1, 2, 2, 1, 1, 2, 1],
        burst=[0.5, 0.5, 0.5, 0.5],
        burst_every=3,
        grade="crisp",
        motions=[("push_in", 4), ("pull_out", 3), ("snap_in", 3), ("still", 2),
                 ("drift_l", 2), ("drift_r", 2), ("drift_up", 2)],
        transitions=[("hardcut", 58), ("slide", 22), ("zoom_punch", 10),
                     ("dissolve", 6), ("whip", 4)],
        beat_pulse=0.018,
        shake=0.0,
        grain=3,
        vignette=0.22,
        bars=0.0,
        hook_style="bar",
    ),
    # ----------------------------------------------------------------- vhs --
    "vhs": dict(
        label="VHS",
        blurb="Retro camcorder energy. Heavy grain, colour bleed, glitch cuts "
              "and a warm faded tape grade.",
        bpm=118,
        phrase=[2, 1, 1, 1, 1, 2, 0.5, 0.5, 1, 2, 1, 1, 0.5, 0.5],
        burst=[0.25, 0.25, 0.25, 0.25],
        burst_every=2,
        grade="retro",
        motions=[("punch", 3), ("push_in", 3), ("snap_in", 3), ("drift_l", 2),
                 ("drift_r", 2), ("pulse", 2), ("roll_in", 2), ("still", 1)],
        transitions=[("hardcut", 40), ("glitch", 24), ("flash", 12),
                     ("whip", 12), ("shake_cut", 8), ("zoom_punch", 4)],
        beat_pulse=0.026,
        shake=0.9,
        grain=16,
        vignette=0.46,
        bars=0.0,
        hook_style="block",
    ),
}

# `luxe` written out longhand so the dict above stays readable.
PRESETS["luxe"] = dict(
    label="Luxe",
    blurb="Slow, deliberate, cinematic. Big smooth pushes, deep contrast and "
          "letterbox bars. Fewer cuts, more weight per photo.",
    bpm=84,
    phrase=[4, 2, 2, 4, 2, 2, 3, 3, 2, 2],
    burst=[1, 1, 1, 1],
    burst_every=3,
    grade="moody",
    motions=[("push_in", 5), ("pull_out", 4), ("drift_l", 3), ("drift_r", 3),
             ("drift_up", 3), ("roll_in", 1)],
    transitions=[("hardcut", 44), ("dissolve", 26), ("blur_dissolve", 16),
                 ("slide", 8), ("zoom_punch", 6)],
    beat_pulse=0.0,
    shake=0.0,
    grain=6,
    vignette=0.50,
    bars=0.055,
    hook_style="plain",
)

PRESET_ORDER = ["hype", "clean", "soft", "vhs", "luxe"]

# Pace multiplies every slot length. 1.0 is the preset's own tempo.
PACES = {"chill": 1.35, "normal": 1.0, "fast": 0.76, "frantic": 0.6}
