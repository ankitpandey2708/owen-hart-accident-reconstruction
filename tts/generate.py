"""Generate narration for the HyperFrames video.

    python tts/generate.py                 # engine from tts/config.json
    python tts/generate.py --engine chatterbox

Writes video/assets/voice/<scene>.wav and video/assets/timing.json:
scene start/duration (seconds, voice-driven) and every word's absolute start/end.
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIDEO = os.path.join(ROOT, "video")
VOICE_DIR = os.path.join(VIDEO, "assets", "voice")
SCRIPT = os.path.join(VIDEO, "script.json")
CFG = os.path.join(HERE, "config.json")

ap = argparse.ArgumentParser()
ap.add_argument("--engine", choices=["kokoro", "chatterbox"])
args = ap.parse_args()
cfg = json.load(open(CFG))
engine = args.engine or cfg["engine"]
py = os.path.join(HERE, f"{engine}-venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
if not os.path.exists(py):
    sys.exit(f"{engine} venv missing: {py}")

script = json.load(open(SCRIPT))
print(f"engine: {engine}")
proc = subprocess.run([py, "-I", os.path.join(HERE, "worker.py"), engine, CFG, SCRIPT, VOICE_DIR],
                      capture_output=True, text=True, encoding="utf-8")
results = {}
for line in proc.stdout.splitlines():
    if line.startswith("{"):
        r = json.loads(line); results[r["id"]] = r
if proc.returncode or len(results) != len(script["scenes"]):
    sys.stderr.write(proc.stderr[-3000:]); sys.exit("synthesis failed")


def loudnorm(path):
    """Normalize each narration file to -16 LUFS, -1.5 dBTP (EBU R128) so the mix lands at -16..-14."""
    tmp = path + ".tmp.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", tmp], check=True)
    os.replace(tmp, path)


for r in results.values():
    loudnorm(r["path"])


def script_words(text):
    return re.findall(r"[\w'’:.,-]*\w[\w'’]*[.,:;!?]?", text)


def transcribe(wav):
    """Word timings for engines without native timestamps (HyperFrames' whisper)."""
    cmd = "npx --yes hyperframes@0.9.59 transcribe " + f'"{wav}" --model small.en --json'
    out = subprocess.run(cmd, cwd=VIDEO, shell=True, capture_output=True, text=True, encoding="utf-8")
    path = os.path.join(VIDEO, "assets", "transcript.json")
    if not os.path.exists(path):
        sys.stderr.write(out.stdout[-2000:] + out.stderr[-2000:]); sys.exit("transcribe failed")
    data = json.load(open(path, encoding="utf-8"))
    os.remove(path)
    return [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in data if re.search(r"\w", w.get("text", ""))]


def align(text, timed, duration):
    """Map script words onto timed words by position; spread evenly if counts differ badly."""
    sw = script_words(text)
    if timed and abs(len(timed) - len(sw)) <= max(1, len(sw) // 10):
        n = len(timed)
        return [{"text": w, "start": timed[min(i * n // len(sw), n - 1)]["start"],
                 "end": timed[min(((i + 1) * n - 1) // len(sw), n - 1)]["end"]} for i, w in enumerate(sw)]
    total = sum(len(w) for w in sw); t = 0.05; out = []
    for w in sw:
        d = (duration - 0.1) * len(w) / total
        out.append({"text": w, "start": round(t, 3), "end": round(t + d, 3)}); t += d
    print("  warning: word timing estimated by length")
    return out


pad = script.get("pad_after", 0.6)
lead = 0.4
t, scenes, words = 0.0, [], []
for sc in script["scenes"]:
    r = results[sc["id"]]
    timed = r["words"] if r["words"] else transcribe(r["path"])
    aligned = align(sc["text"], timed, r["duration"])
    dur = round(lead + r["duration"] + pad + sc.get("hold_after", 0), 3)
    scenes.append({"id": sc["id"], "start": round(t, 3), "duration": dur, "voice": f"assets/voice/{sc['id']}.wav",
                   "voice_start": round(t + lead, 3), "voice_duration": round(r["duration"], 3), "text": sc["text"]})
    for w in aligned:
        words.append({"id": f"w{len(words)}", "scene": sc["id"], "text": w["text"],
                      "start": round(t + lead + w["start"], 3), "end": round(t + lead + w["end"], 3)})
    print(f"  {sc['id']:8s} {r['duration']:5.2f}s  start {t:6.2f}")
    t += dur

timing = {"engine": engine, "total": round(t, 3), "scenes": scenes, "words": words}
json.dump(timing, open(os.path.join(VIDEO, "assets", "timing.json"), "w"), indent=1)
print(f"total {t:.2f}s -> video/assets/timing.json")
