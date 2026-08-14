#!/usr/bin/env python3
"""Assemble the demo video: slides + real terminal capture + narration -> MP4.

Each scene's visual duration is derived from its narration length, so the cut
follows the voiceover instead of a guessed timing sheet.
"""
import pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
SLIDES, AUDIO = ROOT / "slides", ROOT / "audio"
WORK = ROOT / "_work"; WORK.mkdir(exist_ok=True)
OUT = ROOT / "edge-triage-demo.mp4"

TAIL = 0.7          # breathing room after each narration line
W, H, FPS = 1920, 1080, 30

# scene id -> visual source (None means use slides/<id>.png)
SCENES = [
    ("s1", None), ("s2", None), ("s3", None),
    ("s4", ROOT / "scene4.mp4"),
    ("s5", None), ("s6", None), ("s7", None),
]


def duration(path):
    out = subprocess.run(["ffmpeg", "-i", str(path), "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", out)
    if not times:
        sys.exit(f"could not read duration of {path}")
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


segments = []
for sid, vis in SCENES:
    mp3 = AUDIO / f"{sid}.mp3"
    adur = duration(mp3)
    seg = WORK / f"{sid}.mp4"

    if vis is None:
        png = SLIDES / f"{sid}.png"
        total = adur + TAIL
        # Still image + narration, with the audio padded to the full segment so the
        # concat below never hits a stream-length mismatch.
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", str(FPS), "-i", str(png),
            "-i", str(mp3),
            "-filter_complex",
            f"[0:v]scale={W}:{H},format=yuv420p,fade=t=in:st=0:d=0.4,"
            f"fade=t=out:st={total-0.4:.2f}:d=0.4[v];"
            f"[1:a]apad=whole_dur={total:.2f},afade=t=out:st={total-0.3:.2f}:d=0.3[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", str(seg),
        ]
    else:
        vdur = duration(vis)
        total = max(vdur, adur + TAIL)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(vis), "-i", str(mp3),
            "-filter_complex",
            f"[0:v]scale={W}:{H},format=yuv420p,fade=t=in:st=0:d=0.4,"
            f"fade=t=out:st={total-0.4:.2f}:d=0.4[v];"
            f"[1:a]apad=whole_dur={total:.2f},afade=t=out:st={total-0.3:.2f}:d=0.3[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", str(seg),
        ]

    subprocess.run(cmd, check=True)
    segments.append(seg)
    print(f"{sid}: narration {adur:5.2f}s -> segment {total:5.2f}s")

listing = WORK / "concat.txt"
listing.write_text("".join(f"file '{s}'\n" for s in segments))
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
    "-i", str(listing), "-c", "copy", str(OUT),
], check=True)

total = duration(OUT)
print(f"\n{OUT}")
print(f"duration {int(total//60)}:{total%60:05.2f}  ({total:.1f}s)")
if total > 180:
    print("WARNING: exceeds the 3:00 hackathon limit", file=sys.stderr)
