"""Storybook backdrops for every setting the story writer can choose (18). Each returns 4 layers: far, mid, ground, fg.
The first four settings reuse the scenes made for the prototype sketches."""
import math

import numpy as np

from sb_draw import Ctx, INK, GOLD, W, H, MX, MY, mix, shade_of
from sb_scenes import (SCENES, X0, X1, Y1, GROUND, cloud, sky, ground, speckles, stepped_pyramid, palm, pine, tree_round, column, rays)


def _fg_rocks(fg, col=(214, 196, 168), sh=(186, 168, 144)):
    fg.cel_circle(-10, 1230, 80, col, sh, w=3, wob=.03, seed=3)
    fg.cel_circle(760, 1200, 60, col, sh, w=3, wob=.03, seed=5)


def _hills(c, y, col, sh, seed=0, amp=60):
    rng = np.random.default_rng(seed)
    pts = [(X0, y + 80)]
    x = X0
    while x < X1:
        pts.append((x, y - rng.uniform(0, amp)))
        x += rng.uniform(120, 220)
    pts += [(X1, y - rng.uniform(0, amp)), (X1, y + 120), (X0, y + 120)]
    c.cel(pts, col, sh, w=2.6)


def medieval_town(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (176, 204, 230), (246, 232, 212))
    for x, y, s in ((110, 170, 80), (520, 120, 70), (380, 300, 60)):
        cloud(far, x, y, s)
    _hills(far, 700, (146, 172, 136), (120, 146, 114), 2)
    # castle on the hill
    for dx, hh in ((-80, 200), (0, 250), (80, 200)):
        far.cel([(430 + dx - 34, 700 - hh), (430 + dx + 34, 700 - hh), (430 + dx + 34, 700), (430 + dx - 34, 700)], (214, 208, 204), (184, 178, 176), w=2.6)
        far.cel([(430 + dx - 42, 700 - hh + 2), (430 + dx, 700 - hh - 80), (430 + dx + 42, 700 - hh + 2)], (176, 84, 84), (146, 64, 68), w=2.8)
    far.cel([(396, 700), (464, 700), (464, 600), (396, 600)], (200, 194, 190), (172, 166, 164), w=2.6)
    # timber houses
    def house(x0, x1, top, roof):
        mid.cel([(x0, top), (x1, top), (x1, GROUND + 20), (x0, GROUND + 20)], (238, 224, 198), (210, 194, 168), w=3)
        for xx in (x0 + (x1 - x0) * .33, x0 + (x1 - x0) * .66):
            mid.line([(xx, top), (xx, GROUND + 20)], (126, 92, 72), 5)
        mid.line([(x0, top + 70), (x1, top + 70)], (126, 92, 72), 5)
        mid.cel([(x0 - 24, top + 4), ((x0 + x1) / 2, top - 96), (x1 + 24, top + 4)], roof, shade_of(roof, .82), w=3.2)
        mid.cel([(x0 + 20, top + 100), (x0 + 60, top + 100), (x0 + 60, GROUND + 20), (x0 + 20, GROUND + 20)], (150, 108, 80), (120, 84, 62), w=2.6)
        mid.rect(x1 - 60, top + 30, x1 - 26, top + 62, fill=(186, 214, 228), w=2.4)
    house(X0 + 10, 150, 560, (176, 98, 84))
    house(570, X1 - 10, 540, (120, 108, 132))
    for x, s in ((330, 1.0),):
        tree_round(mid, x, 790, 260 * s, (112, 150, 100))
    ground(gr, (178, 168, 132), (150, 140, 108))
    gr.cel([(300, GROUND), (440, GROUND), (620, Y1), (120, Y1)], (206, 190, 150), (180, 164, 126), w=0)
    speckles(gr, GROUND + 30, H + 100, (140, 128, 98), 40, 4)
    _fg_rocks(fg, (176, 170, 164), (146, 140, 138))
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def greek_agora(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (150, 196, 236), (240, 238, 232), y1=720)
    for x, y, s in ((120, 190, 80), (540, 130, 70)):
        cloud(far, x, y, s)
    far.grad(X0, 650, X1, 740, (130, 184, 214), (110, 160, 196))
    far.line([(X0, 650), (X1, 650)], INK, 2.4)
    _hills(far, 690, (196, 196, 168), (170, 170, 144), 5, 40)
    # temple on the acropolis
    mid.cel([(120, 560), (640, 560), (680, 600), (80, 600)], (236, 228, 216), (206, 196, 190), w=3)
    for i in range(7):
        column(mid, 150 + i * 70, 560, 200, 34)
    mid.cel([(120, 340), (640, 340), (640, 360), (120, 360)], (240, 232, 222), (210, 200, 194), w=3)
    mid.cel([(120, 340), (380, 250), (640, 340)], (232, 222, 212), (204, 192, 186), w=3.2)
    mid.cel([(190, 340), (380, 276), (570, 340)], (120, 168, 196), (96, 142, 172), w=2.2)
    for x, s in ((60, 1.0), (680, 1.1)):
        tree_round(mid, x, 790, 240 * s, (132, 152, 112))
    ground(gr, (236, 224, 200), (212, 198, 174), y0=GROUND)
    for i in range(7):
        y = GROUND + 20 + (i ** 1.7) * 14
        gr.line([(X0, y), (X1, y)], (200, 186, 164), 2)
    speckles(gr, GROUND + 30, H + 100, (196, 182, 156), 30, 9)
    fg.cel([(-60, 1280), (-60, 1030), (40, 1030), (40, 1280)], (238, 228, 218), (208, 196, 190), w=3)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def china_palace(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (186, 208, 214), (250, 232, 214), y1=760)
    for x, y, s in ((100, 190, 80), (570, 140, 70)):
        cloud(far, x, y, s, (250, 244, 240))
    for x0, x1, top in ((X0, 330, 430), (220, 640, 380), (480, X1, 470)):
        far.cel([(x0, 740), ((x0 + x1) / 2 - 20, top), ((x0 + x1) / 2 + 40, top + 50), (x1, 740)], (158, 184, 186), (130, 158, 164), w=2.4)
    far.grad(X0, 690, X1, 760, (240, 236, 232), (250, 232, 214))
    # palace: red walls, golden tiered roofs
    def tier(cx, w_, y, h_, roof_h):
        mid.cel([(cx - w_ / 2, y), (cx + w_ / 2, y), (cx + w_ / 2, y + h_), (cx - w_ / 2, y + h_)], (190, 66, 60), (156, 48, 48), w=3)
        for i in range(4):
            xx = cx - w_ / 2 + w_ * (i + .5) / 4
            mid.rect(xx - 8, y + 10, xx + 8, y + h_ - 6, fill=(222, 168, 80), w=2)
        mid.cel([(cx - w_ * .72, y + 6), (cx - w_ * .5, y - roof_h), (cx + w_ * .5, y - roof_h), (cx + w_ * .72, y + 6), (cx + w_ * .6, y + 16), (cx - w_ * .6, y + 16)],
                (222, 176, 80), (190, 144, 60), w=3.2)
        mid.line([(cx - w_ * .72, y + 6), (cx - w_ * .84, y - 8)], (190, 144, 60), 5)
        mid.line([(cx + w_ * .72, y + 6), (cx + w_ * .84, y - 8)], (190, 144, 60), 5)
    tier(380, 520, 620, 160, 70)
    tier(380, 360, 470, 130, 64)
    tier(380, 200, 340, 120, 58)
    mid.circle(380, 262, 12, fill=GOLD, w=2.4)
    ground(gr, (214, 202, 188), (190, 178, 166))
    for i in range(10):
        gr.line([(X0, GROUND + 24 + i * 52), (X1, GROUND + 24 + i * 52)], (182, 170, 160), 2)
    for i in range(0, 14):
        gr.line([(i * 70 - 40 + (i * 41) % 40, GROUND + 24), (i * 70 - 40 + (i * 41) % 40, Y1)], (182, 170, 160), 2)
    for x in (60, 690):  # red pillars + lanterns
        fg.rect(x - 24, 940, x + 24, 1290, fill=(190, 66, 60), w=3)
        fg.ellipse(x + (40 if x < 300 else -40), 1010, 20, 28, fill=(214, 76, 68), w=3)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def desert(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (150, 196, 232), (252, 232, 190))
    far.glow(520, 320, 380, (255, 230, 160), .55)
    far.circle(520, 320, 64, fill=(255, 240, 200), ink=None, w=0)
    far.cel_circle(520, 320, 64, (255, 240, 196), (252, 220, 150), w=3)
    cloud(far, 130, 180, 70, (252, 240, 226))
    far.cel([(X0, 760), (100, 640), (320, 700), (520, 620), (X1, 700), (X1, 800), (X0, 800)], (238, 210, 164), (214, 184, 140), w=2.6)
    mid.cel([(X0, 800), (200, 700), (460, 770), (640, 690), (X1, 760), (X1, 860), (X0, 860)], (232, 202, 152), (208, 176, 128), w=2.6)
    palm(mid, 80, 800, 280, 1)
    palm(mid, 150, 800, 220, -1)
    for x, y, s in ((560, 780, 1.0),):  # cactus
        mid.cel([(x - 14, y), (x + 14, y), (x + 14, y - 150 * s), (x - 14, y - 150 * s)], (116, 156, 108), (92, 130, 88), w=2.6)
        mid.cel([(x + 14, y - 80 * s), (x + 48, y - 80 * s), (x + 48, y - 120 * s), (x + 34, y - 120 * s), (x + 34, y - 94 * s), (x + 14, y - 94 * s)], (116, 156, 108), (92, 130, 88), w=2.4)
    ground(gr, (238, 212, 168), (216, 188, 146))
    speckles(gr, GROUND + 30, H + 100, (206, 176, 136), 50, 3)
    _fg_rocks(fg)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(1, -1))


