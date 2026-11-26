# stickman-history

## NEW: history Shorts in one command (style A5 "Historical Cartoon")

```
node src/shorts.js            # asks how many videos (1-10), then makes them
node src/shorts.js --list     # shows the library: stories made and topics left
```
or double-click `run.bat` and choose 1. Each video is about 1:10 to 1:30. The story is sized to that before it is voiced; if the real voice makes it a little shorter or longer the video is still made, with a note in the summary.

How it works: `library/topics.json` holds 84 history topics (titles written as curiosity questions; 14 of them are true-story types: mocked underdog, weird experiment, clever scheme) (from vidIQ trending/outlier/keyword data fetched 2026-11-22, plus evergreen ones). The tool takes the top-scored topics not made yet, Gemini writes each story (`src/story.js`), the script is saved in `library/stories/`, and `library/index.json` records it so a story is never made twice. Finished videos: `out/shorts/<story>/final.mp4` plus `info.txt` (title, description, tags, facts to verify). Unfinished or failed stories are finished first on the next run.

Voice: **Kokoro** (`kokoro-js`, from YOUTUBE-AGENT) is the default: free, offline, no key, no limits. `run.bat` runs `npm install` once; the model (~330 MB) downloads on first use. Settings in `.env`: `KOKORO_VOICE` (default `am_fenrir`, the calm voice of Oli in YOUTUBE-AGENT), `KOKORO_SPEED` (1.21, which is the Oli speed 0.88 made about 1.4x faster), `KOKORO_DTYPE` (`fp32` clean, or `q8` smaller ~90 MB). Gemini voice is optional: `--voice gemini`. The Gemini key is now only used to write the stories (1 request per video).

Look: the default style is now **storybook** (`--style sb`, vertical 9:16 Shorts, 720x1280): code-drawn backdrops for 21 settings (including indoor museum, room and stairwell), big-headed characters with hats, props and tiny faces, a different code-made music style per story, small code-made sound effects, characters that walk in and sway, and a looping ending: the narrator says "Subscribe, and ring the bell" over the last scene while a Subscribe button is clicked (no separate end card, so viewers do not swipe away). The old stick-figure look is still available with `--style a5 --aspect 16:9`. No AI image/voice credits are used. Menu option 7 remakes a story already made with the current look.

Options: `--count N`, `--topic "my topic"`, `--random`, `--aspect 9:16`, `--mock-story --dry-voice` (test with no key), `--pause 8000` (free-tier limits).
Add topics later: append entries to `library/topics.json` (same fields) after a new vidIQ run.
With the default Kokoro voice there are no voice limits. Only the story writing uses Gemini (1 request per video).
Optional `.env` key `GEMINI_TEXT_MODEL` if the default text model name is not available to your key.

---

# Original stickman explainer (style B5)

Free script-to-video tool for short history videos in a simple stickman-explainer style
(paper background, bold black-and-red captions, a corner presenter, props drawn in code).

- **Voice:** Kokoro (offline, free) by default; Gemini TTS optional (`src/voice.js`, ported from YOUTUBE-AGENT).
- **Look:** drawn frame by frame with Pillow (`render/`). Structure and style follow stickman-video-director's style B5.
- **Assembly:** ffmpeg. Each scene is its own 8-15 s clip, joined at the end, plus a synthesized music bed.
- **Cost:** nothing. No video-generation API, no GPU.

## Setup (once)

1. Node 18+, Python 3, and ffmpeg on your PATH.
2. `pip install pillow numpy`
3. Copy `.env.example` to `.env` and paste your free Gemini key.

## Use

```
node src/voice.js "Test sentence" out/test.mp3     # hear the voice first
node src/make.js scripts/printing-press.json --sample   # first scene only: check style + voice
node src/make.js scripts/printing-press.json            # full video -> out/printing-press/final.mp4
node src/make.js scripts/printing-press.json --aspect 9:16   # vertical for Shorts
node src/make.js scripts/printing-press.json --dry-voice     # test with no key / no internet
```

Free-tier voice limits: if you get rate-limit errors, raise `--pause 8000`. Finished scenes are cached, so a re-run continues where it stopped. After editing the Python code, add `--force`.

## Writing your own script

Copy `scripts/printing-press.json`. Each scene has:

- `narration` - spoken text; wrap words in `[[double brackets]]` to show them in red in the captions.
- `kicker` - the title in the top-left corner. `stamp` - an optional red date stamp.
- `stage.actors` - `x` (0-1), `pose` (stand, walk, wave, point, cheer, think, write, hold, slump), `color` (ink, red, blue, green, brown, gold), `hat` (crown, cap, helmet), `holds` (book, scroll, flag, coins, bulb, quill), `to` (walk to this x).
- `stage.props` - `type`, `x`, optional `y`, `size`, `at` (seconds). Types: sun, cloud, tree, house, town, castle, ship, flag, crown, scroll, book, stack, press, coins, mountain, map, bulb, clock, gear, arrow, pages, crowd.

Aim for about 25-30 words per scene (roughly 10-12 s) and 7-9 scenes for 1-2 minutes. The tool warns if the total passes 2 minutes.

## Notes

- Check every historical fact in your script yourself before publishing. The sample script is an example, not a source.
- Gemini voice terms for monetized YouTube use: read Google's current terms before you rely on it commercially.
- The tool never uploads anything.
