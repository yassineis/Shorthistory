"""Style A5 "Historical Cartoon": colourful period backdrops drawn in code, white round heads,
bold ink outlines, costumes and hats. Everything is Pillow, no assets, no network.

make_backdrop(W, H, S, setting, L) -> supersampled RGB image (drawn once per scene).
"""
import math

import numpy as np
from PIL import Image

from stage import Pen, INK, RED, GOLD

OUTFITS = {
    "red": (200, 50, 30), "blue": (52, 92, 160), "green": (70, 130, 80), "yellow": (235, 190, 60),
    "purple": (120, 70, 150), "brown": (135, 96, 60), "white": (245, 245, 240), "black": (50, 50, 55),
    "orange": (230, 130, 40), "pink": (230, 130, 160), "teal": (40, 140, 150), "gray": (140, 140, 150),
}

# setting: (sky top, sky at horizon, ground colour)
SETTINGS = {
    "edo_street": ((120, 190, 235), (250, 225, 200), (205, 170, 120)),
    "egypt_temple": ((95, 175, 235), (255, 230, 170), (230, 195, 130)),
    "roman_forum": ((100, 170, 235), (225, 240, 250), (225, 215, 195)),
    "medieval_town": ((130, 185, 230), (230, 240, 245), (125, 170, 90)),
    "viking_coast": ((150, 180, 205), (225, 232, 238), (120, 150, 110)),
    "greek_agora": ((90, 170, 235), (225, 240, 250), (230, 220, 195)),
    "china_palace": ((140, 195, 225), (250, 235, 210), (190, 180, 170)),
    "desert": ((110, 180, 235), (255, 225, 165), (235, 200, 135)),
    "ship_sea": ((120, 190, 235), (225, 240, 250), (150, 105, 65)),
    "old_west": ((245, 175, 105), (255, 225, 160), (215, 160, 105)),
    "london": ((165, 165, 160), (225, 215, 190), (130, 125, 125)),
    "cave": ((70, 45, 35), (125, 85, 55), (110, 80, 58)),
    "steppe": ((95, 170, 235), (225, 240, 250), (140, 180, 95)),
    "jungle_temple": ((115, 195, 215), (225, 240, 225), (105, 150, 70)),
    "battlefield": ((150, 170, 190), (225, 215, 195), (140, 150, 90)),
    "harbor": ((120, 190, 235), (240, 240, 235), (165, 125, 85)),
    "moon": ((10, 10, 25), (35, 35, 70), (170, 170, 175)),
    "snow": ((165, 195, 225), (240, 245, 250), (240, 245, 250)),
}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shade(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)


def _sky(W, H, S, top, hor, G):
    ys = np.linspace(0, 1, int(G) + 1, dtype=np.float32)[:, None, None]
    a, b = np.array(top, np.float32), np.array(hor, np.float32)
    col = a + (b - a) * ys
    arr = np.empty((H, W, 3), np.float32)
    arr[:] = np.array(hor, np.float32)
    arr[: int(G) + 1] = np.repeat(col, W, axis=1)
    img = Image.fromarray(arr.astype(np.uint8), "RGB")
    return img.resize((W * S, H * S), Image.BICUBIC)


# ---------------------------------------------------------------- small building blocks
def sun(p, x, y, r, col=(255, 214, 90)):
    p.circle(x, y, r, fill=col, outline=INK, w=p.lw * 0.8)


def cloud(p, x, y, s):
    for dx, dy, r in ((-1.0, 0.1, 0.6), (0, -0.2, 0.8), (1.0, 0.1, 0.65), (0.2, 0.25, 0.7)):
        p.circle(x + dx * s, y + dy * s, r * s, fill=(255, 255, 255), outline=None, wob=False)
    p.line([(x - 1.5 * s, y + 0.6 * s), (x + 1.6 * s, y + 0.6 * s)], w=p.lw * 0.6, color=INK)


