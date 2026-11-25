"""End card for story videos: subscribe button animation + "Up next" title. Writes an mp4 and a silent wav.
Usage: python sb_endcard.py OUT.mp4 WIDTH HEIGHT "Next story title" [seconds]"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sb_sketch import Scene, crop_to, draw_subscribe, draw_cursor, sparkles, ease_io, fit_font, get_font, FFMPEG  # noqa: E402

FPS = 24


def voice_len(path):
    r = subprocess.run([FFMPEG.replace('ffmpeg', 'ffprobe') if FFMPEG.endswith('ffmpeg') else 'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 2.5


def main(out, w, h, title, dur=4.5, voice=None):
    k = max(1.25, w / 720 * 1.5)
    sc = Scene("subscribe", k)
    n = int(dur * FPS)
    tmp = out + ".part.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    click_at = 1.6  # the narrator says "Subscribe" first, then the cursor clicks, then the bell rings
    talk_end = 0.5 + (voice_len(voice) if voice else 1.0)
    for i in range(n):
        t = i / FPS
        ck = t - click_at

        def ex(top, info):
            draw_subscribe(top, t, click=ck if ck > 0 else None)
            if t > 0.3:
                p = ease_io((t - 0.3) / 1.2)
                draw_cursor(top, 700 + (540 - 700) * p, 1000 + (800 - 1000) * p, press=(0 < ck < 0.2))
            if ck > 0:
                sparkles(top, 500, 770, ck, seed=4)
        img, _ = sc.frame(t, extras=ex, talk=("host", 0.5 + 0.5 * abs(math.sin(t * 12))) if t < talk_end else None)
        fr = crop_to(img, k, (w, h), 1.0 + 0.03 * min(1, t / dur))
        d = ImageDraw.Draw(fr)
        # ribbon + title panel
        f = get_font(int(h * 0.034))
        if title:
            tw = d.textlength("UP NEXT", font=f)
            rx0, ry0 = w / 2 - tw / 2 - 46, h * 0.065
            d.rounded_rectangle((rx0, ry0, rx0 + tw + 92, ry0 + h * 0.058), radius=int(h * 0.029), fill=(214, 58, 52), outline=(38, 30, 36), width=max(3, int(h * 0.0026)))
            d.text((w / 2, ry0 + h * 0.029), "UP NEXT", font=f, fill=(255, 255, 255), anchor="mm")
            size_px = int(h * 0.04)
            while True:
                f2 = get_font(size_px)
                words, lines, cur = title.split(), [], ""
                for wd in words:
                    trial = (cur + " " + wd).strip()
                    if d.textlength(trial, font=f2) > w * 0.82 and cur:
                        lines.append(cur)
                        cur = wd
                    else:
                        cur = trial
                lines.append(cur)
                if len(lines) <= 3 or size_px < 24:
                    break
                size_px -= 3
            ph = len(lines) * size_px * 1.28 + h * 0.04
            py0 = h * 0.135
            d.rounded_rectangle((w * 0.07, py0, w * 0.93, py0 + ph), radius=int(h * 0.025), fill=(252, 247, 235), outline=(38, 30, 36), width=max(3, int(h * 0.003)))
            for j, ln in enumerate(lines):
                d.text((w / 2, py0 + h * 0.02 + size_px * (0.64 + 1.28 * j)), ln, font=f2, fill=(38, 30, 36), anchor="mm")
        else:
            f3 = fit_font(d, "Enjoyed this story?", int(h * 0.04), w * 0.88)
            d.text((w / 2, h * 0.3), "Enjoyed this story?", font=f3, fill=(255, 255, 255), anchor="mm", stroke_width=max(3, int(h * .004)), stroke_fill=(38, 30, 36))
        for txt, yf, sz in (("Subscribe so you never miss it" if title else "New history stories", 0.795, 0.03), ("ShortHistory", 0.84, 0.04)):
            f4 = fit_font(d, txt, int(h * sz), w * 0.88)
            tw = d.textlength(txt, font=f4)
            d.text((w * 0.5 - tw / 2, h * yf), txt, font=f4, fill=(255, 255, 255), stroke_width=max(3, int(h * .004)), stroke_fill=(38, 30, 36))
        pr.stdin.write(fr.tobytes())
    pr.stdin.close()
    if pr.wait() != 0:
        sys.exit("ffmpeg failed")
    os.replace(tmp, out)
    wav = os.path.splitext(out)[0] + ".wav"
    if voice:  # narrator line starts 0.5 s in, padded with silence to the length of the video
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", voice, "-af", "aformat=channel_layouts=stereo,aresample=44100,adelay=500|500,apad",
                        "-t", f"{n / FPS:.5f}", "-c:a", "pcm_s16le", "-ar", "44100", wav], check=True)
    else:
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{n / FPS:.5f}", "-c:a", "pcm_s16le", wav], check=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "", float(sys.argv[5]) if len(sys.argv) > 5 else 4.5, sys.argv[6] if len(sys.argv) > 6 else None)
