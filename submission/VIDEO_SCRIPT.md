# Demo Video — Storyboard & Narration

Target **1:55–2:05**. Hard limit 3:00. ~290 words at ~150 wpm.

Pipeline: real Pi capture (`capture/pipeline_run.log`) → slides (HTML → headless Chrome →
PNG) → terminal replay frames (PIL) → ffmpeg concat + ElevenLabs audio → MP4 1920×1080 @ 30fps.

All numbers below are from the 2026-08-14 run on `smartshelf` (Raspberry Pi 5, 4× Cortex-A76).

---

## Scene 1 — Cold open (0:00–0:14)

**Visual:** Black. Mono text types: `Raspberry Pi 5 · 4× Cortex-A76 · 4W · no GPU · no NPU`
Then the model card fades in: `Qwen2-0.5B · Q4_K_M · 380 MB`

**Narration:**
> This is a Raspberry Pi 5. Four ARM cores, four watts, no GPU and no neural accelerator.
> We're running a five-hundred-million-parameter language model on it, and holding every
> response under two seconds.

---

## Scene 2 — The problem (0:14–0:32)

**Visual:** Split panel. Left: threshold rules firing on a noisy trace, several marked
FALSE ALARM. Right: an LLM block stamped `~0.8s` with a queue backing up behind it.

**Narration:**
> Sensor triage is a bad trade. Threshold rules are instant but can't tell a real fault
> from an open freezer door. A language model reads context, but you cannot afford to run
> one on every reading. So we don't.

---

## Scene 3 — Architecture (0:32–0:50)

**Visual:** Pipeline animating left to right. 425 of 480 windows drain off grey at the
threshold gate; 14 peel off yellow on the low-severity fast path; 41 reach the LLM in red.

**Narration:**
> Six threshold rules run in under a tenth of a millisecond and clear four hundred and
> twenty-five of four hundred and eighty windows. Fourteen more alert directly. Only
> forty-one ever reach the model. The cheapest inference is the one you skip.

---

## Scene 4 — Live run (0:50–1:18)  ← REAL CAPTURE

**Visual:** Full-screen terminal replay from `capture/pipeline_run.log`, real timings.
Running p99 counter in the corner, holding under the 2,000 ms line.

**Narration:**
> This is the real hardware. Each alert carries its own latency. The model reads the
> window and returns structured JSON — a severity and a reason an operator can act on.
> Forty-one calls, forty-one valid verdicts, p99 of nine hundred and fifty milliseconds.

---

## Scene 5 — The optimization chain (1:18–1:40)

**Visual:** Optimizations stack as bars; p99 counts down 5,833 → 950 ms.

**Narration:**
> Getting there took a measured chain. Quantization cut memory two and a half times. Eager
> loading erased a five-point-eight second cold start. And shortening our few-shot examples
> cut another four hundred milliseconds — because example length turns out to be a latency
> parameter.

---

## Scene 6 — The uncomfortable part (1:40–1:58)

**Visual:** Two tables side by side. Left, the thread reversal (16.1 / 24.7 / 27.9 tok/s).
Right, the accuracy comparison with the identical F1 values highlighted.

**Narration:**
> Two findings we didn't enjoy. Our own thread optimization had expired — the library was
> fixed upstream, and our workaround was costing one-point-seven times. And scored against
> ground truth, the language model does not beat the six rules it was meant to improve.
> So we don't let it overrule them. It grades and explains; the rules decide.

---

## Scene 7 — Close (1:58–2:08)

**Visual:** Final card — `p99 950 ms · 0/41 over budget · 41/41 valid JSON · 380 MB · $80`
then repo URL + Apache 2.0.

**Narration:**
> Five hundred million parameters, triaging sensor data, on an eighty dollar computer.
> Every number measured on the device. It's all open source.

---

## Asset checklist

- [x] `capture/pipeline_run.log` — real timestamped run (Scene 4)
- [x] `capture/latency_stats.json` — Scene 5/7 numbers
- [x] `capture/accuracy.json` — Scene 6 table
- [x] `capture/thread_bench.json` — Scene 6 thread reversal
- [x] `capture/sysinfo.txt` — Scene 1 device facts
- [ ] 7 narration mp3 segments (ElevenLabs)
- [ ] Thumbnail still (reuse Scene 7 card)
