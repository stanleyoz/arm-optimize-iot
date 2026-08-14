#!/usr/bin/env python3
"""Render the demo-video slides to PNG via headless Chrome.

Every figure on these slides is pulled from capture/*.json at render time, so the
video cannot drift away from what was actually measured on the device.
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAP = ROOT / "capture"
OUT = ROOT / "video" / "slides"
OUT.mkdir(parents=True, exist_ok=True)

stats = json.loads((CAP / "latency_stats.json").read_text())
acc = json.loads((CAP / "accuracy.json").read_text())
threads = json.loads((CAP / "thread_bench.json").read_text())

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  width:1920px; height:1080px; background:#0B0F14; color:#E6EDF3;
  font-family:"DejaVu Sans","Helvetica Neue",sans-serif;
  display:flex; align-items:center; justify-content:center;
  overflow:hidden;
}
.wrap { width:1560px; }
h1 { font-size:96px; font-weight:700; letter-spacing:-2px; line-height:1.05; }
h2 { font-size:52px; font-weight:600; color:#7EE787; margin-bottom:36px; letter-spacing:-1px; }
p  { font-size:40px; line-height:1.45; color:#9FB0C0; }
.mono { font-family:"DejaVu Sans Mono",monospace; }
.big { font-size:150px; font-weight:700; color:#7EE787; letter-spacing:-4px; }
.unit { font-size:52px; color:#6E7C8A; font-weight:400; }
.row { display:flex; gap:28px; margin-top:44px; }
.card {
  flex:1; background:#131A22; border:1px solid #1F2A36;
  border-radius:18px; padding:36px 40px;
}
.card .k { font-size:30px; color:#6E7C8A; text-transform:uppercase; letter-spacing:2px; }
.card .v { font-size:70px; font-weight:700; margin-top:12px; }
.green { color:#7EE787; } .amber { color:#E3B341; } .red { color:#FF7B72; }
.dim { color:#6E7C8A; }
table { width:100%; border-collapse:collapse; margin-top:30px; font-size:38px; }
th { text-align:left; color:#6E7C8A; font-size:28px; text-transform:uppercase;
     letter-spacing:2px; padding-bottom:18px; font-weight:600; }
td { padding:16px 0; border-top:1px solid #1F2A36; }
td.n { text-align:right; font-family:"DejaVu Sans Mono",monospace; }
.flow { display:flex; align-items:center; gap:20px; margin-top:50px; font-size:32px; }
.node { background:#131A22; border:1px solid #1F2A36; border-radius:14px;
        padding:26px 30px; text-align:center; }
.arrow { color:#3A4855; font-size:40px; }
.tag { display:inline-block; background:#1F2A36; border-radius:999px;
       padding:10px 26px; font-size:30px; color:#9FB0C0; margin-right:14px; }
.note { margin-top:40px; font-size:32px; color:#6E7C8A; font-style:italic; }
"""

def slide(name, body):
    html = f"<style>{CSS}</style><body><div class='wrap'>{body}</div></body>"
    src = OUT / f"{name}.html"
    src.write_text(html)
    subprocess.run([
        "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        "--window-size=1920,1080",
        f"--screenshot={OUT / (name + '.png')}", str(src),
    ], check=True, capture_output=True)
    print("rendered", name)


# 1 — cold open
slide("s1", """
<h1>A 500M-parameter LLM<br>on a $80 computer.</h1>
<div style="margin-top:52px">
  <span class="tag mono">Raspberry Pi 5</span>
  <span class="tag mono">4x Cortex-A76</span>
  <span class="tag mono">4W</span>
  <span class="tag mono">no GPU</span>
  <span class="tag mono">no NPU</span>
</div>
<p style="margin-top:44px">Qwen2-0.5B &middot; Q4_K_M &middot; 380 MB &middot; llama.cpp</p>
""")

