"""Render ONE scene to an mp4: stickman stage + captions + narration audio.

Usage: python render_scene.py scene.json
Needs: Pillow, numpy, ffmpeg on PATH. No network, no GPU.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage import (INK, RED, PAPER, COLORS, Pen, clamp, ease_out_back, ease_inout, set_font, make_paper,  # noqa: E402
                   layout, parse_markup, build_chunks, chunk_times, draw_chunk, make_stamp)
from rig import draw_stick  # noqa: E402
from props import PROPS, SKY  # noqa: E402

S = 2  # supersampling for smooth lines
FFMPEG = os.environ.get("FFMPEG_PATH", "ffmpeg")


def audio_envelope(audio, fps, lead, nframes):
    """Per-frame loudness 0..1 of the narration, used to move the presenter's mouth."""
    try:
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", audio, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return np.zeros(nframes, np.float32)
    env = np.zeros(nframes, np.float32)
    per = 16000.0 / fps
    for i in range(nframes):
        a = int(round((i / fps - lead) * 16000))
        b = int(a + per)
        if b <= 0 or a >= len(x):
            continue
        seg = x[max(0, a):min(len(x), b)]
        if len(seg):
            env[i] = float(np.sqrt(np.mean(seg * seg)))
    hi = np.percentile(env[env > 0], 90) if np.any(env > 0) else 1.0
    env = np.clip(env / max(hi, 1e-6), 0, 1)
    k = np.array([0.25, 0.5, 0.25], np.float32)
    return np.convolve(env, k, mode="same")


def actor_state(a, t, total, W):
    x0 = a.get("x", 0.5)
    pose = a.get("pose", "stand")
    face = -1 if a.get("face", "right") == "left" else 1
    to = a.get("to")
    if to is not None:
        t0 = a.get("move_at", 0.5)
        t1 = max(t0 + 0.5, a.get("move_end", total - 0.6))
        p = clamp((t - t0) / (t1 - t0))
        x = x0 + (to - x0) * ease_inout(p)
        if to != x0:
            face = 1 if to > x0 else -1
        if 0 < p < 1:
            pose = "walk"
    else:
        x = x0
    return x * W, pose, face