def mountains(p, W, G, col, n=4, hmax=0.22, seed=0, snow=False):
    xs = [(-0.05 + i * 1.1 / n) * W for i in range(n + 1)]
    for i in range(n):
        x0, x1 = xs[i], xs[i + 1]
        h = (hmax * (0.65 + 0.35 * math.sin(i * 2.3 + seed))) * G
        mx = (x0 + x1) / 2
        p.poly([(x0 - 0.1 * W, G), (mx, G - h), (x1 + 0.1 * W, G)], fill=col, outline=INK, w=p.lw * 0.7)
        if snow:
            p.poly([(mx - 0.045 * W, G - h * 0.72), (mx, G - h), (mx + 0.045 * W, G - h * 0.72),
                    (mx + 0.01 * W, G - h * 0.78), (mx - 0.01 * W, G - h * 0.7)], fill=(255, 255, 255), outline=INK, w=p.lw * 0.5)


def hills(p, W, G, col, amp=0.06, ph=0.0, base=0.0):
    pts = [(-5, G)] + [(k * W / 30, G - base * G - amp * G * (1 + math.sin(k * 0.5 + ph)) / 2) for k in range(-1, 32)] + [(W + 5, G)]
    p.poly(pts, fill=col, outline=INK, w=p.lw * 0.7)


def tree(p, x, G, h, leaf=(95, 160, 70)):
    p.rect(x - 0.05 * h, G - 0.45 * h, x + 0.05 * h, G, fill=(135, 96, 60), outline=INK, w=p.lw * 0.7)
    for dx, dy, r in ((-0.22, -0.55, 0.28), (0.22, -0.55, 0.28), (0, -0.78, 0.33)):
        p.circle(x + dx * h, G + dy * h, r * h, fill=leaf, outline=INK, w=p.lw * 0.7)


def blossom(p, x, G, h):
    tree(p, x, G, h, leaf=(245, 175, 200))


def pine(p, x, G, h, col=(60, 120, 80), snow=False):
    p.rect(x - 0.04 * h, G - 0.15 * h, x + 0.04 * h, G, fill=(120, 85, 55), outline=INK, w=p.lw * 0.6)
    for k in range(3):
        y1 = G - 0.12 * h - k * 0.27 * h
        w = (0.34 - 0.07 * k) * h
        p.poly([(x - w, y1), (x, y1 - 0.42 * h), (x + w, y1)], fill=(235, 242, 248) if snow else col, outline=INK, w=p.lw * 0.6)


def palm(p, x, G, h):
    p.line([(x, G), (x + 0.08 * h, G - 0.5 * h), (x + 0.04 * h, G - 0.85 * h)], w=p.lw * 1.4, color=(135, 96, 60))
    top = (x + 0.04 * h, G - 0.85 * h)
    for a in (-160, -125, -90, -55, -20):
        r = math.radians(a)
        p.poly([top, (top[0] + math.cos(r - 0.25) * 0.4 * h, top[1] + math.sin(r - 0.25) * 0.4 * h + 0.1 * h),
                (top[0] + math.cos(r) * 0.5 * h, top[1] + math.sin(r) * 0.4 * h + 0.2 * h),
                (top[0] + math.cos(r + 0.25) * 0.4 * h, top[1] + math.sin(r + 0.25) * 0.4 * h + 0.1 * h)],
               fill=(70, 150, 80), outline=INK, w=p.lw * 0.5)


def column(p, x, G, h, w, col=(245, 240, 228), cap=None):
    p.rect(x - w / 2, G - h, x + w / 2, G, fill=col, outline=INK, w=p.lw * 0.7)
    p.rect(x - w * 0.7, G - h - 0.06 * h, x + w * 0.7, G - h, fill=cap or col, outline=INK, w=p.lw * 0.7)
    p.rect(x - w * 0.7, G - 0.04 * h, x + w * 0.7, G, fill=cap or col, outline=INK, w=p.lw * 0.7)
    for k in (-0.2, 0.2):
        p.line([(x + k * w, G - h * 0.9), (x + k * w, G - h * 0.1)], w=p.lw * 0.35, color=(190, 185, 170))


def temple(p, x, G, w, h, col=(248, 244, 232), roof=(210, 120, 90), n=6):
    for i in range(n):
        column(p, x - w / 2 + w * (i + 0.5) / n, G, h * 0.78, w / n * 0.5, col)
    p.rect(x - w / 2 - 0.02 * w, G - h * 0.9, x + w / 2 + 0.02 * w, G - h * 0.78, fill=col, outline=INK, w=p.lw * 0.8)
    p.poly([(x - w / 2 - 0.03 * w, G - h * 0.9), (x, G - h * 1.18), (x + w / 2 + 0.03 * w, G - h * 0.9)], fill=roof, outline=INK, w=p.lw * 0.8)


