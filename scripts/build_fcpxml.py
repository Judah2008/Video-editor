#!/usr/bin/env python3
"""Write transcript/cuts.json as an FCPXML timeline that Final Cut Pro opens as a new library.

  python3 scripts/build_fcpxml.py --version 1.13 [--raw raw/clip.mov] [--name "My video"]

Use the newest version your Final Cut ships a DTD for:
  ls "/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/" | grep FCPXMLv
Validate (copy the DTD to a path without spaces first):
  xmllint --noout --dtdvalid /tmp/FCPXMLv1_13.dtd cut.fcpxml
"""
import argparse
from pathlib import Path
from xml.sax.saxutils import quoteattr

from common import ROOT, find_raw, frame_ranges, load_cuts, probe, timecode_to_frames


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw")
    p.add_argument("--version", default="1.11", help="FCPXML version (match your Final Cut's newest DTD)")
    p.add_argument("--name", help="project name (default: the raw clip's name)")
    p.add_argument("--out", default=str(ROOT / "cut.fcpxml"))
    args = p.parse_args()

    raw = find_raw(args.raw)
    info = probe(raw)
    fps = info["fps"]
    ranges = frame_ranges(load_cuts(), fps, info["frames"])
    name = args.name or raw.stem

    # Times are rational multiples of one frame, e.g. 1001/30000s at 29.97.
    def t(frames):
        return "0s" if frames == 0 else f"{frames * fps.denominator}/{fps.numerator}s"

    # Timecoded media: the asset starts at its timecode, and every clip start counts from it.
    tc0 = timecode_to_frames(info["timecode"], fps) if info["timecode"] else 0
    drop = bool(info["timecode"] and ";" in info["timecode"])
    total_raw = info["frames"] or round(info["duration"] * fps)
    total_cut = sum(b - a for a, b in ranges)

    clips, offset = [], 0
    for a, b in ranges:
        clips.append(f'          <asset-clip ref="r2" name={quoteattr(name)} offset="{t(offset)}" '
                     f'start="{t(tc0 + a)}" duration="{t(b - a)}" tcFormat="{"DF" if drop else "NDF"}"/>')
        offset += b - a

    library = (ROOT / f"{name}.fcpbundle").as_uri()
    audio = (f' hasAudio="1" audioSources="1" audioChannels="{info["audio_channels"]}" audioRate="{info["audio_rate"]}"'
             if info["has_audio"] else "")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="{args.version}">
  <import-options>
    <option key="library location" value={quoteattr(library)}/>
    <option key="copy assets" value="0"/>
    <option key="suppress warnings" value="1"/>
  </import-options>
  <resources>
    <format id="r1" frameDuration="{t(1)}" width="{info['width']}" height="{info['height']}"/>
    <asset id="r2" name={quoteattr(name)} start="{t(tc0)}" duration="{t(total_raw)}" hasVideo="1" format="r1"{audio}>
      <media-rep kind="original-media" src={quoteattr(raw.as_uri())}/>
    </asset>
  </resources>
  <library>
    <event name={quoteattr(name)}>
      <project name={quoteattr(name + " - cut")}>
        <sequence format="r1" duration="{t(total_cut)}" tcStart="0s" tcFormat="{"DF" if drop else "NDF"}" audioLayout="stereo" audioRate="48k">
          <spine>
{chr(10).join(clips)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
"""
    Path(args.out).write_text(xml)
    print(f"wrote {args.out}: {len(ranges)} clips, {total_cut} frames at {fps.numerator}/{fps.denominator} fps")
    print("open it with Final Cut (double-click, or File > Import > XML)")


if __name__ == "__main__":
    main()
