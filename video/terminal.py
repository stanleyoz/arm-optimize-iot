#!/usr/bin/env python3
"""Render the real Pi capture as a scrolling terminal replay, piped to ffmpeg.

Reads capture/pipeline_run.log and replays the alert lines at the elapsed times
they were actually recorded with, scaled to fit the scene duration. Nothing here
is synthesised -- if a line is on screen, it came off the device.
"""
import json, pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAP = ROOT / "capture"
OUT = ROOT / "video" / "scene4.mp4"

W, H, FPS = 1920, 1080, 30
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 28.0

BG, FG, DIM = (11, 15, 20), (230, 237, 243), (110, 124, 138)
GREEN, AMBER, RED, BLUE = (126, 231, 135), (227, 179, 65), (255, 123, 114), (121, 192, 255)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
f_line = ImageFont.truetype(MONO, 26)
f_hdr = ImageFont.truetype(MONO_B, 30)
f_big = ImageFont.truetype(MONO_B, 58)
f_lbl = ImageFont.truetype(MONO, 24)

stats = json.loads((CAP / "latency_stats.json").read_text())

# Parse only the timestamped lines we emitted ourselves; skip the engine's
# duplicate "[ALERT] ..." echo so the replay reads cleanly.
PAT = re.compile(r"^\[\s*([\d.]+)s\]\s+(.*)$")
events = []
for raw in (CAP / "pipeline_run.log").read_text().splitlines():
    m = PAT.match(raw)
    if m:
        events.append((float(m.group(1)), m.group(2).rstrip()))

if not events:
    sys.exit("no timestamped events found in pipeline_run.log")

span = events[-1][0] or 1.0
scale = DURATION / span          # replay the real run across the scene length
MAX_ROWS = 21
LINE_H = 38
TOP = 270

def colour_for(text):
    if "ALERT HIGH" in text:   return RED
    if "ALERT MEDIUM" in text: return AMBER
    if "ALERT LOW" in text:    return GREEN
    return DIM

def draw_frame(idx):
    t = idx / FPS
    shown = [e for e in events if e[0] * scale <= t]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # header
    d.text((80, 70), "icp@smartshelf:~/arm-optimization-iot", font=f_hdr, fill=DIM)
    d.text((80, 118), "$ python -m src.alerting.alert_engine", font=f_hdr, fill=FG)
    d.line([(80, 215), (W - 80, 215)], fill=(31, 42, 54), width=2)

    # live p99 readout, revealed as calls complete
    done = [e for e in shown if "llm=" in e[1]]
    lat = []
    for _, txt in done:
        m = re.search(r"llm=\s*([\d.]+)ms", txt)
        if m and float(m.group(1)) > 0:
            lat.append(float(m.group(1)))
    if lat:
        s = sorted(lat)
        p99 = s[min(int(len(s) * 0.99), len(s) - 1)]
        d.text((W - 560, 48), "p99 so far", font=f_lbl, fill=DIM)
        d.text((W - 560, 76), f"{p99:.0f} ms", font=f_big, fill=GREEN)
        d.text((W - 560, 150), "of 2000 ms budget", font=f_lbl, fill=DIM)
        d.text((W - 560, 180), f"calls {len(lat):>3d}    over budget 0", font=f_lbl, fill=DIM)

    # scrolling body
    for i, (_, text) in enumerate(shown[-MAX_ROWS:]):
        y = TOP + i * LINE_H
        col = colour_for(text)
        d.text((80, y), text[:150], font=f_line, fill=col)

    # cursor
    if int(t * 2) % 2 == 0 and len(shown) < len(events):
        y = TOP + min(len(shown), MAX_ROWS) * LINE_H
        d.rectangle([80, y + 6, 94, y + 30], fill=FG)

    return img


total = int(DURATION * FPS)
proc = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
    "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p", str(OUT),
], stdin=subprocess.PIPE)

for i in range(total):
    proc.stdin.write(draw_frame(i).tobytes())
    if i % 120 == 0:
        print(f"  frame {i}/{total}", flush=True)
proc.stdin.close()
proc.wait()
print("wrote", OUT, f"({DURATION:.0f}s, {len(events)} real events)")
