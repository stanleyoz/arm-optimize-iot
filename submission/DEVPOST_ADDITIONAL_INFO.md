# Devpost — "Additional info" section (judges & organizers)

Note: the first four answers are marked *"Appears in project gallery"*, so treat them as
semi-public. Only the free-text question at the end is private-ish.

---

## Q1. What was the hardest part of building or optimizing your project?
*(select all that apply)*

**Tick these four:**

- ☑ **Measuring performance**
- ☑ **Improving model speed or latency**
- ☑ **Debugging runtime or compatibility issues**
- ☑ **Understanding Arm-specific guidance**

**Why these and not others** — each maps to something that actually happened:

| Selection | The evidence |
|---|---|
| Measuring performance | The single hardest part by a distance. Latency was easy to measure and easy to get wrong: our p99 looked fine while the LLM's output was being silently discarded on 41 of 41 calls. Scoring detection accuracy against ground-truth labels is what exposed it. |
| Improving model speed or latency | 5,833 ms → 950 ms p99, across six independent optimizations, each measured separately on-device. |
| Debugging runtime or compatibility issues | A `max_tokens` ceiling truncated JSON mid-object on every call; a regex salvage path could never match because the key it looked for lived in the prompt, not the completion; and llama-cpp-python's threading behaviour reversed between versions. |
| Understanding Arm-specific guidance | Establishing what the on-board Hailo-8 could and couldn't do took real time — it's a CNN engine with no attention primitives or KV cache, so it cannot accelerate LLM inference at all. That isn't obvious from the surrounding material. |

**Deliberately left unticked:** quantization to Q4_K_M was routine (the llama.cpp path is
well-trodden), hardware access was never a problem (we owned the Pi), and dependency
installation was ordinary. Ticking those would overstate the difficulty.

---

## Q2. What would have made it easier to complete your project?
*(select all that apply)*

**Tick these three:**

- ☑ **More benchmarking examples**
- ☑ **More Arm-specific optimization guidance**
- ☑ **Better documentation**

**Why:** the gap was never hardware or setup — it was *methodology*. There is plenty of
material on how to make a model run on Arm, and very little on how to know whether the
thing you built is actually working. A worked example of benchmarking an inference
pipeline end-to-end — percentiles rather than averages, scored against ground truth,
with the failure modes that make a broken pipeline look healthy — would have caught our
central bug in an afternoon instead of on the last day.

**Deliberately left unticked:** hardware access (we had a Pi 5), track guidance (Physical
AI was unambiguous), and judging criteria (the rubric was clear).

---

## Q3. Did this challenge change your likelihood of building on Arm in the future?

**Suggested: "More likely"**

Defensible on the results: a 500M-parameter transformer holding a sub-second p99 on a $80
four-watt board, with no accelerator, is a genuinely better outcome than we expected going
in. Pick "Much more likely" only if that's how you actually feel — the honest read of the
project is that Arm CPU inference cleared the bar, not that it was transformative.

---

## Q4. How likely are you to continue developing, optimizing, or deploying this project?

**This one is genuinely your call and I'd rather not put words in your mouth.**

The honest context: the project sat untouched for a month between the initial build and
this submission. If that reflects your actual intent, "Neutral" or "Somewhat likely" is
the truthful answer and there's no penalty for it. If the accuracy result gave you an
itch to try a 1.5B model or real sensor hardware, "Likely" is fair.

Don't pick "Very likely" to look good — it's the one answer here that's checkable against
your commit history later.

---

## Q5. What is one thing Arm could improve to better support developers like you?

```
Publish version-stamped, reproducible optimization guidance.

Our most expensive mistake was an optimization that expired without telling us. We had
measured that llama-cpp-python ran faster single-threaded on Cortex-A76 — a real GIL
contention effect, where the per-token Python callback re-acquires the lock — and we
built the system around it. Re-measuring immediately before submitting, the result had
completely reversed: 27.9 tok/s at four threads against 16.1 at one. The binding had been
fixed upstream at some point, and our clever workaround had quietly become a 1.7x
slowdown that we were still shipping.

Arm-specific performance advice circulates as timeless folklore — blog posts and forum
answers with no version attached. If Arm maintained a dated, reproducible benchmark
corpus for the common inference stacks, stating the library versions each number was
taken on, developers could tell when their tuning had gone stale instead of carrying a
pessimisation for months.

The corollary, for the guidance itself: tell people how to benchmark, not just how to
optimize. We could have shipped a pipeline whose LLM output was being thrown away on
every call and never known, because the latency numbers looked excellent throughout.
```

(~200 words. Trim the last paragraph if the field is tight — the first two make the point.)
