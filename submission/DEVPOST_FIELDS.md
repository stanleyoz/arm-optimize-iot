# Devpost Submission — Paste-Ready Fields

Draft URL: https://devpost.com/submit-to/30218-arm-create-ai-optimization-challenge/manage/submissions/1069877-iot-triage/project-overview

Each section below maps to one field on the Devpost form. Copy the block, not the heading.

---

## Project name

```
Edge Triage: A 0.5B LLM Watching Sensors on a Raspberry Pi 5
```

Alternative if the form prefers something shorter (the existing draft is "IoT Triage"):

```
Edge Triage
```

---

## Elevator pitch  (Devpost limit: 200 characters)

```
A 500M-parameter LLM triaging sensor data on an $80 Raspberry Pi 5. Hybrid threshold+LLM pipeline holds p99 at 950ms with zero budget misses — 6.1x faster after systematic ARM optimization.
```

(189 characters.)

---

## Track / Category

```
Track 1 — Physical AI
```

---

## Project details  (the long "story" field)

```
## Inspiration

Edge AI is usually pitched as "buy an NPU." We wanted to know what a plain ARM CPU can
actually do — no accelerator, no GPU, no cloud fallback. A Raspberry Pi 5 has four
Cortex-A76 cores and a 4W power envelope. Can that run a real language model inside a
hard real-time budget?

The use case we picked is unglamorous and real: an IoT sensor stream — temperature,
humidity, people count — where something occasionally goes wrong and somebody needs to be
told what and how badly. Threshold rules are fast but stupid; they fire on every open
window and every space heater. An LLM understands context but is far too slow to run on
every reading. That tension is the whole project.

## What it does

A hybrid two-stage pipeline. Stage one is six threshold rules that run in under 0.1 ms and
clear 88% of all sensor windows — no model involved. Stage two escalates only the
ambiguous remainder to Qwen2-0.5B, quantized to Q4_K_M (380 MB), running locally through
llama.cpp. The model emits a structured JSON verdict: alert (bool), reason (string),
severity (low/medium/high). The threshold layer keeps the alert decision; the model grades
and explains it. The accuracy section below says why.

There's a second gate inside stage one: windows that trigger only low-severity rules
(people count alone) alert directly without ever waking the model, skipping 14 of the 55
would-be LLM calls.

Measured on a Raspberry Pi 5 over 4 hours of sensor data — 480 windows, 55 threshold
triggers, 41 LLM escalations:

  p50 LLM triage   773 ms
  p95 LLM triage   864 ms
  p99 LLM triage   950 ms
  Budget misses    0 of 41   (2,000 ms budget)
  Valid JSON       41 of 41

Because the threshold gate absorbs 88% of windows, the effective average cost across the
whole run is 67 ms per window.

## How we built it

The interesting part isn't the architecture, it's the optimization chain. We started at
5.8 seconds p99 and got to 0.95 seconds. Every step was measured independently:

  FP16 -> Q4_K_M quantization       949 MB -> 380 MB          2.5x memory
  max_tokens 128 -> 25              ~8.5s -> ~1.6s per call   5.3x per call
  lazy load -> eager load + warmup  5,833 -> 1,825 ms p99     3.2x cold start
  terse few-shot + "}" stop token   1,825 -> 1,359 ms p99   1.3x, and fixes JSON
  generic pip -> native NEON build  4.0 -> 28.4 tok/s         7x prompt processing
  n_threads=1 -> n_threads=4        1,359 ->   950 ms p99   1.4x
  hybrid threshold gate               787 ->    67 ms avg/win 11.7x system level

Three of those are counterintuitive enough to be worth calling out.

The first is that we had to delete one of our own optimizations. This project originally
found that n_threads=1 was dramatically faster than n_threads=4 through llama-cpp-python —
a real GIL contention effect, where the Python callback fires per generated token and
re-acquires the lock each time. We built around it. Re-measuring on llama-cpp-python
0.3.32 before submitting, the result had reversed completely:

  n_threads=1    16.1 tok/s
  n_threads=2    24.7 tok/s
  n_threads=4    27.9 tok/s

The binding was fixed upstream at some point, and our clever workaround had silently
turned into a 1.7x slowdown that we were still shipping. Deleting it took p99 from 1,359ms
to 950ms. The lesson isn't about threads: it's that an optimization is only valid against
the version you measured it on, and nobody tells you when it expires.

The prompting strategy also inverted. Instruction-style prompts fail at 4-bit — the model
drifts, wraps JSON in prose, truncates mid-object. Switching to few-shot completion, where
the prompt ends mid-structure and the model simply continues the pattern, produced 41/41
valid JSON verdicts. No LoRA, no fine-tuning, no RLHF. We rewired the model's behavior
entirely through prompt shape, which matters a lot when your whole deployment budget is
380 MB on a device with no training capability.

The third one is that example LENGTH is a latency parameter. Our few-shot examples had
long, well-written reasons, so the model wrote long reasons too — and ran past the token
budget that keeps us under two seconds, truncating mid-object every single time. Shortening
the examples cut p99 by 466 ms AND turned a 0% JSON parse rate into 100%. The prose style
of your examples is a performance decision, which is not where you expect to find one.

## Challenges we ran into

The cold start nearly sank the latency budget. Our first honest benchmark showed p99 at
5,833 ms against a 2,000 ms target — a catastrophic miss. It turned out to be a single
outlier: the very first LLM call, which pays for loading the model from disk. Everything
after it ran at 1.3-1.8s. The fix was eager loading plus a warmup inference at startup,
and the warmup has to use the full few-shot prompt, not a trivial one, because llama.cpp
defers some internal allocations until it sees a realistic workload. A short warmup string
leaves the allocation cost sitting in your first real request.

We also chased the on-board Hailo-8 accelerator for a while before establishing that it
cannot help here at all. It's a CNN inference engine — no attention primitives, no KV
cache, no autoregressive decode path. Not "slow for LLMs," structurally incapable of them.
We documented this as a negative result because the marketing around edge AI accelerators
strongly implies otherwise, and the next person deserves to skip that week.

The hardest problem, though, was one we created for ourselves. A max-only prompt is blind
to sensor faults: the hardware writes -99.9C as its fault sentinel, and that lands in the
window MINIMUM, which we weren't passing to the model. The data existed; we threw it away
before the prompt. Passing min and max took sensor-fault detection from 2 of 26 to 24 of 26.

## Accomplishments that we're proud of

Zero budget misses across 41 consecutive LLM escalations on an $80 general-purpose computer,
with a 500M-parameter transformer in the loop, every one returning valid JSON. Not a demo
that works once — a p99 number over a sustained run, with the raw logs committed.

But the thing we're most proud of is a result that makes us look worse. We scored the
hybrid pipeline against ground-truth anomaly labels and found the LLM does not beat the
threshold rules it was meant to improve:

  threshold rules only    precision 0.982   recall 0.692   F1 0.812
  hybrid (rules + LLM)    precision 0.982   recall 0.692   F1 0.812

And when we let the model veto a threshold hit — the "smart filter" architecture everyone
reaches for — recall collapsed from 0.692 to 0.500. A 0.5B model at 4-bit is simply a worse
detector than six tuned if-statements.

So we didn't ship it as a filter. The rules own the alert decision; the model grades
severity and writes the reason, which is what it's genuinely good at on this hardware. It
would have been easy to wire it the flattering way and never run the comparison. The
comparison cost us the headline and we're publishing it anyway.

## What we learned

Optimization on ARM is mostly about finding the thing that isn't the model. Quantization
got us 2.5x on memory, which everyone expects. But the thread reversal, the token budget,
the cold start, and the length of our prose examples together account for far more of the
actual latency win — and none of them are model problems. The largest single gain, 11.7x
at the system level, came from the architectural decision to not call the model at all for
88% of windows.

The cheapest inference is the inference you skip.

And: measure the thing you're claiming. We had a working latency story long before we had
an honest accuracy story, and it would have been very comfortable to stop at the first one.

## What's next

Real sensor hardware instead of synthetic streams — the generator models four anomaly
types faithfully, but it isn't a warehouse. Beyond that: a quantization sweep now that
Q4_K_M is proven as a baseline, batching for multi-room deployments, and testing whether
a 1.5B model still fits the budget once the hybrid gate is doing this much of the work.
```

