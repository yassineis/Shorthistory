"""Storybook renderer for the story pipeline: backdrop + characters + props for ONE scene, frame by frame.
Used by render_scene.py when style == "sb" (vertical 9:16). Captions, title and stamp are added by render_scene.py."""
import math

from PIL import Image

from sb_draw import Ctx, draw_char, W, H, MX, MY
from sb_world import backdrop
from sb_props import draw_prop, BASE, default_y
from sb_actions import draw_action, impact_times, BACKGROUND, ACTIONS

POSE = {"stand": "idle", "walk": "idle", "wave": "wave", "point": "point", "cheer": "cheer", "think": "think", "hold": "hold",
        "slump": "shrug", "write": "hold"}
PARALLAX = (0.25, 0.55, 1.0, 1.3)
BEARD_HATS = {"viking": "viking"}
# moods the story writer can give a character (enhanced mode); the face changes on the key word of the sentence
MOODS = {"shock": "shock", "angry": "angry", "smug": "smug", "excited": "excited", "scared": "scared", "sad": "sad",
         "joy": "joy", "curious": "curious", "worry": "worry"}


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_io(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class StoryScene:
    def __init__(self, setting, actors, props, out_w, out_h, k=None, variant=0, enter=True,
                 enhanced=False, action=None, key_at=None):
        self.enhanced = enhanced  # enhanced true-story mode: moods on key words, prop actions, shake on impacts
        self.action = action if action in ACTIONS else None
        self.key_at = key_at if key_at is not None else 0.8  # when the key word is spoken (seconds into the clip)
        self.enter = enter  # False: characters are already in place (quick cuts inside one location)
        self.variant = variant  # scene number: changes camera direction and zoom so neighbouring scenes do not look alike
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
        enter = 0.7  # characters walk in from the side at the start of every scene
        if self.enter and to is None and t < enter:
            p = ease_io(t / enter)
            x = x0 + (-0.42 if x0 < 0.5 else 0.42) * (1 - p)
            face = 1 if x0 > x else -1
            moving = True
        if to is not None:
            t0 = a.get("move_at", 0.5)
            t1 = max(t0 + 0.5, a.get("move_end", total - 0.6))
            p = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
            x = x0 + (to - x0) * ease_io(p)
            if to != x0:
                face = 1 if to > x0 else -1
            moving = 0 < p < 1
        return x, pose, face, moving

    def frame(self, t, total, mouth=0.0, talking_idx=None, overlay=None):
        k = self.k
        prog = min(1.0, t / max(total, 1))
        v = self.variant
        pan = (-26 + 52 * prog) * (1 if v % 2 == 0 else -1)
        size = self.layers[0].size
        out = Image.new("RGBA", size, (0, 0, 0, 255))
        f = PARALLAX
        for i in range(3):
            out.alpha_composite(self.layers[i].img, (int(pan * f[i] * k), 0))
        top = Ctx(k)
        ref = None
        if self.actors:
            x0_, _, face0_, _ = self._state(self.actors[0], t, total)
            ref = {"x": x0_ * W, "gy": 948, "face": face0_}
        if self.enhanced and self.action in BACKGROUND and ref:
            draw_action(top, self.action, t, self.key_at, ref, total)
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
        i0_info = None
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
            gaze = 0.0
            if self.enhanced:
                mood = a.get("mood")
                if mood in MOODS and t >= self.key_at - 0.05:
                    emo = MOODS[mood]
                    d = t - (self.key_at - 0.05)
                    if d < 0.25:
                        gy -= 12 * math.sin(math.pi * d / 0.25)  # little jump when the reaction lands
                gaze = face * 0.6 + 0.35 * math.sin(t * 1.3 + i)  # eyes look where the character faces, with small darts
            lean = 0.03 * math.sin(t * 1.7 + i * 1.3)  # gentle sway while standing
            if a.get("talk") and (mouth or 0) > 0.3:
                gy -= 3.0  # little lift on the stressed syllables
            if moving:
                gy -= abs(math.sin(t * 7 + i)) * 7
                lean = 0.06
            info = draw_char(top, x * W, gy, 350 * a.get("scale", 1.0), outfit=a.get("outfit", "linen"), hat=hat, emotion=emo,
                      pose=POSE.get(pose, "idle"), face=face, t=t + a.get("offset", 0.0), holds=holds,
                      mouth=(mouth if (a.get("talk") and mouth is not None) else None), robe=(a.get("outfit_kind") == "robe"),
                      beard=beard, lean=lean, emote=emote_kw, seed=i + 2, gaze=gaze, trim=(222, 184, 96) if a.get("outfit_kind") == "robe" else None)
            if i == 0:
                i0_info = info
        if ref is not None and i0_info:
            ref["hand"] = i0_info["hand"]
        if self.enhanced and self.action and self.action not in BACKGROUND and ref:
            draw_action(top, self.action, t, self.key_at, ref, total)
        out.alpha_composite(top.img, (int(pan * f[2] * k), 0))
        out.alpha_composite(self.layers[3].img, (int(pan * f[3] * k), 0))
        if overlay is not None:  # fixed on screen (subscribe button), drawn in the same design space
            ov = Ctx(k)
            overlay(ov)
            out.alpha_composite(ov.img, (0, 0))
        zoom = (1.0 + 0.07 * prog, 1.07 - 0.07 * prog, 1.03 + 0.02 * math.sin(prog * 3.14))[v % 3]
        vw, vh = W / zoom, H / zoom
        l, tp = (MX + W / 2 - vw / 2) * k, (MY + H / 2 - vh / 2 + 10 * (zoom - 1) * 40) * k
        if self.enhanced and self.action:  # picture shake on impacts
            for t0 in impact_times(self.action, self.key_at):
                dt = t - t0
                if 0 <= dt < 0.5:
                    amp = 15 * math.exp(-dt * 7)
                    l += amp * math.sin(dt * 58) * k
                    tp += amp * math.cos(dt * 47) * k
        return out.convert("RGB").resize((self.ow, self.oh), Image.LANCZOS, box=(l, tp, l + vw * k, tp + vh * k))