def tent(p, x, G, w, col=(235, 225, 200), flag=RED):
    p.poly([(x - w, G), (x, G - w * 0.95), (x + w, G)], fill=col, outline=INK, w=p.lw * 0.8)
    p.poly([(x - w * 0.25, G), (x, G - w * 0.5), (x + w * 0.25, G)], fill=(90, 70, 55), outline=INK, w=p.lw * 0.5)
    p.line([(x, G - w * 0.95), (x, G - w * 1.3)], w=p.lw * 0.6)
    p.poly([(x, G - w * 1.3), (x + w * 0.4, G - w * 1.2), (x, G - w * 1.1)], fill=flag, outline=INK, w=p.lw * 0.5)


def gable_house(p, x, G, w, h, wall=(245, 235, 210), roof=(190, 80, 60), beams=True):
    p.rect(x - w / 2, G - h, x + w / 2, G, fill=wall, outline=INK, w=p.lw * 0.8)
    p.poly([(x - w * 0.6, G - h), (x, G - h - w * 0.45), (x + w * 0.6, G - h)], fill=roof, outline=INK, w=p.lw * 0.8)
    if beams:
        for k in (-0.25, 0.25):
            p.line([(x + k * w, G - h), (x + k * w, G)], w=p.lw * 0.6, color=(110, 75, 50))
        p.line([(x - w / 2, G - h * 0.5), (x + w / 2, G - h * 0.5)], w=p.lw * 0.6, color=(110, 75, 50))
    p.rect(x - w * 0.09, G - h * 0.42, x + w * 0.09, G, fill=(120, 80, 55), outline=INK, w=p.lw * 0.6)
    p.rect(x + w * 0.22, G - h * 0.85, x + w * 0.38, G - h * 0.6, fill=(255, 225, 140), outline=INK, w=p.lw * 0.6)


def pagoda_roof(p, x, y, w, col=(70, 80, 110)):
    p.poly([(x - w * 0.62, y + 0.1 * w), (x - w * 0.45, y), (x + w * 0.45, y), (x + w * 0.62, y + 0.1 * w),
            (x + w * 0.5, y + 0.14 * w), (x - w * 0.5, y + 0.14 * w)], fill=col, outline=INK, w=p.lw * 0.8)


def lantern(p, x, y, r, col=RED):
    p.line([(x, y - r * 1.6), (x, y - r)], w=p.lw * 0.4)
    p.ellipse(x, y, r * 0.8, r, fill=col, outline=INK, w=p.lw * 0.6)
    p.line([(x - r * 0.5, y - r * 0.5), (x + r * 0.5, y - r * 0.5)], w=p.lw * 0.3)
    p.line([(x - r * 0.5, y + r * 0.5), (x + r * 0.5, y + r * 0.5)], w=p.lw * 0.3)


def wave_band(p, W, y0, y1, col):
    p.rect(-5, y0, W + 5, y1, fill=col, outline=None, wob=False)
    n = 14
    for k in range(n):
        x = (k + 0.5) * W / n
        for j, yy in enumerate((y0 + (y1 - y0) * 0.3, y0 + (y1 - y0) * 0.65)):
            xx = x + (j * 0.5) * W / n
            p.line([(xx - 0.02 * W, yy), (xx, yy - 0.012 * W), (xx + 0.02 * W, yy)], w=p.lw * 0.45, color=(255, 255, 255))


def ship(p, x, y, s, sail=(250, 245, 230), hull=(120, 80, 50), masts=1):
    p.poly([(x - s, y), (x + s, y), (x + 0.75 * s, y + 0.3 * s), (x - 0.75 * s, y + 0.3 * s)], fill=hull, outline=INK, w=p.lw * 0.8)
    for m in range(masts):
        mx = x + (m - (masts - 1) / 2) * s * 0.8
        p.line([(mx, y), (mx, y - 1.4 * s)], w=p.lw * 0.8, color=INK)
        p.poly([(mx - 0.4 * s, y - 1.3 * s), (mx + 0.4 * s, y - 1.3 * s), (mx + 0.35 * s, y - 0.3 * s), (mx - 0.35 * s, y - 0.3 * s)],
               fill=sail, outline=INK, w=p.lw * 0.7)


