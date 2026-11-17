# One part, 78 feet: the Owen Hart rigging accident (safety study)

A 71-second narrated explainer about the rigging failure that killed professional wrestler Owen Hart at Kemper Arena, Kansas City, on May 23, 1999. It was built for an internal safety and rigging study.

**The one idea:** a single quick-release part was the only thing holding a person 78 ft in the air, with no backup line. A life-safety rig never has a single point of failure.

The reconstruction uses a **generic crash-test mannequin**, never a likeness of the person. The fall is free-fall physics (2.17 s for the drop, about 48 mph) from the commonly reported height of ~78 ft; some reports give ~90 ft.

**Storytelling framework:** [`DIRECTORS_FRAMEWORK.md`](DIRECTORS_FRAMEWORK.md) is a reusable, genre-agnostic framework (audience, controlling idea, structure, scene design, visuals, sound, words, endings, ethics, process and review rubric) for planning and reviewing any video, not only this one.

## Stack

| Layer | Tool |
|---|---|
| Timeline, compositing, audio mix, render | [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML + GSAP, deterministic headless-Chrome render, Apache 2.0) |
| Continuous 3D camera take (shackle, harness, the drop, the fix) | three.js, drawn per frame from timeline time (`video/assets/world.js`) |
| Slow-motion replay of the fall and impact | Blender 5 EEVEE (`blender_scene.py`) |
| Narration (switchable) | Kokoro-82M or Chatterbox, local (`tts/`) |
| Music | HeyGen catalog via HyperFrames `media-use` (free sign-in) |
| Encode | ffmpeg (inside HyperFrames) |

**Finishing:** the 3D world renders 8 sub-frames per frame across a 180° shutter (true motion blur, averaged in linear HDR), then one grade pass: ACES tone map, cool-shadow/warm-highlight split, saturation 0.9, gentle S-curve, vignette and frame-seeded grain. The Blender replay clips get the matched grade through HyperFrames `media-treatment` (`video/grade_replay.json`).

## How this stack compares

Organised by production stage: each layer appears once, and together they cover the whole film.

| Stage | Layer | This project | Code-driven explainer creators (2026) | Professional motion studios |
|---|---|---|---|---|
| **1. Pre-production** | Research & script | Sourced facts → `video/script.json` (138 words, ≤19 per scene) | LLM-drafted script, light fact-check | Researcher + scriptwriter, legal/fact review |
| | Story & spec | `STORYLINES.md` (3 options) → `SPEC.md` (numbers, banned defaults, QA frames) | Prompt or short brief | Treatment, storyboard, animatic |
| **2. Assets** | 3D models | Modelled snap shackle and harness, steel trusses, catwalk; primitive mannequin | Bought or kit-bashed models | Custom-modelled, textured hero assets |
| | 2D graphics & type | HTML/CSS labels on objects, numbers, titles (Oswald / Inter) | Registry blocks, kinetic-type templates | Designed in Illustrator / After Effects |
| | Voice | Kokoro / Chatterbox, local, config-switchable | ElevenLabs / HeyGen voices | Directed human voice actor |
| | Music & effects | HeyGen catalog bed + 4 effects | Catalog bed + effects library | Composer + sound designer (foley, room tone) |
| **3. Animation** | Camera & motion | One continuous three.js take + GSAP, cues keyed to word timings | Template moves, GSAP / Remotion springs | Keyframed by animators, previs |
| **4. Rendering** | 3D render & lighting | three.js raster (spots, rim, env map) + Blender EEVEE replay | three.js raster, sometimes path-traced | Cinema 4D / Blender Cycles, global illumination |
| | Motion blur | True sub-frame: 8 samples, 180° shutter, linear HDR | Per-element blur or none | Render-engine motion blur |
| **5. Post** | Edit & compositing | HyperFrames timeline: world, replay footage, overlay | HyperFrames or Remotion | After Effects + Premiere / DaVinci Resolve |
| | Grade & finishing | Shader grade (split-tone, S-curve, vignette, grain) + matched `media-treatment` on footage | LUT or preset | Colourist |
| | Captions | `subtitles.srt` sidecar from word timings | Burned-in word captions | Subtitle vendor, burned-in or sidecar |
| **6. Audio post** | Mix & loudness | Per-line −16 LUFS normalization, bed levels and fades; final −13.4 LUFS, −1 dBTP | Ducking + normalize | Re-recording mixer |
| **7. Delivery** | Encode & format | ffmpeg via HyperFrames, H.264/AAC 1080p30 | Same | Mastering + per-platform deliverables |
| **8. QA** | Review | `hyperframes check` + snapshot passes against `SPEC.md` | Agent passes + human eyes | Director and client review rounds |

**On par with code-driven creators:** timeline tooling, motion blur, grading and the hardware close-ups. The re-timing is ahead of hand-edited workflows: edit a sentence and the whole film follows the voice.

**Remaining gaps, biggest first:**
1. **Voice:** local TTS is still recognisably synthetic. A cloud voice (HeyGen or ElevenLabs) or a human narrator closes most of it.
2. **Lighting realism:** raster lighting has no bounced light and only approximate soft shadows. HyperFrames' path-traced three.js export would close this, at roughly 75× the render time.
3. **Mannequin:** built from primitives, deliberately generic so it never resembles the real person.
4. **Sound design:** a thin layer, missing cable creak, arena room tone and crowd ambience.
5. **Human review:** no director or client review rounds yet.

**The voice is the clock:** `tts/generate.py` writes the per-word timings, and `video/build.py` derives scene lengths, label cues, audio placement and subtitles from them. Edit `video/script.json`, re-run both scripts, and the whole film re-times.

## Layout

```
video/                     HyperFrames project
  script.json              narration, one entry per scene (hold_after = silent picture after the voice)
  SPEC.md, STORYLINES.md   director's brief and the three storylines considered
  build.py                 timing -> index.html, compositions/*.html, assets/timing.js, subtitles.srt
  assets/world.js          the three.js world (one continuous take, pure function of time)
  assets/lib/              vendored three.js (r170)
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
