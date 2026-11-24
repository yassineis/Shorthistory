"""Detailed beards for the storybook characters (code only, Pillow + numpy).

Follows the svg-beard-drawer method: smooth Bezier-like silhouette, separate mustache layer, shaded base,
many curved hair strands clipped to the silhouette (so nothing floats outside), light + dark tones.

Styles: "full" (trimmed rounded beard), "viking" (long, forked tip, gold rings), "goatee".
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from sb_draw import INK, mix, shade_of

PALETTE = {
    "full": (112, 80, 62),
    "viking": (178, 108, 62),
    "goatee": (74, 60, 58),
    "grey": (176, 172, 170),
}
GOLD = (222, 184, 96)

# silhouettes in units of head radius r, x symmetric around the head centre, y down from the head centre
SIL = {
    "full": [(-.98, .10), (-1.07, .40), (-1.0, .78), (-.74, 1.20), (-.38, 1.44), (0, 1.52), (.38, 1.44), (.74, 1.20), (1.0, .78), (1.07, .40), (.98, .10),
             (.82, .26), (.66, .46), (.34, .54), (0, .52), (-.34, .54), (-.66, .46), (-.82, .26)],
    "viking": [(-1.0, .10), (-1.12, .46), (-1.0, .95), (-.78, 1.40), (-.66, 1.85), (-.44, 2.28), (-.22, 1.90), (0, 1.80), (.22, 1.90), (.44, 2.28), (.66, 1.85),
               (.78, 1.40), (1.0, .95), (1.12, .46), (1.0, .10), (.82, .26), (.66, .46), (.34, .54), (0, .52), (-.34, .54), (-.66, .46), (-.82, .26)],
    "goatee": [(-.30, .55), (-.40, .90), (-.30, 1.25), (-.10, 1.50), (0, 1.58), (.10, 1.50), (.30, 1.25), (.40, .90), (.30, .55), (.12, .66), (-.12, .66)],
}
# mustache (half outline, mirrored): starts at the philtrum, ends at the drooping wing tip
MUST = [(0, .40), (.20, .34), (.48, .38), (.74, .56), (.80, .80), (.58, .70), (.34, .62), (.12, .62)]


def catmull(pts, n=8, closed=True):
    P = [np.array(p, float) for p in pts]
    m = len(P)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for s in range(n):
            t = s / n
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append((float(q[0]), float(q[1])))
    return out


def _world(pts, hx, hy, r, f):
    return [(hx + x * r * (1 if True else f), hy + y * r) for x, y in pts]


def _strands(c, poly_w, base, hx, hy, r, style, seed, density=1.0, flow="down"):
    """Hair strands, clipped to the polygon (design units) by a mask."""
    k = c.k
    pp = [c.P(*p) for p in poly_w]
    xs, ys = [p[0] for p in pp], [p[1] for p in pp]
    x0, y0, x1, y1 = int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs)) + 3, int(max(ys)) + 3
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in pp], fill=255)
    layer = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    inside = np.argwhere(np.asarray(mask) > 0)
    if len(inside) == 0:
        return
    n = int(len(inside) / (k * k) / (r * r) * (34 if flow == "down" else 60) * density)
    n = max(24, min(n, 190))
    light, dark = mix(base, (255, 236, 206), .26), shade_of(base, .74)
    anchor = (hx, hy - .1 * r)
    for i in range(n):
        py, px = inside[rng.integers(0, len(inside))]
        wx, wy = (px + x0) / k - 90, (py + y0) / k - 150  # back to design units
        if flow == "out":  # mustache: from the centre outward and slightly down
            vx, vy = np.sign(wx - hx) * 1.0, .38
        else:  # beard: radiates from above the face and falls toward the chin
            vx, vy = (wx - anchor[0]) * .55 / r, max(.4, (wy - anchor[1]) / r)
            vx *= .55  # pull toward vertical
            vx = -vx * .35 + vx  # gentle fan
        nrm = math.hypot(vx, vy) or 1
        vx, vy = vx / nrm, vy / nrm
        L = r * rng.uniform(.5, .95) * (1.3 if style == "viking" else 1.0) * (.55 if flow == "out" else 1.0)
        wave = math.sin(wy / r * 2.4 + wx / r) * (.10 if style == "viking" else .045) * r
        pts = []
        for sidx in range(8):
            t = sidx / 7
            xq = wx + vx * L * t + wave * math.sin(t * math.pi)
            yq = wy + vy * L * t
            a_ = c.P(xq, yq)
            pts.append((a_[0] - x0, a_[1] - y0))
        light_strand = rng.random() < .5
        col = light if light_strand else dark
        w = max(1, int(r * rng.uniform(.012, .024) * k))
        d.line(pts, fill=col + (170,), width=w, joint="curve")
    # a few thick stylised locks give the beard its shape
    if flow == "down":
        for sd in (-1, 1):
            for j, (u, v) in enumerate(((.5, .55), (.7, .95), (.3, 1.25))):
                lx, ly = hx + sd * u * r, hy + v * r
                pts = []
                for sidx in range(8):
                    t = sidx / 7
                    a_ = c.P(lx - sd * t * r * .22, ly + t * r * (.55 if style != "viking" else .8))
                    pts.append((a_[0] - x0, a_[1] - y0))
                d.line(pts, fill=shade_of(base, .66) + (150,), width=max(1, int(r * .035 * k)), joint="curve")
    a = np.asarray(layer).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * np.asarray(mask, np.float32) / 255).astype(np.uint8)
    c.img.alpha_composite(Image.fromarray(a, "RGBA"), (x0, y0))


def beard_base(c, hx, hy, r, face, style="full", col=None, ow=3.0, seed=1):
    style = "full" if style is True else style
    base = col or PALETTE.get(style, PALETTE["full"])
    sh = shade_of(base, .78)
    shift = face * r * .05
    sil = catmull([(x, y) for x, y in SIL[style]], 8, True)
    poly = [(hx + shift + x * r, hy + y * r) for x, y in sil]
    c.cel(poly, base, sh, w=ow, edge=(.45, .75))
    _strands(c, poly, base, hx + shift, hy, r, style, seed)
    # soft highlight on the upper-left cheek
    c.line([(hx + shift - .78 * r, hy + .45 * r), (hx + shift - .70 * r, hy + .85 * r), (hx + shift - .5 * r, hy + 1.15 * r)], mix(base, (255, 240, 214), .5), r * .05)
    # under-lip shadow
    c.ellipse(hx + shift, hy + 1.02 * r, r * .26, r * .045, fill=shade_of(base, .7), ink=None)
    if style == "viking":  # gold rings tying the two tips
        for sd in (-1, 1):
            x = hx + shift + sd * .5 * r
            c.line([(x - r * .13, hy + 1.88 * r), (x + r * .13, hy + 1.88 * r)], GOLD, r * .09)
            c.line([(x - r * .13, hy + 1.88 * r), (x + r * .13, hy + 1.88 * r)], mix(GOLD, INK, .45), r * .02)
    return base


def mustache(c, hx, hy, r, face, style="full", col=None, ow=3.0, seed=1):
    style = "full" if style is True else style
    base = col or PALETTE.get(style, PALETTE["full"])
    base = mix(base, (255, 255, 255), .06)
    shift = face * r * .05
    right = catmull(MUST, 7, False)
    left = [(-x, y) for x, y in reversed(right)]
    pts = left + right
    # close it with a soft lower edge through the middle
    poly = [(hx + shift + x * r, hy + y * r) for x, y in pts]
    poly = catmull([(x, y) for x, y in zip([p[0] for p in poly], [p[1] for p in poly])], 3, True)
    c.cel(poly, base, shade_of(base, .78), w=ow * .85, edge=(.4, .7))
    _strands(c, poly, base, hx + shift, hy, r, "full", seed + 5, density=1.6, flow="out")
