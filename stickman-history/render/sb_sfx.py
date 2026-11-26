"""Tiny code-made sound effects for story videos (numpy only, free).

  python sb_sfx.py events.json out.wav
events.json: {"total": seconds, "events": [{"t": seconds, "name": "whoosh", "gain": 1.0}, ...]}
Names: whoosh (scene change), door, steps, ding, coins, drum, bell, crowd, thud.
"""
import json
import sys

import numpy as np

from sb_music import SR, tone, noise_hit, kick, add, lowpass, midi, save

NAMES = ("whoosh", "door", "steps", "ding", "coins", "drum", "bell", "crowd", "thud")


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
        add(out, cache[nm], max(0.0, float(e["t"])), float(e.get("gain", 1.0)))
    return np.clip(out, -1, 1)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    save(sys.argv[2], render(spec.get("events", []), float(spec.get("total", 60))))
    print("wrote", sys.argv[2])
