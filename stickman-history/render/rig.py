"""Stickman rig: simple forward-kinematics skeleton, poses, face, hats, held props."""
import math

from stage import INK, RED, GOLD, CREAM, GRAY, STONE, BROWN, BLUE, GREEN


def pose_angles(pose, t, speed=1.0):
    """Angles in degrees measured from straight down; positive swings toward the facing direction.
    Each limb is (upper angle, lower angle)."""
    s = math.sin
    A = dict(ll=(4, 2), rl=(-4, -2), la=(-14, -8), ra=(14, 8), lean=0.0, bob=0.0, jump=0.0, head=0.0)
    if pose == "stand":
        A["bob"] = 0.004 * s(t * 2.2)
        A["head"] = 2 * s(t * 1.3)
    elif pose in ("walk", "march"):
        p = t * (7 if pose == "walk" else 9) * speed
        a, b = 28 * s(p), -28 * s(p)
        A["ll"] = (a, a - 24 * max(0, math.cos(p)))
        A["rl"] = (b, b - 24 * max(0, -math.cos(p)))
        A["ra"] = (a * 0.9, a * 0.9 + 12)
        A["la"] = (b * 0.9, b * 0.9 + 12)
        A["bob"] = 0.012 * abs(s(p))
    elif pose == "wave":
        A["ra"] = (150, 165 + 28 * s(t * 7))
        A["bob"] = 0.004 * s(t * 2.2)
    elif pose == "point":
        A["ra"] = (82, 84)
        A["lean"] = 4
        A["bob"] = 0.004 * s(t * 2.2)
    elif pose == "cheer":
        w = 8 * s(t * 8)
        A["ra"] = (128 + w, 150)
        A["la"] = (-128 - w, -150)
        A["jump"] = 0.035 * abs(s(t * 5))
    elif pose == "think":
        A["ra"] = (40, 155)
        A["head"] = -6
        A["bob"] = 0.004 * s(t * 2.0)
    elif pose == "write":
        A["ra"] = (38, 70 + 6 * s(t * 9))
        A["la"] = (30, 60)
        A["lean"] = 10
    elif pose == "hold":
        A["ra"] = (55, 88)
        A["bob"] = 0.004 * s(t * 2.2)
    elif pose == "slump":
        A["lean"] = 16
        A["head"] = 14
        A["ra"], A["la"] = (8, 4), (-8, -4)
    return A


def _lim(o, length, ang, d):
    a = math.radians(ang)
    return (o[0] + length * math.sin(a) * d, o[1] + length * math.cos(a))


