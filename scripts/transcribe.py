#!/usr/bin/env python3
"""Transcribe the raw clip once with WhisperX (large-v3, word-level alignment) -> transcript/words.json.

Run with the shared WhisperX venv's python (see scripts/setup_whisperx.sh):
  ~/.cache/video-editor/whisperx-venv/bin/python scripts/transcribe.py [--raw raw/clip.mov]
"""
import argparse
import json
import os
import subprocess
import sys

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TRANSCRIPT_DIR, WORDS_JSON, find_raw  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw")
    p.add_argument("--language", help="e.g. en (default: detect)")
    p.add_argument("--force", action="store_true", help="transcribe again even if words.json exists")
    args = p.parse_args()

    raw = find_raw(args.raw)
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    if WORDS_JSON.is_file() and not args.force:
        source = json.loads(WORDS_JSON.read_text()).get("source")
        if source == raw.name:
            print(f"{WORDS_JSON} already exists for {raw.name} - not transcribing twice")
            return
        sys.exit(f"error: {WORDS_JSON} is for {source}, not {raw.name}; move it away or pass --force")

    wav = TRANSCRIPT_DIR / "audio16k.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True)

    import whisperx

    device, compute = "cpu", "int8"
    try:
        import torch
        if torch.cuda.is_available():
            device, compute = "cuda", "float16"
    except Exception:
        pass
    print(f"transcribing on {device} ({compute}); the first run downloads 3-5 GB of models")

    audio = whisperx.load_audio(str(wav))
    try:
        model = whisperx.load_model("large-v3", device, compute_type=compute, language=args.language)
        result = model.transcribe(audio, batch_size=16 if device == "cuda" else 4)
    except Exception as e:
        if device != "cuda":
            raise
        print(f"CUDA failed ({e}); falling back to CPU int8")
        device = "cpu"
        model = whisperx.load_model("large-v3", device, compute_type="int8", language=args.language)
        result = model.transcribe(audio, batch_size=4)

    align_model, meta = whisperx.load_align_model(language_code=result["language"], device=device)
    aligned = whisperx.align(result["segments"], align_model, meta, audio, device, return_char_alignments=False)

    out = {"source": raw.name, "language": result["language"], "segments": aligned["segments"]}
    WORDS_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    wav.unlink()
    n = sum(len(s.get("words", [])) for s in out["segments"])
    print(f"wrote {WORDS_JSON}: {len(out['segments'])} segments, {n} words")


if __name__ == "__main__":
    main()