def ship_sea(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (170, 204, 232), (250, 236, 214), y1=690)
    for x, y, s in ((120, 180, 90), (530, 130, 70), (420, 320, 70)):
        cloud(far, x, y, s)
    mid.grad(X0, 640, X1, 790, (120, 168, 198), (88, 134, 170))
    mid.line([(X0, 640), (X1, 640)], INK, 2.6)
    for i in range(20):
        x, y = -60 + i * 48, 670 + (i % 5) * 20
        mid.arc(x, y, 20, 7, 200, 340, (232, 242, 246), 2.8)
    # far ship + mast and sail of this ship
    mid.cel([(60, 650), (170, 650), (150, 676), (80, 676)], (140, 104, 80), (112, 80, 62), w=2.4)
    mid.line([(115, 650), (115, 560)], (120, 90, 70), 4)
    mid.cel([(116, 560), (160, 640), (116, 646)], (246, 238, 220), (218, 206, 184), w=2.4)
    mid.line([(520, GROUND + 20), (520, 140)], (130, 96, 70), 14)
    mid.cel([(540, 180), (720, 200), (716, 520), (540, 540)], (244, 236, 218), (216, 204, 182), w=3.4)
    mid.cel([(500, 170), (360, 190), (364, 500), (500, 520)], (238, 228, 208), (210, 196, 172), w=3.4)
    mid.cel([(520, 140), (580, 130), (520, 118)], (190, 70, 70), (156, 52, 56), w=2.4)
    # deck
    ground(gr, (180, 132, 92), (150, 106, 72), y0=GROUND + 20)
    for i in range(14):
        y = GROUND + 40 + i * 42
        gr.line([(X0, y), (X1, y)], (120, 88, 62), 2.4)
    for i in range(0, 12):
        gr.line([(i * 90 - 20 + (i * 37) % 50, GROUND + 40), (i * 90 - 20 + (i * 37) % 50, Y1)], (120, 88, 62), 1.8)
    gr.line([(X0, GROUND + 20), (X1, GROUND + 20)], (96, 70, 50), 12)
    for x in range(-40, 760, 80):  # rail posts
        gr.line([(x, GROUND + 20), (x, GROUND - 60)], (120, 88, 62), 8)
    gr.line([(X0, GROUND - 56), (X1, GROUND - 56)], (120, 88, 62), 7)
    fg.cel([(560, 1280), (560, 1190), (700, 1190), (700, 1280)], (150, 108, 76), (122, 86, 60), w=3)
    fg.cel_circle(80, 1250, 56, (176, 152, 120), (146, 124, 96), w=3, wob=.02, seed=2)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def old_west(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (236, 168, 122), (252, 226, 176))
    far.glow(250, 640, 420, (255, 206, 140), .6)
    far.circle(250, 640, 54, fill=(255, 236, 190), ink=None, w=0)
    for x0, x1, top in ((300, 500, 520), (480, 760, 470), (X0, 200, 560)):  # mesas
        far.cel([(x0, 720), (x0 + 20, top), (x1 - 20, top), (x1, 720)], (196, 112, 88), (164, 88, 70), w=2.6)
        for i in range(3):
            far.line([(x0 + 12, top + 30 + i * 36), (x1 - 12, top + 30 + i * 36)], (176, 98, 78), 2)
    # saloon
    mid.cel([(60, 560), (380, 560), (380, GROUND + 20), (60, GROUND + 20)], (190, 140, 98), (160, 114, 78), w=3)
    mid.cel([(40, 500), (400, 500), (400, 560), (40, 560)], (176, 126, 88), (146, 102, 70), w=3)
    mid.rect(150, 508, 290, 546, fill=(244, 226, 190), w=2.6)
    for i in range(7):
        mid.line([(60 + i * 46, 560), (60 + i * 46, GROUND + 20)], (146, 102, 70), 3)
    mid.cel([(110, 640), (190, 640), (190, GROUND + 20), (110, GROUND + 20)], (120, 84, 60), (96, 66, 48), w=2.6)
    mid.cel([(240, 620), (340, 620), (340, 700), (240, 700)], (210, 224, 218), (182, 198, 194), w=2.6)
    for x, y, s in ((560, 790, 1.2), (690, 790, .8)):  # cacti
        mid.cel([(x - 12, y), (x + 12, y), (x + 12, y - 140 * s), (x - 12, y - 140 * s)], (116, 156, 108), (92, 130, 88), w=2.6)
        mid.cel([(x - 12, y - 70 * s), (x - 44, y - 70 * s), (x - 44, y - 110 * s), (x - 30, y - 110 * s), (x - 30, y - 86 * s), (x - 12, y - 86 * s)], (116, 156, 108), (92, 130, 88), w=2.4)
    ground(gr, (222, 176, 128), (196, 150, 108))
    speckles(gr, GROUND + 30, H + 100, (186, 142, 102), 50, 6)
    fg.cel_circle(40, 1230, 70, (190, 140, 110), (160, 116, 90), w=3, wob=.03, seed=4)
    for x in (600, 650):
        fg.line([(x, 1250), (x - 10, 1200)], (180, 150, 100), 3)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def london(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (176, 180, 186), (236, 226, 210), y1=760)
    for x, y, s in ((100, 200, 90), (520, 140, 100), (360, 330, 70)):
        cloud(far, x, y, s, (226, 224, 224))
    # clock tower
    far.cel([(470, 700), (580, 700), (572, 260), (478, 260)], (204, 186, 150), (176, 158, 126), w=3)
    far.cel([(466, 260), (584, 260), (560, 210), (490, 210)], (190, 172, 140), (162, 144, 114), w=3)
    far.cel([(490, 210), (560, 210), (525, 90)], (110, 120, 136), (86, 96, 112), w=3)
    far.cel_circle(525, 350, 36, (250, 246, 232), (222, 214, 196), w=3.4)
    far.line([(525, 350), (525, 326)], INK, 3.2)
    far.line([(525, 350), (542, 356)], INK, 3.2)
    # brick houses
    def row(x0, x1, top, col):
        mid.cel([(x0, top), (x1, top), (x1, GROUND + 20), (x0, GROUND + 20)], col, shade_of(col, .84), w=3)
        for yy in range(int(top) + 24, GROUND + 20, 36):
            mid.line([(x0, yy), (x1, yy)], mix(col, (90, 60, 50), .25), 1.6)
        for i in range(3):
            xx = x0 + 24 + i * (x1 - x0 - 48) / 2
            mid.rect(xx - 16, top + 40, xx + 16, top + 94, fill=(236, 226, 190) if i != 1 else (196, 210, 216), w=2.4)
        mid.cel([(x0 - 8, top), (x1 + 8, top), (x1 + 2, top - 28), (x0 - 2, top - 28)], (96, 92, 104), (72, 68, 80), w=2.8)
    row(X0 + 10, 200, 520, (170, 100, 84))
    row(210, 420, 560, (186, 122, 98))
    row(580, X1 - 10, 500, (160, 96, 80))
    ground(gr, (150, 148, 150), (126, 124, 128))
    for i in range(10):
        y = GROUND + 20 + (i ** 1.6) * 12
        for j in range(-2, 14):
            gr.line([(j * 66 + (i % 2) * 33, y), (j * 66 + (i % 2) * 33 + 40, y)], (118, 116, 120), 2)
    # lamp post
    fg.line([(80, 1290), (80, 880)], (60, 64, 72), 12)
    fg.cel([(56, 880), (104, 880), (96, 830), (64, 830)], (250, 226, 150), (228, 196, 110), w=3)
    fg.glow(80, 850, 130, (255, 230, 160), .35)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def cave(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 40, (64, 46, 44), (118, 82, 64))
    far.rect(X0, GROUND + 39, X1, Y1, fill=(118, 82, 64), ink=None, w=0)
    # mouth of the cave: bright opening
    far.cel([(430, 200), (700, 250), (740, 640), (500, 700), (400, 520)], (186, 214, 220), (160, 190, 200), w=4)
    far.glow(600, 450, 260, (255, 240, 200), .45)
    # stalactites
    rng = np.random.default_rng(3)
    for x in range(-60, 780, 70):
        h = rng.uniform(60, 190)
        far.cel([(x - 28, -MY), (x + 28, -MY), (x + 4, h)], (92, 68, 60), (72, 52, 46), w=2.6)
    # cave paintings
    mid.cel([(X0 + 20, 300), (330, 300), (360, 620), (X0 + 20, 640)], (140, 100, 76), (116, 80, 60), w=3)
    for i, (x, y) in enumerate(((60, 420), (150, 460), (230, 410))):
        mid.line([(x, y), (x + 36, y - 40), (x + 70, y)], (214, 98, 70), 5)
        mid.circle(x + 36, y - 54, 9, fill=(214, 98, 70), ink=None, w=0)
    # campfire
    mid.glow(400, 760, 220, (255, 170, 90), .5)
    for dx in (-30, 0, 30):
        mid.line([(400 + dx, 790), (400 - dx * .4, 760)], (120, 84, 60), 12)
    for dx, h, col in ((0, 70, (250, 150, 70)), (-18, 50, (246, 190, 90)), (16, 44, (250, 200, 110))):
        mid.cel([(400 + dx - 18, 770), (400 + dx, 770 - h), (400 + dx + 18, 770)], col, shade_of(col, .9), w=2.4)
    ground(gr, (132, 96, 72), (104, 74, 56), y0=GROUND + 20)
    speckles(gr, GROUND + 40, H + 100, (92, 66, 50), 40, 3)
    for x, y, r in ((-20, 1220, 90), (720, 1230, 80)):
        fg.cel_circle(x, y, r, (96, 72, 62), (72, 52, 48), w=3, wob=.03, seed=int(abs(x)))
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(1, -1))


