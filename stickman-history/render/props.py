"""Procedural props. Each prop is drawn from simple shapes, so nothing is downloaded or licensed.

Signature: fn(pen, cx, cy, u, t, c)
  u = size unit in pixels, t = scene time in seconds.
  anchor "base": (cx, cy) is the bottom centre (sits on the ground line).
  anchor "center": (cx, cy) is the middle of the prop (floats in the air).
"""
import math

from stage import (INK, RED, GOLD, GREEN, BLUE, BROWN, CREAM, STONE, GRAY, clamp)


def rot(pts, c, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def _blob(p, circles, fill):
    lw = p.lw
    for cx, cy, r in circles:
        p.circle(cx, cy, r + lw / 2, fill=INK, outline=None, wob=False)
    for cx, cy, r in circles:
        p.circle(cx, cy, max(1, r - lw / 2), fill=fill, outline=None, wob=False)


def _cloth(p, x, y, w, h, t, color):
    top = [(x + i / 8 * w, y + math.sin(t * 4 - i * 0.8) * 0.05 * w * (i / 8)) for i in range(9)]
    bot = [(px, py + h) for px, py in reversed(top)]
    p.poly(top + bot, fill=color, outline=INK, w=p.lw * 0.8)


def sun(p, cx, cy, u, t, c):
    r = 0.34 * u
    for k in range(10):
        a = k * 2 * math.pi / 10 + t * 0.35
        p.line([(cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35),
                (cx + math.cos(a) * r * 1.8, cy + math.sin(a) * r * 1.8)], w=p.lw * 0.9, color=GOLD)
    p.circle(cx, cy, r, fill=GOLD)


def cloud(p, cx, cy, u, t, c):
    cx += math.sin(t * 0.6) * 0.12 * u
    _blob(p, [(cx - 0.38 * u, cy + 0.04 * u, 0.2 * u), (cx - 0.1 * u, cy - 0.1 * u, 0.28 * u),
              (cx + 0.22 * u, cy - 0.02 * u, 0.24 * u), (cx + 0.46 * u, cy + 0.07 * u, 0.17 * u)], CREAM)


def tree(p, cx, cy, u, t, c):
    p.line([(cx, cy), (cx, cy - 0.55 * u)], w=p.lw * 2.4, color=BROWN)
    sw = math.sin(t * 1.5) * 0.03 * u
    _blob(p, [(cx + sw - 0.2 * u, cy - 0.8 * u, 0.26 * u), (cx + sw + 0.2 * u, cy - 0.82 * u, 0.26 * u),
              (cx + sw, cy - 1.05 * u, 0.3 * u)], GREEN)


def house(p, cx, cy, u, t, c):
    w, h = 0.42 * u, 0.55 * u
    p.rect(cx - w, cy - h, cx + w, cy, fill=CREAM)
    p.poly([(cx - w * 1.2, cy - h), (cx, cy - h - 0.42 * u), (cx + w * 1.2, cy - h)], fill=RED)
    p.rect(cx - 0.08 * u, cy - 0.3 * u, cx + 0.08 * u, cy, fill=BROWN)
    p.rect(cx + 0.17 * u, cy - 0.42 * u, cx + 0.32 * u, cy - 0.27 * u, fill=GOLD, w=p.lw * 0.7)


def town(p, cx, cy, u, t, c):
    for dx, s in [(-0.9, 0.8), (0.0, 1.0), (0.9, 0.7)]:
        house(p, cx + dx * u * 0.8, cy, u * s, t, c)


def castle(p, cx, cy, u, t, c):
    p.rect(cx - 0.7 * u, cy - 0.7 * u, cx + 0.7 * u, cy, fill=STONE)
    for k in range(4):
        x = cx - 0.7 * u + k * 0.4 * u
        p.rect(x, cy - 0.84 * u, x + 0.22 * u, cy - 0.7 * u, fill=STONE, w=p.lw * 0.8)
    for s in (-1, 1):
        tx = cx + s * 0.72 * u
        p.rect(tx - 0.2 * u, cy - 1.15 * u, tx + 0.2 * u, cy, fill=STONE)
        p.rect(tx - 0.2 * u, cy - 1.28 * u, tx - 0.05 * u, cy - 1.15 * u, fill=STONE, w=p.lw * 0.8)
        p.rect(tx + 0.05 * u, cy - 1.28 * u, tx + 0.2 * u, cy - 1.15 * u, fill=STONE, w=p.lw * 0.8)
    p.poly([(cx - 0.17 * u, cy), (cx - 0.17 * u, cy - 0.3 * u), (cx, cy - 0.46 * u),
            (cx + 0.17 * u, cy - 0.3 * u), (cx + 0.17 * u, cy)], fill=INK)
    p.line([(cx, cy - 0.84 * u), (cx, cy - 1.5 * u)], w=p.lw, color=BROWN)
    _cloth(p, cx, cy - 1.5 * u, 0.4 * u, 0.25 * u, t, RED)


def ship(p, cx, cy, u, t, c):
    a = math.sin(t * 1.8) * 0.05
    pivot = (cx, cy - 0.2 * u)
    hull = rot([(cx - 0.65 * u, cy - 0.38 * u), (cx + 0.65 * u, cy - 0.38 * u),
                (cx + 0.42 * u, cy - 0.08 * u), (cx - 0.42 * u, cy - 0.08 * u)], pivot, a)
    p.poly(hull, fill=BROWN)
    mast = rot([(cx, cy - 0.38 * u), (cx, cy - 1.45 * u)], pivot, a)
    p.line(mast, w=p.lw * 1.2, color=INK)
    sail = rot([(cx + 0.04 * u, cy - 1.4 * u), (cx + 0.6 * u, cy - 0.85 * u), (cx + 0.04 * u, cy - 0.5 * u)], pivot, a)
    p.poly(sail, fill=CREAM)
    pts = [(cx - 0.9 * u + k * 0.15 * u, cy - 0.04 * u + math.sin(t * 3 + k) * 0.03 * u) for k in range(13)]
    p.line(pts, w=p.lw * 0.9, color=BLUE)


def flag(p, cx, cy, u, t, c):
    p.line([(cx, cy), (cx, cy - 1.2 * u)], w=p.lw * 1.2, color=BROWN)
    _cloth(p, cx, cy - 1.2 * u, 0.7 * u, 0.45 * u, t, RED)


def crown(p, cx, cy, u, t, c):
    p.poly([(cx - 0.3 * u, cy + 0.15 * u), (cx - 0.3 * u, cy - 0.2 * u), (cx - 0.15 * u, cy - 0.02 * u),
            (cx, cy - 0.28 * u), (cx + 0.15 * u, cy - 0.02 * u), (cx + 0.3 * u, cy - 0.2 * u),
            (cx + 0.3 * u, cy + 0.15 * u)], fill=GOLD)


def scroll(p, cx, cy, u, t, c):
    cy += math.sin(t * 2) * 0.02 * u
    p.rect(cx - 0.42 * u, cy - 0.28 * u, cx + 0.42 * u, cy + 0.28 * u, fill=CREAM)
    for sx in (-1, 1):
        p.ellipse(cx + sx * 0.42 * u, cy, 0.07 * u, 0.3 * u, fill=STONE)
    for k in range(3):
        y = cy - 0.14 * u + k * 0.12 * u
        p.line([(cx - 0.3 * u, y), (cx + 0.3 * u * (1 - 0.2 * (k == 2)), y)], w=p.lw * 0.5, color=GRAY)
    p.circle(cx + 0.22 * u, cy + 0.2 * u, 0.07 * u, fill=RED, outline=None)


def book(p, cx, cy, u, t, c):
    cy += math.sin(t * 2) * 0.02 * u
    p.poly([(cx - 0.55 * u, cy - 0.3 * u), (cx, cy - 0.2 * u), (cx, cy + 0.3 * u), (cx - 0.55 * u, cy + 0.2 * u)], fill=CREAM)
    p.poly([(cx + 0.55 * u, cy - 0.3 * u), (cx, cy - 0.2 * u), (cx, cy + 0.3 * u), (cx + 0.55 * u, cy + 0.2 * u)], fill=CREAM)
    for k in range(3):
        d = k * 0.1 * u
        p.line([(cx - 0.45 * u, cy - 0.17 * u + d), (cx - 0.08 * u, cy - 0.1 * u + d)], w=p.lw * 0.45, color=GRAY)
        p.line([(cx + 0.45 * u, cy - 0.17 * u + d), (cx + 0.08 * u, cy - 0.1 * u + d)], w=p.lw * 0.45, color=GRAY)


def stack(p, cx, cy, u, t, c):
    specs = [(0.85, RED, 0.0), (0.72, BLUE, 0.04), (0.78, GREEN, -0.03), (0.6, BROWN, 0.05)]
    y = cy
    for w, col, off in specs:
        h = 0.17 * u
        p.rect(cx + off * u - w * u / 2, y - h, cx + off * u + w * u / 2, y, fill=col)
        p.line([(cx + off * u - w * u / 2 + 0.06 * u, y - h * 0.5), (cx + off * u + w * u / 2 - 0.06 * u, y - h * 0.5)],
               w=p.lw * 0.35, color=CREAM)
        y -= h


def press(p, cx, cy, u, t, c):
    a = t * 3
    p.rect(cx - 0.55 * u, cy - 0.2 * u, cx + 0.55 * u, cy, fill=BROWN)
    for s in (-1, 1):
        p.line([(cx + s * 0.4 * u, cy - 0.2 * u), (cx + s * 0.4 * u, cy - 1.15 * u)], w=p.lw * 2.0, color=BROWN)
    p.rect(cx - 0.5 * u, cy - 1.3 * u, cx + 0.5 * u, cy - 1.12 * u, fill=BROWN)
    plate_y = cy - 0.66 * u + 0.12 * u * (0.5 + 0.5 * math.sin(a))
    p.line([(cx, cy - 1.12 * u), (cx, plate_y)], w=p.lw * 1.4, color=INK)
    p.rect(cx - 0.3 * u, plate_y, cx + 0.3 * u, plate_y + 0.13 * u, fill=GRAY)
    lv = 0.5 * u * math.cos(a * 0.5)
    p.line([(cx - lv, cy - 1.4 * u), (cx + lv, cy - 1.4 * u)], w=p.lw * 1.2, color=INK)
    p.circle(cx - lv, cy - 1.4 * u, 0.05 * u, fill=INK, outline=None)
    p.circle(cx + lv, cy - 1.4 * u, 0.05 * u, fill=INK, outline=None)
    p.rect(cx - 0.27 * u, cy - 0.27 * u, cx + 0.27 * u, cy - 0.2 * u, fill=CREAM, w=p.lw * 0.6)


def coins(p, cx, cy, u, t, c):
    for off, n in [(-0.28, 3), (0.0, 5), (0.28, 2)]:
        for k in range(n):
            y = cy - 0.07 * u - k * 0.09 * u
            p.ellipse(cx + off * u, y, 0.14 * u, 0.055 * u, fill=GOLD, w=p.lw * 0.7)


def mountain(p, cx, cy, u, t, c):
    p.poly([(cx - 1.0 * u, cy), (cx - 0.35 * u, cy - 1.0 * u), (cx + 0.2 * u, cy)], fill=STONE)
    p.poly([(cx - 0.1 * u, cy), (cx + 0.5 * u, cy - 0.75 * u), (cx + 1.1 * u, cy)], fill=STONE)
    p.poly([(cx - 0.35 * u, cy - 1.0 * u), (cx - 0.5 * u, cy - 0.78 * u), (cx - 0.38 * u, cy - 0.82 * u),
            (cx - 0.28 * u, cy - 0.76 * u), (cx - 0.2 * u, cy - 0.8 * u)], fill=CREAM, w=p.lw * 0.7)


def map_(p, cx, cy, u, t, c):
    p.rect(cx - 0.6 * u, cy - 0.4 * u, cx + 0.6 * u, cy + 0.4 * u, fill=CREAM)
    p.poly([(cx - 0.5 * u, cy + 0.3 * u), (cx - 0.45 * u, cy - 0.1 * u), (cx - 0.2 * u, cy - 0.3 * u),
            (cx + 0.05 * u, cy - 0.15 * u), (cx + 0.3 * u, cy - 0.3 * u), (cx + 0.5 * u, cy - 0.1 * u),
            (cx + 0.45 * u, cy + 0.3 * u), (cx, cy + 0.2 * u)], fill=(198, 212, 164), outline=GREEN, w=p.lw * 0.6)
    route = [(cx - 0.4 * u, cy + 0.2 * u), (cx - 0.1 * u, cy - 0.12 * u), (cx + 0.15 * u, cy + 0.1 * u), (cx + 0.4 * u, cy - 0.17 * u)]
    prog = clamp(t * 0.5 % 1.6)
    for i in range(1, 25):
        f = i / 24
        if f > prog:
            break
        seg = min(2, int(f * 3))
        lf = f * 3 - seg
        x = route[seg][0] + (route[seg + 1][0] - route[seg][0]) * lf
        y = route[seg][1] + (route[seg + 1][1] - route[seg][1]) * lf
        p.circle(x, y, p.lw * 0.35, fill=RED, outline=None, wob=False)
    x, y, d = route[-1][0], route[-1][1], 0.07 * u
    p.line([(x - d, y - d), (x + d, y + d)], w=p.lw * 0.9, color=RED)
    p.line([(x - d, y + d), (x + d, y - d)], w=p.lw * 0.9, color=RED)


def bulb(p, cx, cy, u, t, c):
    r = 0.26 * u
    flick = 0.5 + 0.5 * math.sin(t * 6)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        if k % 2 == 0 or flick > 0.5:
            p.line([(cx + math.cos(a) * r * 1.4, cy - 0.05 * u + math.sin(a) * r * 1.4),
                    (cx + math.cos(a) * r * 1.8, cy - 0.05 * u + math.sin(a) * r * 1.8)], w=p.lw * 0.8, color=GOLD)
    p.circle(cx, cy - 0.05 * u, r, fill=(250, 226, 130))
    p.rect(cx - 0.1 * u, cy + 0.2 * u, cx + 0.1 * u, cy + 0.34 * u, fill=GRAY, w=p.lw * 0.7)


def clock(p, cx, cy, u, t, c):
    r = 0.34 * u
    p.circle(cx, cy, r, fill=CREAM)
    for k in range(12):
        a = k * math.pi / 6
        p.line([(cx + math.sin(a) * r * 0.82, cy - math.cos(a) * r * 0.82),
                (cx + math.sin(a) * r * 0.95, cy - math.cos(a) * r * 0.95)], w=p.lw * 0.5, color=INK)
    am, ah = t * 3.0, t * 0.25
    p.line([(cx, cy), (cx + math.sin(am) * r * 0.78, cy - math.cos(am) * r * 0.78)], w=p.lw * 0.7, color=INK)
    p.line([(cx, cy), (cx + math.sin(ah) * r * 0.5, cy - math.cos(ah) * r * 0.5)], w=p.lw, color=RED)


def gear(p, cx, cy, u, t, c):
    r = 0.28 * u
    for k in range(8):
        a = k * math.pi / 4 + t * 0.5
        tooth = [(cx + r * 0.9, cy - 0.07 * u), (cx + r * 1.3, cy - 0.07 * u), (cx + r * 1.3, cy + 0.07 * u), (cx + r * 0.9, cy + 0.07 * u)]
        p.poly(rot(tooth, (cx, cy), a), fill=GRAY, w=p.lw * 0.7, wob=False)
    p.circle(cx, cy, r, fill=GRAY, wob=False)
    p.circle(cx, cy, r * 0.35, fill=CREAM, w=p.lw * 0.7, wob=False)


def arrow(p, cx, cy, u, t, c):
    ang = math.radians((c or {}).get("dir", 0))
    pulse = math.sin(t * 4) * 0.05 * u
    a, b = (cx - 0.5 * u + pulse, cy), (cx + 0.5 * u + pulse, cy)
    head = [(b[0] + 0.12 * u, b[1]), (b[0] - 0.12 * u, b[1] - 0.16 * u), (b[0] - 0.12 * u, b[1] + 0.16 * u)]
    p.line(rot([a, b], (cx, cy), ang), w=p.lw * 1.6, color=RED)
    p.poly(rot(head, (cx, cy), ang), fill=RED, outline=RED, w=p.lw * 0.5)


def pages(p, cx, cy, u, t, c):
    for k in range(6):
        ph = (t * 0.35 + k / 6) % 1
        x = cx + (ph - 0.5) * 2.6 * u
        y = cy - math.sin(ph * math.pi) * 0.5 * u + math.sin(k * 2.3) * 0.12 * u
        s = math.sin(ph * math.pi) ** 0.5
        a = math.sin(t * 2 + k) * 0.3
        w, h = 0.17 * u * s, 0.22 * u * s
        sheet = rot([(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)], (x, y), a)
        p.poly(sheet, fill=CREAM, w=p.lw * 0.7)
        for j in range(3):
            q = rot([(x - w * 0.6, y - h * 0.5 + j * h * 0.45), (x + w * 0.6, y - h * 0.5 + j * h * 0.45)], (x, y), a)
            p.line(q, w=p.lw * 0.3, color=GRAY, wob=False)


def crowd(p, cx, cy, u, t, c):
    from rig import draw_stick
    cols = [INK, BLUE, RED, GREEN, BROWN]
    poses = ["cheer", "stand", "wave", "stand", "cheer"]
    for k in range(5):
        draw_stick(p, cx + (k - 2) * 0.38 * u, cy, u * (0.85 + 0.12 * (k % 2)), poses[k], t + k * 0.7,
                   face=-1 if k < 2 else 1, color=cols[k], lw=p.lw * 0.75)


def quill(p, cx, cy, u, t, c):
    p.line([(cx - 0.05 * u, cy + 0.05 * u), (cx + 0.18 * u, cy - 0.32 * u)], w=p.lw * 0.5, color=INK)
    p.poly([(cx + 0.08 * u, cy - 0.12 * u), (cx + 0.36 * u, cy - 0.5 * u), (cx + 0.2 * u, cy - 0.12 * u)],
           fill=CREAM, w=p.lw * 0.5)


# name -> (function, anchor, default y as a fraction of the frame height; None = on the ground)
PROPS = {
    "sun": (sun, "center", 0.20), "cloud": (cloud, "center", 0.17), "tree": (tree, "base", None),
    "house": (house, "base", None), "town": (town, "base", None), "castle": (castle, "base", None),
    "ship": (ship, "base", None), "flag": (flag, "base", None), "crown": (crown, "center", 0.40),
    "scroll": (scroll, "center", 0.45), "book": (book, "center", 0.45), "stack": (stack, "base", None),
    "press": (press, "base", None), "coins": (coins, "base", None), "mountain": (mountain, "base", None),
    "map": (map_, "center", 0.40), "bulb": (bulb, "center", 0.32), "clock": (clock, "center", 0.38),
    "gear": (gear, "center", 0.40), "arrow": (arrow, "center", 0.45), "pages": (pages, "center", 0.45),
    "crowd": (crowd, "base", None), "quill": (quill, "center", 0.45),
}
SKY = {"sun", "cloud", "mountain"}  # drawn behind the ground line


def draw_held(pen, kind, hx, hy, h, t):
    """Draw a prop in an actor's hand."""
    if kind not in PROPS:
        return
    fn, anchor, _ = PROPS[kind]
    u = h * 0.34
    fn(pen, hx, hy if anchor == "base" else hy - 0.04 * h, u, t, None)
