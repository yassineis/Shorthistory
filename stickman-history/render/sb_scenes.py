"""Five storybook history scenes + the subscribe background. Each scene builds 4 layers
(far, mid, ground, fg) so the camera can do parallax, and lists its characters."""
import math

import numpy as np

from sb_draw import Ctx, INK, IVORY, W, H, MX, MY, mix, shade_of

X0, X1, Y1 = -MX, W + MX, H + MY
GROUND = 770


def cloud(c, x, y, s, col=(255, 251, 244)):
    sh = shade_of(col, 0.9)
    for dx, dy, r in ((-1.1, 0.15, 0.55), (-0.4, -0.1, 0.8), (0.5, -0.05, 0.72), (1.2, 0.15, 0.5), (0.1, 0.2, 0.65)):
        c.cel_circle(x + dx * s, y + dy * s, r * s, col, sh, ink=None, w=0)


def sky(c, top, bot, y1=GROUND + 40):
    c.grad(X0, -MY, X1, y1, top, bot)
    c.rect(X0, y1 - 1, X1, Y1, fill=bot, ink=None, w=0)


def rays(c, x, y, spread, n, color, alpha=0.13, length=1200):
    from PIL import Image, ImageDraw
    lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        a = math.radians(90 - spread / 2 + spread * i / max(1, n - 1))
        wid = math.radians(2.2)
        p0 = c.P(x, y)
        p1 = c.P(x + math.cos(a - wid) * length, y + math.sin(a - wid) * length)
        p2 = c.P(x + math.cos(a + wid) * length, y + math.sin(a + wid) * length)
        d.polygon([p0, p1, p2], fill=color + (int(alpha * 255),))
    c.img.alpha_composite(lay)


def ground(c, top, bot, y0=GROUND):
    c.grad(X0, y0, X1, Y1, top, bot)
    c.line([(X0, y0), (X1, y0)], INK, 3.2)


def speckles(c, y0, y1, color, n=40, seed=0, size=(8, 22)):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x, y = rng.uniform(X0, X1), rng.uniform(y0, y1)
        l = rng.uniform(*size)
        c.line([(x - l / 2, y), (x + l / 2, y + 1.5)], color, 2.0)


def stepped_pyramid(c, x0, x1, base, top_y, steps, lit, shade, wlast=0.12):
    # left face lit, right face shade; drawn as stacked blocks
    n = steps
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        y0, y1 = base - (base - top_y) * t0, base - (base - top_y) * t1
        xa0, xa1 = x0 + (x1 - x0) / 2 * t0 * (1 - wlast), x1 - (x1 - x0) / 2 * t0 * (1 - wlast)
        xb0, xb1 = x0 + (x1 - x0) / 2 * t1 * (1 - wlast), x1 - (x1 - x0) / 2 * t1 * (1 - wlast)
        mid = (x0 + x1) / 2
        c.poly([(xa0, y0), (mid, y0), (mid, y1), (xb0, y1)], fill=lit if i % 2 == 0 else mix(lit, shade, .25), ink=INK, w=2.4)
        c.poly([(mid, y0), (xa1, y0), (xb1, y1), (mid, y1)], fill=shade if i % 2 == 0 else mix(shade, lit, .2), ink=INK, w=2.4)


def palm(c, x, base, h, lean=1):
    c.line([(x, base), (x + lean * h * .1, base - h * .5), (x + lean * h * .18, base - h)], (148, 108, 76), 9)
    c.line([(x, base), (x + lean * h * .1, base - h * .5), (x + lean * h * .18, base - h)], INK, 2.0)
    tx, ty = x + lean * h * .18, base - h
    for a in (-170, -140, -105, -75, -40, -10):
        r = math.radians(a)
        pts = [(tx, ty), (tx + math.cos(r - .22) * h * .42, ty + math.sin(r - .22) * h * .3 + h * .06),
               (tx + math.cos(r) * h * .55, ty + math.sin(r) * h * .33 + h * .16),
               (tx + math.cos(r + .22) * h * .42, ty + math.sin(r + .22) * h * .3 + h * .06)]
        c.cel(pts, (118, 152, 112), (92, 124, 90), w=2.4)


def pine(c, x, base, h, col=(98, 128, 108)):
    c.rect(x - h * .035, base - h * .15, x + h * .035, base, fill=(120, 90, 70), w=2)
    for i in range(3):
        y = base - h * .1 - i * h * .26
        wd = h * (.3 - .06 * i)
        c.cel([(x - wd, y), (x, y - h * .42), (x + wd, y)], col, shade_of(col, .82), w=2.4)