def steppe(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (140, 192, 234), (240, 238, 226), y1=700)
    for x, y, s in ((120, 190, 90), (500, 120, 80), (380, 300, 70)):
        cloud(far, x, y, s)
    far.cel([(X0, 700), (80, 600), (240, 650), (420, 570), (620, 640), (X1, 600), (X1, 760), (X0, 760)], (156, 170, 190), (130, 144, 168), w=2.4)
    _hills(mid, 730, (156, 190, 120), (128, 162, 98), 4, 40)
    # yurt (ger)
    def yurt(cx, base, s):
        mid.cel([(cx - 90 * s, base - 80 * s), (cx + 90 * s, base - 80 * s), (cx + 90 * s, base), (cx - 90 * s, base)], (244, 240, 228), (216, 210, 198), w=3)
        mid.cel([(cx - 104 * s, base - 78 * s), (cx, base - 150 * s), (cx + 104 * s, base - 78 * s)], (236, 228, 212), (208, 198, 182), w=3)
        mid.cel([(cx - 22 * s, base - 54 * s), (cx + 22 * s, base - 54 * s), (cx + 22 * s, base), (cx - 22 * s, base)], (176, 84, 80), (146, 64, 62), w=2.6)
        mid.line([(cx - 90 * s, base - 78 * s), (cx + 90 * s, base - 78 * s)], (176, 84, 80), 5)
    yurt(210, 790, 1.2)
    yurt(580, 780, .9)
    ground(gr, (160, 194, 118), (130, 164, 96))
    speckles(gr, GROUND + 30, H + 100, (118, 150, 88), 60, 5, size=(6, 16))
    for x, y in ((90, 1130), (280, 1200), (630, 1150)):
        for a in range(5):
            gr.circle(x + 9 * math.cos(a * 1.256), y + 9 * math.sin(a * 1.256), 6, fill=(248, 232, 150), w=1.8)
    _fg_rocks(fg, (176, 176, 168), (146, 146, 142))
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def jungle_temple(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (170, 214, 214), (236, 242, 214), y1=760)
    rays(far, 560, -60, 50, 7, (255, 244, 190), .12, 1000)
    for x in (-20, 140, 640, 760):  # background trees
        far.line([(x, 780), (x + 10, -MY)], (94, 120, 84), 40)
    # stepped temple
    stepped_pyramid(mid, 130, 650, 790, 380, 8, (178, 184, 160), (146, 154, 132), wlast=.28)
    mid.cel([(330, 380), (450, 380), (450, 310), (330, 310)], (168, 174, 150), (138, 146, 124), w=3)
    mid.poly([(366, 380), (414, 380), (414, 330), (366, 330)], fill=(60, 66, 60), w=2.4)
    for i in range(10):  # moss
        mid.ellipse(160 + i * 52, 700 + (i % 3) * 22, 30, 12, fill=(110, 150, 94), ink=None, w=0)
    ground(gr, (110, 152, 84), (88, 128, 68), y0=GROUND + 10)
    speckles(gr, GROUND + 30, H + 100, (80, 116, 62), 60, 3)
    # big leaves + vines foreground
    for x, y, a in ((20, 1180, -30), (700, 1160, 210), (80, 1280, 10), (650, 1280, 170)):
        for da in (-30, 0, 30):
            r = math.radians(a + da - 90)
            fg.cel([(x, y), (x + math.cos(r - .3) * 120, y + math.sin(r - .3) * 120), (x + math.cos(r) * 190, y + math.sin(r) * 190), (x + math.cos(r + .3) * 120, y + math.sin(r + .3) * 120)],
                   (86, 138, 82), (66, 112, 64), w=2.8)
    for x in (120, 600):
        fg.line([(x, -MY), (x + 14, 160), (x - 8, 320)], (88, 128, 72), 7)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def battlefield(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (160, 170, 186), (240, 220, 194), y1=740)
    for x, y, s in ((110, 200, 100), (500, 150, 120), (330, 330, 80)):
        cloud(far, x, y, s, (214, 212, 214))
    _hills(far, 690, (150, 156, 116), (124, 130, 94), 8, 50)
    # distant banners and spears
    for x, h in ((80, 200), (180, 160), (560, 190), (650, 150)):
        far.line([(x, 700), (x, 700 - h)], (100, 80, 66), 4)
        far.cel([(x, 700 - h), (x + 56, 700 - h + 14), (x, 700 - h + 38)], (178, 70, 72), (146, 52, 58), w=2.2)
    # tents
    for cx, base, s, col in ((300, 780, 1.1, (232, 220, 190)), (500, 790, .9, (214, 168, 150))):
        mid.cel([(cx - 110 * s, base), (cx, base - 150 * s), (cx + 110 * s, base)], col, shade_of(col, .86), w=3)
        mid.cel([(cx - 24 * s, base), (cx, base - 70 * s), (cx + 24 * s, base)], (80, 60, 56), (60, 44, 42), w=2.4)
    # smoke columns
    for x in (120, 640):
        for i in range(5):
            mid.circle(x + math.sin(i) * 10, 640 - i * 56, 26 + i * 7, fill=(180, 178, 182), ink=None, w=0)
    ground(gr, (166, 150, 104), (140, 124, 86))
    speckles(gr, GROUND + 30, H + 100, (122, 108, 76), 60, 3)
    for x, y in ((90, 1100), (300, 1230), (620, 1150)):  # stuck arrows
        gr.line([(x, y), (x + 22, y - 90)], (120, 90, 70), 3.4)
        gr.cel([(x + 22, y - 90), (x + 14, y - 74), (x + 30, y - 78)], (170, 170, 176), (140, 140, 150), w=1.6)
    _fg_rocks(fg, (140, 138, 132), (112, 110, 108))
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def harbor(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (150, 200, 234), (246, 238, 220), y1=690)
    for x, y, s in ((110, 180, 90), (520, 130, 70)):
        cloud(far, x, y, s)
    mid.grad(X0, 640, X1, 790, (130, 178, 208), (96, 144, 180))
    mid.line([(X0, 640), (X1, 640)], INK, 2.6)
    for i in range(20):
        x, y = -60 + i * 48, 670 + (i % 5) * 20
        mid.arc(x, y, 20, 7, 200, 340, (236, 244, 248), 2.8)
    # lighthouse
    mid.cel([(560, 640), (620, 640), (606, 380), (574, 380)], (246, 240, 232), (216, 208, 200), w=3)
    for i, yy in enumerate((440, 520)):
        mid.cel([(570 + i * 4, yy), (610 - i * 4, yy), (608 - i * 4, yy + 36), (572 + i * 4, yy + 36)], (190, 70, 70), (156, 52, 56), w=2)
    mid.cel([(570, 380), (610, 380), (606, 340), (574, 340)], (255, 236, 160), (240, 212, 120), w=3)
    mid.cel([(566, 340), (614, 340), (590, 300)], (176, 84, 84), (146, 64, 68), w=3)
    mid.glow(590, 360, 130, (255, 238, 170), .4)
    # boats
    for x, y, s in ((170, 700, 1.0), (330, 690, .7)):
        mid.cel([(x - 80 * s, y - 40 * s), (x + 80 * s, y - 40 * s), (x + 56 * s, y), (x - 56 * s, y)], (150, 108, 80), (120, 84, 62), w=3)
        mid.line([(x, y - 40 * s), (x, y - 180 * s)], (130, 96, 70), 6)
        mid.cel([(x + 4, y - 170 * s), (x + 70 * s, y - 80 * s), (x + 4, y - 50 * s)], (246, 238, 220), (218, 206, 184), w=2.6)
    # wooden pier
    ground(gr, (176, 134, 98), (148, 108, 78), y0=GROUND + 10)
    for i in range(12):
        y = GROUND + 30 + i * 46
        gr.line([(X0, y), (X1, y)], (116, 84, 60), 2.6)
    for x in range(-30, 760, 120):
        gr.line([(x, GROUND + 10), (x, GROUND - 40)], (110, 80, 58), 14)
    # crates and barrels
    for x, y in ((600, 1230), (680, 1260)):
        fg.cel([(x - 50, y - 80), (x + 50, y - 80), (x + 50, y), (x - 50, y)], (190, 146, 98), (160, 120, 78), w=3)
        fg.line([(x - 50, y - 80), (x + 50, y)], (140, 104, 70), 3)
        fg.line([(x + 50, y - 80), (x - 50, y)], (140, 104, 70), 3)
    fg.cel_circle(60, 1250, 54, (176, 140, 100), (146, 112, 78), w=3, wob=.02, seed=7)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def moon(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 40, (22, 24, 46), (60, 62, 96))
    far.rect(X0, GROUND + 39, X1, Y1, fill=(60, 62, 96), ink=None, w=0)
    rng = np.random.default_rng(5)
    for _ in range(90):
        far.circle(rng.uniform(X0, X1), rng.uniform(-MY, 680), rng.uniform(1.2, 3.2), fill=(250, 248, 232), ink=None, w=0)
    far.glow(520, 260, 260, (150, 190, 255), .5)
    far.cel_circle(520, 260, 96, (96, 156, 214), (60, 116, 176), w=3.4)
    far.cel([(470, 230), (510, 200), (540, 232), (520, 270), (480, 262)], (112, 172, 120), (88, 146, 96), ink=None, w=0)
    far.cel([(530, 280), (576, 270), (590, 310), (550, 330)], (112, 172, 120), (88, 146, 96), ink=None, w=0)
    mid.cel([(X0, 780), (120, 720), (300, 760), (520, 700), (X1, 750), (X1, 840), (X0, 840)], (164, 166, 178), (136, 138, 154), w=2.6)
    ground(gr, (186, 188, 198), (150, 152, 166))
    for x, y, rx, ry in ((120, 960, 80, 22), (560, 1080, 110, 30), (300, 1190, 90, 24), (660, 900, 50, 14)):
        gr.ellipse(x, y, rx, ry, fill=(160, 162, 176), w=2.6)
    fg.cel_circle(40, 1230, 90, (140, 142, 156), (112, 114, 132), w=3, wob=.03, seed=3)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(1, -1))