def longship(p, x, y, s):
    p.poly([(x - 1.3 * s, y - 0.35 * s), (x - 1.0 * s, y), (x + 1.0 * s, y), (x + 1.3 * s, y - 0.35 * s),
            (x + 0.8 * s, y + 0.25 * s), (x - 0.8 * s, y + 0.25 * s)], fill=(140, 95, 55), outline=INK, w=p.lw * 0.8)
    p.line([(x, y), (x, y - 1.2 * s)], w=p.lw * 0.8)
    p.poly([(x - 0.5 * s, y - 1.1 * s), (x + 0.5 * s, y - 1.1 * s), (x + 0.5 * s, y - 0.2 * s), (x - 0.5 * s, y - 0.2 * s)],
           fill=(240, 235, 220), outline=INK, w=p.lw * 0.7)
    for k in range(3):
        p.line([(x - 0.5 * s + k * 0.5 * s, y - 1.1 * s), (x - 0.5 * s + k * 0.5 * s, y - 0.2 * s)], w=p.lw * 0.5, color=RED)


def pyramid(p, x, G, w, h, col=(235, 200, 130)):
    p.poly([(x - w / 2, G), (x, G - h), (x + w / 2, G)], fill=col, outline=INK, w=p.lw * 0.8)
    p.poly([(x, G - h), (x + w / 2, G), (x + w * 0.05, G)], fill=_shade(col, 0.86), outline=INK, w=p.lw * 0.6)


def dune(p, W, G, col, amp, ph):
    pts = [(-5, G)] + [(k * W / 30, G - amp * G * (1 + math.sin(k * 0.35 + ph)) / 2) for k in range(-1, 32)] + [(W + 5, G)]
    p.poly(pts, fill=col, outline=INK, w=p.lw * 0.6)


def stars(p, W, G, n=70):
    rng = np.random.default_rng(5)
    for _ in range(n):
        x, y, r = rng.random() * W, rng.random() * G * 0.95, 1.0 + rng.random() * 2.0
        p.circle(x, y, r, fill=(255, 255, 230), outline=None, wob=False)


# ---------------------------------------------------------------- settings
def _edo(p, W, G):
    mountains(p, W, G, (110, 140, 190), n=1, hmax=0.34, snow=True)
    for x in (0.12, 0.88):
        blossom(p, x * W, G, 0.42 * G)
    for i, x in enumerate((0.1, 0.3, 0.7, 0.9)):
        w, h = 0.19 * W, 0.2 * G
        gable_house(p, x * W, G, w, h, wall=(240, 225, 195), roof=(70, 80, 110), beams=False)
        p.rect(x * W - w * 0.4, G - h * 0.8, x * W + w * 0.4, G - h * 0.3, fill=(250, 240, 215), outline=INK, w=p.lw * 0.6)
        pagoda_roof(p, x * W, G - h * 1.02, w * 1.1)
        lantern(p, x * W + (0.34 if i % 2 else -0.34) * w, G - h * 0.55, 0.035 * G)
    for x in (0.38, 0.62):
        lantern(p, x * W, 0.34 * G, 0.05 * G)
    p.line([(0.3 * W, 0.25 * G), (0.7 * W, 0.25 * G)], w=p.lw * 0.4)


def _egypt(p, W, G):
    sun(p, 0.82 * W, 0.2 * G, 0.1 * G, (255, 190, 80))
    pyramid(p, 0.12 * W, G, 0.28 * W, 0.4 * G)
    pyramid(p, 0.28 * W, G, 0.16 * W, 0.24 * G)
    for x in (0.38, 0.62):
        p.poly([(x * W - 0.1 * W, G), (x * W - 0.075 * W, G - 0.55 * G), (x * W + 0.075 * W, G - 0.55 * G), (x * W + 0.1 * W, G)],
               fill=(225, 190, 130), outline=INK, w=p.lw * 0.8)
        for k in range(4):
            p.line([(x * W - 0.04 * W, G - (0.12 + 0.1 * k) * G), (x * W + 0.04 * W, G - (0.12 + 0.1 * k) * G)], w=p.lw * 0.4, color=(60, 100, 170))
    p.rect(0.38 * W + 0.1 * W - 2, G - 0.3 * G, 0.62 * W - 0.1 * W + 2, G, fill=(30, 25, 25), outline=INK, w=p.lw * 0.8)
    for x in (0.9, 0.07):
        palm(p, x * W, G, 0.55 * G)