def tree_round(c, x, base, h, col):
    c.rect(x - h * .04, base - h * .5, x + h * .04, base, fill=(136, 100, 80), w=2.4)
    for dx, dy, r in ((-.2, -.58, .3), (.2, -.58, .3), (0, -.78, .34), (0, -.52, .3)):
        c.cel_circle(x + dx * h, base + dy * h, r * h, col, shade_of(col, .84), w=2.4, wob=.015, seed=int(x + dy * 10))


def column(c, x, base, h, wd, col=(240, 228, 220), sh=(208, 192, 190), cap=True):
    c.cel([(x - wd / 2, base - h), (x + wd / 2, base - h), (x + wd / 2, base), (x - wd / 2, base)], col, sh, w=2.6)
    for k in (-.18, .05, .27):
        c.line([(x + k * wd, base - h * .92), (x + k * wd, base - h * .08)], mix(col, sh, .6), 1.8)
    if cap:
        c.cel([(x - wd * .72, base - h - h * .07), (x + wd * .72, base - h - h * .07), (x + wd * .72, base - h), (x - wd * .72, base - h)], col, sh, w=2.6)
    c.cel([(x - wd * .7, base - h * .05), (x + wd * .7, base - h * .05), (x + wd * .7, base), (x - wd * .7, base)], col, sh, w=2.6)


def arch_wall(c, x0, x1, base, h, n, col, sh):
    wd = (x1 - x0) / n
    c.cel([(x0, base - h), (x1, base - h), (x1, base), (x0, base)], col, sh, w=2.6)
    for i in range(n):
        cx = x0 + wd * (i + .5)
        pts = [(cx - wd * .3, base)] + [(cx + wd * .3 * math.cos(math.radians(a)), base - h * .55 - wd * .3 * math.sin(math.radians(a))) for a in range(180, -1, -15)] + [(cx + wd * .3, base)]
        c.poly(pts, fill=mix(sh, (60, 50, 60), .35), w=2.4)


# =========================================================================== 1. EGYPT
def egypt(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (186, 210, 222), (248, 226, 190))
    far.glow(520, 430, 360, (255, 214, 150), .55)
    far.circle(520, 430, 62, fill=(255, 238, 200), ink=None, w=0)
    for x, y, s in ((90, 150, 80), (400, 90, 60), (610, 240, 70)):
        cloud(far, x, y, s, (252, 240, 226))
    # distant dunes + pyramids
    far.cel([(X0, 760), (-40, 700), (180, 668), (380, 712), (560, 690), (X1, 730), (X1, 800), (X0, 800)], (234, 208, 168), (214, 184, 148), w=2.4)
    stepped_pyramid(far, 40, 260, 722, 610, 1, (226, 196, 150), (196, 164, 126))
    stepped_pyramid(far, 150, 300, 724, 650, 1, (230, 200, 154), (200, 168, 130))
    # the big pyramid under construction (mid)
    stepped_pyramid(mid, 280, 800, 790, 360, 9, (238, 210, 166), (206, 174, 134), wlast=0.2)
    mid.poly([(300, 788), (520, 540), (590, 540), (390, 788)], fill=(214, 184, 142), w=2.6)  # ramp
    for i in range(7):
        t = i / 6
        mid.line([(310 + t * 210, 780 - t * 240), (326 + t * 210, 780 - t * 240 - 14)], INK, 2.0)
    for x in (70, 640):
        palm(mid, x, 790, 300, 1 if x < 300 else -1)
    ground(gr, (236, 212, 170), (212, 184, 142))
    speckles(gr, GROUND + 30, H + 100, (200, 172, 134), 46, 3)
    for i in range(7):
        gr.ellipse(120 + i * 78, 1100 + (i % 2) * 40, 12, 5, fill=(214, 188, 148), ink=None, w=0)
    # foreground
    fg.cel_circle(-10, 1230, 80, (214, 196, 168), (186, 168, 144), w=3, wob=.03, seed=3)
    fg.cel_circle(760, 1200, 60, (214, 196, 168), (186, 168, 144), w=3, wob=.03, seed=5)
    for x in (610, 650, 690):
        fg.line([(x, 1250), (x - 8, 1210)], (150, 140, 100), 3)
        fg.line([(x + 6, 1250), (x + 12, 1215)], (150, 140, 100), 3)
    chars = [
        dict(name="worker", x=230, gy=940, h=350, outfit="linen", hat="bandana", emotion="worry", pose="pull", face=1, lean=.07, emote="sweat", beard=False),
        dict(name="scribe", x=560, gy=935, h=345, outfit="ochre", hat="nemes", emotion="curious", pose="show", face=-1, holds="scroll", robe=True, trim=True),
    ]
    props = [dict(kind="block", x=400, gy=940, w=150, h=100)]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=props, light=(1, -1))