def snow(k):
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    sky(far, (186, 206, 228), (244, 244, 246), y1=700)
    for x, y, s in ((120, 190, 90), (520, 130, 80)):
        cloud(far, x, y, s, (250, 250, 252))
    for x0, x1, top in ((X0, 360, 420), (220, 640, 340), (480, X1, 440)):
        mx = (x0 + x1) / 2
        far.cel([(x0, 720), (mx - 20, top), (mx + 30, top + 40), (x1, 720)], (160, 176, 206), (132, 150, 184), w=2.6)
        far.cel([(mx - 70, top + 78), (mx - 20, top), (mx + 30, top + 40), (mx + 6, top + 50), (mx - 20, top + 70), (mx - 40, top + 84)], (250, 250, 252), (222, 226, 240), w=2.2)
    for x, s in ((60, 1.1), (150, .8), (610, 1.2), (690, .9)):
        pine(mid, x, 790, 300 * s, (88, 120, 104))
        mid.cel([(x - 52 * s, 790 - 190 * s), (x, 790 - 300 * s), (x + 52 * s, 790 - 190 * s), (x + 20 * s, 790 - 214 * s), (x - 20 * s, 790 - 214 * s)], (250, 250, 252), (222, 226, 240), ink=None, w=0)
    ground(gr, (246, 248, 252), (214, 222, 238))
    for x, y in ((90, 960), (320, 1060), (560, 1000), (200, 1200), (640, 1210)):
        gr.ellipse(x, y, 70, 14, fill=(232, 238, 248), ink=None, w=0)
    rng = np.random.default_rng(2)
    for _ in range(40):
        fg.circle(rng.uniform(X0, X1), rng.uniform(-MY, 1300), rng.uniform(2, 4.5), fill=(255, 255, 255), ink=None, w=0)
    fg.cel_circle(-10, 1240, 80, (238, 242, 250), (206, 214, 232), w=3, wob=.03, seed=3)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def _plank_floor(gr, top, bot, seam, y0=GROUND):
    gr.grad(X0, y0, X1, Y1, top, bot)
    gr.line([(X0, y0), (X1, y0)], INK, 3.2)
    for i in range(1, 9):  # boards run toward the viewer
        x = X0 + (X1 - X0) * i / 9
        gr.line([(x * .55 + 360 * .45, y0), (x, Y1)], seam, 2.0)
    for j in range(1, 6):
        y = y0 + (j ** 1.7) * 16
        gr.line([(X0, y), (X1, y)], seam, 1.6)