def draw_stick(pen, x, gy, h, pose, t, face=1, color=INK, hat=None, holds=None,
               mouth=None, scarf=False, speed=1.0, lw=None, head_fill=CREAM, outfit=None, outfit_kind="tunic"):
    """Draw a stickman with feet on y=gy, centred on x. Returns key joint positions."""
    A = pose_angles(pose, t, speed)
    d = face
    lw = lw or pen.lw
    torso, thigh, shin, ua, fa, hr = 0.30 * h, 0.20 * h, 0.20 * h, 0.15 * h, 0.15 * h, 0.098 * h
    lean = math.radians(A["lean"])
    hip = (0.0, 0.0)
    sh = (torso * math.sin(lean) * d, -torso * math.cos(lean))
    kl = _lim(hip, thigh, A["ll"][0], d)
    fl = _lim(kl, shin, A["ll"][1], d)
    kr = _lim(hip, thigh, A["rl"][0], d)
    fr = _lim(kr, shin, A["rl"][1], d)
    el = _lim(sh, ua, A["la"][0], d)
    hl = _lim(el, fa, A["la"][1], d)
    er = _lim(sh, ua, A["ra"][0], d)
    hr_ = _lim(er, fa, A["ra"][1], d)
    ha = lean * 1.2 + math.radians(A["head"])
    hc = (sh[0] + 0.13 * h * math.sin(ha) * d, sh[1] - 0.13 * h * math.cos(ha))

    oy = gy - max(fl[1], fr[1]) - A["jump"] * h - A["bob"] * h

    def T(p):
        return (p[0] + x, p[1] + oy)

    foot = 0.05 * h * d
    pen.line([T(hip), T(kl), T(fl), T((fl[0] + foot, fl[1]))], w=lw, color=color)
    pen.line([T(hip), T(kr), T(fr), T((fr[0] + foot, fr[1]))], w=lw, color=color)
    if outfit:  # clothing drawn over the legs, under the arms
        bw = 0.085 * h
        if outfit_kind == "robe":
            by, bb = 0.33 * h, 0.15 * h
        else:
            by, bb = 0.07 * h, 0.105 * h
        pen.poly([T((sh[0] - bw, sh[1] + 0.01 * h)), T((sh[0] + bw, sh[1] + 0.01 * h)),
                  T((bb, by)), T((-bb, by))], fill=outfit, outline=color, w=lw * 0.9)
        pen.line([T((-0.095 * h, 0.01 * h)), T((0.095 * h, 0.01 * h))], w=lw * 0.7, color=color)
    pen.line([T(hip), T(sh)], w=lw, color=color)
    pen.line([T(sh), T(el), T(hl)], w=lw, color=color)
    pen.line([T(sh), T(er), T(hr_)], w=lw, color=color)
    if scarf:
        s0 = T((sh[0] - 0.04 * h * d, sh[1] + 0.012 * h))
        s1 = T((sh[0] + 0.04 * h * d, sh[1] + 0.012 * h))
        pen.line([s0, s1], w=lw * 1.5, color=RED)
        pen.line([s0, T((sh[0] - 0.09 * h * d, sh[1] + 0.09 * h))], w=lw * 1.1, color=RED)

    c = T(hc)
    pen.circle(c[0], c[1], hr, fill=head_fill, outline=color, w=lw)
    ex = c[0] + d * 0.02 * h
    for dx in (-0.034 * h, 0.034 * h):
        pen.circle(ex + dx, c[1] - 0.016 * h, max(1.6, lw * 0.42), fill=color, outline=None, wob=False)
    my = c[1] + 0.045 * h
    mx = c[0] + d * 0.02 * h
    if mouth is not None and mouth > 0.08:
        pen.ellipse(mx, my, 0.026 * h, (0.01 + 0.03 * mouth) * h, fill=color, outline=None, wob=False)
    else:
        pen.line([(mx - 0.026 * h, my), (mx + 0.026 * h, my + 0.005 * h)], w=lw * 0.55, color=color, wob=False)

    if hat:
        _hat(pen, hat, c, hr, lw)
    if holds:
        from props import draw_held
        hx, hy = T(hr_)
        draw_held(pen, holds, hx, hy, h, t)
    return {"hand_r": T(hr_), "hand_l": T(hl), "head": c, "hr": hr}


