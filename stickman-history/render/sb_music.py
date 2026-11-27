"""Free music + SFX made entirely from code (numpy only). Five different styles.

  python sb_music.py N out.wav [seconds]    # N = 1..5
Styles: 1 music box lullaby, 2 folk guitar, 3 lo-fi chill, 4 adventure marimba, 5 cinematic epic.
"""
import sys
import wave

import numpy as np

SR = 44100


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.3, s=0.0, r=0.1):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / max(d, 1e-3)))
    e = np.maximum(e, s)
    tail = int(r * SR)
    if tail and n > tail:
        e[-tail:] *= np.linspace(1, 0, tail)
    return e


def tone(f, dur, harm=(1, .4, .2), a=0.005, d=0.4, vib=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * t + (vib * np.sin(2 * np.pi * 5.2 * t) if vib else 0)
    y = sum(h * np.sin(ph * (i + 1)) for i, h in enumerate(harm))
    return y * env(n, a, d)


_PLUCKS = {}


def pluck(f, dur, damp=0.996):
    """Karplus-Strong string (cached: each note is only computed once)."""
    key = (round(f, 3), dur, damp)
    if key in _PLUCKS:
        return _PLUCKS[key]
    _PLUCKS[key] = _pluck(f, dur, damp)
    return _PLUCKS[key]


def _pluck(f, dur, damp):
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = np.random.default_rng(int(f)).uniform(-1, 1, p)
    out = np.empty(n)
    for i in range(n):
        j = i % p
        out[i] = buf[j]
        buf[j] = damp * 0.5 * (buf[j] + buf[(j + 1) % p])
    return out


def noise_hit(dur, lo=0.0, decay=0.05, seed=0):
    n = int(dur * SR)
    x = np.random.default_rng(seed).normal(0, 1, n)
    if lo:
        x = x - np.convolve(x, np.ones(int(lo)) / lo, "same")
    return x * np.exp(-np.arange(n) / SR / decay)


def kick(dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def add(mix, y, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(mix) or i < 0:
        return
    y = y[: len(mix) - i]
    mix[i:i + len(y)] += y * g


def reverb(x, secs=1.6, wet=0.25, seed=3):
    n = int(secs * SR)
    ir = np.random.default_rng(seed).normal(0, 1, n) * np.exp(-np.arange(n) / SR / (secs / 4))
    ir /= np.abs(ir).sum() / 8
    m = len(x) + n
    nfft = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return x * (1 - wet) + y * wet


def lowpass(x, k=40):
    return np.convolve(x, np.ones(k) / k, "same")


def pad(freqs, dur, g=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in freqs:
        for det in (-0.4, 0.0, 0.5):
            y += np.sin(2 * np.pi * (f + det) * t)
    e = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return y / (3 * len(freqs)) * e * g


# progression roots (MIDI) and chord notes, C major-ish: C  Am  F  G
CHORDS = [(60, 64, 67), (57, 60, 64), (53, 57, 60), (55, 59, 62)]
PENT = [72, 74, 76, 79, 81, 84]


def style1(dur):  # music box lullaby
    m = np.zeros(int(dur * SR))
    beat = 60 / 76
    rng = np.random.default_rng(1)
    for b in range(int(dur / beat)):
        t0 = b * beat
        ch = CHORDS[(b // 4) % 4]
        if b % 4 == 0:
            for i, nn in enumerate(ch):
                add(m, tone(midi(nn - 12), 2.6, (1, .3, .1), d=1.2), t0 + i * 0.03, .22)
        n = PENT[rng.integers(0, len(PENT))] if b % 2 else ch[(b // 2) % 3] + 12
        add(m, tone(midi(n), 1.8, (1, .55, .25, .12), a=.003, d=.55), t0, .30)
        if b % 2 == 0:
            add(m, tone(midi(n + 12), 1.2, (1, .3), a=.003, d=.3), t0 + beat / 2, .12)
    return reverb(m, 2.0, .32)


def style2(dur):  # folk guitar (Karplus-Strong), strummed
    m = np.zeros(int(dur * SR))
    beat = 60 / 96
    for b in range(int(dur / beat / 2)):
        t0 = b * beat * 2
        ch = CHORDS[(b // 2) % 4]
        for i, nn in enumerate((ch[0] - 12,) + ch + (ch[0] + 12,)):
            add(m, pluck(midi(nn), 1.6), t0 + i * 0.035, .24)
        for j in (1, 1.5):  # gentle second strum
            for i, nn in enumerate(ch):
                add(m, pluck(midi(nn + 12), .8), t0 + j * beat + i * 0.025, .14)
    add(m, pad([midi(48), midi(55)], dur), 0, .12)
    return reverb(m, 1.2, .2)


def style3(dur):  # lo-fi chill
    m = np.zeros(int(dur * SR))
    beat = 60 / 74
    for b in range(int(dur / beat)):
        t0 = b * beat
        ch = CHORDS[(b // 4) % 4]
        if b % 4 == 0:
            for nn in ch + (ch[0] + 14,):
                y = tone(midi(nn), 3.0, (1, .35, .12), a=.012, d=1.2, vib=0.4)
                add(m, y, t0, .17)
        if b % 2 == 0:
            add(m, kick(), t0, .5)
        if b % 4 == 2:
            add(m, noise_hit(.18, lo=18, decay=.06, seed=b), t0, .35)  # snare-ish
        for h in (0.0, 0.5):
            add(m, noise_hit(.05, lo=0, decay=.012, seed=b + 9), t0 + h * beat, .06)
    m = lowpass(m, 6)
    m += np.random.default_rng(7).normal(0, 0.004, len(m))  # vinyl hiss
    for t in np.random.default_rng(8).uniform(0, dur, 30):
        add(m, noise_hit(.01, decay=.003, seed=int(t * 100)), t, .1)
    return reverb(m, 1.0, .15)


def style4(dur):  # adventure marimba
    m = np.zeros(int(dur * SR))
    beat = 60 / 112
    rng = np.random.default_rng(4)
    scale = [60, 62, 64, 67, 69, 72, 74, 76]
    for b in range(int(dur / beat * 2)):
        t0 = b * beat / 2
        ch = CHORDS[(b // 8) % 4]
        if b % 2 == 0:
            nn = ch[(b // 2) % 3] - (12 if b % 4 == 0 else 0)
            add(m, tone(midi(nn + 12), .5, (1, 0, .6, 0, .2), a=.002, d=.18), t0, .32)
        if b % 8 in (3, 5, 7):
            add(m, tone(midi(scale[rng.integers(0, 8)] + 12), .4, (1, 0, .5), a=.002, d=.15), t0, .22)
        if b % 4 == 0:
            add(m, kick(.3), t0, .55 if b % 8 == 0 else .3)
        if b % 8 == 4:
            add(m, noise_hit(.14, lo=14, decay=.05, seed=b), t0, .3)
    add(m, pad([midi(48), midi(55), midi(60)], dur), 0, .15)
    return reverb(m, 1.2, .2)


def style5(dur):  # cinematic epic: pad swell, low strings, big drums, riser
    m = np.zeros(int(dur * SR))
    bar = 60 / 84 * 4
    for i in range(int(dur / bar) + 1):
        ch = CHORDS[i % 4]
        add(m, pad([midi(ch[0] - 24), midi(ch[0] - 12), midi(ch[1] - 12), midi(ch[2])], bar + 1.2, 1.0), i * bar, .26)
        for j in range(4):
            add(m, tone(midi(ch[0] - 12 + (0, 7, 12, 7)[j]), bar / 3, (1, .5, .3, .2), a=.05, d=.5, vib=.5), i * bar + j * bar / 4, .16)
    beat = bar / 4
    for b in range(int(dur / beat)):
        if b % 4 == 0:
            add(m, kick(.5), b * beat, .95)
            add(m, noise_hit(.8, lo=60, decay=.25, seed=b), b * beat, .20)
        elif b % 4 == 2:
            add(m, kick(.35), b * beat, .5)
    # riser into the subscribe card
    r0 = 17.5
    n = int((dur - r0) * SR)
    ris = np.random.default_rng(5).normal(0, 1, n) * np.linspace(0, 1, n) ** 2
    add(m, lowpass(ris, 5) * .16, r0)
    return reverb(m, 2.4, .35)


STYLES = {1: style1, 2: style2, 3: style3, 4: style4, 5: style5}


def sfx(mix_len, n):
    """Whoosh at the camera cut (sketch 4-5), pop on subscribe card, click + sparkle chime on the button."""
    s = np.zeros(mix_len)
    if n >= 4:
        w = int(.5 * SR)
        x = lowpass(np.random.default_rng(2).normal(0, 1, w), 25) * np.sin(np.linspace(0, np.pi, w)) ** 1.5
        add(s, x * 2.2, 9.0, .5)
    add(s, tone(520, .25, (1, .3), a=.002, d=.08) , 20.2, .3)  # card pop
    if n >= 5:
        add(s, noise_hit(.03, decay=.008, seed=3), 22.4, .8)  # click
        for i, nn in enumerate((84, 88, 91, 96)):
            add(s, tone(midi(nn), .9, (1, .4, .2), a=.002, d=.3), 22.42 + i * .07, .22)
    return s


def render(n, dur=24.0):
    m = STYLES[n](dur)
    m = m / (np.abs(m).max() + 1e-9) * 0.55
    # duck the music a little under the narration window (0.5s-19.5s), full volume on the outro
    duck = np.ones(len(m))
    duck[int(.5 * SR):int(19.5 * SR)] = 0.55
    duck = lowpass(duck, 4000)
    m *= duck
    m += sfx(len(m), n) * .6
    fade = int(1.2 * SR)
    m[-fade:] *= np.linspace(1, 0, fade)
    m[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
    return np.clip(m, -1, 1)


def render_bg(n, dur, hush=None):
    """Music bed for a whole story video: one of the 5 styles, quiet, with fade in/out, no sound effects."""
    m = STYLES[n](dur)
    m = m / (np.abs(m).max() + 1e-9) * 0.5
    fi, fo = int(1.0 * SR), int(2.0 * SR)
    m[:fi] *= np.linspace(0, 1, fi)
    m[-fo:] *= np.linspace(1, 0, fo)
    if hush is not None:  # enhanced mode: shape the music like a story, then go quiet for the subscribe line
        tt = np.arange(len(m)) / SR
        arc = np.where(tt < 4, 1.2, 0.9) + 0.25 * np.clip((tt - dur * 0.6) / (dur * 0.35), 0, 1)
        arc = np.where(tt >= hush, 0.45, arc)
        arc = np.convolve(arc, np.ones(int(0.4 * SR)) / int(0.4 * SR), mode="same")
        m = m * arc
    return np.clip(m, -1, 1)


def save(path, y):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    n = int(sys.argv[1])
    d = float(sys.argv[3]) if len(sys.argv) > 3 else 24.0
    hush = float(sys.argv[sys.argv.index("--hush") + 1]) if "--hush" in sys.argv else None
    save(sys.argv[2], render_bg(n, d, hush) if "--bg" in sys.argv else render(n, d))
    print("wrote", sys.argv[2])
