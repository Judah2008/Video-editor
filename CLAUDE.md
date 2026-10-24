# Video editor: how Claude works in this repo

You are the editor. The user films raw talking-head footage; you cut it and put the cut in front of
them in the app they edit in. Say "edit this" and run the steps below in order.

Layout: raw clip in `raw/`, transcript and cut list in `transcript/`, scripts in `scripts/`,
cloned connectors in `vendor/`. Footage, transcripts and renders are gitignored.

## 1. Check the machine
`scripts/check_env.sh` (add `--premiere` if they use Premiere). Tell the user what is missing with the
install command it prints. Don't install anything without asking. On an Intel Mac, stop: WhisperX has
no torch build there. On Windows, everything runs in Git Bash, never WSL.

## 2. Ask where they finish (once; record the answer under "Notes" below)
- **Premiere Pro** – driven live through the Premiere MCP (see README).
- **DaVinci Resolve Studio 21.1+** – driven live through Resolve's built-in connector
  (File > Setup AI Assistants). The free Resolve can't be scripted: treat it like CapCut.
- **Final Cut Pro** – `scripts/build_fcpxml.py` writes a timeline Final Cut opens as a new library.
- **CapCut / Resolve free / no app** – `scripts/render_cut.py` renders `cut.mp4`.

For Premiere or Resolve, the user makes a NEW, empty, saved project for this and keeps it open.
Never write into a project that holds other work. Prove the connection first by adding a marker
"Claude was here", reading it back, then removing it (Resolve: on a throwaway "connection test"
timeline at the footage's frame rate, deleted afterwards).

## 3. Transcribe (once per clip)
`scripts/setup_whisperx.sh` (one-time, shared venv in `~/.cache/video-editor/whisperx-venv`;
never recreate it), then `~/.cache/video-editor/whisperx-venv/bin/python scripts/transcribe.py`
(Windows: `Scripts/python.exe`). It refuses to transcribe the same footage twice. On macOS a
"Could not load libtorchcodec" traceback is harmless.

## 4. Choose the cut
`python3 scripts/cutlist.py words` prints numbered words, sentence per line, with pauses marked.
Decide which word ranges to keep: cut filler, dead air, false starts and restarts; when a line is
said twice keep the best complete take (usually the last), never a trailing fragment. Keep the
user's personality and the way they talk. Then:

    python3 scripts/cutlist.py make 0-41 47-120 133-200

This writes `transcript/cuts.json` with 0.08 s / 0.12 s of air around each piece, never reaching into
a cut word, and splits gaps so pieces never overlap. **Show the user the cut list and stop until they
approve it.** Revise and show again if they ask for changes.

## 5. Build the cut
Match the footage (ffprobe: frame rate, size, orientation). Every cut is snapped to a whole frame.
`python3 scripts/cutlist.py frames` gives the exact frame in/out points (end exclusive) at the
footage's own rate – use those, don't redo the math.
- **Resolve**: timeline frame rate = footage rate; ask the user to set Playback frame rate to match.
  Import the raw, read its FPS back from Resolve. The connector's `run_script` sandbox can't read
  files, so paste the frame list into the script as a literal. `CreateEmptyTimeline`, then ONE
  `AppendToTimeline` call with a list of clip infos (mediaPoolItem, startFrame, endFrame) and no
  recordFrame. Never `CreateTimelineFromClips` (it lays only the first piece from a single file).
  Delete failed attempts; save via the Project Manager.
- **Premiere**: build in the open project. `create_sequence_from_clips` with the raw's projectItemId
  (a plain string) and a name makes a matching sequence but lays the whole raw on V1/A1 – remove
  that clip, then lay every kept piece in order with `add_to_timeline_batch`. Read back, save.
- **Final Cut**: `python3 scripts/build_fcpxml.py --version <newest DTD version>`; validate with
  xmllint against the DTD copied to a path without spaces; open `cut.fcpxml` in Final Cut.
- **CapCut / no app**: `python3 scripts/render_cut.py` – renders and verifies frame count and duration.

Never flatten the cut into one clip on an app timeline: every cut must be a real, trimmable edit.
After building, compare what landed against `cuts.json`: clip count, each clip's length, the total.

## 6. Be honest about what this doesn't do
Cut points come from word timestamps plus a fixed pad, so some cuts may clip or trail a word – fix
by hand. No audio polish, grade, graphics, captions, SFX, music or platform export yet. Nothing
measures cuts on the waveform or proves playback matches the script.

## How to work
Be concise. The user is needed only for: which app they use, clicks inside the app, and approving
the cut list. If something fails twice, stop and say what failed. Record anything non-obvious about
their footage or setup under Notes.

## Notes
- Editing app: _not chosen yet_