---

## Built With  (tags)

```
python
llama.cpp
qwen2
gguf
quantization
raspberry-pi
arm
neon
cortex-a76
aarch64
numpy
pandas
pytest
edge-ai
iot
```

---

## Try it out links

```
https://github.com/stanleyoz/arm-optimize-iot
```

---

## Video demo link

The finished video is committed at `video/edge-triage-demo.mp4` (2:00, 1920x1080, 8.3 MB).

**You need to upload it** — I have no way to publish to YouTube from here. Steps:

1. Upload `video/edge-triage-demo.mp4` to YouTube
2. Set visibility to **Public** or **Unlisted** (Devpost requires a publicly reachable link;
   Public is the safer read of the rules)
3. Title suggestion: `Edge Triage - a 0.5B LLM on a Raspberry Pi 5`
4. Paste the watch URL into the Devpost "Video demo link" field

```
TODO - paste YouTube URL here after upload
```

---

## Checklist before hitting Submit

- [ ] Repo is public and Apache 2.0 (verified: yes)
- [ ] Video uploaded, set to public (not unlisted-only if the rules require public)
- [ ] Video is under 3 minutes
- [ ] Track set to Physical AI
- [ ] Thumbnail image uploaded
- [ ] Deadline: Aug 14 2026, 4:00pm PDT = Aug 15, 07:00 AWST

---

## Additional info (judges & organizers)

The four multi-select / scale questions and the free-text answer are drafted separately in
[`DEVPOST_ADDITIONAL_INFO.md`](DEVPOST_ADDITIONAL_INFO.md). Note that the first four
"appear in project gallery" — they are semi-public, not private feedback.