# =========================================================================== 2. VIKING
def viking(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (206, 202, 218), (250, 218, 186), y1=700)
    far.glow(250, 690, 420, (255, 200, 150), .6)
    far.circle(250, 690, 58, fill=(255, 232, 196), ink=None, w=0)
    for x, y, s in ((120, 180, 90), (520, 130, 70), (420, 310, 80)):
        cloud(far, x, y, s, (252, 232, 226))
    for x0, x1, top in ((X0, 300, 470), (180, 560, 400), (420, X1, 500)):
        far.cel([(x0, 700), ((x0 + x1) / 2 - 20, top), ((x0 + x1) / 2 + 30, top + 40), (x1, 700)], (152, 164, 188), (124, 136, 164), w=2.6)
        mx = (x0 + x1) / 2
        far.cel([(mx - 52, top + 62), (mx - 20, top), (mx + 30, top + 40), (mx + 4, top + 50), (mx - 18, top + 74)], (246, 244, 246), (214, 214, 228), w=2.2)
    # sea
    mid.grad(X0, 690, X1, GROUND + 70, (156, 182, 196), (120, 150, 172))
    mid.line([(X0, 690), (X1, 690)], INK, 2.6)
    for i in range(18):
        x, y = -60 + i * 52, 720 + (i % 4) * 18
        mid.arc(x, y, 22, 8, 200, 340, (232, 240, 244), 2.8)
    # longship
    hull = [(330, 700), (640, 700), (680, 660), (664, 728), (560, 766), (390, 766), (310, 728), (300, 664)]
    mid.cel(hull, (150, 108, 80), (120, 84, 62), w=3.2)
    for i in range(7):
        mid.circle(350 + i * 44, 722, 14, fill=(222, 190, 120) if i % 2 else (178, 82, 76), w=2.2)
    mid.line([(485, 700), (485, 420)], (130, 96, 70), 8)
    mid.line([(485, 700), (485, 420)], INK, 2)
    mid.cel([(420, 450), (550, 450), (560, 640), (410, 640)], (246, 236, 214), (218, 204, 180), w=3)
    for i in range(4):
        mid.line([(432 + i * 32, 452), (432 + i * 32, 640)], (178, 82, 76), 6)
    mid.cel([(300, 664), (270, 600), (296, 590), (318, 640)], (150, 108, 80), (120, 84, 62), w=3)  # dragon prow
    ground(gr, (140, 168, 128), (108, 136, 100), y0=GROUND + 30)
    gr.cel([(X0, GROUND + 30), (X1, GROUND + 30), (X1, GROUND + 78), (X0, GROUND + 94)], (230, 214, 178), (206, 190, 156), w=2.6)
    speckles(gr, GROUND + 140, H + 100, (96, 124, 90), 40, 8)
    for x, s in ((60, 1.1), (140, .8), (660, 1.0)):
        pine(gr, x, GROUND + 40, 260 * s)
    fg.cel_circle(40, 1230, 90, (160, 162, 170), (128, 130, 142), w=3, wob=.03, seed=4)
    fg.cel_circle(690, 1210, 70, (160, 162, 170), (128, 130, 142), w=3, wob=.03, seed=2)
    chars = [
        dict(name="leif", x=250, gy=960, h=360, outfit="cocoa", hat="viking", emotion="surprise", pose="point", face=1, beard=True, cape="red", gaze=1),
        dict(name="crew", x=520, gy=950, h=335, outfit="teal", hat="hood", emotion="happy", pose="hold", face=-1, holds="oar"),
    ]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=[], light=(-1, -1))


