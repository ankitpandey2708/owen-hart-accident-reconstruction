"""Write the HyperFrames composition from the voice timings.

    python ../tts/generate.py   # voice -> assets/timing.json
    python build.py             # timing -> index.html, compositions/*.html, assets/timing.js, subtitles

Scene lengths, label cues, audio placement and subtitles all follow assets/timing.json,
so editing script.json and re-running both commands re-times the whole film.
"""
import json, os, re, html

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "assets", "timing.json")))
S = {s["id"]: s for s in T["scenes"]}
TOTAL = round(T["total"], 3)
G, DROP = 9.81, 23.0
TF = (2 * DROP / G) ** 0.5


def word(scene, prefix, k=0):
    ws = [w for w in T["words"] if w["scene"] == scene and re.sub(r"[^\w:']", "", w["text"].lower()).startswith(prefix)]
    return ws[min(k, len(ws) - 1)]["start"] if ws else S[scene]["voice_start"]


def end(sid):
    return S[sid]["start"] + S[sid]["duration"]


T_OPEN = word("release", "opened")
T_IMPACT = T_OPEN + TF
r3 = lambda x: f"{x:.3f}".rstrip("0").rstrip(".")

# ---------------------------------------------------------------- timing.js for the 3D world
open(os.path.join(HERE, "assets", "timing.js"), "w").write("window.HF_TIMING = " + json.dumps(T) + ";\n")

# ---------------------------------------------------------------- overlay (titles and numbers not tied to 3D objects)
# (id, start, end, html, css)
OV = [
    ("ov-hook", word("hook", "sailors") - 0.2, end("hook") - 0.15,
     '<span class="w">One part.</span> <span class="w amber">78 feet.</span>', "left:140px; top:780px;", "display"),
    ("ov-n1", word("fall", "seventy") , end("fall") - 0.1, '<span class="w amber">78</span><small>ft</small>', "left:140px; top:150px;", "num"),
    ("ov-n2", word("fall", "two"), end("fall") - 0.1, '<span class="w amber">2.2</span><small>s</small>', "left:140px; top:330px;", "num"),
    ("ov-n3", word("fall", "fifty"), end("fall") - 0.1, '<span class="w amber">48</span><small>mph</small>', "left:140px; top:510px;", "num"),
    ("ov-n4", word("fall", "fifty") + 0.4, end("fall") - 0.1, "free-fall estimate from 78 ft", "left:146px; top:700px;", "note"),
    ("ov-rope", word("impact", "top"), end("impact") - 0.1, 'Top rope<small>~1 ft from the turnbuckle</small>', "left:1180px; top:250px;", "label"),
    ("ov-aorta", word("impact", "aorta"), end("impact") - 0.1, '<span class="red">Severed aorta</span><small>blunt-force trauma</small>', "left:1180px; top:420px;", "label"),
    ("ov-time", word("after", "8:12") , end("after") - 0.15, '<span class="w">8:12</span><small>PM</small>', "left:140px; top:640px;", "num"),
    ("ov-age", word("after", "thirty"), end("after") - 0.15, "age 34", "left:146px; top:830px;", "note-lg"),
    ("ov-end", S["end"]["start"] + 0.25, TOTAL - 0.05, "No single point of failure.", "left:0; right:0; top:420px; text-align:center;", "display"),
    ("ov-name", S["end"]["voice_start"] + S["end"]["voice_duration"] + 0.6, TOTAL - 0.05, "Owen Hart &nbsp;·&nbsp; 1965 – 1999", "left:0; right:0; top:560px; text-align:center;", "note-lg"),
]
DIP = [(S["fall"]["start"] - 0.1, 0.2), (S["after"]["start"] - 0.1, 0.2)]   # dip cuts into/out of the replay

ov_html, ov_js = [], []
for i, (oid, a, b, inner, css, kind) in enumerate(OV):
    ov_html.append(f'<div id="{oid}" class="clip {kind}" data-start="{r3(a)}" data-duration="{r3(b - a)}" data-track-index="{1 + (i % 2)}" style="{css}"><div class="in">{inner}</div></div>')
    ov_js.append(f'tl.fromTo("#{oid} .in", {{opacity:0, filter:"blur(8px)"}}, {{opacity:1, filter:"blur(0px)", duration:0.18, ease:"expo.out"}}, {r3(a)});')
    ov_js.append(f'tl.to("#{oid} .in", {{opacity:0, filter:"blur(6px)", duration:0.12, ease:"power2.in"}}, {r3(b - 0.12)});')
for j, (a, d) in enumerate(DIP):
    ov_html.append(f'<div id="ov-dip{j}" class="clip dip" data-start="{r3(a)}" data-duration="{r3(d)}" data-track-index="3"><div class="in"></div></div>')
    ov_js.append(f'tl.fromTo("#ov-dip{j} .in", {{opacity:0}}, {{opacity:1, duration:0.1, ease:"none"}}, {r3(a)});')
    ov_js.append(f'tl.to("#ov-dip{j} .in", {{opacity:0, duration:0.1, ease:"none"}}, {r3(a + 0.1)});')

