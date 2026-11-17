"""Runs inside an engine venv. Synthesizes every scene of script.json.
argv: <engine> <config.json> <script.json> <out_dir>
Writes <out_dir>/<id>.wav and prints one JSON line per scene:
{"id":..., "path":..., "duration":..., "words":[{"text","start","end"}] | null}
"""
import json, sys, os, re
import numpy as np
import soundfile as sf

engine, cfg_path, script_path, out_dir = sys.argv[1:5]
cfg = json.load(open(cfg_path))[engine]
scenes = json.load(open(script_path))["scenes"]
os.makedirs(out_dir, exist_ok=True)


def emit(sid, path, audio, sr, words):
    sf.write(path, audio, sr, subtype="PCM_16")
    print(json.dumps({"id": sid, "path": path, "duration": len(audio) / sr, "words": words}), flush=True)


if engine == "kokoro":
    from kokoro import KPipeline
    voice = cfg.get("voice", "am_michael")
    pipe = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
    SR = 24000
    for sc in scenes:
        chunks, words, offset = [], [], 0.0
        for res in pipe(sc["text"], voice=voice, speed=cfg.get("speed", 1.0)):
            audio = res.audio.numpy() if hasattr(res.audio, "numpy") else np.asarray(res.audio)
            for tk in (res.tokens or []):
                if tk.start_ts is None or not re.search(r"\w", tk.text):
                    continue
                words.append({"text": tk.text, "start": round(offset + tk.start_ts, 3), "end": round(offset + tk.end_ts, 3)})
            chunks.append(audio)
            offset += len(audio) / SR
        emit(sc["id"], os.path.join(out_dir, sc["id"] + ".wav"), np.concatenate(chunks), SR, words)

elif engine == "chatterbox":
    import torch
    from chatterbox.tts import ChatterboxTTS
    torch.manual_seed(cfg.get("seed", 7))
    model = ChatterboxTTS.from_pretrained(device="cpu")
    kw = {k: cfg[k] for k in ("exaggeration", "cfg_weight", "temperature") if k in cfg}
    if cfg.get("voice_prompt"):
        kw["audio_prompt_path"] = cfg["voice_prompt"]
    for sc in scenes:
        torch.manual_seed(cfg.get("seed", 7))
        try:
            wav = model.generate(sc["text"], **kw)
        except TypeError:   # older releases lack some kwargs
            kw.pop("temperature", None)
            wav = model.generate(sc["text"], **kw)
        emit(sc["id"], os.path.join(out_dir, sc["id"] + ".wav"), wav.squeeze(0).cpu().numpy(), model.sr, None)
else:
    sys.exit(f"unknown engine {engine}")
