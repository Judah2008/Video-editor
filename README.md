# Video-editor
This is what I use for my ai videos

Claude Code as a rough-cut editor: drop a raw talking-head clip in `raw/`, ask Claude to "edit this",
approve the cut list, and get the cut as real trimmable clips in your editor (or a rendered MP4).
`CLAUDE.md` holds the full workflow Claude follows.

## Setup (on your own computer)
1. Clone this repo and open Claude Code in it.
2. `scripts/check_env.sh` – needs ffmpeg, git, [uv](https://docs.astral.sh/uv/) and Python 3.11 via uv
   (`--premiere` also checks for Node 22+). Apple Silicon only on Mac.
3. `scripts/setup_whisperx.sh` – one-time WhisperX install (first transcription downloads 3–5 GB).
4. Connect your editor:
   - **Resolve Studio 21.1+**: File > Setup AI Assistants, restart Claude Code with your project open.
   - **Premiere**: clone the MCP server and install its panel:
     ```
     git clone https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP vendor/premiere-mcp
     cd vendor/premiere-mcp && git checkout v1.2.3 && npm install && npm run build
     npm run setup:mac        # or: npm run setup:win (PowerShell)
     ```
     Register it in a `.mcp.json` here (`node vendor/premiere-mcp/dist/index.js`, env
     `PREMIERE_TEMP_DIR` = the panel's temp folder, `PREMIERE_MCP_TELEMETRY=0`, `"timeout": 600000`),
     then in Premiere: Window > Extensions > MCP Bridge (CEP) > Start Bridge.
     Review that third-party code before running it.
   - **Final Cut / CapCut / no app**: nothing to connect.

## Scripts
| Script | Does |
|---|---|
| `scripts/transcribe.py` | WhisperX large-v3 with word timings → `transcript/words.json` (once per clip) |
| `scripts/cutlist.py words` / `make` / `show` / `frames` | read the transcript, write and inspect `transcript/cuts.json` |
| `scripts/render_cut.py` | one-pass ffmpeg render → `cut.mp4`, verified frame for frame |
| `scripts/build_fcpxml.py` | Final Cut timeline → `cut.fcpxml` (handles embedded/drop-frame timecode) |

Based on the free starter prompt from Jason Cooperson's "Claude Video Editor" blueprint.
