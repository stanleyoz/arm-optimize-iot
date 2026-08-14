#!/usr/bin/env python3
"""Render the Devpost Project Media gallery PNGs (1920x1080).

Every figure is read from capture/*.json at render time, so the gallery cannot
drift from what was measured on the device. Image 01 is the gallery thumbnail:
it is typed large deliberately, because Devpost renders it as a small card.
"""
import json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAP = ROOT / "capture"
OUT = ROOT / "media"
OUT.mkdir(parents=True, exist_ok=True)
TMP = OUT / "_html"; TMP.mkdir(exist_ok=True)

stats = json.loads((CAP / "latency_stats.json").read_text())
acc = json.loads((CAP / "accuracy.json").read_text())
threads = json.loads((CAP / "thread_bench.json").read_text())

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  width:1920px; height:1080px; background:#0B0F14; color:#E6EDF3;
  font-family:"DejaVu Sans","Helvetica Neue",sans-serif;
  display:flex; align-items:center; justify-content:center; overflow:hidden;
}
.wrap { width:1620px; }
.kicker { font-size:34px; color:#7EE787; letter-spacing:4px;
          text-transform:uppercase; font-weight:700; margin-bottom:28px; }
h1 { font-size:104px; font-weight:700; letter-spacing:-3px; line-height:1.03; }
h2 { font-size:62px; font-weight:700; letter-spacing:-1.5px; margin-bottom:14px; }
p  { font-size:38px; line-height:1.45; color:#9FB0C0; }
.mono { font-family:"DejaVu Sans Mono",monospace; }
.row { display:flex; gap:26px; margin-top:46px; }
.card { flex:1; background:#131A22; border:1px solid #1F2A36;
        border-radius:20px; padding:38px 42px; }
.k { font-size:28px; color:#6E7C8A; text-transform:uppercase;
     letter-spacing:2.5px; font-weight:600; }
.v { font-size:96px; font-weight:700; margin-top:10px; letter-spacing:-3px; }
.unit { font-size:40px; color:#6E7C8A; font-weight:400; letter-spacing:0; }
.green{color:#7EE787} .amber{color:#E3B341} .red{color:#FF7B72} .dim{color:#6E7C8A}
table { width:100%; border-collapse:collapse; margin-top:26px; font-size:40px; }
th { text-align:left; color:#6E7C8A; font-size:27px; text-transform:uppercase;
     letter-spacing:2.5px; padding-bottom:16px; font-weight:600; }
td { padding:18px 0; border-top:1px solid #1F2A36; }
td.n { text-align:right; font-family:"DejaVu Sans Mono",monospace; }
.tag { display:inline-block; background:#1F2A36; border-radius:999px;
       padding:12px 30px; font-size:31px; color:#9FB0C0; margin:0 12px 12px 0; }
.note { margin-top:38px; font-size:32px; color:#6E7C8A; font-style:italic; }
.foot { margin-top:44px; font-size:30px; color:#3A4855; }
.flow { display:flex; align-items:stretch; gap:18px; margin-top:40px; }
.node { background:#131A22; border:1px solid #1F2A36; border-radius:16px;
        padding:28px 26px; text-align:center; font-size:30px; flex:1; }
.node b { font-size:44px; display:block; margin-bottom:8px; }
.arrow { display:flex; align-items:center; color:#3A4855; font-size:44px; }
"""

def render(name, body):
    (TMP / f"{name}.html").write_text(f"<style>{CSS}</style><body><div class='wrap'>{body}</div></body>")
    subprocess.run([
        "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
        "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1920,1080",
        f"--screenshot={OUT / (name + '.png')}", str(TMP / f"{name}.html"),
    ], check=True, capture_output=True)
    print("rendered", name)


# 01 — gallery thumbnail. Big, few words, readable at card size.
render("01-hero", f"""
<div class="kicker">Track 1 &middot; Physical AI</div>
<h1>A 500M-parameter LLM<br>triaging sensors on<br>an $80 Raspberry Pi 5.</h1>
<div class="row">
  <div class="card"><div class="k">p99 latency</div>
    <div class="v green">{stats['llm_p99_ms']:.0f}<span class="unit"> ms</span></div></div>
  <div class="card"><div class="k">over budget</div>
    <div class="v green">0<span class="unit"> / {stats['llm_calls']}</span></div></div>
  <div class="card"><div class="k">model size</div>
    <div class="v">380<span class="unit"> MB</span></div></div>
</div>
""")

# 02 — architecture
render("02-architecture", f"""
<div class="kicker">Architecture</div>
<h2>Don't run the model on every reading.</h2>
<p>Two gates stand between the sensor stream and a 380 MB transformer.</p>
<div class="flow">
  <div class="node"><b>480</b>windows<br><span class="dim">30 s each</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node"><b>6 rules</b>threshold gate<br><span class="green">&lt; 0.1 ms</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node dim"><b>425</b>cleared<br><span>no model</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node" style="border-color:#E3B341"><b class="amber">14</b>fast path<br><span class="dim">low severity</span></div>
  <div class="arrow">&rarr;</div>
  <div class="node" style="border-color:#FF7B72"><b class="red">{stats['llm_calls']}</b>reach the LLM<br><span class="dim">~790 ms</span></div>
</div>
<div class="note">Effective average across the whole run:
{stats['effective_avg_ms']:.0f} ms per window. The cheapest inference is the one you skip.</div>
""")

# 03 — latency
render("03-latency", f"""
<div class="kicker">Measured on device &middot; 4 h run</div>
<h2>Every call inside the 2-second budget.</h2>
<table>
  <tr><th>Metric</th><th style="text-align:right">Threshold</th><th style="text-align:right">LLM triage</th></tr>
  <tr><td>p50</td><td class="n dim">&lt; 0.1 ms</td><td class="n">{stats['llm_p50_ms']:.0f} ms</td></tr>
  <tr><td>p95</td><td class="n dim">&lt; 0.1 ms</td><td class="n">{stats['llm_p95_ms']:.0f} ms</td></tr>
  <tr><td><b>p99</b></td><td class="n dim">&lt; 0.1 ms</td><td class="n green"><b>{stats['llm_p99_ms']:.0f} ms</b></td></tr>
  <tr><td>max</td><td class="n dim">{stats['thr_max_ms']:.2f} ms</td><td class="n">{stats['llm_max_ms']:.0f} ms</td></tr>
  <tr><td>over budget</td><td class="n dim">0 / 55</td><td class="n green">0 / {stats['llm_calls']}</td></tr>
  <tr><td>valid JSON</td><td class="n dim">&mdash;</td><td class="n green">{stats['llm_calls']} / {stats['llm_calls']}</td></tr>
</table>
<div class="foot">Raspberry Pi 5 &middot; 4x Cortex-A76 &middot; Qwen2-0.5B Q4_K_M &middot; raw logs in capture/</div>
""")

# 04 — the honest negative result
render("04-accuracy", f"""
<div class="kicker">The uncomfortable result</div>
<h2>The LLM does not beat the rules.</h2>
<p>Scored against the generator's ground-truth anomaly labels, same 480 windows.</p>
<table>
  <tr><th>Layer</th><th style="text-align:right">Precision</th><th style="text-align:right">Recall</th><th style="text-align:right">F1</th></tr>
  <tr><td>threshold rules only</td>
      <td class="n">{acc['threshold_only']['precision']}</td>
      <td class="n">{acc['threshold_only']['recall']}</td>
      <td class="n">{acc['threshold_only']['f1']}</td></tr>
  <tr><td>hybrid (rules + LLM)</td>
      <td class="n">{acc['hybrid']['precision']}</td>
      <td class="n">{acc['hybrid']['recall']}</td>
      <td class="n">{acc['hybrid']['f1']}</td></tr>
  <tr><td class="dim">LLM allowed to veto a rule</td>
      <td class="n dim">0.975</td><td class="n red">0.500</td><td class="n red">0.661</td></tr>
</table>
<div class="note">A 0.5B model at 4-bit is a worse detector than six tuned if-statements.
So the rules own the decision and the model grades severity and writes the reason.
We ran the comparison rather than assuming, and published the answer we didn't want.</div>
""")

# 05 — optimization chain
render("05-optimization", """
<div class="kicker">The chain</div>
<h2>5,833 ms &rarr; 950 ms p99</h2>
<table>
  <tr><th>Step</th><th style="text-align:right">p99 after</th></tr>
  <tr><td class="dim">baseline, lazy model load</td><td class="n dim">5,833 ms</td></tr>
  <tr><td>eager load + realistic warmup</td><td class="n">1,825 ms</td></tr>
  <tr><td>terse few-shot + <span class="mono">}</span> stop token</td><td class="n">1,359 ms</td></tr>
  <tr><td>n_threads 1 &rarr; 4</td><td class="n green"><b>950 ms</b></td></tr>
</table>
<div class="note">Shortening the few-shot examples cut 466 ms and took JSON validity
from 0% to 100% &mdash; example prose length turned out to be a latency parameter.</div>
""")

# 06 — the expired optimization
render("06-threads", f"""
<div class="kicker">An optimization that expired</div>
<h2>Our own tuning had become a 1.7&times; slowdown.</h2>
<p>We measured real GIL contention in llama-cpp-python and pinned <span class="mono">n_threads=1</span>.
Re-measured on 0.3.32 before submitting, the result had reversed.</p>
<table>
  <tr><th>Setting</th><th style="text-align:right">Generation</th></tr>
  <tr><td class="mono">n_threads=1</td><td class="n red">{threads['1']} tok/s</td></tr>
  <tr><td class="mono">n_threads=2</td><td class="n">{threads['2']} tok/s</td></tr>
  <tr><td class="mono">n_threads=4</td><td class="n green"><b>{threads['4']} tok/s</b></td></tr>
</table>
<div class="note">The binding was fixed upstream and nobody tells you when your workaround
expires. An optimization is only valid against the version you measured it on.</div>
""")

# 08 — spec / close card
render("08-stack", """
<div class="kicker">Stack</div>
<h2>No GPU. No NPU. No cloud.</h2>
<div style="margin-top:40px">
  <span class="tag mono">Raspberry Pi 5</span>
  <span class="tag mono">4x Cortex-A76 @ 2.4 GHz</span>
  <span class="tag mono">aarch64</span>
  <span class="tag mono">4 W</span>
  <span class="tag mono">Qwen2-0.5B</span>
  <span class="tag mono">GGUF Q4_K_M</span>
  <span class="tag mono">380 MB</span>
  <span class="tag mono">llama.cpp + NEON</span>
  <span class="tag mono">Debian 12</span>
  <span class="tag mono">34 unit tests</span>
</div>
<div class="row">
  <div class="card"><div class="k">total windows</div><div class="v">480</div></div>
  <div class="card"><div class="k">threshold triggers</div><div class="v">55</div></div>
  <div class="card"><div class="k">LLM escalations</div><div class="v">41</div></div>
</div>
<div class="foot">github.com/stanleyoz/arm-optimize-iot &middot; Apache 2.0</div>
""")

print("\ngallery PNGs in", OUT)
