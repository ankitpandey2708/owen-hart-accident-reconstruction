# One part, 78 feet: the Owen Hart rigging accident (safety study)

A 71-second narrated explainer about the rigging failure that killed professional wrestler Owen Hart at Kemper Arena, Kansas City, on May 23, 1999. It was built for an internal safety and rigging study.

**The one idea:** a single quick-release part was the only thing holding a person 78 ft in the air, with no backup line. A life-safety rig never has a single point of failure.

The reconstruction uses a **generic crash-test mannequin**, never a likeness of the person. The fall is free-fall physics (2.17 s for the drop, about 48 mph) from the commonly reported height of ~78 ft; some reports give ~90 ft.

## Stack

| Layer | Tool |
|---|---|
| Timeline, compositing, audio mix, render | [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML + GSAP, deterministic headless-Chrome render, Apache 2.0) |
| Continuous 3D camera take (shackle, harness, the drop, the fix) | three.js, drawn per frame from timeline time (`video/assets/world.js`) |
| Slow-motion replay of the fall and impact | Blender 5 EEVEE (`blender_scene.py`) |
| Narration (switchable) | Kokoro-82M or Chatterbox, local (`tts/`) |
| Music | HeyGen catalog via HyperFrames `media-use` (free sign-in) |
| Encode | ffmpeg (inside HyperFrames) |

**The voice is the clock:** `tts/generate.py` writes the per-word timings, and `video/build.py` derives scene lengths, label cues, audio placement and subtitles from them. Edit `video/script.json`, re-run both scripts, and the whole film re-times.

## Layout

```
video/                     HyperFrames project
  script.json              narration, one entry per scene (hold_after = silent picture after the voice)
  SPEC.md, STORYLINES.md   director's brief and the three storylines considered
  build.py                 timing -> index.html, compositions/*.html, assets/timing.js, subtitles.srt
  assets/world.js          the three.js world (one continuous take, pure function of time)
  assets/lib/              vendored three.js
tts/
  config.json              engine + voice settings
  generate.py, worker.py   synthesis, loudness normalization (-16 LUFS), word timings
blender_scene.py           Blender scenes (arena flyover, fall reconstruction)
render_all.sh              renders the Blender scenes
```

## Build

Requirements: Node 22+, ffmpeg, Python 3.11 (via `uv`), Blender 5.x for the replay footage. Windows paths are shown.

```bash
# 1. voices: one-time setup of the engine environments
cd tts
uv venv -p 3.11 kokoro-venv     && uv pip install -p kokoro-venv "kokoro>=0.9" soundfile "en_core_web_sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
uv venv -p 3.11 chatterbox-venv && uv pip install -p chatterbox-venv chatterbox-tts soundfile
cd ..

# 2. replay footage (Blender), then cut the two replay clips
./render_all.sh
ffmpeg -framerate 30 -start_number 225 -i frames/s5/%04d.png -frames:v 260 -c:v libx264 -crf 16 -pix_fmt yuv420p video/assets/footage/replay_fall.mp4
ffmpeg -framerate 30 -start_number 485 -i frames/s5/%04d.png -frames:v 240 -c:v libx264 -crf 16 -pix_fmt yuv420p video/assets/footage/replay_impact.mp4
cp node_modules/three/build/three.module.min.js video/assets/lib/

# 3. music + sound effects (needs `npx hyperframes auth login`, free)
#    music: video/audio_request.json -> assets/bgm/track.mp3
#    sfx:   video/assets/sfx/{latch,whoosh,thud,bass}.mp3 (resolved with `npx hyperframes media-use resolve --type sfx`)

# 4. narration -> timings -> composition -> render
python tts/generate.py                      # or: --engine chatterbox
cd video && python build.py
npx hyperframes check
npx hyperframes preview --background        # optional: scrub in the browser
npx hyperframes render -o renders/one_part_78_feet.mp4
```

Music and sound-effect files are licensed through HeyGen and are not committed, so step 3 is needed on a fresh clone.

## Voice config (`tts/config.json`)

| Key | Values | Default |
|---|---|---|
| `engine` | `kokoro`, `chatterbox` | `kokoro` |
| `kokoro.voice` | any Kokoro voice, e.g. `am_michael`, `am_adam`, `bm_george`, `af_heart`, `bf_emma` | `am_michael` |
| `kokoro.speed` | 0.7–1.3 | `0.95` |
| `chatterbox.exaggeration` | 0–1 (emotion intensity) | `0.35` |
| `chatterbox.cfg_weight` | 0–1 (pacing / adherence) | `0.5` |
| `chatterbox.temperature` | 0.1–1.5 | `0.7` |
| `chatterbox.seed` | integer (deterministic takes) | `7` |
| `chatterbox.voice_prompt` | path to a ~10 s reference WAV to clone, or `null` | `null` |

`python tts/generate.py --engine chatterbox` overrides the engine for one run. Kokoro gives native word timestamps. Chatterbox output is aligned with `npx hyperframes transcribe`.

## Blender render flags (`blender_scene.py` / `render_all.sh`)

The defaults reproduce the published replay: 1080p, 16 samples, full lighting and EEVEE.

| Flag | Values | Default | Effect | Approx. speed-up |
|------|--------|---------|--------|------------------|
| `--res` | `540`, `720`, `1080`, `1440`, `2160` | `1080` | Output resolution (16:9 height) | 720 → ~2× |
| `--samples` | `1`–`64` | `16` | EEVEE anti-aliasing / soft-shadow samples | 8 → ~1.5× |
| `--fast-lights` | flag | off | Hard shadows, drops two fill lights | ~1.3× |
| `--draft` | flag | off | Workbench engine, flat preview; ignores `--samples` | ~10× |
| `start end` | two frame numbers | full scene | Render only that frame range | — |

## Sources

- Wikipedia: "Over the Edge (1999)" and "Owen Hart"
- Deseret News, "Family of wrestler settles wrongful-death lawsuit" (Oct 31, 2000)
- Robb & Robb LLC case archive (1999–2000 coverage of the lawsuit and settlement)

In memory of Owen Hart, 1965–1999.
