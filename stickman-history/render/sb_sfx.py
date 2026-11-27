"""Tiny code-made sound effects for story videos (numpy only, free).

  python sb_sfx.py events.json out.wav
events.json: {"total": seconds, "events": [{"t": seconds, "name": "whoosh", "gain": 1.0}, ...]}
Names: whoosh (scene change), door, steps, ding, coins, drum, bell, crowd, thud,
plus (enhanced mode) step2, glass, splash, crash, laugh, gasp, boing, thunder, applause, creak, zap.
"""
import json
import sys

import numpy as np

from sb_music import SR, tone, noise_hit, kick, add, lowpass, midi, save

NAMES = ("whoosh", "door", "steps", "ding", "coins", "drum", "bell", "crowd", "thud",
         "step2", "glass", "splash", "crash", "laugh", "gasp", "boing", "thunder", "applause", "creak", "zap")


def _whoosh():
    w = int(.42 * SR)
    x = lowpass(np.random.default_rng(2).normal(0, 1, w), 22) * np.sin(np.linspace(0, np.pi, w)) ** 1.6
    return x * 1.6


def _make(name):
    n = int(2.0 * SR)
    m = np.zeros(n)
    if name == "whoosh":
        add(m, _whoosh(), 0, .5)
    elif name == "door":  # latch click, then a wooden thud
        add(m, noise_hit(.025, decay=.006, seed=3), 0, .8)
        add(m, tone(95, .3, (1, .5, .2), a=.002, d=.09), .06, .7)
        add(m, noise_hit(.12, lo=30, decay=.04, seed=4), .06, .35)
    elif name == "steps":
        for i in range(4):
            add(m, noise_hit(.07, lo=50, decay=.022, seed=10 + i), i * .27, .6)
            add(m, tone(70 + 6 * (i % 2), .12, (1, .4), a=.002, d=.04), i * .27, .35)
    elif name == "ding":
        add(m, tone(midi(88), 1.2, (1, .4, .2), a=.002, d=.45), 0, .5)
    elif name == "coins":
        for i, nn in enumerate((90, 94, 91, 96, 93)):
            add(m, tone(midi(nn), .35, (1, .5, .3), a=.001, d=.09), i * .06, .3)
    elif name == "drum":
        add(m, kick(.6), 0, .95)
        add(m, noise_hit(.5, lo=60, decay=.18, seed=5), 0, .2)
    elif name == "bell":
        add(m, tone(midi(79), 1.9, (1, .6, .35, .2), a=.002, d=.9), 0, .45)
    elif name == "crowd":
        x = lowpass(np.random.default_rng(6).normal(0, 1, n), 30)
        mod = .6 + .4 * np.sin(np.linspace(0, 11, n))
        add(m, x * mod * np.sin(np.linspace(0, np.pi, n)) ** .6 * 2.2, 0, .5)
    elif name == "thud":
        add(m, kick(.35), 0, .8)
        add(m, noise_hit(.1, lo=40, decay=.03, seed=8), 0, .3)
    elif name == "step2":  # two quick footsteps
        for i in range(2):
            add(m, noise_hit(.06, lo=50, decay=.02, seed=20 + i), i * .22, .55)
            add(m, tone(68 + 8 * i, .1, (1, .4), a=.002, d=.035), i * .22, .3)
    elif name == "glass":  # bright shatter
        add(m, noise_hit(.5, lo=2500, decay=.14, seed=31), 0, .45)
        for i, f in enumerate((92, 97, 100, 95, 102, 99)):
            add(m, tone(midi(f), .25, (1, .5), a=.001, d=.06), .02 + i * .045, .22)
    elif name == "splash":
        x = lowpass(np.random.default_rng(32).normal(0, 1, n), 12)
        add(m, x * np.exp(-np.linspace(0, 6, n)) * 2.4, 0, .6)
        add(m, tone(180, .2, (1,), a=.002, d=.06), 0, .2)
    elif name == "crash":  # big impact: low boom plus rattling noise
        add(m, kick(.5), 0, .9)
        add(m, noise_hit(.9, lo=300, decay=.3, seed=33), 0, .5)
        add(m, noise_hit(.3, lo=1200, decay=.1, seed=34), .08, .3)
    elif name == "laugh":  # five bouncy "ha" bursts
        for i in range(5):
            f = 330 - i * 18
            add(m, tone(f, .16, (1, .6, .3), a=.01, d=.06), i * .19, .3)
            add(m, noise_hit(.12, lo=900, decay=.04, seed=40 + i), i * .19, .12)
    elif name == "gasp":  # quick breath in
        x = lowpass(np.random.default_rng(35).normal(0, 1, int(.4 * SR)), 5)
        env = np.sin(np.linspace(0, np.pi, len(x))) ** 2 * np.linspace(.3, 1, len(x))
        add(m, x * env * 3.5, 0, .5)
    elif name == "boing":  # springy pitch wobble
        tt = np.arange(int(.5 * SR)) / SR
        f = 220 + 160 * np.exp(-tt * 5) * np.sin(2 * np.pi * 9 * tt)
        add(m, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5), 0, .45)
    elif name == "thunder":
        x = lowpass(np.random.default_rng(36).normal(0, 1, n), 40)
        env = np.exp(-np.linspace(0, 3.2, n)) * (0.6 + 0.4 * np.sin(np.linspace(0, 40, n)))
        add(m, x * env * 3.0, 0, .6)
        add(m, kick(.5), .02, .6)
    elif name == "applause":
        rng = np.random.default_rng(37)
        x = np.zeros(n)
        for k in range(160):
            p = int(rng.uniform(0, n - 900))
            x[p:p + 400] += rng.normal(0, 1, 400) * np.exp(-np.linspace(0, 8, 400))
        add(m, x * np.sin(np.linspace(0, np.pi, n)) ** .5 * .55, 0, .5)
    elif name == "creak":  # slow squeaky pitch slide
        tt = np.arange(int(1.2 * SR)) / SR
        f = 300 + 120 * np.sin(2 * np.pi * 1.7 * tt) + 90 * tt
        sq = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * .4 + np.sin(2 * np.pi * np.cumsum(f * 2) / SR) * .3
        add(m, sq * np.sin(np.linspace(0, np.pi, len(tt))) ** 1.5, 0, .22)
    elif name == "zap":  # quick electric zip
        tt = np.arange(int(.35 * SR)) / SR
        f = 2400 * np.exp(-tt * 9) + 200
        add(m, np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-tt * 8), 0, .25)
    return m


def render(events, total):
    out = np.zeros(int((total + 1) * SR))
    cache = {}
    for e in events:
        nm = e.get("name")
        if nm not in NAMES:
            continue
        if nm not in cache:
            cache[nm] = _make(nm)
            pk = float(np.abs(cache[nm]).max())
            if pk > 0.95:
                cache[nm] = cache[nm] * (0.95 / pk)  # no clipping
            elif nm in ("creak", "zap") and pk > 0:
                cache[nm] = cache[nm] * (0.5 / pk)
        add(out, cache[nm], max(0.0, float(e["t"])), float(e.get("gain", 1.0)))
    return np.clip(out, -1, 1)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    save(sys.argv[2], render(spec.get("events", []), float(spec.get("total", 60))))
    print("wrote", sys.argv[2])
