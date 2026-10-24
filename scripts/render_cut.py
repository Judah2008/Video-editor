#!/usr/bin/env python3
"""Render transcript/cuts.json as ./cut.mp4 in one ffmpeg pass, then verify it frame for frame.

For CapCut, DaVinci Resolve (free) or no editing app.
  python3 scripts/render_cut.py [--raw raw/clip.mov] [--out cut.mp4]
"""
import argparse
import subprocess
from fractions import Fraction
from pathlib import Path

from common import ROOT, die, find_raw, frame_ranges, load_cuts, probe


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw")
    p.add_argument("--out", default=str(ROOT / "cut.mp4"))
    p.add_argument("--crf", default="16")
    args = p.parse_args()

    raw = find_raw(args.raw)
    info = probe(raw)
    fps = info["fps"]
    ranges = frame_ranges(load_cuts(), fps, info["frames"])

    parts, labels = [], []
    for i, (a, b) in enumerate(ranges):
        parts.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]")
        labels.append(f"[v{i}]")
        if info["has_audio"]:
            t0, t1 = Fraction(a) / fps, Fraction(b) / fps
            parts.append(f"[0:a]atrim=start={float(t0):.6f}:end={float(t1):.6f},asetpts=PTS-STARTPTS[a{i}]")
            labels.append(f"[a{i}]")
    n_audio = 1 if info["has_audio"] else 0
    parts.append("".join(labels) + f"concat=n={len(ranges)}:v=1:a={n_audio}[v]" + ("[a]" if n_audio else ""))

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
           "-filter_complex", ";".join(parts), "-map", "[v]"]
    if n_audio:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "320k"]
    # passthrough, never -r: forcing a rate silently duplicates frames at the cuts.
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", args.crf, "-pix_fmt", "yuv420p",
            "-fps_mode", "passthrough", "-movflags", "+faststart", args.out]
    subprocess.run(cmd, check=True)

    expected_frames = sum(b - a for a, b in ranges)
    expected_secs = float(Fraction(expected_frames) / fps)
    counted = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", args.out],
        check=True, capture_output=True, text=True).stdout.strip()
    got = probe(args.out)
    print(f"{Path(args.out).name}: {counted} frames, {got['duration']:.3f}s "
          f"(expected {expected_frames} frames, {expected_secs:.3f}s, {len(ranges)} pieces)")
    if int(counted) != expected_frames:
        die("frame count does not match cuts.json")
    if abs(got["duration"] - expected_secs) > 1.5 / float(fps):
        die("duration does not match cuts.json")
    print("verified")


if __name__ == "__main__":
    main()
