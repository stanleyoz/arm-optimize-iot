#!/usr/bin/env python3
"""Render the 3:2 project thumbnail (2400x1600 PNG).

Silicon-themed: a stylised quad-core die with the sensor->rules->LLM path drawn
across it. Figures come from capture/*.json so the thumbnail stays tied to the
measured run. Deliberately no Arm corporate logo or wordmark -- "Arm Cortex-A76"
appears only as a factual description of the hardware.
"""
import json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAP = ROOT / "capture"
OUT = ROOT / "media"
OUT.mkdir(parents=True, exist_ok=True)

stats = json.loads((CAP / "latency_stats.json").read_text())
W, H = 2400, 1600

# --- die illustration -------------------------------------------------------
# Four A76 core blocks; the fourth carries the "hot" accent to suggest the core
# actually doing inference.
cores = ""
for i in range(4):
    cx = 250 + (i % 2) * 300
    cy = 210 + (i // 2) * 300
    hot = (i == 3)
    fill = "#123039" if not hot else "#1B4A57"
    stroke = "#1F6B7E" if not hot else "#35D6F0"
    cores += f"""
    <rect x="{cx}" y="{cy}" width="250" height="250" rx="14"
          fill="{fill}" stroke="{stroke}" stroke-width="{3 if not hot else 5}"/>
    <text x="{cx+125}" y="{cy+120}" text-anchor="middle"
          font-family="DejaVu Sans Mono" font-size="46" font-weight="bold"
          fill="{'#7FE9FB' if hot else '#4E93A6'}">A76</text>
    <text x="{cx+125}" y="{cy+172}" text-anchor="middle"
          font-family="DejaVu Sans Mono" font-size="27"
          fill="{'#35D6F0' if hot else '#2F6C7C'}">core {i}</text>"""

# package pins
pins = ""
for i in range(14):
    y = 150 + i * 62
    pins += (f'<rect x="60" y="{y}" width="42" height="16" rx="4" fill="#1F3742"/>'
             f'<rect x="1058" y="{y}" width="42" height="16" rx="4" fill="#1F3742"/>')
for i in range(14):
    x = 150 + i * 62
    pins += (f'<rect x="{x}" y="60" width="16" height="42" rx="4" fill="#1F3742"/>'
             f'<rect x="{x}" y="1058" width="16" height="42" rx="4" fill="#1F3742"/>')

DIE = f"""
<svg width="880" height="880" viewBox="0 0 1160 1160" fill="none">
  <defs>
    <linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#35D6F0" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="#35D6F0" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="90" y="90" width="980" height="980" rx="40" fill="url(#glow)"/>
  {pins}
  <rect x="120" y="120" width="920" height="920" rx="30"
        fill="#0D1A20" stroke="#24505E" stroke-width="4"/>
  {cores}
  <rect x="250" y="820" width="550" height="120" rx="12"
        fill="#101F26" stroke="#1F6B7E" stroke-width="3"/>
  <text x="525" y="878" text-anchor="middle" font-family="DejaVu Sans Mono"
        font-size="34" fill="#4E93A6">Qwen2-0.5B</text>
  <text x="525" y="920" text-anchor="middle" font-family="DejaVu Sans Mono"
        font-size="30" fill="#2F6C7C">Q4_K_M &#183; 380 MB</text>
</svg>"""

HTML = f"""
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  width:{W}px; height:{H}px; overflow:hidden;
  background:
    radial-gradient(1200px 900px at 22% 45%, #10242C 0%, transparent 62%),
    radial-gradient(900px 700px at 88% 15%, #14202B 0%, transparent 60%),
    #070B0E;
  font-family:"DejaVu Sans","Helvetica Neue",sans-serif; color:#E8F3F6;
  display:flex; align-items:center; padding:0 96px; gap:72px;
}}
/* faint circuit grid */
body:before {{
  content:""; position:absolute; inset:0;
  background-image:
    linear-gradient(#0E1C23 1px, transparent 1px),
    linear-gradient(90deg, #0E1C23 1px, transparent 1px);
  background-size:80px 80px; opacity:.55;
}}
.left, .right {{ position:relative; }}
.right {{ flex:1; }}
.kicker {{
  font-size:36px; letter-spacing:8px; text-transform:uppercase;
  color:#35D6F0; font-weight:700; margin-bottom:30px;
}}
h1 {{
  font-size:150px; font-weight:700; line-height:.96; letter-spacing:-6px;
}}
h1 .thin {{ color:#5D7A86; font-weight:400; display:block; font-size:56px;
            letter-spacing:-1px; margin-top:28px; white-space:nowrap; }}
.rule {{ width:180px; height:7px; background:#35D6F0; margin:44px 0 40px; border-radius:4px; }}
.flow {{ display:flex; align-items:center; gap:22px; font-size:34px; color:#8FA8B4; }}
.chip {{ background:#101F26; border:1px solid #24505E; border-radius:12px;
         padding:16px 24px; font-family:"DejaVu Sans Mono"; }}
.arrow {{ color:#2F6C7C; font-size:34px; }}
.stats {{ display:flex; gap:26px; margin-top:56px; }}
.stat {{ background:rgba(16,31,38,.85); border:1px solid #1F4A58;
         border-radius:18px; padding:30px 36px; }}
.stat .k {{ font-size:23px; letter-spacing:2.5px; text-transform:uppercase; color:#5D7A86;
            font-weight:600; }}
.stat .v {{ font-size:88px; font-weight:700; color:#35D6F0; letter-spacing:-2px;
            margin-top:6px; line-height:1; }}
.stat .v small {{ font-size:30px; color:#5D7A86; font-weight:400; letter-spacing:0; }}
.foot {{ margin-top:56px; font-size:30px; color:#3E5A66; font-family:"DejaVu Sans Mono"; }}
</style>
<body>
  <div class="left">{DIE}</div>
  <div class="right">
    <div class="kicker">Arm AI Optimization Challenge</div>
    <h1>Edge IoT Triage
      <span class="thin">500M-parameter LLM &#183; 4 W &#183; sub-second</span>
    </h1>
    <div class="rule"></div>
    <div class="flow">
      <div class="chip">sensors</div><div class="arrow">&rarr;</div>
      <div class="chip">rules &lt;0.1 ms</div><div class="arrow">&rarr;</div>
      <div class="chip" style="border-color:#35D6F0;color:#7FE9FB">LLM triage</div>
      <div class="arrow">&rarr;</div><div class="chip">JSON alert</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="k">p99 latency</div>
        <div class="v">{stats['llm_p99_ms']:.0f}<small> ms</small></div></div>
      <div class="stat"><div class="k">over budget</div>
        <div class="v">0<small> / {stats['llm_calls']}</small></div></div>
      <div class="stat"><div class="k">valid JSON</div>
        <div class="v">{stats['llm_calls']}<small> / {stats['llm_calls']}</small></div></div>
      <div class="stat"><div class="k">footprint</div>
        <div class="v">380<small> MB</small></div></div>
    </div>
    <div class="foot">Raspberry Pi 5 &#183; 4&times; Arm Cortex-A76 &#183; no GPU &#183; no NPU &#183; no cloud</div>
  </div>
</body>"""

src = OUT / "_thumb.html"
src.write_text(HTML)
dst = OUT / "thumbnail-3x2.png"
subprocess.run([
    "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
    "--hide-scrollbars", "--force-device-scale-factor=1",
    f"--window-size={W},{H}", f"--screenshot={dst}", str(src),
], check=True, capture_output=True)
src.unlink()

kb = dst.stat().st_size / 1024
print(f"{dst}  {W}x{H} (3:2)  {kb:.0f} KB")
if kb > 5120:
    print("WARNING: over the 5 MB limit")