def _roman(p, W, G):
    temple(p, 0.5 * W, G, 0.34 * W, 0.62 * G, roof=(200, 90, 70), n=6)
    for x in (0.1, 0.9):
        pine(p, x * W, G, 0.5 * G, col=(60, 120, 70))


def _medieval(p, W, G):
    hills(p, W, G, (150, 190, 110), amp=0.18, base=0.18)
    p.rect(0.4 * W, G - 0.62 * G, 0.6 * W, G - 0.2 * G, fill=(190, 185, 175), outline=INK, w=p.lw * 0.8)
    for x in (0.4, 0.5, 0.6):
        p.rect(x * W - 0.02 * W, G - 0.7 * G, x * W + 0.02 * W, G - 0.62 * G, fill=(190, 185, 175), outline=INK, w=p.lw * 0.7)
    p.poly([(0.47 * W, G - 0.62 * G), (0.5 * W, G - 0.82 * G), (0.53 * W, G - 0.62 * G)], fill=(190, 70, 60), outline=INK, w=p.lw * 0.7)
    for i, x in enumerate((0.08, 0.23, 0.78, 0.92)):
        gable_house(p, x * W, G, 0.13 * W, (0.24 + 0.05 * (i % 2)) * G)
    for x in (0.34, 0.68):
        tree(p, x * W, G, 0.4 * G)


def _viking(p, W, G):
    mountains(p, W, G, (110, 130, 150), n=3, hmax=0.4, snow=True)
    wave_band(p, W, 0.62 * G, G, (70, 130, 175))
    longship(p, 0.78 * W, 0.78 * G, 0.1 * G)
    p.poly([(0.0, G), (0.0, 0.8 * G), (0.3 * W, G)], fill=(120, 150, 110), outline=None, wob=False)
    p.poly([(0.05 * W, G - 0.05 * G), (0.08 * W, G - 0.2 * G), (0.24 * W, G - 0.2 * G), (0.27 * W, G - 0.05 * G)],
           fill=(110, 140, 85), outline=INK, w=p.lw * 0.8)
    p.rect(0.1 * W, G - 0.12 * G, 0.14 * W, G - 0.05 * G, fill=(90, 60, 40), outline=INK, w=p.lw * 0.6)
    for x in (0.34, 0.4):
        pine(p, x * W, G, 0.4 * G)


def _greek(p, W, G):
    sun(p, 0.85 * W, 0.2 * G, 0.08 * G)
    wave_band(p, W, 0.7 * G, G, (70, 150, 210))
    hills(p, W, 0.78 * G, (205, 190, 150), amp=0.3, base=0.0)
    temple(p, 0.5 * W, 0.62 * G, 0.3 * W, 0.4 * G, n=7)
    for x in (0.08, 0.2, 0.9):
        tree(p, x * W, G, 0.38 * G, leaf=(130, 150, 80))


def _china(p, W, G):
    mountains(p, W, G, (150, 175, 190), n=3, hmax=0.4, seed=1)
    cx = 0.5 * W
    p.rect(cx - 0.25 * W, G - 0.12 * G, cx + 0.25 * W, G, fill=(185, 175, 165), outline=INK, w=p.lw * 0.8)
    for k in range(5):
        x = cx - 0.2 * W + k * 0.1 * W
        p.rect(x - 0.012 * W, G - 0.5 * G, x + 0.012 * W, G - 0.12 * G, fill=(190, 45, 35), outline=INK, w=p.lw * 0.6)
    p.rect(cx - 0.25 * W, G - 0.58 * G, cx + 0.25 * W, G - 0.5 * G, fill=(190, 45, 35), outline=INK, w=p.lw * 0.7)
    for y, w in ((0.62, 0.34), (0.76, 0.24)):
        p.poly([(cx - w * W, G - (y - 0.04) * G), (cx - 0.65 * w * W, G - (y + 0.12) * G), (cx + 0.65 * w * W, G - (y + 0.12) * G),
                (cx + w * W, G - (y - 0.04) * G)], fill=(235, 180, 50), outline=INK, w=p.lw * 0.8)
    for x in (0.08, 0.92):
        lantern(p, x * W, 0.3 * G, 0.07 * G)


