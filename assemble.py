"""Encode each scene clip with narration, concat, add subtitles.
Usage: python assemble.py [--res 540|720|1080|1440|2160] [--crf N]
Every scene is scaled to --res (default 1080), so Blender and three.js frames may differ in resolution."""
import json, os, re, subprocess, glob, argparse
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
RES = {540: (960, 540), 720: (1280, 720), 1080: (1920, 1080), 1440: (2560, 1440), 2160: (3840, 2160)}
ap = argparse.ArgumentParser()
ap.add_argument("--res", type=int, choices=sorted(RES), default=1080)
ap.add_argument("--crf", type=int, default=18, help="x264 quality, 0-51 (lower = better/larger)")
args = ap.parse_args()
OW, OH = RES[args.res]
SC = f"scale={OW}:{OH}:flags=lanczos"
ORDER = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
AUDIO = {"s1": "s1_title", "s2": "s2_who", "s3": "s3_arena", "s4": "s4_rig", "s5": "s5_fall",
         "s6": "s6_after", "s7": "s7_lessons", "s8": "s8_memoriam"}
LEAD = 0.5  # seconds of silence before narration
narr = {x["id"]: x["text"] for x in json.load(open("narration.json"))}

def run(cmd):
    print(" ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True)

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

os.makedirs("clips", exist_ok=True)
starts, t = {}, 0.0
for s in ORDER:
    n = len(glob.glob(f"frames/{s}/*.png"))
    d = n / FPS
    a = f"audio/{AUDIO[s]}.wav"
    fo = max(0, d - 0.6)
    vf = f"fade=t=in:st=0:d=0.5,fade=t=out:st={fo:.3f}:d=0.6,format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", f"frames/{s}/%04d.png"]
    if s == "s5":
        cmd += ["-framerate", str(FPS), "-i", "frames/hud5/%04d.png", "-i", a,
                "-filter_complex", f"[0]{SC}[b];[1]{SC}[h];[b][h]overlay=format=auto,{vf}[v];[2]adelay={int(LEAD*1000)}:all=1,apad[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-i", a, "-filter_complex", f"[0]{SC},{vf}[v];[1]adelay={int(LEAD*1000)}:all=1,apad[a]",
                "-map", "[v]", "-map", "[a]"]
    cmd += ["-t", f"{d:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", f"clips/{s}.mp4"]
    run(cmd)
    starts[s] = (t, d)
    t += d

with open("clips/list.txt", "w") as f:
    for s in ORDER:
        f.write(f"file '{s}.mp4'\n")

# subtitles: split narration into sentences, time by character share
def ts(x):
    h, r = divmod(x, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")

srt, i = [], 1
for s in ORDER:
    t0, d = starts[s]
    a_d = dur(f"audio/{AUDIO[s]}.wav")
    parts = [p.strip() for p in re.split(r"(?<=[.:])\s+", narr[AUDIO[s]]) if p.strip()]
    total = sum(len(p) for p in parts)
    c = t0 + LEAD
    for p in parts:
        span = a_d * len(p) / total
        srt.append(f"{i}\n{ts(c)} --> {ts(c + span)}\n{p}\n"); i += 1
        c += span
open("owen_hart_accident_reconstruction.srt", "w", encoding="utf-8").write("\n".join(srt))

run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "clips/list.txt",
     "-i", "owen_hart_accident_reconstruction.srt", "-map", "0", "-map", "1",
     "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
     "-movflags", "+faststart", "owen_hart_accident_reconstruction.mp4"])
print("TOTAL", round(t, 2), "s")
