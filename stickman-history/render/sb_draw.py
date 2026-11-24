"""Storybook cartoon drawing kit (free, Pillow + numpy only).

Design space is 720x1280 (9:16). Everything is drawn at k pixels per design unit, with a margin around the
frame so the camera can push in and pan. Shapes get a soft "cel" shadow, bold organic outlines, muted colours.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
MX, MY = 90, 150  # margin around the frame, design units

INK = (52, 44, 48)
IVORY = (251, 244, 232)
IVORY_SH = (232, 219, 202)
CREAM = (246, 238, 222)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade_of(c, k=0.80):
    # shadow tone: darker and slightly warmer/purple, still muted
    return (int(c[0] * k), int(c[1] * k * 0.97), int(c[2] * k * 1.02 if k < 1 else c[2]))


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Ctx:
    def __init__(self, k, fill=None):
        self.k = k
        self.size = (int((W + 2 * MX) * k), int((H + 2 * MY) * k))
        self.img = Image.new("RGBA", self.size, fill or (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def P(self, x, y):
        return ((x + MX) * self.k, (y + MY) * self.k)

    # ---- plain shapes
    def poly(self, pts, fill=None, ink=INK, w=3.0):
        pp = [self.P(*p) for p in pts]
        if fill is not None:
            self.d.polygon(pp, fill=fill)
        if ink and w > 0:
            self.d.line(pp + [pp[0]], fill=ink, width=max(1, int(w * self.k)), joint="curve")
            r = w * self.k / 2
            for x, y in pp:
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=ink)

    def line(self, pts, color=INK, w=3.0):
        pp = [self.P(*p) for p in pts]
        self.d.line(pp, fill=color, width=max(1, int(w * self.k)), joint="curve")
        r = w * self.k / 2
        for x, y in (pp[0], pp[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def circle(self, cx, cy, r, fill=None, ink=INK, w=3.0):
        x, y = self.P(cx, cy)
        R = r * self.k
        self.d.ellipse((x - R, y - R, x + R, y + R), fill=fill, outline=ink if (ink and w > 0) else None,
                       width=max(1, int(w * self.k)))

    def ellipse(self, cx, cy, rx, ry, fill=None, ink=INK, w=3.0):
        x, y = self.P(cx, cy)
        self.d.ellipse((x - rx * self.k, y - ry * self.k, x + rx * self.k, y + ry * self.k), fill=fill,
                       outline=ink if (ink and w > 0) else None, width=max(1, int(w * self.k)))

    def rect(self, x0, y0, x1, y1, fill=None, ink=INK, w=3.0):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, ink, w)

    def rrect(self, x0, y0, x1, y1, r, fill=None, ink=INK, w=3.0):
        a, b = self.P(x0, y0), self.P(x1, y1)
        self.d.rounded_rectangle((a[0], a[1], b[0], b[1]), radius=r * self.k, fill=fill,
                                 outline=ink if (ink and w > 0) else None, width=max(1, int(w * self.k)))

    def arc(self, cx, cy, rx, ry, a0, a1, color=INK, w=3.0):
        x, y = self.P(cx, cy)
        self.d.arc((x - rx * self.k, y - ry * self.k, x + rx * self.k, y + ry * self.k), a0, a1, fill=color,
                   width=max(1, int(w * self.k)))

    def soft_ellipse(self, cx, cy, rx, ry, color=(40, 30, 40), alpha=0.22):
        x, y = self.P(cx, cy)
        RX, RY = int(rx * self.k), int(ry * self.k)
        yy, xx = np.mgrid[-RY:RY, -RX:RX].astype(np.float32)
        a = np.clip(1 - np.sqrt((xx / RX) ** 2 + (yy / RY) ** 2), 0, 1) ** 0.6 * alpha
        layer = np.zeros((2 * RY, 2 * RX, 4), np.uint8)
        layer[..., :3] = color
        layer[..., 3] = (a * 255).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(layer, "RGBA"), (int(x - RX), int(y - RY)))

    # ---- gradients and glow
    def grad(self, x0, y0, x1, y1, c0, c1, horizontal=False):
        a, b = self.P(x0, y0), self.P(x1, y1)
        ax, ay, bx, by = int(a[0]), int(a[1]), int(b[0]), int(b[1])
        w, h = max(1, bx - ax), max(1, by - ay)
        t = np.linspace(0, 1, w if horizontal else h, dtype=np.float32)
        t = t[None, :, None] if horizontal else t[:, None, None]
        arr = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
        arr = np.broadcast_to(arr, (h, w, 3)).astype(np.uint8)
        self.img.paste(Image.fromarray(arr, "RGB"), (ax, ay))

    def glow(self, cx, cy, r, color, alpha=0.6):
        x, y = self.P(cx, cy)
        R = int(r * self.k)
        yy, xx = np.mgrid[-R:R, -R:R].astype(np.float32)
        a = np.clip(1 - np.sqrt(xx * xx + yy * yy) / R, 0, 1) ** 1.6 * alpha
        layer = np.zeros((2 * R, 2 * R, 4), np.uint8)
        layer[..., :3] = color
        layer[..., 3] = (a * 255).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(layer, "RGBA"), (int(x - R), int(y - R)))

    # ---- shapes with a soft cel shadow (light comes from the upper left)
    def cel(self, pts, base, shade=None, ink=INK, w=3.0, ldir=(-0.6, -0.8), edge=(0.55, 0.68)):
        shade = shade or shade_of(base)
        pp = [self.P(*p) for p in pts]
        xs, ys = [p[0] for p in pp], [p[1] for p in pp]
        x0, y0, x1, y1 = int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs)) + 3, int(max(ys)) + 3
        if x1 <= x0 or y1 <= y0:
            return
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in pp], fill=255)
        self.d.polygon(pp, fill=base)
        gy, gx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
        t = ((gx - gx.mean()) * -ldir[0] + (gy - gy.mean()) * -ldir[1])
        t = t / (np.abs(t).max() + 1e-6) * 0.5 + 0.5
        a = _smooth(t, *edge)
        sh = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        sh[..., :3] = shade
        sh[..., 3] = (a * np.asarray(m, np.float32) * 0.95).astype(np.uint8)
        self.img.alpha_composite(Image.fromarray(sh, "RGBA"), (x0, y0))
        if ink and w > 0:
            self.d.line(pp + [pp[0]], fill=ink, width=max(1, int(w * self.k)), joint="curve")
            r = w * self.k / 2
            for x, y in pp:
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=ink)

    def cel_circle(self, cx, cy, r, base, shade=None, ink=INK, w=3.0, wob=0.0, seed=0, **kw):
        rng = np.random.default_rng(seed)
        n = 44
        ph = rng.random(3) * 6.28
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r * (1 + wob * (0.6 * math.sin(2 * a + ph[0]) + 0.4 * math.sin(3 * a + ph[1])))
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.cel(pts, base, shade, ink, w, **kw)


def rounded_pts(pts, rad, n=5):
    """Round the corners of a polygon (design units)."""
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % m]
        v1 = np.array(p0, float) - p1
        v2 = np.array(p2, float) - p1
        l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
        r = min(rad, l1 / 2.2, l2 / 2.2)
        a = p1 + v1 / l1 * r
        b = p1 + v2 / l2 * r
        for s in range(n + 1):
            t = s / n
            q = (1 - t) ** 2 * a + 2 * t * (1 - t) * np.array(p1, float) + t * t * b
            out.append((float(q[0]), float(q[1])))
    return out


# ======================================================================= characters
POSES = {  # (upper-arm angle, bend) for back arm, front arm.  0 = down, 90 = forward, 180 = up
    "idle": ((10, 12), (12, 16)),
    "point": ((8, 10), (84, -4)),
    "wave": ((8, 10), (150, -25)),
    "think": ((12, 14), (48, 112)),
    "hold": ((14, 10), (60, 60)),
    "cheer": ((165, -12), (165, -12)),
    "pull": ((70, 5), (62, 8)),
    "show": ((50, 30), (100, -10)),
    "shrug": ((38, 30), (38, 30)),
}

OUTFITS = {
    "linen": ((236, 224, 198), (214, 199, 170)),
    "cocoa": ((148, 104, 76), (118, 82, 60)),
    "plum": ((104, 76, 118), (80, 58, 94)),
    "navy": ((70, 84, 118), (52, 63, 92)),
    "sage": ((132, 154, 122), (104, 126, 96)),
    "rust": ((176, 104, 80), (146, 82, 62)),
    "charcoal": ((86, 84, 94), (62, 60, 70)),
    "white": ((244, 240, 232), (220, 213, 204)),
    "red": ((178, 78, 72), (146, 58, 56)),
    "ochre": ((208, 166, 88), (176, 138, 68)),
    "teal": ((90, 148, 148), (66, 120, 122)),
    # names used by the story writer
    "blue": ((86, 116, 168), (62, 90, 138)),
    "green": ((104, 146, 100), (80, 120, 80)),
    "yellow": ((234, 198, 96), (204, 166, 70)),
    "purple": ((134, 98, 152), (106, 74, 124)),
    "brown": ((150, 106, 78), (120, 84, 60)),
    "black": ((70, 68, 78), (48, 46, 56)),
    "orange": ((226, 140, 78), (194, 110, 56)),
    "pink": ((222, 150, 166), (190, 120, 140)),
    "gray": ((156, 156, 164), (126, 126, 136)),
}
GOLD = (222, 184, 96)
GOLD_SH = (188, 150, 70)


def _hat(c, kind, hx, hy, r, face, w, outfit_col):
    top = hy - r
    if kind == "crown":
        pts = [(hx - r * .62, top + r * .12), (hx - r * .7, top - r * .42), (hx - r * .32, top - r * .12), (hx, top - r * .52),
               (hx + r * .32, top - r * .12), (hx + r * .7, top - r * .42), (hx + r * .62, top + r * .12)]
        c.cel(pts, GOLD, GOLD_SH, w=w)
        c.circle(hx, top - r * .1, r * .09, fill=(176, 70, 78), w=w * .5)
    elif kind == "laurel":
        for i in range(9):
            a = math.radians(196 + i * 18.5)
            c.ellipse(hx + math.cos(a) * r * 1.0, hy + math.sin(a) * r * 1.0, r * .17, r * .09, fill=(124, 154, 96), w=w * .45)
    elif kind == "kasa":
        c.cel([(hx - r * 1.55, top + r * .55), (hx, top - r * .55), (hx + r * 1.55, top + r * .55), (hx, top + r * .38)],
              (226, 196, 128), (196, 164, 100), w=w)
    elif kind == "nemes":  # back lappets are drawn before the head (see draw_char); this is the cap on top
        pts = [(hx - r * 1.08, hy - r * .12), (hx - r * .98, top + r * .1), (hx - r * .55, top - r * .12), (hx + r * .55, top - r * .12),
               (hx + r * .98, top + r * .1), (hx + r * 1.08, hy - r * .12), (hx + r * .72, hy - r * .36), (hx - r * .72, hy - r * .36)]
        c.cel(pts, (84, 116, 158), (62, 92, 132), w=w)
        for i in range(3):
            yy = top + r * (.18 + i * .2)
            c.line([(hx - r * .8, yy), (hx + r * .8, yy)], GOLD, w * .6)
    elif kind == "bandana":
        c.cel([(hx - r * 1.0, hy - r * .22), (hx - r * .7, top + r * .02), (hx + r * .7, top + r * .02), (hx + r * 1.0, hy - r * .22),
               (hx + r * .8, hy - r * .02), (hx - r * .8, hy - r * .02)], (226, 212, 186), (198, 182, 156), w=w * .9)
        kx = hx - face * r * 1.05
        c.cel([(kx, hy - r * .2), (kx - face * r * .5, hy - r * .02), (kx - face * r * .42, hy - r * .46)], (226, 212, 186), (198, 182, 156), w=w * .8)
    elif kind == "viking":
        pts = [(hx - r * 1.02, hy - r * .1), (hx - r * .85, top - r * .02), (hx, top - r * .28), (hx + r * .85, top - r * .02), (hx + r * 1.02, hy - r * .1),
               (hx + r * .9, hy - r * .28), (hx - r * .9, hy - r * .28)]
        c.cel(pts, (150, 150, 158), (118, 118, 128), w=w)
        c.line([(hx, top - r * .28), (hx, hy + r * .1)], INK, w * .9)
        c.line([(hx - r * .92, hy - r * .24), (hx + r * .92, hy - r * .24)], GOLD_SH, w * .6)
    elif kind == "roman":
        pts = [(hx - r * 1.0, hy - r * .05), (hx - r * .8, top - r * .08), (hx + r * .8, top - r * .08), (hx + r * 1.0, hy - r * .05),
               (hx + r * .8, hy - r * .3), (hx - r * .8, hy - r * .3)]
        c.cel(pts, (190, 160, 100), (160, 130, 76), w=w)
        c.cel([(hx - r * .08, top - r * .08), (hx - r * .2, top - r * .5), (hx + r * .5, top - r * .5), (hx + r * .45, top - r * .08)],
              (176, 74, 70), (146, 56, 56), w=w * .8)
    elif kind == "cap":
        c.cel([(hx - r * .98, hy - r * .2), (hx - r * .8, top + r * .02), (hx + r * .8, top + r * .02), (hx + r * .98, hy - r * .2)],
              outfit_col, shade_of(outfit_col), w=w)
    elif kind == "topknot":
        c.cel_circle(hx - face * r * .1, top - r * .12, r * .26, (60, 54, 62), (44, 40, 48), w=w * .8)
    elif kind == "towel":
        c.cel([(hx - r * 1.0, hy - r * .12), (hx - r * .72, top + r * .05), (hx + r * .72, top + r * .05), (hx + r * 1.0, hy - r * .12),
               (hx + r * .9, hy - r * .02), (hx - r * .9, hy - r * .02)], (240, 240, 236), (214, 214, 210), w=w * .9)
        c.line([(hx - r * .9, hy - r * .12), (hx + r * .9, hy - r * .12)], (96, 120, 160), w * .7)
    elif kind == "helmet":
        c.cel([(hx - r * 1.02, hy - r * .05), (hx - r * .9, top - r * .05), (hx - r * .4, top - r * .4), (hx + r * .4, top - r * .4), (hx + r * .9, top - r * .05),
               (hx + r * 1.02, hy - r * .05), (hx + r * .8, hy - r * .3), (hx - r * .8, hy - r * .3)], (176, 180, 190), (140, 144, 156), w=w)
        c.line([(hx - r * .92, hy - r * .26), (hx + r * .92, hy - r * .26)], (120, 124, 136), w * .7)
        c.line([(hx, top - r * .38), (hx, hy - r * .28)], (132, 136, 148), w * .6)
    elif kind == "tophat":
        c.cel([(hx - r * .62, top + r * .3), (hx - r * .58, top - r * .98), (hx + r * .58, top - r * .98), (hx + r * .62, top + r * .3)], (64, 58, 70), (44, 40, 50), w=w)
        c.line([(hx - r * .61, top + r * .02), (hx + r * .61, top + r * .02)], (176, 70, 78), w * 1.6)
        c.cel([(hx - r * 1.2, top + r * .3), (hx + r * 1.2, top + r * .3), (hx + r * 1.05, top + r * .5), (hx - r * 1.05, top + r * .5)], (64, 58, 70), (44, 40, 50), w=w)
    elif kind == "tricorn":
        c.cel([(hx - r * 1.4, top + r * .55), (hx - r * .7, top - r * .12), (hx, top - r * .3), (hx + r * .7, top - r * .12), (hx + r * 1.4, top + r * .55),
               (hx + r * .6, top + r * .36), (hx - r * .6, top + r * .36)], (66, 68, 94), (46, 48, 70), w=w)
        c.line([(hx - r * 1.38, top + r * .53), (hx - r * .7, top - r * .1), (hx, top - r * .28), (hx + r * .7, top - r * .1), (hx + r * 1.38, top + r * .53)], GOLD, w * .6)
    elif kind == "turban":
        c.cel([(hx - r * 1.06, hy - r * .2), (hx - r * .98, top - r * .08), (hx - r * .45, top - r * .6), (hx + r * .45, top - r * .6), (hx + r * .98, top - r * .08),
               (hx + r * 1.06, hy - r * .2), (hx + r * .5, hy - r * .42), (hx - r * .5, hy - r * .42)], (238, 230, 210), (210, 200, 178), w=w)
        for i in range(3):
            c.line([(hx - r * .92 + i * r * .1, hy - r * .3 - i * r * .3), (hx + r * .5 + i * r * .1, top - r * .1 + i * r * .05 - r * .1)], (206, 194, 168), w * .6)
        c.circle(hx + face * r * .1, top + r * .1, r * .13, fill=(176, 70, 78), w=w * .6)
    elif kind == "kabuto":
        c.cel([(hx - r * 1.06, hy - r * .05), (hx - r * .92, top - r * .05), (hx - r * .4, top - r * .4), (hx + r * .4, top - r * .4), (hx + r * .92, top - r * .05),
               (hx + r * 1.06, hy - r * .05), (hx + r * .85, hy - r * .3), (hx - r * .85, hy - r * .3)], (86, 82, 98), (62, 58, 74), w=w)
        for sd in (-1, 1):
            c.line([(hx + sd * r * .12, top - r * .38), (hx + sd * r * .62, top - r * 1.05)], GOLD, w * 1.4)
        c.line([(hx - r * .95, hy - r * .26), (hx + r * .95, hy - r * .26)], GOLD_SH, w * .7)
    elif kind == "cowboy":
        c.cel([(hx - r * .6, top + r * .38), (hx - r * .55, top - r * .5), (hx, top - r * .36), (hx + r * .55, top - r * .5), (hx + r * .6, top + r * .38)], (150, 106, 72), (120, 82, 54), w=w)
        c.line([(hx - r * .58, top + r * .1), (hx + r * .58, top + r * .1)], (96, 66, 50), w * 1.4)
        c.cel([(hx - r * 1.5, top + r * .5), (hx - r * .8, top + r * .3), (hx + r * .8, top + r * .3), (hx + r * 1.5, top + r * .5),
               (hx + r * .8, top + r * .64), (hx - r * .8, top + r * .64)], (160, 116, 80), (128, 90, 60), w=w)
    elif kind == "hood":  # back of the hood is drawn before the head; this is the front rim
        c.cel([(hx - r * 1.05, hy - r * .1), (hx - r * .9, top + r * .05), (hx, top - r * .2), (hx + r * .9, top + r * .05), (hx + r * 1.05, hy - r * .1),
               (hx + r * .7, hy - r * .4), (hx - r * .7, hy - r * .4)], mix(outfit_col, (40, 40, 50), .15), shade_of(outfit_col), w=w)


def _object(c, kind, x, y, h, w, face, t=0.0):
    u = h / 330.0
    if kind == "scroll":
        c.rrect(x - 20 * u, y - 12 * u, x + 20 * u, y + 12 * u, 6 * u, fill=(244, 232, 204), w=w * .7)
        c.ellipse(x - 20 * u, y, 5 * u, 12 * u, fill=(226, 208, 170), w=w * .6)
        c.ellipse(x + 20 * u, y, 5 * u, 12 * u, fill=(226, 208, 170), w=w * .6)
    elif kind == "oar":
        c.line([(x - face * 8 * u, y + 140 * u), (x + face * 10 * u, y - 120 * u)], (150, 108, 74), w * 1.7)
        c.cel([(x + face * 6 * u, y - 120 * u), (x + face * 24 * u, y - 90 * u), (x + face * 12 * u, y - 60 * u), (x - face * 2 * u, y - 92 * u)],
              (176, 130, 90), (146, 104, 70), w=w * .8)
    elif kind == "sheet":
        c.cel([(x - 22 * u, y - 28 * u), (x + 22 * u, y - 28 * u), (x + 22 * u, y + 24 * u), (x - 22 * u, y + 24 * u)], (250, 246, 236), (226, 220, 206), w=w * .7)
        for i in range(4):
            c.line([(x - 14 * u, y - 16 * u + i * 10 * u), (x + 14 * u, y - 16 * u + i * 10 * u)], (120, 110, 110), w * .4)
    elif kind == "bread":
        c.cel_circle(x, y, 17 * u, (214, 164, 98), (184, 134, 74), w=w * .7)
    elif kind == "stick":
        c.line([(x - face * 4 * u, y + 90 * u), (x + face * 6 * u, y - 70 * u)], (150, 108, 74), w * 1.5)
    elif kind == "lantern":
        c.line([(x, y - 30 * u), (x, y - 8 * u)], INK, w * .5)
        c.ellipse(x, y + 12 * u, 13 * u, 18 * u, fill=(214, 120, 90), w=w * .7)
    elif kind == "book":
        c.cel([(x - 24 * u, y - 28 * u), (x + 24 * u, y - 28 * u), (x + 24 * u, y + 28 * u), (x - 24 * u, y + 28 * u)], (158, 82, 80), (126, 62, 64), w=w * .7)
        c.line([(x - 17 * u, y - 28 * u), (x - 17 * u, y + 28 * u)], (226, 190, 120), w * .6)
        c.line([(x - 6 * u, y - 8 * u), (x + 14 * u, y - 8 * u)], (226, 190, 120), w * .5)
    elif kind == "flag":
        c.line([(x, y - 80 * u), (x + face * 4 * u, y + 90 * u)], (150, 108, 74), w * 1.3)
        c.cel([(x, y - 80 * u), (x + face * 64 * u, y - 62 * u + 6 * math.sin(t * 4) * u), (x, y - 30 * u)], (190, 70, 70), (156, 52, 56), w=w * .7)
    elif kind == "coins":
        for i in range(3):
            c.ellipse(x, y + 16 * u - i * 10 * u, 20 * u, 8 * u, fill=GOLD, w=w * .6)
    elif kind == "quill":
        c.line([(x - face * 10 * u, y + 40 * u), (x + face * 18 * u, y - 50 * u)], (120, 96, 80), w * .7)
        c.cel([(x + face * 18 * u, y - 50 * u), (x + face * 36 * u, y - 34 * u), (x + face * 8 * u, y - 4 * u)], (244, 238, 226), (216, 208, 196), w=w * .6)
    elif kind == "bulb":
        c.circle(x, y, 14 * u, fill=(255, 232, 140), w=w * .7)
        c.rect(x - 7 * u, y + 12 * u, x + 7 * u, y + 24 * u, fill=(176, 172, 176), w=w * .6)


def draw_char(c, x, gy, h, outfit="linen", hat=None, emotion="smile", pose="idle", face=1, t=0.0, mouth=None,
              holds=None, robe=False, cape=None, beard=False, belt=True, gaze=0.0, lean=0.0, emote=None, seed=1,
              arms=None, trim=None, w=None, beard_col=None):
    """x, gy = feet position. h = full height. face = +1 right / -1 left. mouth = 0..1 talking amount."""
    ow = w or max(2.4, h * 0.0105)
    base, sh = OUTFITS.get(outfit, OUTFITS["linen"])
    r = 0.205 * h
    breath = math.sin(t * 2.2 + seed) * 0.004 * h
    sway = math.sin(t * 1.3 + seed) * 0.006 * h

    def L(y):  # lean: upper body shifts forward
        return lean * h * max(0.0, (gy - y) / h) ** 1.4 * face

    hip_y = gy - 0.335 * h
    sh_y = gy - 0.655 * h + breath
    hc_y = gy - h + r + breath
    hx = x + L(hc_y) + sway * 0.6
    sx = x + L(sh_y) + sway * 0.3

    # --- cape behind the body
    if cape:
        cb, cs = cape if isinstance(cape, tuple) else OUTFITS[cape]
        c.cel([(sx - face * 0.07 * h, sh_y), (sx + face * 0.07 * h, sh_y), (x - face * 0.26 * h + math.sin(t * 2 + seed) * 0.01 * h, gy - 0.05 * h),
               (x + face * 0.16 * h, gy - 0.02 * h)], cb, cs, w=ow)

    # ground contact shadow
    c.soft_ellipse(x + face * 0.02 * h, gy + 0.004 * h, 0.22 * h, 0.04 * h)
    # --- legs
    for side, off in ((-1, -0.045), (1, 0.045)):
        lx0, lx1 = x + off * h, x + off * h * 1.35
        c.line([(lx0, hip_y), (lx1, gy - 0.02 * h)], INK, 0.040 * h)
        c.line([(lx0, hip_y), (lx1, gy - 0.02 * h)], (236, 226, 212) if robe is False else (236, 226, 212), 0.026 * h)
        c.ellipse(lx1 + face * 0.02 * h, gy - 0.012 * h, 0.04 * h, 0.022 * h, fill=(98, 76, 66), w=ow * .8)

    # --- body (tunic or robe)
    hem = gy - 0.08 * h if robe else hip_y + 0.065 * h
    half_sh, half_hem = 0.105 * h, (0.19 if robe else 0.14) * h
    pts = rounded_pts([(sx - half_sh, sh_y), (sx + half_sh, sh_y), (x + half_hem, hem), (x - half_hem, hem)], 0.05 * h)
    c.cel(pts, base, sh, w=ow)
    if trim:
        tb = trim if isinstance(trim, tuple) else GOLD
        c.line([(sx - half_sh * .35, sh_y + 0.01 * h), (x - half_hem * .1, hem - 0.01 * h)], tb, 0.014 * h)
    if belt:
        by = hip_y - 0.01 * h
        c.cel([(x - 0.125 * h, by - 0.022 * h), (x + 0.125 * h, by - 0.022 * h), (x + 0.13 * h, by + 0.022 * h), (x - 0.13 * h, by + 0.022 * h)],
              mix(base, (90, 70, 60), 0.55), mix(sh, (60, 46, 42), 0.55), w=ow * .7)
    # neck + collar
    c.line([(hx, hc_y + r * .8), (sx, sh_y + 0.005 * h)], INK, 0.034 * h)
    c.line([(hx, hc_y + r * .8), (sx, sh_y + 0.005 * h)], IVORY, 0.020 * h)

    # --- arms
    a_back, a_front = arms or POSES.get(pose, POSES["idle"])
    wob = math.sin(t * 2.6 + seed)
    hands = []
    for idx, (a, b) in enumerate((a_back, a_front)):
        front = idx == 1
        a = a + (wob * 3 if pose in ("idle", "show") else 0) + (math.sin(t * 9) * 12 if pose == "wave" and front else 0)
        s = (sx + (face * 0.09 * h if front else -face * 0.09 * h), sh_y + 0.03 * h)
        a1 = math.radians(a)
        e = (s[0] + math.sin(a1) * face * 0.15 * h, s[1] + math.cos(a1) * 0.15 * h)
        a2 = math.radians(a + b)
        hd = (e[0] + math.sin(a2) * face * 0.14 * h, e[1] + math.cos(a2) * 0.14 * h)
        c.line([s, e], INK, 0.040 * h)
        c.line([s, e], base, 0.027 * h)
        c.line([e, hd], INK, 0.034 * h)
        c.line([e, hd], IVORY, 0.021 * h)
        c.cel_circle(hd[0], hd[1], 0.034 * h, IVORY, IVORY_SH, w=ow * .8, seed=idx)
        hands.append(hd)
    if holds:
        _object(c, holds, hands[1][0], hands[1][1], h, ow, face, t)

    # --- head
    if hat == "hood":
        c.cel([(hx - r * 1.15, hc_y + r * .9), (hx - r * 1.1, hc_y - r * .3), (hx, hc_y - r * 1.5), (hx + r * 1.1, hc_y - r * .3), (hx + r * 1.15, hc_y + r * .9)],
              base, sh, w=ow)
    if hat == "nemes":
        c.cel([(hx - r * 1.1, hc_y + r * 1.3), (hx - r * 1.08, hc_y - r * .1), (hx + r * 1.08, hc_y - r * .1), (hx + r * 1.1, hc_y + r * 1.3),
               (hx + r * .78, hc_y + r * .75), (hx - r * .78, hc_y + r * .75)], (84, 116, 158), (62, 92, 132), w=ow)
    c.cel_circle(hx, hc_y, r, IVORY, IVORY_SH, w=ow * 1.25, wob=0.012, seed=seed)
    if beard:
        from sb_beard import beard_base
        beard_base(c, hx, hc_y, r, face, beard, beard_col, ow, seed)
    fx = hx + face * r * 0.2 + gaze * r * 0.0
    ey = hc_y + r * 0.02
    blink = (t * 0.9 + seed * 0.37) % 3.1 < 0.11
    ex = r * 0.40
    ed = max(2.2, r * 0.095)
    emo = emotion
    if emo in ("happy", "joy"):
        for sd in (-1, 1):
            c.arc(fx + sd * ex, ey + r * .05, r * .13, r * .13, 200, 340, INK, ow * 1.1)
    else:
        for sd in (-1, 1):
            px = fx + sd * ex + gaze * r * 0.1
            if blink:
                c.line([(px - ed, ey), (px + ed, ey)], INK, ow * .9)
            elif emo == "surprise":
                c.circle(px, ey, ed * 1.35, fill=IVORY, ink=INK, w=ow * .7)
                c.circle(px + gaze * ed * .5, ey, ed * .55, fill=INK, ink=None)
            else:
                c.circle(px, ey, ed, fill=INK, ink=None)
    # brows
    if emo in ("worry", "sad", "curious", "proud", "surprise"):
        for sd in (-1, 1):
            tilt = {"worry": 0.5 * sd, "sad": 0.5 * sd, "curious": -0.3 * sd if sd > 0 else 0.1, "proud": -0.2 * sd, "surprise": 0.0}[emo]
            by = ey - r * (0.3 if emo != "surprise" else 0.42)
            c.line([(fx + sd * ex - r * .13, by + tilt * r * .13), (fx + sd * ex + r * .13, by - tilt * r * .13)], INK, ow * .9)
    # mouth
    my = hc_y + r * (0.80 if beard else 0.46)
    mxp = fx + face * r * 0.04
    if mouth is not None and mouth > 0.04:
        m = min(1.0, mouth)
        c.ellipse(mxp, my + r * .02, r * (0.13 + 0.05 * m), r * (0.03 + 0.17 * m), fill=(120, 52, 60), ink=INK, w=ow * .8)
    elif emo in ("happy", "joy"):
        c.poly([(mxp - r * .2, my - r * .03), (mxp + r * .2, my - r * .03), (mxp, my + r * .24)], fill=(120, 52, 60), w=ow * .8)
    elif emo in ("smile", "proud"):
        c.arc(mxp, my - r * .12, r * .2, r * .2, 25, 155, INK, ow)
    elif emo == "surprise":
        c.ellipse(mxp, my + r * .06, r * .09, r * .13, fill=(120, 52, 60), w=ow * .7)
    elif emo in ("worry", "curious"):
        c.line([(mxp - r * .13, my + r * .06), (mxp + r * .13, my + r * .02)], INK, ow * .9)
    elif emo == "sad":
        c.arc(mxp, my + r * .22, r * .18, r * .14, 205, 335, INK, ow)
    else:
        c.line([(mxp - r * .12, my + r * .04), (mxp + r * .12, my + r * .04)], INK, ow * .9)
    if beard:
        from sb_beard import mustache
        mustache(c, hx, hc_y, r, face, beard, beard_col, ow, seed)
    if hat:
        _hat(c, hat, hx, hc_y - r * 0.2, r, face, ow, base)
    if emo in ("surprise",) or emote == "!":
        for i, a in enumerate((-68, -90, -112)):
            ca = math.radians(a)
            c.line([(hx + math.cos(ca) * r * 1.2, hc_y + math.sin(ca) * r * 1.2), (hx + math.cos(ca) * r * 1.5, hc_y + math.sin(ca) * r * 1.5)], INK, ow * .8)
    if emote == "?":
        c.arc(hx + r * 1.1, hc_y - r * 1.15, r * .26, r * .26, 180, 400, INK, ow)
        c.circle(hx + r * 1.2, hc_y - r * .62, ow * .8, fill=INK, ink=None)
    if emote == "sweat":
        c.poly([(hx + face * r * 1.0, hc_y - r * .5), (hx + face * r * 1.12, hc_y - r * .2), (hx + face * r * .88, hc_y - r * .2)], fill=(172, 206, 226), w=ow * .6)
    return {"head": (hx, hc_y), "r": r, "hand": hands[1]}


def get_font(size, bold=True):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()