overlay = f"""<template>
  <style>
    #root {{ position:absolute; inset:0; font-family: Inter, sans-serif; color:#F2F0EA; }}
    #root .clip {{ position:absolute; }}
    .in {{ opacity:0; }}
    .display .in {{ font-family: Oswald, sans-serif; font-weight:700; font-size:112px; letter-spacing:-0.01em; line-height:1; text-shadow:0 4px 30px rgba(0,0,0,.6); }}
    .num .in {{ font-family: Oswald, sans-serif; font-weight:700; font-size:150px; line-height:1; text-shadow:0 4px 30px rgba(0,0,0,.65); }}
    .num small {{ font-family: Inter, sans-serif; font-size:44px; font-weight:700; margin-left:14px; color:#F2F0EA; }}
    .note .in {{ font-size:28px; color:#cfcac0; text-shadow:0 2px 12px rgba(0,0,0,.8); }}
    .note-lg .in {{ font-size:40px; font-weight:400; color:#e6e1d8; text-shadow:0 2px 14px rgba(0,0,0,.8); }}
    .label .in {{ font-size:44px; font-weight:700; line-height:1.15; padding:14px 22px; background:rgba(8,8,10,.72); border-left:5px solid #F2A93B; }}
    .label small {{ display:block; font-size:28px; font-weight:400; color:#d6d1c8; }}
    .amber {{ color:#F2A93B; }} .red {{ color:#E0301E; }}
    .dip {{ inset:0; }} .dip .in {{ position:absolute; inset:0; background:#000; }}
  </style>
  <div id="root" data-composition-id="overlay" data-width="1920" data-height="1080" data-layout-allow-overlap>
    {chr(10).join('    ' + h for h in ov_html)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + j for j in ov_js)}
    tl.set({{}}, {{}}, {r3(TOTAL)});
    window.__timelines["overlay"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- world (three.js) + its anchored labels
LABELS = [
    ("lb-arena", "Kemper Arena<small>Kansas City · May 23, 1999</small>", ""),
    ("lb-height", '<span class="amber">78 ft</span><small>rafters to ring</small>', "amber"),
    ("lb-plan", "Planned release<small>a few feet above the mat</small>", ""),
    ("lb-lanyard", "Pull lanyard", "red"),
    ("lb-rated", "Rated locking connector", "green"),
    ("lb-two", "Second, independent line", "green"),
    ("lb-noqr", "No quick release on the load", "green"),
]
world = f"""<template>
  <style>
    #root {{ position:absolute; inset:0; overflow:hidden; }}
    #world-canvas {{ position:absolute; inset:0; width:1920px; height:1080px; }}
    .lb {{ position:absolute; left:0; top:0; opacity:0; font-family: Inter, sans-serif; color:#F2F0EA; font-size:36px; font-weight:700;
          line-height:1.15; white-space:nowrap; padding:10px 18px 12px; background:rgba(8,8,10,.74); border-left:5px solid #F2F0EA;
          margin:-40px 0 0 34px; }}
    .lb small {{ display:block; font-size:28px; font-weight:400; color:#d6d1c8; }}
    .lb.amber {{ border-color:#F2A93B; }} .lb.red {{ border-color:#E0301E; }} .lb.green {{ border-color:#3FBF7F; }}
    .lb .amber {{ color:#F2A93B; }} .lb .red {{ color:#E0301E; }}
    .lb::before {{ content:""; position:absolute; left:-34px; top:40px; width:30px; height:3px; background:currentColor; opacity:.9; }}
  </style>
  <div id="root" data-composition-id="world" data-width="1920" data-height="1080" data-layout-allow-overlap data-layout-allow-overflow>
    <canvas id="world-canvas" width="1920" height="1080"></canvas>
    {chr(10).join(f'    <div id="{i}" class="lb {c}">{h}</div>' for i, h, c in LABELS)}
  </div>
  <script src="assets/timing.js"></script>
  <script src="assets/world.js"></script>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.set({{}}, {{}}, {r3(TOTAL)});
    window.__timelines["world"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- root: scene hosts, footage, audio
# Replay footage grade, matched to the 3D world's grade pass (assets/world.js). Validated with
# `npx hyperframes media-treatment --grading grade_replay.json --dry-run`.
GRADE = json.dumps(json.load(open(os.path.join(HERE, 'grade_replay.json'))), separators=(',', ':'))
SFX = [  # (id, file, start, volume, fade_out)
    ("sfx-latch", "assets/sfx/latch.mp3", 0.3, 0.9, 0),
    ("sfx-snap", "assets/sfx/latch.mp3", T_OPEN, 1.0, 0),
    ("sfx-fall", "assets/sfx/whoosh.mp3", T_OPEN + 0.05, 0.55, 0.3),
    ("sfx-thud", "assets/sfx/thud.mp3", T_IMPACT, 0.9, 0),
    ("sfx-bass", "assets/sfx/bass.mp3", T_IMPACT, 0.8, 1.0),
    ("sfx-replay", "assets/sfx/thud.mp3", S["impact"]["start"] + 0.94, 0.35, 0),
]
SFX_DUR = {"assets/sfx/latch.mp3": 0.366, "assets/sfx/whoosh.mp3": TF - 0.06, "assets/sfx/thud.mp3": 2.116, "assets/sfx/bass.mp3": 3.582}

voice = "\n".join(
    f'      <audio id="vo-{s["id"]}" class="clip" src="{s["voice"]}" data-start="{r3(s["voice_start"])}" data-duration="{r3(s["voice_duration"])}" data-track-index="5" data-volume="1"></audio>'
    for s in T["scenes"])
def sfx_tag(k, i, f, st, v, fo):
    fade = f' data-fade-out="{fo}"' if fo > 0 else ""
    lane = 7 if k % 2 == 0 else 8       # overlapping effects need a second lane
    return (f'      <audio id="{i}" class="clip" src="{f}" data-start="{r3(st)}" '
            f'data-duration="{r3(min(SFX_DUR[f], TOTAL - st))}" data-track-index="{lane}" data-volume="{v}"{fade}></audio>')


sfx = "\n".join(sfx_tag(k, *row) for k, row in enumerate(SFX))
BGM_A_END = T_OPEN                       # the music stops at the snap
BGM_B = S["fix"]["start"]                # and returns for the fix
bgm = (f'      <audio id="bgm-a" class="clip" src="assets/bgm/track.mp3" data-start="0" data-duration="{r3(BGM_A_END)}" data-track-index="6" data-volume="0.16" data-fade-in="0.4" data-fade-out="0.08"></audio>\n'
       f'      <audio id="bgm-b" class="clip" src="assets/bgm/track.mp3" data-start="{r3(BGM_B)}" data-media-start="19.5" data-duration="{r3(TOTAL - BGM_B)}" data-track-index="6" data-volume="0.18" data-fade-in="1.5" data-fade-out="1.8"></audio>')

index = f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>One part, 78 feet</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ width:1920px; height:1080px; overflow:hidden; background:#07080a; }}
      #root {{ position:relative; width:100%; height:100%; }}
      .footage {{ position:absolute; left:0; top:0; width:1920px; height:1080px; object-fit:cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{r3(TOTAL)}" data-width="1920" data-height="1080">
      <div id="world" data-composition-id="world" data-composition-src="compositions/world.html" data-start="0" data-duration="{r3(TOTAL)}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index:1"></div>
      <video id="replay-fall" class="clip footage" src="assets/footage/replay_fall.mp4" data-color-grading='{GRADE}' data-start="{r3(S['fall']['start'])}" data-duration="{r3(S['fall']['duration'])}" data-track-index="2" muted playsinline style="z-index:2"></video>
      <video id="replay-impact" class="clip footage" src="assets/footage/replay_impact.mp4" data-color-grading='{GRADE}' data-start="{r3(S['impact']['start'])}" data-duration="{r3(S['impact']['duration'])}" data-track-index="2" muted playsinline style="z-index:2"></video>
      <div id="overlay" data-composition-id="overlay" data-composition-src="compositions/overlay.html" data-start="0" data-duration="{r3(TOTAL)}" data-track-index="3" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index:3"></div>
{voice}
{bgm}
{sfx}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.set({{}}, {{}}, {r3(TOTAL)});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""

os.makedirs(os.path.join(HERE, "compositions"), exist_ok=True)
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(index)
open(os.path.join(HERE, "compositions", "world.html"), "w", encoding="utf-8").write(world)
open(os.path.join(HERE, "compositions", "overlay.html"), "w", encoding="utf-8").write(overlay)

# ---------------------------------------------------------------- subtitles sidecar (4-6 word groups)
def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")

out, n = [], 1
for s in T["scenes"]:
    ws = [w for w in T["words"] if w["scene"] == s["id"]]
    grp = []
    for i, w in enumerate(ws):
        grp.append(w)
        if len(grp) >= 6 or w["text"][-1] in ".,:;?!" and len(grp) >= 3 or i == len(ws) - 1:
            out.append(f"{n}\n{ts(grp[0]['start'])} --> {ts(grp[-1]['end'] + 0.15)}\n{' '.join(x['text'] for x in grp)}\n"); n += 1; grp = []
open(os.path.join(HERE, "subtitles.srt"), "w", encoding="utf-8").write("\n".join(out))
print(f"built: {TOTAL}s, open {T_OPEN:.2f}s, impact {T_IMPACT:.2f}s, {len(OV)} overlays, {n - 1} subtitle groups")
