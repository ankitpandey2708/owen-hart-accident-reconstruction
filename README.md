# Owen Hart Accident: Forensic Reconstruction (Safety Study)

A roughly 3-minute narrated explainer video about the rigging failure that killed professional wrestler Owen Hart at Kemper Arena, Kansas City, on May 23, 1999. It was built for an internal safety and rigging study.

The video is generated entirely from code, using **Blender** (3D arena and fall reconstruction), **three.js** (mechanism diagrams, cards and HUD, captured headlessly), **ffmpeg** (encode and assembly) and Windows SAPI text-to-speech.

The reconstruction uses a **generic crash-test mannequin**. Fall timing comes from free-fall physics (no drag) with the commonly reported height of about 78 ft (24 m); some reports give about 90 ft.

## Scenes

| # | Scene | Tool |
|---|-------|------|
| s1 | Title | three.js + HTML |
| s2 | Who he was | three.js + HTML |
| s3 | Arena flyover, height scale | Blender |
| s4 | Vest harness, snap shackle mechanism, the planned stunt | three.js |
| s5 | Fall reconstruction: real time, slow-motion replay, impact analysis | Blender + HTML HUD overlay |
| s6 | Aftermath timeline | three.js + HTML |
| s7 | Failure analysis: 1999 rig vs. a life-safety rig | three.js |
| s8 | In memory | three.js + HTML |

## Build

Requirements: Blender 5.x, ffmpeg, Node 18+, Python 3, Microsoft Edge (for headless capture), Windows (for SAPI TTS).

```bash
npm install
powershell -ExecutionPolicy Bypass -File tts.ps1          # narration -> audio/
./render_all.sh                                           # Blender s3, s5 -> frames/
node capture.mjs s1 15.5 && node capture.mjs s2 16.1      # three.js scenes -> frames/
node capture.mjs s4 27.5 && node capture.mjs s6 35.7
node capture.mjs s7 20.2 && node capture.mjs s8 13.1
node capture.mjs hud5 33.5                                # transparent HUD for s5
python assemble.py                                        # -> owen_hart_accident_reconstruction.mp4 + .srt (flags below)
```

`render_all.sh` resolves output paths itself. Set `BLENDER=/path/to/blender` if Blender isn't in the default Windows location.

## Render flags

The defaults reproduce the published render: 1080p, 16 samples, full lighting and EEVEE. Every flag is optional.

### `blender_scene.py` / `render_all.sh`

`render_all.sh` passes any flags through to both Blender scenes:

```bash
./render_all.sh                                  # default (final quality)
./render_all.sh --res 720 --samples 8 --fast-lights
./render_all.sh --draft --res 540                # quick timing preview
# single scene / frame range:
blender -b -P blender_scene.py -- s5 /abs/out/dir 485 725 --samples 12
```

| Flag | Values | Default | Effect | Approx. speed-up |
|------|--------|---------|--------|------------------|
| `--res` | `540`, `720`, `1080`, `1440`, `2160` (16:9 height) | `1080` | Output resolution | 720 → ~2×; 540 → ~4× |
| `--samples` | integer `1`–`64` | `16` | EEVEE anti-aliasing / soft-shadow samples | 8 → ~1.5× |
| `--fast-lights` | flag (on/off) | off | Hard shadows, drops two fill lights | ~1.3× |
| `--draft` | flag (on/off) | off | Workbench engine: flat colours, no glow or real shadows. Ignores `--samples` | ~10× |
| `start end` | two frame numbers | full scene | Render only that frame range | — |

Trade-offs: lower `--res` softens thin cables and ropes. Fewer `--samples` adds edge shimmer and grainy shadows. `--fast-lights` gives a darker, flatter, harder-edged look. `--draft` is for checking cameras and timing only, not for a deliverable.

### `assemble.py`

| Flag | Values | Default | Effect |
|------|--------|---------|--------|
| `--res` | `540`, `720`, `1080`, `1440`, `2160` | `1080` | Final video resolution; every scene is scaled to it, so Blender frames rendered at a different `--res` still merge with the 1080p three.js frames |
| `--crf` | integer `0`–`51` | `18` | x264 quality (lower = better and larger) |

```bash
python assemble.py --res 720 --crf 23
```

## Sources

- Wikipedia: "Over the Edge (1999)" and "Owen Hart"
- Deseret News, "Family of wrestler settles wrongful-death lawsuit" (Oct 31, 2000)
- Robb & Robb LLC case archive (1999–2000 news coverage of the lawsuit and settlement)

In memory of Owen Hart, 1965–1999.
