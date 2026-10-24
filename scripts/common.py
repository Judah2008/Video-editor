"""Shared helpers: ffprobe, frame math, project paths. Standard library only."""
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
TRANSCRIPT_DIR = ROOT / "transcript"
WORDS_JSON = TRANSCRIPT_DIR / "words.json"
CUTS_JSON = TRANSCRIPT_DIR / "cuts.json"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".mxf", ".webm"}


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_raw(path=None):
    """Return the raw clip: the given path, or the only video file in raw/."""
    if path:
        p = Path(path).resolve()
        if not p.is_file():
            die(f"{p} not found")
        return p
    clips = sorted(p for p in RAW_DIR.glob("*") if p.suffix.lower() in VIDEO_EXTS)
    if not clips:
        die("no video in raw/ - copy your clip there first")
    if len(clips) > 1:
        die("more than one video in raw/ - pass the one to use: " + ", ".join(c.name for c in clips))
    return clips[0]


def probe(path):
    """Frame rate, size, orientation, duration, timecode and audio layout of a clip."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if video is None:
        die(f"{path} has no video stream")

    fps = Fraction(video.get("r_frame_rate", "0/1"))
    avg = Fraction(video.get("avg_frame_rate", "0/1") or "0/1")
    if fps == 0 or (avg and abs(fps - avg) / avg > Fraction(1, 100)):
        # r_frame_rate is the stream's timebase guess; trust the average when they disagree a lot.
        fps = avg
    fps = _snap_fps(fps)

    rotation = 0
    for sd in video.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    rotation = int(video.get("tags", {}).get("rotate", rotation)) % 360

    width, height = video["width"], video["height"]
    if rotation in (90, 270):
        width, height = height, width

    timecode = video.get("tags", {}).get("timecode") or data["format"].get("tags", {}).get("timecode")
    duration = float(video.get("duration") or data["format"]["duration"])

    return {
        "path": str(path),
        "fps": fps,
        "width": width,
        "height": height,
        "rotation": rotation,
        "orientation": "vertical" if height > width else "landscape" if width > height else "square",
        "duration": duration,
        "frames": int(video["nb_frames"]) if video.get("nb_frames", "").isdigit() else None,
        "timecode": timecode,
        "has_audio": audio is not None,
        "audio_channels": int(audio["channels"]) if audio else 0,
        "audio_rate": int(audio["sample_rate"]) if audio else 0,
    }


def _snap_fps(fps):
    """Snap near-standard rates (e.g. 2997/100) to their exact NTSC fractions."""
    for std in (Fraction(24000, 1001), Fraction(30000, 1001), Fraction(60000, 1001),
                Fraction(24), Fraction(25), Fraction(30), Fraction(50), Fraction(60)):
        if abs(fps - std) < Fraction(1, 100):
            return std
    return fps


def to_frame(seconds, fps):
    return round(Fraction(seconds).limit_denominator(1_000_000) * fps)


def timecode_to_frames(tc, fps):
    """Frames from a SMPTE timecode string; ';' marks drop-frame."""
    drop = ";" in tc
    hh, mm, ss, ff = (int(x) for x in tc.replace(";", ":").split(":"))
    nominal = round(fps)
    frames = ((hh * 60 + mm) * 60 + ss) * nominal + ff
    if drop:
        dropped = 2 if nominal == 30 else 4
        minutes = hh * 60 + mm
        frames -= dropped * (minutes - minutes // 10)
    return frames


def load_cuts(path=CUTS_JSON):
    if not Path(path).is_file():
        die(f"{path} not found - write the cut list first")
    segments = json.loads(Path(path).read_text())["segments"]
    if not segments:
        die("cuts.json has no segments")
    return segments


def frame_ranges(segments, fps, total_frames=None):
    """[(start_frame, end_frame_exclusive)] snapped to the footage's frame grid."""
    ranges = []
    for i, seg in enumerate(segments):
        a, b = to_frame(seg["start"], fps), to_frame(seg["end"], fps)
        if total_frames is not None:
            b = min(b, total_frames)
        if b <= a:
            die(f"segment {i} is shorter than one frame after snapping: {seg}")
        if ranges and a < ranges[-1][1]:
            die(f"segment {i} overlaps or runs backwards from segment {i - 1}")
        ranges.append((a, b))
    return ranges
