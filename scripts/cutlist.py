#!/usr/bin/env python3
"""Read the transcript and write/inspect the cut list.

  python3 scripts/cutlist.py words              numbered words with times, grouped by sentence
  python3 scripts/cutlist.py make 0-41 47-120   keep those word ranges (inclusive) -> transcript/cuts.json
  python3 scripts/cutlist.py show               print cuts.json for review
  python3 scripts/cutlist.py frames             cuts.json as frame in/out points at the footage's rate
"""
import argparse
import json
import sys

from common import CUTS_JSON, WORDS_JSON, die, find_raw, frame_ranges, load_cuts, probe

PAD_BEFORE = 0.08
PAD_AFTER = 0.12


def load_words():
    if not WORDS_JSON.is_file():
        die(f"{WORDS_JSON} not found - run scripts/transcribe.py first")
    data = json.loads(WORDS_JSON.read_text())
    words = []
    for seg in data["segments"]:
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": w.get("start"), "end": w.get("end"),
                          "sentence_end": False})
        if words:
            words[-1]["sentence_end"] = True
    # Alignment leaves some tokens (numbers, symbols) without times: borrow from neighbours.
    for i, w in enumerate(words):
        if w["start"] is None:
            prev_end = next((words[j]["end"] for j in range(i - 1, -1, -1) if words[j]["end"] is not None), 0.0)
            w["start"] = prev_end
        if w["end"] is None:
            next_start = next((words[j]["start"] for j in range(i + 1, len(words)) if words[j]["start"] is not None), None)
            w["end"] = next_start if next_start is not None else w["start"] + 0.2
    return words


def cmd_words(_):
    words = load_words()
    line, line_start = [], 0.0
    for i, w in enumerate(words):
        if not line:
            line_start = w["start"]
        gap = w["start"] - words[i - 1]["end"] if i else w["start"]
        if gap >= 0.7:
            line.append(f"[pause {gap:.1f}s]")
        line.append(f"{i}:{w['word']}")
        if w["sentence_end"] or i == len(words) - 1:
            print(f"{line_start:8.2f}  " + " ".join(line))
            line = []


def parse_ranges(specs, n):
    ranges = []
    for spec in specs:
        for part in spec.split(","):
            a, _, b = part.partition("-")
            a, b = int(a), int(b or a)
            if not (0 <= a <= b < n):
                die(f"bad range {part} (transcript has words 0-{n - 1})")
            ranges.append((a, b))
    ranges.sort()
    merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def cmd_make(args):
    words = load_words()
    duration = probe(find_raw(args.raw))["duration"]
    segments = []
    for a, b in parse_ranges(args.ranges, len(words)):
        start = words[a]["start"] - PAD_BEFORE
        end = words[b]["end"] + PAD_AFTER
        if a > 0:
            start = max(start, words[a - 1]["end"])  # never reach into a word that was cut
        if b + 1 < len(words):
            end = min(end, words[b + 1]["start"])
        segments.append({"start": max(0.0, start), "end": min(duration, end),
                         "text": " ".join(w["word"] for w in words[a:b + 1]),
                         "_first": a, "_last": b})
    # Two kept pieces closer than the padding: split the gap between them.
    for prev, cur in zip(segments, segments[1:]):
        if prev["end"] > cur["start"]:
            mid = (words[prev["_last"]]["end"] + words[cur["_first"]]["start"]) / 2
            prev["end"] = cur["start"] = mid
    for s in segments:
        s["start"], s["end"] = round(s["start"], 3), round(s["end"], 3)
        del s["_first"], s["_last"]
    CUTS_JSON.write_text(json.dumps({"segments": segments}, indent=2) + "\n")
    print(f"wrote {CUTS_JSON.relative_to(CUTS_JSON.parent.parent)}")
    cmd_show(args)


def cmd_show(_):
    segments = load_cuts()
    total = 0.0
    for i, s in enumerate(segments):
        length = s["end"] - s["start"]
        total += length
        print(f"{i:3}  {s['start']:8.2f} - {s['end']:8.2f}  ({length:5.2f}s)  {s.get('text', '')}")
    print(f"{len(segments)} pieces, {total:.2f}s total")


def cmd_frames(args):
    info = probe(find_raw(args.raw))
    ranges = frame_ranges(load_cuts(), info["fps"], info["frames"])
    json.dump({"fps": f"{info['fps'].numerator}/{info['fps'].denominator}",
               "end_exclusive": True,
               "ranges": [[a, b] for a, b in ranges]}, sys.stdout, indent=2)
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw", help="raw clip (default: the only video in raw/)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("words").set_defaults(fn=cmd_words)
    m = sub.add_parser("make")
    m.add_argument("ranges", nargs="+", help="word index ranges to keep, e.g. 0-41 47-120")
    m.set_defaults(fn=cmd_make)
    sub.add_parser("show").set_defaults(fn=cmd_show)
    sub.add_parser("frames").set_defaults(fn=cmd_frames)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