def museum(k):  # gallery hall: paintings on the walls, polished floor, velvet ropes (for heists, art, palaces indoors)
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 30, (236, 222, 200), (210, 190, 164))
    far.rect(X0, GROUND + 29, X1, Y1, fill=(210, 190, 164), ink=None, w=0)
    far.rect(X0, 640, X1, 700, fill=(150, 98, 78), w=2.6)  # wainscot
    far.rect(X0, 700, X1, GROUND + 30, fill=(124, 82, 66), w=2.6)
    far.glow(360, -40, 380, (255, 244, 214), .55)  # skylight
    far.cel([(260, -MY), (460, -MY), (500, 40), (220, 40)], (214, 232, 244), (190, 212, 228), w=3)
    frames = ((40, 190, 190, 330, (92, 128, 96)), (250, 150, 440, 380, (170, 112, 82)), (500, 190, 650, 330, (84, 110, 150)))
    for x0, y0, x1, y1, col in frames:
        mid.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, fill=(216, 176, 84), w=3)
        mid.rect(x0, y0, x1, y1, fill=col, w=2.4)
    mid.circle(345, 250, 46, fill=(236, 206, 170), w=2.6)  # a portrait in the centre frame
    mid.cel([(290, 380), (300, 292), (390, 292), (400, 380)], (76, 54, 46), (58, 40, 36), w=2.6)
    mid.cel([(300, 224), (345, 190), (390, 224), (392, 270), (298, 270)], (90, 62, 44), (70, 48, 36), w=2.4)
    mid.circle(345, 252, 38, fill=(240, 214, 180), w=2.4)
    for x in (X0 + 40, X1 - 40):
        column(mid, x, GROUND + 28, 520, 70, col=(228, 214, 196), sh=(198, 182, 166))
    _plank_floor(gr, (192, 138, 96), (150, 104, 72), (122, 84, 60))
    for x in (60, 660):  # velvet rope posts
        fg.cel([(x - 10, 1100), (x + 10, 1100), (x + 14, 1250), (x - 14, 1250)], (216, 176, 84), (186, 148, 62), w=3)
        fg.cel_circle(x, 1090, 18, (216, 176, 84), (186, 148, 62), w=3)
    fg.line([(60, 1110), (360, 1160), (660, 1110)], (160, 40, 56), 9)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(0, -1))


