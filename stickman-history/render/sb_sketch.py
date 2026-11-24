"""Compose storybook frames, render stills, and build the 5 prototype sketches (silent narration + music).

Usage:
  python sb_sketch.py stills OUT_DIR            # 5 pictures + subscribe frame (1080x1920 PNG)
  python sb_sketch.py sketch N OUT_DIR [--fast] # sketch 1..5 -> mp4 (needs ffmpeg)
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sb_draw import Ctx, draw_char, get_font, W, H, MX, MY, INK, IVORY, mix  # noqa: E402
from sb_scenes import SCENES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.environ.get("FFMPEG_PATH", "ffmpeg")
PARALLAX = (0.25, 0.55, 1.0, 1.0, 1.3)  # far, mid, ground, chars+props, fg


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_io(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Scene:
    """Static layers are drawn once; characters and props are redrawn each frame."""

    def __init__(self, name, k):
        self.k = k
        self.name = name
        d = SCENES[name](k)
        self.layers, self.chars, self.props, self.light = d["layers"], d["chars"], d["props"], d["light"]

    def frame(self, t, pan=0.0, extras=None, talk=None, overrides=None, hide=()):
        k = self.k
        size = self.layers[0].size
        out = Image.new("RGBA", size, (0, 0, 0, 255))
        f = PARALLAX
        out.alpha_composite(self.layers[0].img, (int(pan * f[0] * k), 0))
        out.alpha_composite(self.layers[1].img, (int(pan * f[1] * k), 0))
        out.alpha_composite(self.layers[2].img, (int(pan * f[2] * k), 0))
        top = Ctx(k)
        info = {}
        for i, ch in enumerate(self.chars):
            if ch["name"] in hide:
                continue
            spec = dict(ch)
            spec.update((overrides or {}).get(ch["name"], {}))
            name = spec.pop("name")
            x, gy, h = spec.pop("x"), spec.pop("gy"), spec.pop("h")
            m = talk if (talk and talk[0] == name) else None
            info[name] = draw_char(top, x, gy, h, t=t, mouth=(talk[1] if m else None), seed=i + 2, **spec)
        for p in self.props:
            if p["kind"] == "block":
                bx, by, bw, bh = p["x"], p["gy"], p["w"], p["h"]
                top.soft_ellipse(bx, by + 4, bw * .75, 18)
                top.cel([(bx - bw / 2, by - bh), (bx + bw / 2, by - bh), (bx + bw / 2, by), (bx - bw / 2, by)], (214, 202, 186), (180, 166, 152), w=3.4)
                top.cel([(bx - bw / 2, by - bh), (bx + bw / 2, by - bh), (bx + bw / 2 - 22, by - bh - 28), (bx - bw / 2 + 22, by - bh - 28)], (232, 222, 208), (204, 192, 178), w=3.4)
                top.line([(bx - bw / 2 - 20, by + 4), (bx + bw / 2 + 20, by + 4)], (136, 100, 76), 9)
                if "worker" in info:  # rope from the worker's hand to the block
                    hx, hy = info["worker"]["hand"]
                    top.line([(hx, hy), ((hx + bx - bw / 2) / 2, (hy + by - bh * .4) / 2 + 22), (bx - bw / 2, by - bh * .4)], (170, 140, 96), 4.5)
        if extras:
            extras(top, info)
        out.alpha_composite(top.img, (int(pan * f[3] * k), 0))
        out.alpha_composite(self.layers[3].img, (int(pan * f[4] * k), 0))
        return out, info


def crop_to(img, k, out_size, zoom=1.0, cx=0.0, cy=0.0, shake=(0, 0)):
    vw, vh = W / zoom, H / zoom
    l = (MX + W / 2 + cx + shake[0] - vw / 2) * k
    t = (MY + H / 2 + cy + shake[1] - vh / 2) * k
    return img.convert("RGB").resize(out_size, Image.LANCZOS, box=(l, t, l + vw * k, t + vh * k))


# ---------------------------------------------------------------- captions
def fit_font(d, text, size, maxw):
    f = get_font(size)
    while d.textlength(text, font=f) > maxw and size > 10:
        size -= 2
        f = get_font(size)
    return f


def caption_groups(text, per=2):
    words = text.split()
    return [" ".join(words[i:i + per]) for i in range(0, len(words), per)]


def draw_caption(img, text, t_in, accent=False, y_frac=0.795):
    """Bold white text with dark outline, pops in with a small bounce. Works on a final-size RGB frame."""
    OW, OH = img.size
    sc = 0.78 + 0.22 * ease_out_back(t_in / 0.16)
    size = int(OH * 0.062 * sc)
    d = ImageDraw.Draw(img)
    font = fit_font(d, text, size, OW * 0.9)
    size = font.size
    tw = d.textlength(text, font=font)
    x, y = (OW - tw) / 2, OH * y_frac - size / 2
    col = (255, 226, 120) if accent else (255, 255, 255)
    d.text((x, y), text, font=font, fill=col, stroke_width=max(3, int(size * 0.14)), stroke_fill=(38, 30, 36))


def line_caption(img, text, t_in, y_frac=0.77):
    OW, OH = img.size
    size = int(OH * 0.034)
    font = get_font(size)
    d = ImageDraw.Draw(img)
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=font) > OW * 0.84 and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = trial
    lines.append(cur)
    a = min(1.0, t_in / 0.2)
    y0 = OH * y_frac - len(lines) * size * 0.62
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=font)
        d.text(((OW - tw) / 2, y0 + i * size * 1.3 + (1 - a) * 10), ln, font=font, fill=(255, 255, 255),
               stroke_width=max(2, int(size * 0.13)), stroke_fill=(38, 30, 36))


# ---------------------------------------------------------------- subscribe card
def draw_subscribe(top, t, click=None, host_info=None, sparkle=0.0):
    """Button on the transparent top layer. click = seconds since the click (None = not clicked)."""
    pop = ease_out_back(t / 0.4)
    bx, by = 500, 770
    clicked = click is not None and click > 0
    sq = 1.0 - (0.07 * math.sin(min(1, click / 0.25) * math.pi) if (click is not None and 0 < click < 0.25) else 0)
    wd, ht = 300 * pop * sq, 92 * pop * sq
    col = (108, 108, 118) if clicked else (214, 58, 52)
    top.soft_ellipse(bx, by + ht / 2 + 8, wd * .55, 14)
    top.rrect(bx - wd / 2, by - ht / 2, bx + wd / 2, by + ht / 2, 46 * pop, fill=col, ink=INK, w=4)
    if pop > .6:
        label = "SUBSCRIBED" if clicked else "SUBSCRIBE"
        f = get_font(int((32 if not clicked else 28) * pop * top.k))
        d = top.d
        px, py = top.P(bx + 22, by)
        d.text((px, py), label, font=f, fill=(255, 255, 255), anchor="mm")
        # bell
        bxx = bx - wd / 2 + 48
        sw = math.sin(click * 22) * 14 * max(0, 1 - click / 1.4) if clicked else 0
        ang = math.radians(sw)
        pts = [(bxx - 15, by + 12), (bxx - 11, by - 4), (bxx - 3, by - 16), (bxx + 3, by - 16), (bxx + 11, by - 4), (bxx + 15, by + 12)]
        pts = [(bxx + (x - bxx) * math.cos(ang) - (y - by) * math.sin(ang), by + (x - bxx) * math.sin(ang) + (y - by) * math.cos(ang)) for x, y in pts]
        top.poly(pts, fill=(255, 255, 255), ink=INK, w=2.2)
        top.circle(bxx, by + 17, 4.5, fill=(255, 255, 255), w=2)
    # cursor
    return bx, by


def draw_cursor(top, x, y, press=False):
    s = 1.0 - (0.12 if press else 0)
    pts = [(x, y), (x, y + 46 * s), (x + 12 * s, y + 35 * s), (x + 20 * s, y + 52 * s), (x + 29 * s, y + 48 * s), (x + 21 * s, y + 32 * s), (x + 36 * s, y + 31 * s)]
    top.poly(pts, fill=(255, 255, 255), ink=INK, w=3)


def sparkles(top, cx, cy, t, n=14, seed=1):
    rng = np.random.default_rng(seed)
    for i in range(n):
        a = rng.uniform(0, 6.28)
        sp = rng.uniform(80, 220)
        life = 0.9
        if t < 0 or t > life:
            continue
        r = sp * (t / life)
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r + 60 * (t / life) ** 2
        s = (1 - t / life) * rng.uniform(5, 10)
        col = [(255, 214, 110), (255, 160, 150), (170, 214, 236), (190, 226, 160)][i % 4]
        top.circle(x, y, s, fill=col, ink=None)


# ---------------------------------------------------------------- particles
def particles(top, kind, t, seed=0, n=26):
    rng = np.random.default_rng(seed)
    for i in range(n):
        x0, y0 = rng.uniform(-60, W + 60), rng.uniform(0, 960)
        sp = rng.uniform(.4, 1.0)
        ph = rng.uniform(0, 6.28)
        if kind == "dust":
            x = (x0 + t * 22 * sp) % (W + 120) - 60
            y = y0 + math.sin(t * .8 + ph) * 14
            top.circle(x, y, 2.6 * sp + 1, fill=(255, 244, 214), ink=None)
        elif kind == "petal":
            x = (x0 + t * 18 * sp + math.sin(t + ph) * 16) % (W + 120) - 60
            y = (y0 + t * 46 * sp) % 1000
            top.ellipse(x, y, 5, 3, fill=(244, 188, 204), ink=None)
        elif kind == "mote":
            x = (x0 + math.sin(t * .4 + ph) * 30) % (W + 120) - 60
            y = (y0 - t * 12 * sp) % 900
            top.circle(x, y, 2.2 * sp + 1, fill=(255, 240, 200), ink=None)
        elif kind == "spray":
            x = (x0 + t * 30 * sp) % (W + 120) - 60
            y = 700 + rng.uniform(0, 60) + math.sin(t * 2 + ph) * 6
            top.circle(x, y, 2.2, fill=(240, 246, 250), ink=None)


def vignette(img, strength=0.28):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    f = 1 - np.clip(d - 0.55, 0, 1) ** 1.6 * strength
    return Image.fromarray((np.asarray(img, np.float32) * f[..., None]).clip(0, 255).astype(np.uint8))


# ---------------------------------------------------------------- stills
def stills(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for i, name in enumerate(["egypt", "viking", "edo", "rome", "workshop"], 1):
        sc = Scene(name, 3)
        img, _ = sc.frame(0.0)
        crop_to(img, 3, (1080, 1920)).save(os.path.join(out_dir, f"picture_{i}_{name}.png"))
        print("still", name)
    sc = Scene("subscribe", 3)

    def ex(top, info):
        draw_subscribe(top, 1.0)
    img, _ = sc.frame(0.6, extras=ex)
    fr = crop_to(img, 3, (1080, 1920))
    d = ImageDraw.Draw(fr)
    for txt, y, size in (("Enjoyed this story?", 0.30, 0.045), ("New history stories", 0.80, 0.03), ("ShortHistory", 0.845, 0.04)):
        f = fit_font(d, txt, int(1920 * size), 1080 * 0.88)
        tw = d.textlength(txt, font=f)
        d.text((1080 * 0.5 - tw / 2, 1920 * y), txt, font=f, fill=(255, 255, 255), stroke_width=7, stroke_fill=(38, 30, 36))
    fr.save(os.path.join(out_dir, "picture_6_subscribe.png"))
    print("still subscribe")


# ---------------------------------------------------------------- "up next" frame (teases the next story of the library)
def next_story_card(title, k=3, size=(1080, 1920), channel=None):
    sc = Scene("subscribe", k)

    def ex(top, info):
        draw_subscribe(top, 1.0)
    img, _ = sc.frame(0.6, extras=ex)
    fr = crop_to(img, k, size)
    OW, OH = size
    d = ImageDraw.Draw(fr)
    # ribbon "UP NEXT"
    f = get_font(int(OH * 0.034))
    tw = d.textlength("UP NEXT", font=f)
    rx0, ry0 = OW / 2 - tw / 2 - 46, OH * 0.065
    d.rounded_rectangle((rx0, ry0, rx0 + tw + 92, ry0 + OH * 0.058), radius=int(OH * 0.029), fill=(214, 58, 52), outline=(38, 30, 36), width=5)
    d.text((OW / 2, ry0 + OH * 0.029), "UP NEXT", font=f, fill=(255, 255, 255), anchor="mm")
    # cream panel with the title, wrapped on up to 3 lines
    size_px = int(OH * 0.04)
    while True:
        f = get_font(size_px)
        words, lines, cur = title.split(), [], ""
        for w_ in words:
            trial = (cur + " " + w_).strip()
            if d.textlength(trial, font=f) > OW * 0.82 and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = trial
        lines.append(cur)
        if len(lines) <= 3 or size_px < 30:
            break
        size_px -= 3
    ph = len(lines) * size_px * 1.28 + OH * 0.04
    py0 = OH * 0.135
    d.rounded_rectangle((OW * 0.07, py0, OW * 0.93, py0 + ph), radius=int(OH * 0.025), fill=(252, 247, 235), outline=(38, 30, 36), width=6)
    for i, ln in enumerate(lines):
        d.text((OW / 2, py0 + OH * 0.02 + size_px * (0.64 + 1.28 * i)), ln, font=f, fill=(38, 30, 36), anchor="mm")
    for txt, yf, sz in (("Subscribe so you never miss it", 0.795, 0.03), (channel or LINES["channel"], 0.84, 0.04)):
        f = fit_font(d, txt, int(OH * sz), OW * 0.88)
        tw = d.textlength(txt, font=f)
        d.text((OW * 0.5 - tw / 2, OH * yf), txt, font=f, fill=(255, 255, 255), stroke_width=7, stroke_fill=(38, 30, 36))
    return fr


# ---------------------------------------------------------------- sketches
LINES = json.load(open(os.path.join(HERE, "..", "sketches", "lines.json"), encoding="utf-8"))
FPS = 24
DUR = 24.0
SUB_T = 20.2  # subscribe card starts


def sketch_cfg(n):
    # each sketch adds one more feature on top of the one before
    return dict(
        push=n >= 2, words=n >= 2, particles=n >= 3, talk=n >= 3, parallax=n >= 4, whip=n >= 4,
        grain=n >= 5, shake=n >= 5, click=n >= 5,
    )


def render_sketch(n, out_dir, fast=False):
    os.makedirs(out_dir, exist_ok=True)
    meta = LINES["sketches"][n - 1]
    cfg = sketch_cfg(n)
    OW, OH = (540, 960) if fast else (720, 1280)
    k = 1.25 if fast else 2.0
    sc = Scene(meta["scene"], k)
    sub = Scene("subscribe", k)
    lines = meta["lines"]
    starts = [l["start"] for l in lines]
    frames_dir = os.path.join(out_dir, f"frames{n}")
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    nframes = int(DUR * FPS)
    main_name = sc.chars[0]["name"]
    whip_t, whip_len = (9.2, 0.45) if cfg["whip"] else (None, 0)
    kinds = {"egypt": "dust", "viking": "spray", "edo": "petal", "rome": "dust", "workshop": "mote"}

    for fi in range(nframes):
        t = fi / FPS
        # which caption line / group is active
        cur = None
        for li, l in enumerate(lines):
            dur = len(l["text"].split()) / 2.6
            if l["start"] <= t < l["start"] + dur + 0.25:
                cur = (li, l, dur)
        talking = cur is not None and t < cur[1]["start"] + cur[2]
        mouth = (0.35 + 0.65 * abs(math.sin(t * 13.0) * math.sin(t * 5.3 + 1))) if (cfg["talk"] and talking) else None

        if t < SUB_T:
            shot2 = whip_t is not None and t >= whip_t + whip_len / 2
            pan = 0.0
            zoom, cx, cy = 1.0, 0.0, 0.0
            if cfg["push"]:
                zoom = 1.0 + 0.07 * (t / SUB_T)
            if cfg["parallax"]:
                pan = -34 + 68 * (t / SUB_T) if not shot2 else -10 + 20 * ((t - whip_t) / (SUB_T - whip_t))
                zoom = 1.05 + 0.05 * (t / SUB_T)
            if shot2:  # close-up on the main character
                ch = sc.chars[0]
                zoom, cx, cy = 1.55 + 0.1 * ((t - whip_t) / (SUB_T - whip_t)), ch["x"] - W / 2 + 60, ch["gy"] - ch["h"] * 0.55 - H / 2
            shake = (0, 0)
            if cfg["shake"]:
                for ev in (0.0, whip_t + whip_len / 2 if whip_t else 99):
                    dt = t - ev
                    if 0 <= dt < 0.35:
                        shake = (math.sin(dt * 70) * 7 * (1 - dt / 0.35), math.cos(dt * 61) * 5 * (1 - dt / 0.35))

            def ex(top, info, t=t):
                if cfg["particles"]:
                    particles(top, kinds[meta["scene"]], t, seed=n)
            img, info = sc.frame(t, pan=pan, extras=ex, talk=(main_name, mouth) if mouth is not None else None)
            frame = crop_to(img, k, (OW, OH), zoom, cx, cy, shake)
            if cfg["whip"] and whip_t is not None and abs(t - whip_t) < whip_len / 2:  # whip: horizontal smear
                p = (t - (whip_t - whip_len / 2)) / whip_len
                amt = int(OW * 0.12 * math.sin(p * math.pi)) + 1
                arr = np.asarray(frame, np.float32)
                acc = np.zeros_like(arr)
                for s_ in range(0, amt, max(1, amt // 8)):
                    acc += np.roll(arr, (s_ - amt // 2) * (1 if p < .5 else -1), axis=1)
                cnt = len(range(0, amt, max(1, amt // 8)))
                frame = Image.fromarray((acc / cnt).clip(0, 255).astype(np.uint8))
        else:
            ts = t - SUB_T
            click_at = 2.2 if cfg["click"] else None
            ck = (ts - click_at) if click_at is not None else None

            def ex(top, info, ts=ts, ck=ck):
                draw_subscribe(top, ts, click=ck if (ck is not None and ck > 0) else None)
                if cfg["click"] and ts > 1.0:
                    p = ease_io((ts - 1.0) / 1.2)
                    cxp, cyp = 640 - 150 * (1 - p) + (150 if False else 0), 900 - 160 * (1 - p)
                    tx, ty = 540, 800
                    draw_cursor(top, 700 + (tx - 700) * p, 1000 + (ty - 1000) * p, press=(ck is not None and 0 < ck < 0.2))
                if ck is not None and ck > 0:
                    sparkles(top, 500, 770, ck, seed=4)
            img, info = sub.frame(t, extras=ex, talk=("host", 0.5 + 0.5 * abs(math.sin(t * 12))) if (cfg["talk"] and ts < 2.2) else None)
            frame = crop_to(img, k, (OW, OH), 1.0 + (0.03 if cfg["push"] else 0) * min(1, ts / 3.0))
            d = ImageDraw.Draw(frame)
            for txt, yf, sz in (("Enjoyed this story?", 0.30, 0.04), ("New history stories", 0.79, 0.027), (LINES["channel"], 0.83, 0.036)):
                f = fit_font(d, txt, int(OH * sz), OW * 0.88)
                tw = d.textlength(txt, font=f)
                d.text((OW * 0.5 - tw / 2, OH * yf), txt, font=f, fill=(255, 255, 255), stroke_width=max(3, int(OH * .004)), stroke_fill=(38, 30, 36))

        # captions
        if t < SUB_T and cur is not None:
            li, l, dur = cur
            local = t - l["start"]
            if cfg["words"]:
                groups = caption_groups(l["text"], 2)
                weights = np.array([max(2, len(g)) for g in groups], float)
                edges = np.concatenate([[0], np.cumsum(weights) / weights.sum()]) * dur
                gi = int(np.clip(np.searchsorted(edges, local, side="right") - 1, 0, len(groups) - 1))
                draw_caption(frame, groups[gi], local - edges[gi], accent=(gi % 3 == 1))
            else:
                line_caption(frame, l["text"], local)
        elif t >= SUB_T:
            ts = t - SUB_T
            if ts > 0.1:
                if cfg["words"]:
                    draw_caption(frame, "FOLLOW FOR MORE", ts - 0.1, accent=True, y_frac=0.935)
                else:
                    line_caption(frame, LINES["cta"], ts, y_frac=0.935)
        if cfg["grain"]:
            frame = vignette(frame, 0.32)
            g = np.random.default_rng(fi).normal(0, 3.5, (OH, OW, 1)).astype(np.float32)
            frame = Image.fromarray((np.asarray(frame, np.float32) + g).clip(0, 255).astype(np.uint8))
        frame.save(os.path.join(frames_dir, f"f{fi:04d}.png"))
        if fi % 48 == 0:
            print(f"  sketch {n}: {fi}/{nframes}", flush=True)

    video = os.path.join(out_dir, f"sketch{n}_silent.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", video], check=True)
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)
    return video


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        stills(sys.argv[2])
    elif sys.argv[1] == "nextcard":
        next_story_card(sys.argv[2]).save(sys.argv[3])
        print("wrote", sys.argv[3])
    elif sys.argv[1] == "sketch":
        print(render_sketch(int(sys.argv[2]), sys.argv[3], "--fast" in sys.argv))
