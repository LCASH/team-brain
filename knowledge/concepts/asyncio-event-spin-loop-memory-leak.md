---
title: "asyncio Event.wait() Spin-Loop Memory Leak"
aliases: [event-wait-spin-loop, change-event-clear, asyncio-event-leak, sse-producer-spin-loop, event-set-without-clear]
tags: [value-betting, python, asyncio, bug, memory-leak, architecture]
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# asyncio Event.wait() Spin-Loop Memory Leak

On 2026-05-08, the v3 value betting scanner's RSS memory ballooned from ~300MB to 35GB+ at ~75MB/sec. After three wrong hypotheses (Playwright page leak, unbounded WebSocket queue, stale Chromium), **py-spy** stack traces pinpointed the root cause: `store.change_event.wait()` in the SSE producer (`v3/pipeline/server.py:304`) never cleared the event after waking. Once set, every subsequent `asyncio.wait_for(change_event.wait(), timeout=...)` returned instantly, spinning the asyncio loop at millions of iterations/sec and leaking Task + TimerHandle objects. The fix is one line: `change_event.clear()` before `wait()`. The identical bug had previously been fixed in the tracker but never applied to the SSE producer.

## Key Points

- `asyncio.Event.wait()` returns instantly if the event is already set — without `.clear()`, once set it stays set forever, creating an infinite spin loop
- The SSE producer's `_stream_events` function at `server.py:304` was the hot loop — py-spy showed it dominating CPU with millions of iterations/sec
- Memory leak rate: ~75 MB/sec from Task + TimerHandle object accumulation — process reached 35GB+ before being killed
- The **same bug had already been fixed in the tracker** but was never applied to the SSE producer — a copy-paste architecture where the fix wasn't propagated
- Three wrong hypotheses were explored before profiling: (1) Playwright page leak from missing try/finally, (2) unbounded WebSocket queue from Network.enable flooding, (3) stale Chromium needing fresh AdsPower profiles
- **py-spy was the decisive tool** — `py-spy dump --pid` gave immediate stack traces that identified the real culprit in seconds after hours of wrong guesses

## Details

### The Spin-Loop Mechanism

Python's `asyncio.Event` is a synchronization primitive with two states: set and unset. `event.wait()` blocks until the event is set. Critically, `event.wait()` **returns immediately if the event is already set** — it does not consume the "set" state. Only `event.clear()` resets it to unset.

The v3 DataStore uses a `change_event` to notify consumers when new odds data arrives. The pattern should be:

```python
# Correct pattern
while True:
    change_event.clear()  # Reset before waiting
    await asyncio.wait_for(change_event.wait(), timeout=5)
    # Process new data...
```

The SSE producer omitted the `.clear()` call:

```python
# Bug pattern (server.py:304)
while True:
    await asyncio.wait_for(change_event.wait(), timeout=5)
    # Process new data...
    # BUG: event stays set → next wait() returns instantly → infinite loop
```

Once any scraper set the event (on first data arrival), the SSE producer's loop became an infinite spin: `wait()` returned instantly, the loop body executed (yielding SSE data), and the next `wait()` returned instantly again. Each iteration created asyncio Task and TimerHandle objects (from the `wait_for` wrapper) that were never garbage collected fast enough, leaking at ~75 MB/sec.

### Why Three Hypotheses Were Wrong

**Hypothesis 1 — Playwright page leak**: A real but unrelated bug was found: `_fetch_wizard_in_tab` and `_fetch_wizard_body` had missing `try/finally` around page lifecycle, meaning `CancelledError` during `asyncio.sleep()` would leak pages. This was fixed but RSS continued growing — the page leak was ~22 MB/min (steady-state after fix), not the 3 GB/min observed during the blowup.

**Hypothesis 2 — WebSocket queue overflow**: `_raw_ws_listener` (Network.enable) was flooding the asyncio queue. Applied `max_queue=128` + substring filter before `json.loads`. Didn't help because the WS listener wasn't the hot path.

**Hypothesis 3 — Stale Chromium**: Bounced AdsPower profiles for fresh Chrome instances. Same growth pattern — disproved.

**Hypothesis 4 (correct) — py-spy**: `py-spy dump --pid <pid>` instantly showed `_stream_events` at `server.py:304` as the hot function, with the `change_event.wait()` call dominating. The fix was immediately obvious.

### The Recurring Pattern

This is the second time the `Event.wait()` without `.clear()` bug has occurred in the v3 codebase. The tracker had the identical bug — it was fixed when the event-driven tracker was first deployed. But the SSE producer was written separately and inherited the same pattern without the fix. This is a classic "fix doesn't propagate across copies" anti-pattern: when the same design pattern is implemented in multiple places, a bug fix in one location doesn't automatically apply to the others.

### Diagnostic Lesson: Profile, Don't Guess

The three wrong hypotheses consumed hours of debugging time. py-spy identified the real cause in seconds. The RSS growth rate (~75 MB/sec) happened to match estimates for httpx SSL context creation, leading to a plausible but incorrect red herring about HTTP connection pools. The lesson: **for memory/CPU issues in live Python processes, attach a profiler immediately instead of reasoning from symptoms.** py-spy requires no code changes, no restart, and no debugger attachment — it reads stack frames from a running process via system calls.

## Related Concepts

- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where the DataStore's change_event powers both the tracker and SSE producer; the bug was in the SSE consumer of this shared primitive
- [[concepts/vps-sse-cascade-silent-crash]] - SSE-related server crashes; the spin-loop is a different SSE failure mode (resource exhaustion vs error cascade)
- [[connections/silent-type-coercion-data-corruption]] - The spin-loop produced plausible wrong output (SSE data was still streaming, just at infinite rate) rather than obvious errors
- [[concepts/playwright-node-pipe-crash-vector]] - Hypothesis 1 (page leak) was a real Playwright bug, just not the root cause of the memory blowup

## Sources

- [[daily/lcash/2026-05-08.md]] - RSS ballooned 300MB→35GB+ at ~75MB/sec; three wrong hypotheses (Playwright page leak, WS queue overflow, stale Chromium) before py-spy pinpointed `_stream_events` at server.py:304; `change_event.wait()` without `.clear()` created infinite spin loop leaking Task+TimerHandle objects; identical bug previously fixed in tracker but not SSE producer; all defensive fixes (max_queue, try/finally page lifecycle, substring filter) retained as good hygiene despite not being root cause; V3_WS_LISTENER env gate confirmed WS layer was not the source (Session 18:36)