def _desert(p, W, G):
    sun(p, 0.8 * W, 0.22 * G, 0.1 * G, (255, 200, 90))
    dune(p, W, G, (240, 205, 140), 0.25, 0.5)
    dune(p, W, G, (225, 185, 120), 0.14, 2.0)
    for x in (0.2, 0.32):  # camels
        y = G - 0.06 * G
        p.ellipse(x * W, y - 0.1 * G, 0.045 * W, 0.045 * G, fill=(190, 140, 85), outline=INK, w=p.lw * 0.7)
        p.circle(x * W - 0.01 * W, y - 0.17 * G, 0.014 * W, fill=(190, 140, 85), outline=INK, w=p.lw * 0.6)
        p.circle(x * W + 0.012 * W, y - 0.17 * G, 0.014 * W, fill=(190, 140, 85), outline=INK, w=p.lw * 0.6)
        p.line([(x * W - 0.03 * W, y - 0.07 * G), (x * W - 0.03 * W, y + 0.04 * G)], w=p.lw * 0.8)
        p.line([(x * W + 0.03 * W, y - 0.07 * G), (x * W + 0.03 * W, y + 0.04 * G)], w=p.lw * 0.8)
        p.line([(x * W - 0.04 * W, y - 0.13 * G), (x * W - 0.07 * W, y - 0.22 * G)], w=p.lw * 0.7)
    palm(p, 0.9 * W, G, 0.55 * G)


def _ship(p, W, G):
    wave_band(p, W, 0.45 * G, G, (60, 125, 185))
    ship(p, 0.8 * W, 0.58 * G, 0.07 * G, masts=2)
    sun(p, 0.9 * W, 0.2 * G, 0.07 * G)
    # deck: ground is planks, with a mast + sail behind the actors
    p.line([(0.5 * W, G), (0.5 * W, 0.08 * G)], w=p.lw * 1.4, color=(110, 75, 50))
    p.poly([(0.5 * W + 4, 0.14 * G), (0.72 * W, 0.2 * G), (0.7 * W, 0.62 * G), (0.5 * W + 4, 0.66 * G)], fill=(250, 245, 230), outline=INK, w=p.lw * 0.8)
    p.poly([(0.5 * W - 4, 0.14 * G), (0.3 * W, 0.2 * G), (0.32 * W, 0.62 * G), (0.5 * W - 4, 0.66 * G)], fill=(245, 238, 220), outline=INK, w=p.lw * 0.8)
    p.rect(-5, G - 0.14 * G, W + 5, G, fill=(150, 105, 65), outline=INK, w=p.lw * 0.8)


def _west(p, W, G):
    sun(p, 0.5 * W, 0.45 * G, 0.14 * G, (255, 235, 150))
    for x, w, h in ((0.12, 0.2, 0.42), (0.85, 0.28, 0.5)):
        p.poly([(x * W - w * W / 2, G), (x * W - w * W * 0.35, G - h * G), (x * W + w * W * 0.35, G - h * G), (x * W + w * W / 2, G)],
               fill=(200, 105, 70), outline=INK, w=p.lw * 0.8)
    for i, x in enumerate((0.25, 0.4, 0.6, 0.75)):
        h = (0.38 + 0.08 * (i % 2)) * G
        p.rect(x * W - 0.07 * W, G - h, x * W + 0.07 * W, G, fill=(170, 120, 80), outline=INK, w=p.lw * 0.8)
        p.rect(x * W - 0.05 * W, G - h * 0.7, x * W - 0.01 * W, G - h * 0.4, fill=(255, 225, 140), outline=INK, w=p.lw * 0.6)
        p.line([(x * W - 0.07 * W, G - h), (x * W + 0.07 * W, G - h)], w=p.lw * 0.9)


