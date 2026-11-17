# SPEC: One part, 78 feet

```text
GOAL:    the viewer leaves knowing one quick-release part was the only thing holding a person 78 ft up,
         with nothing backing it up, and that a life-safety rig never has a single point of failure.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps, H.264 + AAC; soft .srt sidecar (no burned-in captions).
TIME:    voice-driven, 72.3 s (assets/timing.json, from tts/generate.py). The voice is the clock:
         each label lands on the word that names it.
LOOK:    medium = an arena at night: black steel and canvas under one warm key.
         ground: the arena itself (floor #0b0c0f, stands #1a1714 to #3a2e26 seeded noise), never a void.
         ink #F2F0EA; measurement amber #F2A93B (ruler, numbers); failure red #E0301E, used ONLY
         on the shackle opening, the missing backup line and the impact. Fix green #3FBF7F only in the fix scene.
         display: Oswald 700, 88-120 px, tracking -1%; labels: Inter 700 30 px / Inter 400 24 px.
         light: warm key spot 3400 K over the ring (3 m above the ring at 24 deg), cool rim from behind (#9DB4FF, 0.6),
         hemisphere fill 0.25, RoomEnvironment env intensity 0.5, metal roughness >= 0.35. No bloom.
OBJECTS: snap shackle (polished stainless: swivel eye, jaw, hinged gate, plunger, red pull lanyard);
         padded vest harness (black webbing, back plate, D-ring); steel cable to a rafter catwalk;
         crash-test mannequin (yellow / black joints: never a likeness of a person); 20 ft ring with
         3 red ropes and blue pads; 78 ft ruler in 10 ft ticks; corrected rig: 2 cables, 2 locking carabiners.
MOTION:  camera = one continuous take in the 3D world, every move power2.inOut, 1.2-3.0 s per move;
         labels: whole-line blur 8 -> 0 px + opacity 0 -> 1 in 0.18 s (expo.out); exits 0.12 s; labels hold still.
         numbers: blur-in per word 0.13 s, 0.07 s stagger. Gate: snaps open in 3 frames (0.1 s), linear.
         fall: real free fall, y = h - 4.905 t^2, 2.17 s, no easing.
SHOTS:   hook     0.0-6.6   macro of the shackle; gate snaps shut (click at 0.35 s); line "One part. 78 feet."
         who      6.6-16.2  continuous pull-back: shackle -> vest -> cable -> rafters -> the 78 ft drop; ruler lands on "above"
         plan     16.2-23.9 wide side view; ghost mannequin slides down a dashed path to the planned release mark
         release  23.9-34.6 dive back to the shackle; lanyard; "backup line: none"; at 29.9 the gate opens,
                            mannequin drops away, camera looks straight down from the catwalk: 2.17 s real time, impact,
                            then 1.5 s near-silence (the music stopped at the snap)
         fall     34.6-41.8 dip cut into the Blender slow replay; numbers 78 ft / 2.2 s / 48 mph land on their words
         impact   41.8-49.5 Blender close-up at the corner; "top rope, ~1 ft from turnbuckle"; "aorta" in red
         after    49.5-56.7 back in the world, high over the ring, mannequin gone; "8:12 PM" and "age 34"
         fix      56.7-65.3 truck from the open shackle to a corrected rig; 3 labels on their parts (green); music returns
         end      65.3-72.3 pull up and back; "No single point of failure." then "Owen Hart, 1965-1999"; hold 2 s
BANNED:  dark void with floating UI; glow/bloom/particles; HUD readouts as decoration; three cards in a row;
         bullet slides; text repeating the narration word for word; titles moving after they land;
         gore, blood, or any depiction of the real person (mannequin only).
QA:      0.4 (shackle fills > 40% of frame), 12.5 (vest + cable visible), 16.0 (ruler + ring), 21 (ghost path),
         28.5 (backup-line label), 30.9 (mannequin mid-fall), 37.5 (numbers), 45 (impact labels), 52 (8:12 PM),
         62 (fix labels), 70 (end line).
```
