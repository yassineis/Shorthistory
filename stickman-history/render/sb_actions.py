"""Prop actions for the enhanced true-story mode: small animations that show the ONE thing happening in a shot.
Each action is a pure function of time, drawn with the same Ctx kit as the characters (design space 720x1280).

  throw  a ball flies from the main character's hand and bounces       swing  a hammer strikes twice
  fall   a crate drops from above and lands with dust                   impact a comic starburst
  door   a door in the back wall swings open with light                 sail   a boat crosses the sea
  glide  a plane glides down with a contrail                            train  a steam train rolls past
"""
import math

from sb_draw import INK

ACTIONS = ("throw", "swing", "fall", "impact", "door", "sail", "glide", "train")
BACKGROUND = ("door", "sail", "glide", "train")  # drawn behind the characters
WHITE, DARK, WOOD, GOLD, STEEL = (250, 246, 238), (62, 48, 44), (150, 104, 70), (240, 200, 90), (150, 156, 168)


def _clip(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def _ease_in(x):
    x = _clip(x)
    return x * x


def _ease_io(x):
    x = _clip(x)
    return x * x * (3 - 2 * x)


def _rot(pts, cx, cy, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in pts]


def impact_times(name, at):
    """Moments (seconds) when the picture should shake."""
    return {"throw": [at + 1.25], "swing": [at + 0.42, at + 1.32], "fall": [at + 0.75], "impact": [at]}.get(name, [])


def draw_action(c, name, t, at, ref, total):
    """ref = {"x": main character x in design px, "gy": ground y, "face": +1/-1}. at = when the action starts (seconds)."""
    fn = globals().get("_" + name)
    if fn:
        fn(c, t, at, ref, total)


def _hand(ref):
    if ref.get("hand"):
        return ref["hand"]
    return ref["x"] + ref["face"] * 82, ref["gy"] - 225


def _throw(c, t, at, ref, total):
    f, gy = ref["face"], ref["gy"]
    sx, sy = _hand(ref)
    ex = _clip(ref["x"] + f * 360, 70, 650)
    ey = gy - 14
    dur = 1.25
    p = (t - at) / dur
    r = 21
    if p < 0:
        x, y = sx, sy
    elif p <= 1:
        x = sx + (ex - sx) * p
        y = sy + (ey - sy) * p - 4 * 270 * p * (1 - p)
        for i in range(1, 5):  # fading trail
            q = max(0.0, p - i * 0.045)
            c.circle(sx + (ex - sx) * q, sy + (ey - sy) * q - 4 * 270 * q * (1 - q), r * (1 - i * 0.16), fill=(236, 232, 222), ink=None)
    else:
        q = (t - at - dur) / 0.55
        x, y = ex + _clip(q) * f * 26, ey - 70 * 4 * _clip(q) * (1 - _clip(q))
        if q < 0.45:  # dust where it lands
            for sd in (-1, 1):
                c.soft_ellipse(ex + sd * (10 + 40 * q), ey + r - 4, 24 + 30 * q, 8 + 10 * q, (150, 120, 90), 0.35 * (1 - q / 0.45))
    c.soft_ellipse(x, ey + r, 20, 6, (40, 30, 40), 0.18)
    c.circle(x, y, r, fill=WHITE, ink=INK, w=3.0)
    for dx, dy in ((-7, -6), (6, -8), (0, 4), (-9, 8), (9, 5)):
        c.circle(x + dx, y + dy, 2.1, fill=(200, 196, 186), ink=None)


def _swing(c, t, at, ref, total):
    f = ref["face"]
    px, py = _hand(ref)
    ang = None
    for cyc in (0, 1):
        u = (t - at - 0.9 * cyc) / 0.9
        if 0 <= u <= 1:
            if u < 0.47:
                ang = -125 + 160 * _ease_in(u / 0.47)
            else:
                ang = 35 - 160 * _ease_io((u - 0.47) / 0.53)
            break
    if ang is None:
        return
    a = math.radians(ang)
    ux, uy = f * math.sin(a), -math.cos(a)
    L = 118
    tip = (px + ux * L, py + uy * L)
    c.line([(px, py), tip], INK, 14)
    c.line([(px, py), tip], WOOD, 8)
    nx, ny = -uy, ux
    hw, hh = 34, 15
    head = [(tip[0] + nx * hh - ux * 4, tip[1] + ny * hh - uy * 4), (tip[0] + nx * hh + ux * hw, tip[1] + ny * hh + uy * hw),
            (tip[0] - nx * hh + ux * hw, tip[1] - ny * hh + uy * hw), (tip[0] - nx * hh - ux * 4, tip[1] - ny * hh - uy * 4)]
    c.poly(head, fill=STEEL, w=3)
    if ang >= 30:  # spark at the strike
        sx, sy = tip[0] + ux * 30, tip[1] + uy * 30
        for k in range(8):
            aa = k * math.pi / 4
            c.line([(sx + math.cos(aa) * 14, sy + math.sin(aa) * 14), (sx + math.cos(aa) * 30, sy + math.sin(aa) * 30)], GOLD, 5)


def _fall(c, t, at, ref, total):
    f, gy = ref["face"], ref["gy"]
    x = _clip(ref["x"] + f * 235, 90, 630)
    dur = 0.75
    p = (t - at) / dur
    size = 74
    gnd = gy - size / 2 - 8
    if p < 0:
        return
    if p <= 1:
        y = -120 + (gnd + 120) * _ease_in(p)
        sq = 1.0
    else:
        q = _clip((t - at - dur) / 0.5)
        y = gnd - 34 * 4 * q * (1 - q) * (1 - q)
        sq = 1.0 - 0.22 * math.exp(-q * 9) * (1 if q < 0.35 else 0)
        for sd in (-1, 1):
            c.soft_ellipse(x + sd * (46 + 80 * q), gnd + size / 2, 36 + 40 * q, 11 + 8 * q, (160, 130, 100), 0.4 * (1 - q))
    c.soft_ellipse(x, gnd + size / 2 + 4, size * .6, 9, (40, 30, 40), 0.2)
    h = size * sq
    c.rect(x - size / 2, y + size / 2 - h, x + size / 2, y + size / 2, fill=(196, 150, 92), w=3.5)
    c.line([(x - size / 2, y + size / 2 - h), (x + size / 2, y + size / 2)], (120, 84, 52), 4)
    c.line([(x + size / 2, y + size / 2 - h), (x - size / 2, y + size / 2)], (120, 84, 52), 4)


def _impact(c, t, at, ref, total):
    d = t - at
    if d < 0 or d > 0.6:
        return
    s = (_ease_io(d / 0.12) if d < 0.12 else 1.0) * (1.0 - _ease_in((d - 0.3) / 0.3))
    cx, cy = _clip(ref["x"] + ref["face"] * 170, 90, 630), ref["gy"] - 215
    pts = []
    for i in range(16):
        rr = (86 if i % 2 == 0 else 44) * s
        a = i * math.pi / 8 + 0.2
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    c.poly(pts, fill=(255, 214, 70), w=4)
    c.poly([(cx + (x - cx) * .55, cy + (y - cy) * .55) for x, y in pts], fill=(255, 246, 200), ink=None)


def _door(c, t, at, ref, total):
    f = ref["face"]
    dx = _clip(ref["x"] + f * 270, 130, 590)
    w, h, base = 112, 235, 790
    c.rect(dx - w / 2 - 10, base - h - 10, dx + w / 2 + 10, base, fill=(88, 66, 56), w=3.5)
    open_ = _ease_io((t - at) / 0.9)
    if open_ > 0:
        c.glow(dx, base - h / 2, 170, (255, 226, 150), 0.55 * open_)
    c.rect(dx - w / 2, base - h, dx + w / 2, base, fill=(255, 226, 150) if open_ > 0.02 else (126, 88, 62), ink=INK, w=3)
    pw = w * math.cos(math.radians(78 * open_))
    hx = dx - w / 2
    c.poly([(hx, base - h), (hx + pw, base - h - 8 * open_), (hx + pw, base + 6 * open_), (hx, base)], fill=(150, 104, 70), w=3.5)
    c.circle(hx + pw * .82, base - h / 2, 5, fill=GOLD, w=2)


def _sail(c, t, at, ref, total):
    p = _clip((t - at) / max(2.0, total - at + 0.4))
    x = -150 + (720 + 300) * p
    y = 690 + math.sin(t * 2.0) * 5
    s = 0.55
    X = lambda dx: x + dx * s
    Y = lambda dy: y + dy * s
    c.poly([(X(-80), Y(0)), (X(80), Y(0)), (X(56), Y(34)), (X(-56), Y(34))], fill=(132, 84, 58), w=3)
    c.line([(X(0), Y(0)), (X(0), Y(-150))], INK, 4)
    c.poly([(X(6), Y(-144)), (X(74), Y(-18)), (X(6), Y(-18))], fill=WHITE, w=3)
    c.poly([(X(-6), Y(-120)), (X(-52), Y(-18)), (X(-6), Y(-18))], fill=(236, 226, 206), w=3)
    c.line([(X(-90), Y(36)), (X(-30), Y(38))], (255, 255, 255), 3)
    c.line([(X(30), Y(38)), (X(96), Y(36))], (255, 255, 255), 3)


def _glide(c, t, at, ref, total):
    p = _clip((t - at) / 3.2)
    x, y = -110 + 880 * p, 220 + 420 * (p ** 1.3)
    ang = math.atan2(420 * 1.3 * (p ** 0.3), 880) * 0.7
    for i in range(1, 9):  # contrail
        q = max(0.0, p - i * 0.03)
        c.circle(-110 + 880 * q - 36, 220 + 420 * (q ** 1.3), 12 - i * 1.1, fill=(246, 246, 250), ink=None)
    body = _rot([(x - 62, y - 11), (x + 66, y - 7), (x + 82, y), (x + 66, y + 7), (x - 62, y + 11)], x, y, ang)
    c.poly(body, fill=WHITE, w=3.5)
    c.poly(_rot([(x - 8, y), (x - 38, y + 52), (x - 22, y + 52), (x + 22, y + 4)], x, y, ang), fill=(226, 224, 218), w=3.5)
    c.poly(_rot([(x - 8, y), (x - 38, y - 40), (x - 22, y - 40), (x + 22, y - 4)], x, y, ang), fill=(226, 224, 218), w=3.5)
    c.poly(_rot([(x - 58, y - 8), (x - 74, y - 42), (x - 54, y - 42), (x - 40, y - 8)], x, y, ang), fill=(214, 84, 76), w=3.5)


def _train(c, t, at, ref, total):
    p = _clip((t - at) / 2.6)
    x = -420 + 1500 * p
    base = 800
    for i in range(5):  # smoke
        age = (t - at - i * 0.16)
        if age > 0:
            c.circle(x + 120 - i * 34 - age * 20, base - 150 - age * 34, 15 + age * 12, fill=(226, 226, 232), ink=None)
    for k in (1, 2):  # carriages
        cx = x - k * 190
        c.rect(cx - 86, base - 96, cx + 86, base - 22, fill=[(176, 84, 72), (88, 120, 160)][k - 1], w=3.5)
        for wx in (-52, 52):
            c.circle(cx + wx, base - 12, 17, fill=DARK, w=3)
    c.rect(x - 56, base - 100, x + 112, base - 22, fill=(60, 66, 80), w=3.5)  # boiler
    c.rect(x - 112, base - 134, x - 36, base - 22, fill=(176, 60, 56), w=3.5)  # cab
    c.rect(x + 78, base - 142, x + 104, base - 100, fill=INK, w=3)  # chimney
    for wx in (-70, 10, 78):
        wr = 22
        c.circle(x + wx, base - 14, wr, fill=DARK, w=3)
        a = (t - at) * 14 + wx
        c.line([(x + wx - math.cos(a) * wr * .8, base - 14 - math.sin(a) * wr * .8), (x + wx + math.cos(a) * wr * .8, base - 14 + math.sin(a) * wr * .8)], STEEL, 3)