def _london(p, W, G):
    for k in range(9):
        x = (0.02 + k * 0.115) * W
        h = (0.3 + 0.12 * ((k * 5) % 3)) * G
        p.rect(x, G - h, x + 0.1 * W, G, fill=(165, 85, 70), outline=INK, w=p.lw * 0.7)
        p.rect(x + 0.02 * W, G - h - 0.08 * G, x + 0.035 * W, G - h, fill=(120, 70, 60), outline=INK, w=p.lw * 0.6)
        for j in range(2):
            p.rect(x + 0.02 * W + j * 0.04 * W, G - h * 0.75, x + 0.045 * W + j * 0.04 * W, G - h * 0.5, fill=(255, 225, 140), outline=INK, w=p.lw * 0.5)
    p.rect(0.46 * W, G - 0.78 * G, 0.54 * W, G, fill=(205, 185, 140), outline=INK, w=p.lw * 0.8)
    p.poly([(0.45 * W, G - 0.78 * G), (0.5 * W, G - 0.98 * G), (0.55 * W, G - 0.78 * G)], fill=(90, 110, 120), outline=INK, w=p.lw * 0.8)
    p.circle(0.5 * W, G - 0.66 * G, 0.028 * W, fill=(255, 250, 230), outline=INK, w=p.lw * 0.6)
    for x in (0.3, 0.7):
        p.line([(x * W, G), (x * W, G - 0.3 * G)], w=p.lw * 0.9)
        p.circle(x * W, G - 0.32 * G, 0.02 * G, fill=(255, 230, 130), outline=INK, w=p.lw * 0.6)


def _cave(p, W, G):
    rng = np.random.default_rng(3)
    for k in range(14):
        x = (k + 0.5) * W / 14
        h = (0.1 + 0.18 * rng.random()) * G
        p.poly([(x - 0.03 * W, -5), (x, h), (x + 0.03 * W, -5)], fill=(85, 58, 42), outline=INK, w=p.lw * 0.7)
    for x, y, c in ((0.2, 0.4, (210, 120, 80)), (0.75, 0.35, (230, 200, 120))):  # cave paintings
        p.ellipse(x * W, y * G, 0.05 * W, 0.07 * G, fill=c, outline=INK, w=p.lw * 0.6)
        p.circle(x * W + 0.055 * W, y * G - 0.04 * G, 0.02 * W, fill=c, outline=INK, w=p.lw * 0.6)
    fx, fy = 0.5 * W, G
    p.poly([(fx - 0.03 * W, fy), (fx - 0.015 * W, fy - 0.12 * G), (fx, fy - 0.07 * G), (fx + 0.015 * W, fy - 0.15 * G), (fx + 0.03 * W, fy)],
           fill=(255, 170, 40), outline=INK, w=p.lw * 0.7)
    p.line([(fx - 0.04 * W, fy), (fx + 0.04 * W, fy - 0.01 * G)], w=p.lw * 1.2, color=(110, 75, 50))


def _steppe(p, W, G):
    mountains(p, W, G, (130, 160, 190), n=4, hmax=0.25, seed=2, snow=True)
    hills(p, W, G, (155, 195, 105), amp=0.08, base=0.0)
    for x in (0.12, 0.3, 0.82):
        w = 0.07 * W
        p.rect(x * W - w, G - 0.14 * G, x * W + w, G, fill=(250, 245, 235), outline=INK, w=p.lw * 0.7)
        p.poly([(x * W - w * 1.1, G - 0.14 * G), (x * W, G - 0.34 * G), (x * W + w * 1.1, G - 0.14 * G)], fill=(250, 245, 235), outline=INK, w=p.lw * 0.7)
        p.rect(x * W - w, G - 0.08 * G, x * W + w, G - 0.05 * G, fill=RED, outline=None, wob=False)
    cloud(p, 0.6 * W, 0.2 * G, 0.04 * G)