# =========================================================================== 3. EDO
def edo(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (190, 214, 232), (250, 232, 226))
    for x, y, s in ((110, 190, 80), (520, 120, 90)):
        cloud(far, x, y, s)
    far.cel([(130, 700), (360, 380), (390, 380), (610, 700)], (168, 182, 208), (140, 154, 186), w=2.6)
    far.cel([(300, 470), (360, 380), (390, 380), (440, 470), (405, 456), (375, 476), (345, 454)], (248, 246, 248), (222, 222, 236), w=2.2)
    # castle on hill
    far.cel([(X0, 760), (60, 690), (300, 650), (460, 700), (X1, 760)], (146, 172, 136), (120, 146, 114), w=2.6)
    for i, (w_, y_) in enumerate(((120, 640), (90, 590), (60, 545))):
        far.cel([(540 - w_ / 2, y_ + 50), (540 + w_ / 2, y_ + 50), (540 + w_ / 2 - 6, y_), (540 - w_ / 2 + 6, y_)], (246, 240, 230), (218, 208, 204), w=2.2)
        far.cel([(540 - w_ * .7, y_ + 4), (540, y_ - 26), (540 + w_ * .7, y_ + 4)], (92, 98, 122), (70, 76, 100), w=2.2)
    # shops left and right
    def shop(x0, x1, top, roofc=(84, 92, 118)):
        mid.cel([(x0, top), (x1, top), (x1, GROUND + 20), (x0, GROUND + 20)], (236, 216, 184), (206, 184, 154), w=3)
        for i in range(5):
            mid.line([(x0 + (x1 - x0) * i / 4, top), (x0 + (x1 - x0) * i / 4, GROUND + 20)], (146, 108, 84), 5)
        mid.cel([(x0 - 30, top + 6), (x1 + 30, top + 6), (x1 + 6, top - 62), (x0 - 6, top - 62)], roofc, shade_of(roofc, .8), w=3.2)
        mid.cel([(x0 + 14, top + 70), (x1 - 14, top + 70), (x1 - 14, GROUND + 20), (x0 + 14, GROUND + 20)], (226, 196, 150), (194, 164, 124), w=2.4)
        for i in range(3):
            xx = x0 + 26 + i * (x1 - x0 - 52) / 2
            mid.cel([(xx - 22, top + 34), (xx + 22, top + 34), (xx + 18, top + 92), (xx - 18, top + 92)], (240, 232, 214) if i != 1 else (82, 98, 140), (210, 200, 184), w=2.2)
    shop(X0 + 20, 170, 560)
    shop(560, X1 - 10, 520, (96, 84, 108))
    for x, y in ((190, 610), (540, 600)):
        mid.line([(x, y - 40), (x, y - 14)], INK, 2)
        mid.ellipse(x, y + 8, 18, 26, fill=(198, 86, 78), w=2.6)
        mid.line([(x - 10, y - 6), (x + 10, y - 6)], (150, 60, 56), 2)
    # cherry blossom tree
    mid.line([(330, 790), (340, 640), (300, 560)], (120, 88, 76), 14)
    mid.line([(340, 650), (410, 580)], (120, 88, 76), 10)
    for dx, dy, r in ((300, 520, 70), (360, 500, 80), (250, 560, 60), (420, 560, 60), (330, 450, 62), (400, 510, 55)):
        mid.cel_circle(dx, dy, r, (244, 196, 206), (216, 160, 176), w=2.6, wob=.02, seed=dx)
    ground(gr, (214, 186, 150), (190, 164, 130))
    speckles(gr, GROUND + 30, H + 100, (176, 150, 118), 50, 6)
    for i in range(14):
        gr.ellipse(40 + i * 52, 1000 + (i * 37) % 230, 7, 3, fill=(246, 206, 214), ink=None, w=0)
    for x, y in ((650, 1210),):
        fg.cel([(x - 40, y - 90), (x + 40, y - 90), (x + 50, y), (x - 50, y)], (170, 170, 176), (140, 140, 150), w=3)
        fg.cel([(x - 56, y - 120), (x + 56, y - 120), (x + 40, y - 90), (x - 40, y - 90)], (170, 170, 176), (140, 140, 150), w=3)
    chars = [
        dict(name="samurai", x=240, gy=955, h=360, outfit="navy", hat="topknot", emotion="curious", pose="think", face=1, emote="?", trim=(222, 184, 96)),
        dict(name="seller", x=520, gy=950, h=335, outfit="linen", hat="towel", emotion="happy", pose="show", face=-1, holds="bread"),
    ]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=[], light=(-1, -1))


