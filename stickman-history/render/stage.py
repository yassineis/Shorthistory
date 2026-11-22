"""Shared drawing helpers: palette, fonts, hand-drawn pen, paper texture, layout, captions.

Style reference: stickman-video-director style B5 "Character Explainer" (warm paper, bold
black-and-red type, stickmen acting out ideas, presenter in the corner, narration leads).
Everything is drawn in code with Pillow, so it is free and runs offline.
"""
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

INK = (27, 26, 23)
RED = (200, 50, 30)
PAPER = (241, 230, 207)
CREAM = (251, 246, 234)
GOLD = (217, 166, 46)
GREEN = (92, 128, 66)
BLUE = (61, 92, 125)
BROWN = (135, 96, 60)
STONE = (205, 196, 178)
GRAY = (150, 142, 128)
COLORS = {"ink": INK, "red": RED, "blue": BLUE, "green": GREEN, "brown": BROWN, "gold": GOLD}


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease_out_back(p):
    p = clamp(p)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2


def ease_inout(p):
    p = clamp(p)
    return p * p * (3 - 2 * p)


# ---------------------------------------------------------------- fonts
_FONT_PATH = None
_FONT_CACHE = {}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def set_font(path=None):
    global _FONT_PATH
    _FONT_CACHE.clear()
    for p in ([path] if path else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            _FONT_PATH = p
            return p
    _FONT_PATH = None
    return None


def get_font(px):
    px = max(6, int(round(px)))
    f = _FONT_CACHE.get(px)
    if f is None:
        try:
            f = ImageFont.truetype(_FONT_PATH, px) if _FONT_PATH else ImageFont.load_default(px)
        except Exception:
            f = ImageFont.load_default()
        _FONT_CACHE[px] = f
    return f


# ---------------------------------------------------------------- pen
class Pen:
    """Draws in final-resolution coordinates onto a supersampled image, with a slight
    hand-drawn wobble that changes a few times per second ("boiling line" look)."""

    def __init__(self, img, S, seed, lw):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.S = S
        self.seed = seed
        self.lw = lw

    def _j(self, x, y, amp):
        return (x + amp * math.sin(x * 0.031 + y * 0.047 + self.seed * 2.1),
                y + amp * math.cos(x * 0.043 - y * 0.029 + self.seed * 1.7))

    def _pts(self, pts, wob, amp=1.1):
        out = []
        for x, y in pts:
            if wob:
                x, y = self._j(x, y, amp)
            out.append((x * self.S, y * self.S))
        return out

    def _w(self, w):
        return max(1, int(round((w if w is not None else self.lw) * self.S)))

    def line(self, pts, w=None, color=INK, wob=True):
        p = self._pts(pts, wob)
        w_px = self._w(w)
        self.d.line(p, fill=color, width=w_px, joint="curve")
        r = w_px / 2
        for x, y in (p[0], p[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def poly(self, pts, fill=None, outline=INK, w=None, wob=True):
        p = self._pts(pts, wob)
        if fill is not None:
            self.d.polygon(p, fill=fill)
        if outline is not None:
            w_px = self._w(w)
            self.d.line(p + [p[0]], fill=outline, width=w_px, joint="curve")
            r = w_px / 2
            for x, y in p:
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=outline)

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, w=None, wob=True):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=fill, outline=outline, w=w, wob=wob)

    def circle(self, cx, cy, r, fill=None, outline=INK, w=None, wob=True):
        self.ellipse(cx, cy, r, r, fill=fill, outline=outline, w=w, wob=wob)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=INK, w=None, wob=True):
        if wob:
            cx, cy = self._j(cx, cy, 0.9)
        s = self.S
        width = self._w(w) if outline is not None else 0
        self.d.ellipse(((cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s),
                       fill=fill, outline=outline, width=width)

    def arc(self, cx, cy, r, a0, a1, w=None, color=INK):
        s = self.S
        self.d.arc(((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s), a0, a1,
                   fill=color, width=self._w(w))

    def text(self, xy, txt, size, fill=INK, anchor="la"):
        self.d.text((xy[0] * self.S, xy[1] * self.S), txt, font=get_font(size * self.S),
                    fill=fill, anchor=anchor)

    def tw(self, txt, size):
        return get_font(size * self.S).getlength(txt) / self.S


# ---------------------------------------------------------------- paper
def make_paper(W, H, S):
    rng = np.random.default_rng(7)
    base = np.empty((H, W, 3), np.float32)
    base[:] = PAPER
    small = rng.normal(0, 1, (H // 64 + 3, W // 64 + 3)).astype(np.float32)
    small = (small - small.min()) / max(1e-6, float(np.ptp(small)))
    blot = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                      dtype=np.float32) / 255.0 - 0.5
    grain = rng.normal(0, 1, (H, W)).astype(np.float32)
    base += (blot * 14 + grain * 2.5)[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base *= (1 - 0.10 * np.clip(r - 0.6, 0, 1))[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    return img.resize((W * S, H * S), Image.BICUBIC) if S > 1 else img


# ---------------------------------------------------------------- layout
def layout(W, H):
    wide = W >= H
    return {
        "wide": wide,
        "ground": (0.74 if wide else 0.60) * H,
        "actor_h": (0.34 if wide else 0.20) * H,
        "cap_x0": 0.06 * W, "cap_x1": 0.94 * W,
        "cap_y0": (0.80 if wide else 0.68) * H, "cap_y1": (0.95 if wide else 0.90) * H,
        "cap_size": (0.052 if wide else 0.034) * H,
        "kicker_xy": (0.06 * W, 0.06 * H),
        "kicker_size": (0.07 if wide else 0.042) * H,
        "presenter_x": (0.91 if wide else 0.86) * W,
        "presenter_h": (0.30 if wide else 0.17) * H,
        "stamp_xy": ((0.78 if wide else 0.72) * W, (0.24 if wide else 0.17) * H),
        "stamp_size": (0.075 if wide else 0.05) * H,
        "line_w": max(3.0, 0.0105 * H),
    }


# ---------------------------------------------------------------- captions
def parse_markup(text):
    """'a [[red words]] b' -> [(word, is_red), ...]"""
    marked = re.sub(r"\[\[(.+?)\]\]", lambda m: " ".join("\x01" + w for w in m.group(1).split()), text)
    words = []
    for tok in marked.split():
        words.append((tok.lstrip("\x01"), tok.startswith("\x01")))
    return words


def build_chunks(words, maxw, tw):
    """Greedy-wrap words into caption chunks of at most two lines."""
    space = tw(" ")
    chunks, lines, line, cur = [], [], [], 0.0
    for w, red in words:
        ww = tw(w)
        if line and cur + space + ww > maxw:
            lines.append(line)
            line, cur = [], 0.0
            if len(lines) == 2:
                chunks.append(lines)
                lines = []
        cur = (cur + space if line else 0.0) + ww
        line.append((w, red, ww))
    if line:
        lines.append(line)
    if lines:
        chunks.append(lines)
    return chunks, space


def chunk_times(chunks, start, dur):
    weights = [sum(len(w) + 2 for ln in c for w, _, _ in ln) for c in chunks]
    total = float(sum(weights)) or 1.0
    out, t = [], start
    for wgt in weights:
        d = dur * wgt / total
        out.append((t, t + d))
        t += d
    return out


def draw_chunk(pen, chunk, space, size, x0, x1, y0, y1):
    lh = size * 1.28
    y = (y0 + y1) / 2 - lh * len(chunk) / 2
    for line in chunk:
        wline = sum(w for _, _, w in line) + space * (len(line) - 1)
        x = (x0 + x1) / 2 - wline / 2
        for w, red, ww in line:
            pen.text((x, y), w, size, RED if red else INK)
            x += ww + space
        y += lh


def make_stamp(text, size, S):
    f = get_font(size * S)
    d = ImageDraw.Draw(Image.new("L", (4, 4)))
    bb = d.textbbox((0, 0), text, font=f)
    pad = int(size * 0.35 * S)
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw = max(2, int(size * 0.08 * S))
    d.rounded_rectangle((bw, bw, w - bw, h - bw), radius=int(size * 0.2 * S), outline=RED + (255,), width=bw)
    d.text((pad - bb[0], pad - bb[1]), text, font=f, fill=RED + (255,))
    return im.rotate(8, expand=True, resample=Image.BICUBIC)
