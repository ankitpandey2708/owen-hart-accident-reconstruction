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
python assemble.py                                        # -> owen_hart_accident_reconstruction.mp4 + .srt
```

The Blender script takes absolute output paths (see `render_all.sh`); edit them for your machine.

## Sources

- Wikipedia: "Over the Edge (1999)" and "Owen Hart"
- Deseret News, "Family of wrestler settles wrongful-death lawsuit" (Oct 31, 2000)
- Robb & Robb LLC case archive (1999–2000 news coverage of the lawsuit and settlement)

In memory of Owen Hart, 1965–1999.