# =========================================================================== 4. ROME
def rome(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (170, 198, 224), (244, 228, 206), y1=760)
    for x, y, s in ((140, 160, 90), (520, 230, 80), (380, 90, 60)):
        cloud(far, x, y, s)
    far.cel([(X0, 760), (80, 640), (260, 610), (420, 690), (600, 630), (X1, 700), (X1, 800), (X0, 800)], (150, 172, 138), (124, 146, 112), w=2.6)
    for x, h in ((60, 150), (110, 110), (640, 160)):
        far.cel([(x - 14, 700), (x, 700 - h), (x + 14, 700)], (84, 112, 94), (64, 92, 76), w=2.2)
    arch_wall(far, X0, 300, 720, 150, 4, (232, 214, 196), (204, 184, 172))
    # temple
    mid.cel([(150, 760), (600, 760), (600, 738), (150, 738)], (226, 212, 204), (198, 184, 180), w=3)
    mid.cel([(170, 738), (580, 738), (580, 716), (170, 716)], (232, 218, 210), (204, 190, 186), w=3)
    for i in range(6):
        column(mid, 205 + i * 62, 716, 270, 38)
    mid.cel([(150, 446), (600, 446), (600, 424), (150, 424)], (234, 220, 212), (206, 192, 188), w=3)
    mid.cel([(150, 424), (375, 300), (600, 424)], (222, 150, 124), (190, 120, 100), w=3.2)
    mid.cel([(220, 424), (375, 338), (530, 424)], (238, 214, 196), (212, 188, 172), w=2.4)
    mid.circle(375, 396, 18, fill=(222, 184, 96), w=2.4)
    # banner
    mid.line([(660, 300), (660, 560)], (130, 96, 70), 6)
    mid.cel([(630, 330), (690, 330), (690, 520), (660, 560), (630, 520)], (150, 62, 70), (120, 46, 58), w=3)
    mid.circle(660, 380, 14, fill=(222, 184, 96), w=2.2)
    ground(gr, (238, 228, 214), (214, 202, 190))
    for i in range(9):  # floor tiles, simple perspective
        y = GROUND + 20 + (i ** 1.7) * 14
        gr.line([(X0, y), (X1, y)], (200, 188, 180), 2)
    for i in range(-6, 14):
        gr.line([(360 + (i - 4) * 14, GROUND + 22), (360 + (i - 4) * 150, Y1)], (200, 188, 180), 2)
    fg.cel([(-70, 1280), (-70, 1000), (30, 1000), (30, 1280)], (234, 220, 214), (206, 192, 188), w=3)
    fg.cel([(-84, 1000), (44, 1000), (44, 976), (-84, 976)], (238, 224, 218), (210, 196, 192), w=3)
    chars = [
        dict(name="general", x=250, gy=960, h=365, outfit="white", hat="roman", emotion="proud", pose="point", face=1, cape="red", trim=(222, 184, 96)),
        dict(name="soldier", x=530, gy=950, h=335, outfit="rust", hat="laurel", emotion="worry", pose="hold", face=-1, holds="stick", emote="sweat"),
    ]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=[], light=(-1, -1))