def _jungle(p, W, G):
    for k in range(5):
        w = (0.4 - 0.065 * k) * W * 0.8
        p.rect(0.5 * W - w / 2, G - (k + 1) * 0.1 * G, 0.5 * W + w / 2, G - k * 0.1 * G, fill=(185, 180, 160), outline=INK, w=p.lw * 0.8)
    p.rect(0.5 * W - 0.05 * W, G - 0.66 * G, 0.5 * W + 0.05 * W, G - 0.5 * G, fill=(160, 155, 135), outline=INK, w=p.lw * 0.8)
    p.rect(0.5 * W - 0.015 * W, G - 0.6 * G, 0.5 * W + 0.015 * W, G - 0.5 * G, fill=(40, 40, 40), outline=INK, w=p.lw * 0.5)
    for x in (0.06, 0.16, 0.84, 0.94):
        tree(p, x * W, G, 0.6 * G, leaf=(50, 130, 70))
    for x in (0.12, 0.88):
        palm(p, x * W, G, 0.6 * G)


def _battle(p, W, G):
    hills(p, W, G, (155, 165, 100), amp=0.15, base=0.1)
    for x, c in ((0.15, RED), (0.3, RED), (0.72, (60, 90, 170)), (0.88, (60, 90, 170))):
        tent(p, x * W, G, 0.055 * W, flag=c)
    for x in (0.45, 0.55):
        cloud(p, x * W, 0.45 * G, 0.04 * G)


def _harbor(p, W, G):
    wave_band(p, W, 0.5 * G, G, (70, 130, 185))
    for x, s in ((0.2, 0.06), (0.45, 0.08), (0.7, 0.055)):
        ship(p, x * W, 0.62 * G, s * G, masts=2)
    for x, h in ((0.06, 0.3), (0.94, 0.34)):
        gable_house(p, x * W, G, 0.15 * W, h * G, wall=(235, 215, 180), roof=(150, 90, 70))
    p.rect(-5, G - 0.08 * G, W + 5, G, fill=(160, 120, 80), outline=INK, w=p.lw * 0.8)


def _moon(p, W, G):
    stars(p, W, G)
    p.circle(0.8 * W, 0.28 * G, 0.12 * G, fill=(70, 130, 215), outline=INK, w=p.lw * 0.8)
    p.poly([(0.77 * W, 0.2 * G), (0.82 * W, 0.18 * G), (0.84 * W, 0.28 * G), (0.78 * W, 0.3 * G)], fill=(80, 170, 100), outline=None, wob=False)
    for x, r in ((0.2, 0.05), (0.55, 0.035), (0.85, 0.05)):
        p.ellipse(x * W, 1.05 * G, r * W, 0.02 * G, fill=(150, 150, 155), outline=INK, w=p.lw * 0.5)


def _snow(p, W, G):
    mountains(p, W, G, (190, 205, 225), n=4, hmax=0.35, snow=True)
    for x in (0.06, 0.15, 0.85, 0.94, 0.3, 0.7):
        pine(p, x * W, G, (0.55 if x < 0.2 or x > 0.8 else 0.35) * G, snow=True)


BUILD = {"edo_street": _edo, "egypt_temple": _egypt, "roman_forum": _roman, "medieval_town": _medieval,
         "viking_coast": _viking, "greek_agora": _greek, "china_palace": _china, "desert": _desert,
         "ship_sea": _ship, "old_west": _west, "london": _london, "cave": _cave, "steppe": _steppe,
         "jungle_temple": _jungle, "battlefield": _battle, "harbor": _harbor, "moon": _moon, "snow": _snow}


def make_backdrop(W, H, S, setting, L):
    setting = setting if setting in SETTINGS else "medieval_town"
    top, hor, gcol = SETTINGS[setting]
    G = L["ground"]
    img = _sky(W, H, S, top, hor, G)
    p = Pen(img, S, seed=3, lw=L["line_w"])
    if setting not in ("moon", "cave", "london"):
        cloud(p, 0.56 * W, 0.2 * G, 0.045 * G)
        cloud(p, 0.93 * W, 0.1 * G, 0.035 * G)
    BUILD[setting](p, W, G)
    # ground band + line
    p.rect(-5, G, W + 5, H + 5, fill=gcol, outline=None, wob=False)
    p.line([(-5, G), (W + 5, G)], w=L["line_w"] * 0.9, color=INK)
    rng = np.random.default_rng(11)
    for _ in range(26):  # a few ground tufts / stones
        x, y = rng.random() * W, G + (0.05 + 0.5 * rng.random()) * (H - G)
        p.line([(x - 7, y), (x + 7, y + 1.5)], w=L["line_w"] * 0.35, color=_shade(gcol, 0.8))
    return img
