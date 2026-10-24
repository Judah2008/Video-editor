#!/usr/bin/env bash
# Create the shared WhisperX environment once; reused by every project. Never recreates it.
set -euo pipefail
export PYTHONUTF8=1 HF_HUB_DISABLE_SYMLINKS=1

venv=~/.cache/video-editor/whisperx-venv
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) py="$venv/Scripts/python.exe"; win=1 ;; *) py="$venv/bin/python"; win=0 ;; esac

if [ -x "$py" ]; then
  echo "WhisperX venv already exists: $venv"
else
  uv venv "$venv" --python 3.11
  uv pip install --python "$py" whisperx
fi

# Windows + NVIDIA: PyPI torch is CPU-only. Swap in the CUDA build of the SAME versions WhisperX installed.
if [ "$win" = 1 ] && command -v nvidia-smi >/dev/null && ! "$py" -c "import torch,sys;sys.exit(not torch.cuda.is_available())" 2>/dev/null; then
  read -r tv tav < <("$py" -c "import torch,torchaudio;print(torch.__version__.split('+')[0], torchaudio.__version__.split('+')[0])")
  uv pip install --python "$py" --reinstall-package torch --reinstall-package torchaudio \
    "torch==$tv" "torchaudio==$tav" --index-url https://download.pytorch.org/whl/cu128
fi

"$py" -c "import torch, whisperx.asr; print('whisperx ok; cuda:', torch.cuda.is_available())"
echo "transcribe with: $py scripts/transcribe.py"
