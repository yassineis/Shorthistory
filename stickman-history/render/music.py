"""Generate a soft, original background music bed (no samples, no licences): slow pad chords plus
gentle plucks, synthesized with numpy.

Usage: python music.py <seconds> <out.wav>
"""
import sys
import wave

import numpy as np

SR = 44100
# Am - F - C - G, notes in Hz
CHORDS = [
    [220.00, 261.63, 329.63],
    [174.61, 220.00, 261.63],
    [196.00, 261.63, 329.63],
    [196.00, 246.94, 293.66],
]


def make(seconds):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    beat = 60.0 / 76.0
    bar = beat * 4
    k = 0
    while k * bar < seconds:
        notes = CHORDS[k % len(CHORDS)]
        a, b = int(k * bar * SR), min(n, int((k + 1) * bar * SR + 0.6 * SR))
        seg = np.arange(b - a) / SR
        env = np.minimum(1, seg / 0.8) * np.exp(-np.maximum(0, seg - bar) * 5)
        for f in notes:
            tone = np.sin(2 * np.pi * f * seg) + 0.35 * np.sin(2 * np.pi * f * 2 * seg + 0.4)
            out[a:b] += (0.10 * env * tone).astype(np.float32)
        # soft pluck arpeggio, two per beat
        for j in range(8):
            ts = int((k * bar + j * beat / 2) * SR)
            if ts >= n:
                break
            f = notes[j % 3] * 2
            m = min(n - ts, int(0.9 * SR))
            s = np.arange(m) / SR
            out[ts:ts + m] += (0.07 * np.exp(-s * 6) * np.sin(2 * np.pi * f * s)).astype(np.float32)
        k += 1
    fade = int(min(2.0, seconds / 4) * SR)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(out))) or 1.0
    return out / peak * 0.5


def write_wav(path, mono):
    pcm = (np.clip(mono, -1, 1) * 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python music.py <seconds> <out.wav>")
    write_wav(sys.argv[2], make(float(sys.argv[1])))
