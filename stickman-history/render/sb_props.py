"""Storybook props for the story pipeline (same look as sb_draw / sb_scenes). Pure code, no images.

draw_prop(c, kind, x, y, s, t): `y` is the ground line for BASE props and the centre for ICON props.
"""
import math

from sb_draw import INK, GOLD, GOLD_SH, mix, shade_of
from sb_scenes import cloud, tree_round, pine

BASE = {"tree", "house", "town", "castle", "ship", "flag", "stack", "press", "coins", "mountain", "crowd"}
SKY_ICON = {"sun": 250, "cloud": 190, "crown": 330, "bulb": 360, "clock": 380, "gear": 380, "arrow": 400}  # default centre y
FLOAT = {"scroll", "book", "map", "pages", "quill", "crown", "bulb", "clock", "gear", "arrow"}


def default_y(kind):
    return SKY_ICON.get(kind, 380)


def _icon_shadow(c, x, y, s):
    c.glow(x, y, 120 * s, (255, 244, 214), .35)


def draw_prop(c, kind, x, y, s, t=0.0):
    if kind in FLOAT:
        y = y + math.sin(t * 2.1 + x) * 6
        _icon_shadow(c, x, y, s)
    u = s
    if kind == "sun":
        c.glow(x, y, 190 * u, (255, 220, 140), .5)
        for i in range(10):
            a = i * math.pi / 5 + t * .15
            c.line([(x + math.cos(a) * 76 * u, y + math.sin(a) * 76 * u), (x + math.cos(a) * 100 * u, y + math.sin(a) * 100 * u)], (240, 190, 90), 6)
        c.cel_circle(x, y, 60 * u, (252, 214, 118), (232, 180, 84), w=3.4)
    elif kind == "cloud":
        cloud(c, x, y, 52 * u)
    elif kind == "tree":
        tree_round(c, x, y, 300 * u, (118, 156, 108))
    elif kind == "house":
        w, h = 150 * u, 110 * u
        c.cel([(x - w / 2, y - h), (x + w / 2, y - h), (x + w / 2, y), (x - w / 2, y)], (238, 220, 190), (208, 188, 160), w=3)
        c.cel([(x - w * .62, y - h + 4), (x, y - h - 80 * u), (x + w * .62, y - h + 4)], (176, 98, 84), (146, 76, 66), w=3.2)
        c.cel([(x - 18 * u, y - 70 * u), (x + 18 * u, y - 70 * u), (x + 18 * u, y), (x - 18 * u, y)], (150, 108, 80), (120, 84, 62), w=2.6)
        c.rect(x + 34 * u, y - 86 * u, x + 58 * u, y - 58 * u, fill=(186, 214, 228), w=2.4)
    elif kind == "town":
        for i, (dx, hh) in enumerate(((-120, 120), (-40, 160), (50, 130), (130, 100))):
            w = 80 * u
            col = [(238, 220, 190), (226, 206, 190), (232, 222, 200), (240, 214, 186)][i]
            c.cel([(x + dx * u - w / 2, y - hh * u), (x + dx * u + w / 2, y - hh * u), (x + dx * u + w / 2, y), (x + dx * u - w / 2, y)], col, shade_of(col, .88), w=2.8)
            c.cel([(x + dx * u - w * .62, y - hh * u + 3), (x + dx * u, y - hh * u - 50 * u), (x + dx * u + w * .62, y - hh * u + 3)], (170, 96, 84), (140, 74, 66), w=3)
            c.rect(x + dx * u - 10 * u, y - hh * u * .55, x + dx * u + 10 * u, y - hh * u * .3, fill=(186, 214, 228), w=2)
    elif kind == "castle":
        w, h = 240 * u, 170 * u
        c.cel([(x - w / 2, y - h), (x + w / 2, y - h), (x + w / 2, y), (x - w / 2, y)], (206, 200, 196), (176, 170, 170), w=3)
        for i in range(6):
            c.rect(x - w / 2 + i * w / 6 + 4, y - h - 22 * u, x - w / 2 + i * w / 6 + w / 12 + 4, y - h, fill=(206, 200, 196), w=2.4)
        for sd in (-1, 1):
            tx = x + sd * w * .5
            c.cel([(tx - 34 * u, y - h - 60 * u), (tx + 34 * u, y - h - 60 * u), (tx + 34 * u, y), (tx - 34 * u, y)], (214, 208, 204), (184, 178, 176), w=3)
            c.cel([(tx - 44 * u, y - h - 58 * u), (tx, y - h - 150 * u), (tx + 44 * u, y - h - 58 * u)], (176, 84, 84), (146, 64, 68), w=3)
        c.poly([(x - 28 * u, y), (x - 28 * u, y - 70 * u)] + [(x + 28 * u * math.cos(math.radians(a)), y - 70 * u - 28 * u * math.sin(math.radians(a))) for a in range(180, -1, -20)] + [(x + 28 * u, y)],
               fill=(86, 66, 66), w=2.6)
    elif kind == "ship":
        c.cel([(x - 120 * u, y - 60 * u), (x + 120 * u, y - 60 * u), (x + 90 * u, y), (x - 90 * u, y)], (150, 108, 80), (120, 84, 62), w=3.2)
        c.line([(x, y - 60 * u), (x, y - 290 * u)], (130, 96, 70), 8)
        c.cel([(x + 6, y - 270 * u), (x + 110 * u, y - 160 * u), (x + 6, y - 80 * u)], (246, 238, 220), (218, 206, 184), w=3)
        c.cel([(x - 6, y - 250 * u), (x - 86 * u, y - 150 * u), (x - 6, y - 90 * u)], (240, 230, 208), (212, 200, 176), w=3)
        c.cel([(x, y - 290 * u), (x + 40 * u, y - 280 * u), (x, y - 266 * u)], (190, 70, 70), (156, 52, 56), w=2.4)
    elif kind == "flag":
        c.line([(x, y), (x, y - 260 * u)], (130, 96, 70), 8)
        c.cel([(x, y - 260 * u), (x + 130 * u, y - 240 * u + math.sin(t * 3) * 8 * u), (x, y - 170 * u)], (190, 70, 70), (156, 52, 56), w=3)
        c.circle(x + 48 * u, y - 215 * u, 14 * u, fill=GOLD, w=2.2)
    elif kind == "stack":
        for j in range(5):
            c.cel([(x - 70 * u, y - j * 26 * u), (x + 70 * u, y - j * 26 * u), (x + 76 * u, y - 20 * u - j * 26 * u), (x - 64 * u, y - 20 * u - j * 26 * u)],
                  (248, 242, 228), (222, 214, 200), w=2.6)
    elif kind == "press":
        c.cel([(x - 80 * u, y), (x - 50 * u, y), (x - 50 * u, y - 200 * u), (x - 80 * u, y - 200 * u)], (142, 104, 78), (114, 82, 62), w=3)
        c.cel([(x + 50 * u, y), (x + 80 * u, y), (x + 80 * u, y - 200 * u), (x + 50 * u, y - 200 * u)], (142, 104, 78), (114, 82, 62), w=3)
        c.cel([(x - 90 * u, y - 200 * u), (x + 90 * u, y - 200 * u), (x + 90 * u, y - 230 * u), (x - 90 * u, y - 230 * u)], (156, 116, 86), (124, 90, 68), w=3)
        c.line([(x, y - 230 * u), (x, y - 300 * u)], (96, 80, 80), 12)
        c.line([(x - 70 * u, y - 304 * u), (x + 70 * u, y - 304 * u)], (156, 116, 86), 9)
        c.cel([(x - 60 * u, y - 40 * u), (x + 60 * u, y - 40 * u), (x + 60 * u, y), (x - 60 * u, y)], (96, 80, 80), (72, 60, 64), w=3)
    elif kind == "coins":
        for i, (dx, r) in enumerate(((-34, 1), (30, 1), (0, 1.1))):
            for j in range(3 - i % 2):
                c.ellipse(x + dx * u, y - 12 * u - j * 12 * u, 36 * u, 12 * u, fill=GOLD, w=2.6)
    elif kind == "mountain":
        c.cel([(x - 190 * u, y), (x - 20 * u, y - 280 * u), (x + 30 * u, y - 250 * u), (x + 200 * u, y)], (160, 170, 190), (132, 142, 168), w=3)
        c.cel([(x - 62 * u, y - 210 * u), (x - 20 * u, y - 280 * u), (x + 30 * u, y - 250 * u), (x + 6 * u, y - 226 * u), (x - 20 * u, y - 236 * u)], (248, 246, 248), (222, 222, 236), w=2.4)
    elif kind == "crowd":
        for i, dx in enumerate((-110, -55, 0, 55, 110)):
            hh = 120 * u * (0.9 + 0.1 * (i % 2))
            col = [(178, 98, 84), (96, 130, 150), (200, 170, 100), (130, 150, 110), (150, 110, 140)][i]
            c.cel([(x + dx * u - 20 * u, y - hh * .62), (x + dx * u + 20 * u, y - hh * .62), (x + dx * u + 24 * u, y), (x + dx * u - 24 * u, y)], col, shade_of(col, .82), w=2.6)
            c.cel_circle(x + dx * u, y - hh * .82, 18 * u, (251, 244, 232), (232, 219, 202), w=2.6)
    elif kind == "crown":
        c.cel([(x - 62 * u, y + 30 * u), (x - 70 * u, y - 40 * u), (x - 34 * u, y - 4 * u), (x, y - 56 * u), (x + 34 * u, y - 4 * u), (x + 70 * u, y - 40 * u), (x + 62 * u, y + 30 * u)], GOLD, GOLD_SH, w=3.4)
        c.circle(x, y + 8 * u, 9 * u, fill=(176, 70, 78), w=2.4)
    elif kind in ("scroll", "pages", "quill"):
        if kind == "quill":
            c.line([(x - 50 * u, y + 70 * u), (x + 40 * u, y - 60 * u)], (120, 96, 80), 6)
            c.cel([(x + 40 * u, y - 60 * u), (x + 84 * u, y - 70 * u), (x + 56 * u, y - 4 * u)], (244, 238, 226), (216, 208, 196), w=3)
        elif kind == "pages":
            for j in range(3):
                c.cel([(x - 48 * u + j * 14, y - 64 * u - j * 8), (x + 48 * u + j * 14, y - 64 * u - j * 8), (x + 48 * u + j * 14, y + 56 * u - j * 8), (x - 48 * u + j * 14, y + 56 * u - j * 8)],
                      (250, 246, 236), (224, 218, 204), w=2.8)
            for i in range(5):
                c.line([(x - 30 * u + 28, y - 36 * u + i * 20 * u - 16), (x + 30 * u + 28, y - 36 * u + i * 20 * u - 16)], (130, 120, 120), 2.4)
        else:
            c.rrect(x - 70 * u, y - 36 * u, x + 70 * u, y + 36 * u, 12 * u, fill=(244, 232, 204), w=3.2)
            c.ellipse(x - 70 * u, y, 10 * u, 36 * u, fill=(226, 208, 170), w=3)
            c.ellipse(x + 70 * u, y, 10 * u, 36 * u, fill=(226, 208, 170), w=3)
            for i in range(3):
                c.line([(x - 44 * u, y - 14 * u + i * 14 * u), (x + 44 * u, y - 14 * u + i * 14 * u)], (130, 110, 100), 2.4)
    elif kind == "book":
        c.cel([(x - 62 * u, y - 48 * u), (x + 62 * u, y - 48 * u), (x + 62 * u, y + 48 * u), (x - 62 * u, y + 48 * u)], (158, 82, 80), (126, 62, 64), w=3.4)
        c.line([(x - 44 * u, y - 48 * u), (x - 44 * u, y + 48 * u)], (226, 190, 120), 4)
        c.rrect(x - 22 * u, y - 20 * u, x + 36 * u, y + 2 * u, 5 * u, fill=(226, 190, 120), w=2.2)
    elif kind == "map":
        c.cel([(x - 80 * u, y - 52 * u), (x + 80 * u, y - 52 * u), (x + 80 * u, y + 52 * u), (x - 80 * u, y + 52 * u)], (240, 224, 188), (214, 194, 156), w=3.2)
        c.line([(x - 50 * u, y + 20 * u), (x - 10 * u, y - 10 * u), (x + 24 * u, y + 14 * u), (x + 56 * u, y - 24 * u)], (176, 82, 76), 3.4)
        c.line([(x + 50 * u, y - 34 * u), (x + 64 * u, y - 20 * u)], (176, 82, 76), 4)
        c.line([(x + 64 * u, y - 34 * u), (x + 50 * u, y - 20 * u)], (176, 82, 76), 4)
    elif kind == "bulb":
        c.glow(x, y, 120 * u, (255, 236, 150), .5)
        c.cel_circle(x, y, 44 * u, (255, 236, 150), (240, 206, 110), w=3.4)
        c.rect(x - 22 * u, y + 40 * u, x + 22 * u, y + 70 * u, fill=(176, 172, 176), w=3)
    elif kind == "clock":
        c.cel_circle(x, y, 64 * u, (250, 246, 236), (222, 214, 200), w=4)
        for i in range(12):
            a = i * math.pi / 6
            c.line([(x + math.cos(a) * 50 * u, y + math.sin(a) * 50 * u), (x + math.cos(a) * 58 * u, y + math.sin(a) * 58 * u)], INK, 3)
        a = t * 1.3
        c.line([(x, y), (x + math.cos(a) * 44 * u, y + math.sin(a) * 44 * u)], INK, 4)
        c.line([(x, y), (x + math.cos(a / 12) * 28 * u, y + math.sin(a / 12) * 28 * u)], INK, 5)
    elif kind == "gear":
        pts = []
        for i in range(24):
            a = i * math.pi / 12 + t * .4
            r = 66 * u if i % 2 == 0 else 50 * u
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        c.cel(pts, (176, 178, 190), (146, 148, 164), w=3.2)
        c.circle(x, y, 20 * u, fill=(226, 224, 218), w=3)
    elif kind == "arrow":
        c.cel([(x - 80 * u, y - 22 * u), (x + 20 * u, y - 22 * u), (x + 20 * u, y - 56 * u), (x + 84 * u, y), (x + 20 * u, y + 56 * u), (x + 20 * u, y + 22 * u), (x - 80 * u, y + 22 * u)],
              (200, 84, 76), (166, 62, 60), w=3.4)
