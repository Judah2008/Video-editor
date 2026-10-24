#!/usr/bin/env bash
# Check this machine for what the editor needs. Installs nothing.
# Usage: scripts/check_env.sh [--premiere]
missing=()
ok()   { printf '  ok       %s\n' "$1"; }
miss() { printf '  MISSING  %s  ->  %s\n' "$1" "$2"; missing+=("$1"); }

case "$(uname -s)" in
  Darwin) os=mac ;;
  MINGW*|MSYS*|CYGWIN*) os=windows ;;
  *) os=linux ;;
esac
inst() { case $os in mac) echo "brew install $1" ;; windows) echo "winget install $2" ;; *) echo "your package manager: $1" ;; esac; }

echo "OS: $os ($(uname -m))"
if [ "$os" = mac ] && [ "$(uname -m)" != arm64 ]; then
  echo "  STOP: Intel Mac. WhisperX's torch has no build for Intel Macs, so transcription won't run here."
fi

command -v ffmpeg  >/dev/null && ok "ffmpeg ($(ffmpeg -version | head -1 | cut -d' ' -f3))" || miss ffmpeg "$(inst ffmpeg Gyan.FFmpeg)"
command -v ffprobe >/dev/null && ok ffprobe || miss ffprobe "comes with ffmpeg"
command -v git     >/dev/null && ok git     || miss git "$(inst git Git.Git)"
if command -v uv >/dev/null; then
  ok "uv ($(uv --version | cut -d' ' -f2))"
  if py=$(uv python find 3.11 2>/dev/null); then ok "python 3.11 ($py)"; else miss "python 3.11" "uv python install 3.11"; fi
else
  miss uv "$(inst uv astral-sh.uv)"
fi
command -v python3 >/dev/null && ok "python3 for the helper scripts ($(python3 --version 2>&1))" || miss python3 "uv python install 3.11"

if [ "$1" = --premiere ]; then
  if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then
    ok "node $(node --version)"
  else
    miss "node 22+" "$(inst node OpenJS.NodeJS.LTS)"
  fi
fi

venv=~/.cache/video-editor/whisperx-venv
if [ -d "$venv" ]; then ok "WhisperX venv ($venv)"; else echo "  todo     WhisperX venv  ->  scripts/setup_whisperx.sh"; fi

[ ${#missing[@]} -eq 0 ] && echo "ready" || { echo "missing: ${missing[*]}"; exit 1; }