def main(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    W, H, fps = spec["width"], spec["height"], spec.get("fps", 24)
    set_font(spec.get("font"))
    L = layout(W, H)
    lead, tail = spec.get("lead", 0.45), spec.get("tail", 0.55)
    adur = spec["audio_duration"]
    total = lead + adur + tail
    nframes = int(math.ceil(total * fps))
    env = audio_envelope(spec["audio"], fps, lead, nframes)
    paper = make_paper(W, H, S)
    stage = spec.get("stage", {})
    props = stage.get("props", [])
    actors = stage.get("actors", [])
    presenter_on = spec.get("presenter", True)

    probe = Pen(paper.copy(), S, 0, L["line_w"])
    cap_size = L["cap_size"]
    chunks, space = build_chunks(parse_markup(spec["narration"]), L["cap_x1"] - L["cap_x0"],
                                 lambda s: probe.tw(s, cap_size))
    times = chunk_times(chunks, lead, adur)
    kicker = spec.get("kicker", "")
    stamp_img = make_stamp(spec["stamp"], L["stamp_size"], S) if spec.get("stamp") else None
    stamp_at = spec.get("stamp_at", lead + 1.0)

    tmp_out = spec["out"] + ".part.mp4"  # renamed only on success, so a crash never leaves a bad cached clip
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp_out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    paper_flat = Image.new("RGB", (W, H), PAPER)
    ground = L["ground"]
    for i in range(nframes):
        t = i / fps
        img = paper.copy()
        pen = Pen(img, S, seed=int(t * 8) % 997, lw=L["line_w"])

        def draw_props(sky):
            for k, pr in enumerate(props):
                kind = pr.get("type")
                if kind not in PROPS or (kind in SKY) != sky:
                    continue
                fn, anchor, dy = PROPS[kind]
                at = pr.get("at", min(0.35 + 0.4 * k, max(0.0, total - 0.8)))
                if t < at:
                    continue
                sc = ease_out_back((t - at) / 0.4)
                u = L["actor_h"] * 0.62 * pr.get("size", 1.0) * max(0.01, sc)
                cx = pr.get("x", 0.5) * W
                # heights in the script are written for 16:9 (ground at 74%); rescale for other layouts
                k = ground / (0.74 * H)
                if "y" in pr:
                    cy = pr["y"] * H * k
                elif dy is not None:
                    cy = dy * H * k + (0 if L["wide"] else 0.045 * H)  # keep sky props clear of the title
                else:
                    cy = ground
                fn(pen, cx, cy, u, t, pr)

        draw_props(True)
        # hand-drawn ground line
        pts = [(0.03 * W + k * 0.94 * W / 40, ground + math.sin(k * 1.7) * 1.5) for k in range(41)]
        pen.line(pts, w=L["line_w"] * 0.8, color=INK)
        draw_props(False)

        for a in actors:
            ax, pose, face = actor_state(a, t, total, W)
            holds = a.get("holds") or ("quill" if pose == "write" else None)
            draw_stick(pen, ax, ground, L["actor_h"] * a.get("scale", 1.0), pose, t + a.get("offset", 0.0),
                       face=face, color=COLORS.get(a.get("color", "ink"), INK), hat=a.get("hat"), holds=holds)

        if presenter_on:
            draw_stick(pen, L["presenter_x"], ground, L["presenter_h"], spec.get("presenter_pose", "stand"),
                       t, face=-1, scarf=True, mouth=float(env[i]) if lead <= t <= lead + adur else 0.0)

        if stamp_img is not None and t >= stamp_at:
            p = (t - stamp_at) / 0.35
            sc = ease_out_back(p) if p < 1 else 1.0
            w, h = max(1, int(stamp_img.width * sc)), max(1, int(stamp_img.height * sc))
            layer = stamp_img.resize((w, h), Image.BICUBIC) if sc != 1.0 else stamp_img
            img.paste(layer, (int(L["stamp_xy"][0] * S - w / 2), int(L["stamp_xy"][1] * S - h / 2)), layer)

        if kicker and t >= 0.1:
            kx, ky = L["kicker_xy"]
            ks = L["kicker_size"]
            pen.text((kx, ky), kicker, ks, INK)
            wk = pen.tw(kicker, ks) * ease_inout((t - 0.15) / 0.5)
            pen.line([(kx, ky + ks * 1.2), (kx + wk, ky + ks * 1.2)], w=L["line_w"] * 1.3, color=RED, wob=False)

        for (t0, t1), ch in zip(times, chunks):
            last = ch is chunks[-1]
            if t0 <= t < t1 or (last and t >= t0):
                draw_chunk(pen, ch, space, cap_size, L["cap_x0"], L["cap_x1"], L["cap_y0"], L["cap_y1"])
                break

        frame = img.reduce(S) if S > 1 else img
        if t < 0.18:
            frame = Image.blend(paper_flat, frame, clamp(t / 0.18))
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed while writing " + spec["out"])
    os.replace(tmp_out, spec["out"])

    # Narration goes to its own lossless WAV, exactly as long as the video clip. make.js joins the WAVs
    # and encodes the audio ONCE, so there are no click/pop artifacts at scene changes (joining separately
    # encoded AAC clips leaves a splice at every join). Short fades remove any hard edge from the voice.
    fade = 0.012
    ms = int(lead * 1000)
    af = (f"aformat=channel_layouts=stereo,aresample=44100,afade=t=in:d={fade},"
          f"afade=t=out:st={max(0.0, adur - fade):.3f}:d={fade},adelay={ms}|{ms},apad")
    wav = os.path.splitext(spec["out"])[0] + ".wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", spec["audio"], "-af", af,
                    "-t", f"{nframes / fps:.5f}", "-c:a", "pcm_s16le", "-ar", "44100", wav], check=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python render_scene.py scene.json")
    main(sys.argv[1])