# =========================================================================== 5. WORKSHOP
def workshop(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 40, (150, 112, 90), (190, 148, 112))
    far.rect(X0, GROUND + 39, X1, Y1, fill=(190, 148, 112), ink=None, w=0)
    for i in range(-2, 14):  # wall planks
        far.line([(i * 62, -MY), (i * 62, GROUND + 40)], (132, 98, 78), 3)
    # arched window with light
    far.cel([(480, 420), (480, 250)] + [(570 + 90 * math.cos(math.radians(a)), 250 - 90 * math.sin(math.radians(a))) for a in range(180, -1, -15)] + [(660, 420)],
            (186, 214, 228), (160, 190, 210), w=5)
    far.line([(570, 160), (570, 420)], (120, 88, 70), 5)
    far.line([(480, 300), (660, 300)], (120, 88, 70), 5)
    far.circle(530, 230, 24, fill=(255, 250, 236), ink=None, w=0)
    far.glow(570, 330, 300, (255, 232, 170), .5)
    rays(far, 570, 330, 70, 8, (255, 238, 190), .10, 900)
    # beams
    far.cel([(X0, 70), (X1, 70), (X1, 110), (X0, 110)], (118, 84, 68), (92, 64, 54), w=3)
    far.cel([(120, -MY), (160, -MY), (160, GROUND + 40), (120, GROUND + 40)], (118, 84, 68), (92, 64, 54), w=3)
    # shelves with books
    for y in (360, 500):
        mid.cel([(X0 + 10, y), (330, y), (330, y + 16), (X0 + 10, y + 16)], (122, 88, 70), (96, 68, 56), w=3)
        x = -60
        cols = [(150, 82, 78), (86, 110, 134), (200, 164, 96), (96, 132, 100), (124, 90, 124)]
        for i in range(10):
            hgt = 64 + (i * 13) % 28
            wd = 20 + (i * 7) % 10
            mid.cel([(x, y), (x + wd, y), (x + wd, y - hgt), (x, y - hgt)], cols[i % 5], shade_of(cols[i % 5], .82), w=2.4)
            x += wd + 2
    # printing press
    mid.cel([(380, 770), (480, 770), (480, 520), (380, 520)], (142, 104, 78), (114, 82, 62), w=3.4)
    mid.cel([(540, 770), (640, 770), (640, 520), (540, 520)], (142, 104, 78), (114, 82, 62), w=3.4)
    mid.cel([(360, 520), (660, 520), (660, 480), (360, 480)], (156, 116, 86), (124, 90, 68), w=3.4)
    mid.cel([(420, 700), (600, 700), (600, 740), (420, 740)], (96, 80, 80), (72, 60, 64), w=3.2)
    mid.line([(510, 480), (510, 400)], (96, 80, 80), 14)
    mid.line([(420, 396), (600, 396)], (156, 116, 86), 11)
    mid.circle(420, 396, 13, fill=(178, 134, 98), w=3)
    mid.circle(600, 396, 13, fill=(178, 134, 98), w=3)
    ground(gr, (176, 134, 100), (146, 108, 82))
    for i in range(10):
        y = GROUND + 20 + i * 54
        gr.line([(X0, y), (X1, y)], (130, 96, 74), 2.4)
    for i in range(0, 14):
        gr.line([(i * 120 - 60 + (i * 53) % 80, GROUND + 20), (i * 120 - 60 + (i * 53) % 80, Y1)], (130, 96, 74), 2)
    for j in range(5):  # paper stacks
        fg.cel([(560, 1250 - j * 22), (690, 1250 - j * 22), (698, 1232 - j * 22), (568, 1232 - j * 22)], (248, 242, 228), (222, 214, 200), w=2.4)
    fg.cel([(-40, 1280), (-40, 1170), (60, 1170), (60, 1280)], (110, 84, 72), (86, 64, 56), w=3)
    chars = [
        dict(name="printer", x=260, gy=955, h=360, outfit="charcoal", hat="cap", emotion="proud", pose="pull", face=1, beard=True, lean=.05),
        dict(name="apprentice", x=520, gy=1000, h=330, outfit="sage", hat=None, emotion="happy", pose="show", face=-1, holds="sheet"),
    ]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=[], light=(1, -1))


def subscribe(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (196, 218, 232), (252, 238, 220), y1=900)
    far.glow(580, 260, 380, (255, 226, 170), .5)
    for x, y, s in ((120, 170, 80), (560, 120, 70), (330, 300, 60)):
        cloud(far, x, y, s)
    mid.cel([(X0, 880), (120, 780), (330, 760), (560, 830), (X1, 800), (X1, 960), (X0, 960)], (162, 184, 140), (134, 156, 114), w=3)
    mid.cel([(X0, 960), (200, 880), (480, 900), (X1, 860), (X1, 1020), (X0, 1020)], (146, 170, 126), (120, 144, 104), w=3)
    ground(gr, (176, 194, 146), (150, 172, 124), y0=1010)
    for x, y, c_ in ((90, 1100, (240, 178, 188)), (610, 1160, (246, 224, 160)), (200, 1210, (240, 178, 188))):
        for a in range(5):
            fg.circle(x + 10 * math.cos(a * 1.256), y + 10 * math.sin(a * 1.256), 7, fill=c_, w=2)
        fg.circle(x, y, 5, fill=(250, 220, 120), w=1.6)
    chars = [dict(name="host", x=220, gy=1000, h=520, outfit="teal", hat="bandana", emotion="happy", pose="wave", face=1)]
    return dict(layers=[far, mid, gr, fg], chars=chars, props=[], light=(-1, -1))


SCENES = {"egypt": egypt, "viking": viking, "edo": edo, "rome": rome, "workshop": workshop, "subscribe": subscribe}
