"""Storybook renderer for the story pipeline: backdrop + characters + props for ONE scene, frame by frame.
Used by render_scene.py when style == "sb" (vertical 9:16). Captions, title and stamp are added by render_scene.py."""
import math

from PIL import Image

from sb_draw import Ctx, draw_char, W, H, MX, MY
from sb_world import backdrop
from sb_props import draw_prop, BASE, default_y

POSE = {"stand": "idle", "walk": "idle", "wave": "wave", "point": "point", "cheer": "cheer", "think": "think", "hold": "hold",
        "slump": "shrug", "write": "hold"}
PARALLAX = (0.25, 0.55, 1.0, 1.3)
BEARD_HATS = {"viking": "viking"}


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_io(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class StoryScene:
    def __init__(self, setting, actors, props, out_w, out_h, k=None):
        self.k = k or max(1.25, out_w / W * 1.5)
        self.ow, self.oh = out_w, out_h
        self.layers = backdrop(setting, self.k)["layers"]
        self.actors, self.props = actors or [], props or []

    # position/pose of an actor at time t (same rules as the old renderer)
    def _state(self, a, t, total):
        x0 = a.get("x", 0.5)
        pose = a.get("pose", "stand")
        face = -1 if a.get("face", "right") == "left" else 1
        to, moving = a.get("to"), False
        x = x0
        if to is not None:
            t0 = a.get("move_at", 0.5)
            t1 = max(t0 + 0.5, a.get("move_end", total - 0.6))
            p = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
            x = x0 + (to - x0) * ease_io(p)
            if to != x0:
                face = 1 if to > x0 else -1
            moving = 0 < p < 1
        return x, pose, face, moving

    def frame(self, t, total, mouth=0.0, talking_idx=None):
        k = self.k
        pan = -26 + 52 * min(1.0, t / max(total, 1))
        size = self.layers[0].size
        out = Image.new("RGBA", size, (0, 0, 0, 255))
        f = PARALLAX
        for i in range(3):
            out.alpha_composite(self.layers[i].img, (int(pan * f[i] * k), 0))
        top = Ctx(k)
        # props that stand on the ground sit behind the characters; icons float in front of the sky
        for j, pr in enumerate(self.props):
            kind = pr.get("type")
            at = pr.get("at", min(0.35 + 0.4 * j, max(0.0, total - 0.8)))
            if t < at:
                continue
            sc = max(0.01, ease_out_back((t - at) / 0.4)) * pr.get("size", 1.0) * 0.95
            x = pr.get("x", 0.5) * W
            y = 800 if kind in BASE else pr.get("y_px") or default_y(kind)
            try:
                draw_prop(top, kind, x, y, sc, t)
            except Exception:
                pass
        for i, a in enumerate(self.actors):
            x, pose, face, moving = self._state(a, t, total)
            holds = a.get("holds") or ("quill" if pose == "write" else None)
            em = a.get("emote")
            emo = a.get("emotion") or ("happy" if (a.get("talk") and not em) else "smile")
            emote_kw = None
            if em in ("!", "?"):
                emote_kw = em
            elif em == "!?":
                emote_kw = "?"
            elif em == "...":
                emo, emote_kw = "worry", "sweat"
            elif em == ":(":
                emo = "sad"
            hat = a.get("hat")
            beard = a.get("beard") or BEARD_HATS.get(hat, False)
            gy = 948 + (i % 2) * -10 + (6 if x > 0.5 else 0)
            lean = 0.0
            if moving:
                gy -= abs(math.sin(t * 7 + i)) * 7
                lean = 0.06
            draw_char(top, x * W, gy, 350 * a.get("scale", 1.0), outfit=a.get("outfit", "linen"), hat=hat, emotion=emo,
                      pose=POSE.get(pose, "idle"), face=face, t=t + a.get("offset", 0.0), holds=holds,
                      mouth=(mouth if (a.get("talk") and mouth is not None) else None), robe=(a.get("outfit_kind") == "robe"),
                      beard=beard, lean=lean, emote=emote_kw, seed=i + 2, trim=(222, 184, 96) if a.get("outfit_kind") == "robe" else None)
        out.alpha_composite(top.img, (int(pan * f[2] * k), 0))
        out.alpha_composite(self.layers[3].img, (int(pan * f[3] * k), 0))
        zoom = 1.0 + 0.06 * min(1.0, t / max(total, 1))
        vw, vh = W / zoom, H / zoom
        l, tp = (MX + W / 2 - vw / 2) * k, (MY + H / 2 - vh / 2 + 10 * (zoom - 1) * 40) * k
        return out.convert("RGB").resize((self.ow, self.oh), Image.LANCZOS, box=(l, tp, l + vw * k, tp + vh * k))