def _hat(pen, kind, c, r, lw):
    top = c[1] - r
    if kind == "crown":
        pen.poly([(c[0] - 0.8 * r, top + 0.15 * r), (c[0] - 0.8 * r, top - 0.7 * r),
                  (c[0] - 0.4 * r, top - 0.25 * r), (c[0], top - 0.85 * r),
                  (c[0] + 0.4 * r, top - 0.25 * r), (c[0] + 0.8 * r, top - 0.7 * r),
                  (c[0] + 0.8 * r, top + 0.15 * r)], fill=GOLD, outline=INK, w=lw * 0.8)
    elif kind in ("helmet", "cap"):
        fill = GRAY if kind == "helmet" else RED
        pts = [(c[0] + math.cos(math.radians(a)) * 1.08 * r, c[1] - 0.1 * r + math.sin(math.radians(a)) * 1.08 * r)
               for a in range(180, 361, 15)]
        pen.poly(pts, fill=fill, outline=INK, w=lw * 0.8)
        if kind == "cap":
            pen.line([(c[0] - 1.1 * r, c[1] - 0.1 * r), (c[0] + 1.5 * r, c[1] - 0.1 * r)], w=lw * 0.9, color=INK)
    elif kind == "kasa":  # Edo straw hat
        pen.poly([(c[0] - 1.5 * r, top + 0.45 * r), (c[0], top - 0.75 * r), (c[0] + 1.5 * r, top + 0.45 * r)],
                 fill=(222, 190, 110), outline=INK, w=lw * 0.8)
    elif kind == "nemes":  # Egyptian striped headdress
        pen.poly([(c[0] - 1.15 * r, c[1] + 1.5 * r), (c[0] - 1.1 * r, c[1] - 0.2 * r), (c[0] - 0.6 * r, top - 0.2 * r),
                  (c[0] + 0.6 * r, top - 0.2 * r), (c[0] + 1.1 * r, c[1] - 0.2 * r), (c[0] + 1.15 * r, c[1] + 1.5 * r),
                  (c[0] + 0.85 * r, c[1] + 0.5 * r), (c[0] - 0.85 * r, c[1] + 0.5 * r)],
                 fill=(60, 100, 170), outline=INK, w=lw * 0.8)
        pen.line([(c[0] - 0.9 * r, top + 0.1 * r), (c[0] + 0.9 * r, top + 0.1 * r)], w=lw * 0.8, color=GOLD)
    elif kind == "laurel":
        for k in range(7):
            a = math.radians(200 + k * 23)
            pen.circle(c[0] + math.cos(a) * 1.02 * r, c[1] + math.sin(a) * 1.02 * r, 0.2 * r, fill=GREEN, outline=INK, w=lw * 0.6)
    elif kind == "viking":
        pts = [(c[0] + math.cos(math.radians(a)) * 1.08 * r, c[1] - 0.1 * r + math.sin(math.radians(a)) * 1.08 * r)
               for a in range(180, 361, 15)]
        pen.poly(pts, fill=GRAY, outline=INK, w=lw * 0.8)
        for sgn in (-1, 1):
            pen.poly([(c[0] + sgn * 1.0 * r, c[1] - 0.45 * r), (c[0] + sgn * 1.7 * r, top - 0.7 * r),
                      (c[0] + sgn * 1.25 * r, c[1] - 0.55 * r)], fill=CREAM, outline=INK, w=lw * 0.7)
    elif kind == "tophat":
        pen.rect(c[0] - 0.7 * r, top - 1.1 * r, c[0] + 0.7 * r, top + 0.1 * r, fill=(45, 45, 52), outline=INK, w=lw * 0.8)
        pen.rect(c[0] - 1.1 * r, top - 0.05 * r, c[0] + 1.1 * r, top + 0.2 * r, fill=(45, 45, 52), outline=INK, w=lw * 0.8)
    elif kind == "hood":
        pen.poly([(c[0] - 1.2 * r, c[1] + 0.9 * r), (c[0] - 1.1 * r, c[1] - 0.3 * r), (c[0], top - 0.55 * r),
                  (c[0] + 1.1 * r, c[1] - 0.3 * r), (c[0] + 1.2 * r, c[1] + 0.9 * r)], fill=BROWN, outline=INK, w=lw * 0.8)
        pen.circle(c[0], c[1] + 0.05 * r, 0.8 * r, fill=(255, 255, 255), outline=INK, w=lw)
    elif kind == "tricorn":
        pen.poly([(c[0] - 1.5 * r, top + 0.35 * r), (c[0] - 0.9 * r, top - 0.5 * r), (c[0] + 0.9 * r, top - 0.5 * r),
                  (c[0] + 1.5 * r, top + 0.35 * r)], fill=(50, 50, 70), outline=INK, w=lw * 0.8)
    elif kind == "turban":
        pen.ellipse(c[0], top + 0.1 * r, 1.15 * r, 0.7 * r, fill=(240, 235, 220), outline=INK, w=lw * 0.8)
        pen.circle(c[0], top + 0.1 * r, 0.2 * r, fill=RED, outline=INK, w=lw * 0.6)
    elif kind == "kabuto":  # samurai helmet
        _hat(pen, "helmet", c, r, lw)
        pen.poly([(c[0], top - 0.1 * r), (c[0] - 0.5 * r, top - 1.0 * r), (c[0], top - 0.55 * r), (c[0] + 0.5 * r, top - 1.0 * r)],
                 fill=GOLD, outline=INK, w=lw * 0.7)
    elif kind == "cowboy":
        pen.ellipse(c[0], top + 0.2 * r, 1.7 * r, 0.3 * r, fill=BROWN, outline=INK, w=lw * 0.8)
        pen.rect(c[0] - 0.7 * r, top - 0.7 * r, c[0] + 0.7 * r, top + 0.2 * r, fill=BROWN, outline=INK, w=lw * 0.8)