def interior(k):  # warm room: panelled wall, sunny window, bookshelf, lamp (houses, workshops, courts, studies)
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 30, (222, 190, 150), (196, 160, 122))
    far.rect(X0, GROUND + 29, X1, Y1, fill=(196, 160, 122), ink=None, w=0)
    for x in range(int(X0), int(X1), 70):
        far.line([(x, -MY), (x, GROUND + 30)], (176, 140, 104), 2.2)
    far.rect(X0, 690, X1, GROUND + 30, fill=(150, 108, 80), w=2.6)
    mid.rect(70, 190, 270, 470, fill=(190, 222, 240), w=4)  # window with light
    mid.line([(170, 190), (170, 470)], INK, 4)
    mid.line([(70, 330), (270, 330)], INK, 4)
    mid.glow(170, 330, 260, (255, 236, 180), .5)
    mid.rect(430, 170, 690, 610, fill=(132, 92, 68), w=3)  # bookshelf
    rng = np.random.default_rng(6)
    for r in range(3):
        y0 = 190 + r * 140
        mid.line([(430, y0 + 128), (690, y0 + 128)], INK, 3)
        x = 442
        while x < 676:
            wd = rng.uniform(14, 26)
            col = [(176, 70, 66), (80, 118, 150), (206, 168, 80), (92, 130, 96), (140, 96, 140)][int(rng.integers(0, 5))]
            mid.rect(x, y0 + 28, x + wd, y0 + 126, fill=col, w=1.8)
            x += wd + 2
    mid.line([(360, -MY), (360, 60)], INK, 3)  # hanging lamp
    mid.glow(360, 100, 200, (255, 214, 130), .55)
    mid.cel([(330, 100), (390, 100), (408, 70), (312, 70)], (214, 176, 90), (180, 142, 66), w=3)
    _plank_floor(gr, (176, 128, 90), (138, 96, 66), (112, 78, 54))
    fg.cel_circle(-20, 1240, 70, (132, 92, 68), (104, 72, 52), w=3, wob=.03, seed=2)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