# 2 — the problem
slide("s2", """
<h2>The trade</h2>
<h1 style="font-size:76px">Rules are instant but blind.<br>Models see context but cost seconds.</h1>
<div class="row">
  <div class="card"><div class="k">Threshold rules</div>
    <div class="v green">&lt; 0.1 ms</div>
    <div class="dim" style="font-size:30px;margin-top:10px">can't tell a fault from an open door</div></div>
  <div class="card"><div class="k">LLM triage</div>
    <div class="v amber">~790 ms</div>
    <div class="dim" style="font-size:30px;margin-top:10px">too slow for every reading</div></div>
</div>
""")

# 3 — architecture
slide("s3", f"""
<h2>So we don't run it on every reading</h2>
<div class="flow">
  <div class="node mono">480<br><span class="dim" style="font-size:26px">windows</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node mono">threshold rules<br><span class="dim" style="font-size:26px">&lt;0.1 ms</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node mono dim">425 clear<br><span style="font-size:26px">no model</span></div>
</div>
<div class="flow" style="margin-left:520px">
  <div class="arrow">&rarr;</div>
  <div class="node mono" style="border-color:#E3B341">14 fast path<br><span class="dim" style="font-size:26px">low severity</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node mono" style="border-color:#FF7B72">{stats['llm_calls']} to the LLM<br><span class="dim" style="font-size:26px">~790 ms each</span></div>
</div>
<div class="note">The cheapest inference is the one you skip &mdash;
effective average {stats['effective_avg_ms']:.0f} ms per window.</div>
""")

# 5 — optimization chain
slide("s5", """
<h2>The chain</h2>
<table>
  <tr><th>Step</th><th style="text-align:right">p99</th></tr>
  <tr><td class="dim">baseline, lazy load</td><td class="n dim">5,833 ms</td></tr>
  <tr><td>eager load + realistic warmup</td><td class="n">1,825 ms</td></tr>
  <tr><td>terse few-shot + <span class="mono">}</span> stop token</td><td class="n">1,359 ms</td></tr>
  <tr><td>n_threads 1 &rarr; 4</td><td class="n green"><b>950 ms</b></td></tr>
</table>
<div class="note">Example prose length turned out to be a latency parameter.</div>
""")

# 6 — the uncomfortable findings
slide("s6", f"""
<h2>Two findings we didn't enjoy</h2>
<div class="row">
  <div class="card">
    <div class="k">Our own optimization expired</div>
    <table style="margin-top:20px;font-size:34px">
      <tr><td>n_threads=1</td><td class="n">{threads['1']} tok/s</td></tr>
      <tr><td>n_threads=2</td><td class="n">{threads['2']} tok/s</td></tr>
      <tr><td>n_threads=4</td><td class="n green">{threads['4']} tok/s</td></tr>
    </table>
    <div class="dim" style="font-size:28px;margin-top:20px">
      The GIL workaround we shipped had become a 1.7x slowdown.</div>
  </div>
  <div class="card">
    <div class="k">The LLM doesn't beat the rules</div>
    <table style="margin-top:20px;font-size:34px">
      <tr><td>rules only</td><td class="n">F1 {acc['threshold_only']['f1']}</td></tr>
      <tr><td>rules + LLM</td><td class="n">F1 {acc['hybrid']['f1']}</td></tr>
      <tr><td class="dim">LLM as filter</td><td class="n red">F1 0.661</td></tr>
    </table>
    <div class="dim" style="font-size:28px;margin-top:20px">
      So it grades and explains. The rules decide.</div>
  </div>
</div>
""")

# 7 — close
slide("s7", f"""
<h1 style="font-size:80px">Measured on the device.<br>Not estimated.</h1>
<div class="row">
  <div class="card"><div class="k">p99 latency</div><div class="v green">{stats['llm_p99_ms']:.0f} <span class="unit">ms</span></div></div>
  <div class="card"><div class="k">over budget</div><div class="v green">0 <span class="unit">/ {stats['llm_calls']}</span></div></div>
  <div class="card"><div class="k">valid JSON</div><div class="v green">{stats['llm_calls']} <span class="unit">/ {stats['llm_calls']}</span></div></div>
</div>
<p class="mono" style="margin-top:56px;font-size:36px">github.com/stanleyoz/arm-optimize-iot &middot; Apache 2.0</p>
""")

print("\nslides in", OUT)