def stairwell(k):  # dark staircase: moody, one lamp (hiding, escapes, secrets, night scenes indoors)
    far, mid, gr, fg = Ctx(k), Ctx(k), Ctx(k), Ctx(k)
    far.grad(X0, -MY, X1, GROUND + 30, (46, 52, 74), (84, 84, 104))
    far.rect(X0, GROUND + 29, X1, Y1, fill=(84, 84, 104), ink=None, w=0)
    for y in range(-100, 700, 90):  # stone blocks
        for x in range(int(X0) + (45 if (y // 90) % 2 else 0), int(X1), 90):
            far.rect(x, y, x + 88, y + 88, fill=None, ink=(58, 62, 84), w=2)
    # stairs climbing to the right, a door at the top
    for i in range(8):
        x0 = 200 + i * 60
        top = 700 - i * 60
        mid.cel([(x0, top), (x0 + 60, top), (x0 + 60, GROUND + 30), (x0, GROUND + 30)], (122, 122, 140), (92, 92, 112), w=2.8)
    mid.cel([(640, 220), (700, 220), (700, 280), (640, 280)], (96, 64, 52), (74, 48, 40), w=3)
    mid.line([(200, 640), (640, 160)], (70, 52, 46), 8)  # banister
    mid.glow(150, 330, 240, (255, 206, 120), .6)  # lamp on the wall
    mid.cel([(138, 330), (162, 330), (170, 360), (130, 360)], (226, 186, 96), (190, 150, 70), w=2.6)
    gr.grad(X0, GROUND, X1, Y1, (92, 92, 112), (64, 64, 84))
    gr.line([(X0, GROUND), (X1, GROUND)], INK, 3.2)
    speckles(gr, GROUND + 30, H + 100, (62, 62, 84), 30, 4)
    fg.cel_circle(740, 1240, 80, (70, 70, 92), (52, 52, 72), w=3, wob=.03, seed=7)
    return dict(layers=[far, mid, gr, fg], chars=[], props=[], light=(-1, -1))


BACKDROPS = {
    "egypt_temple": SCENES["egypt"], "viking_coast": SCENES["viking"], "edo_street": SCENES["edo"], "roman_forum": SCENES["rome"],
    "medieval_town": medieval_town, "greek_agora": greek_agora, "china_palace": china_palace, "desert": desert, "ship_sea": ship_sea,
    "old_west": old_west, "london": london, "cave": cave, "steppe": steppe, "jungle_temple": jungle_temple, "battlefield": battlefield,
    "harbor": harbor, "moon": moon, "snow": snow, "museum": museum, "interior": interior, "stairwell": stairwell,
}


def backdrop(setting, k):
    fn = BACKDROPS.get(setting) or BACKDROPS["medieval_town"]
    return fn(k)
