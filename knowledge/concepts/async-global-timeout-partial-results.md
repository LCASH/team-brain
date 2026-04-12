---
title: "Async Global Timeout with Partial Results"
aliases: [global-timeout-pattern, mutable-container-pattern, partial-scan-results]
tags: [asyncio, python, patterns, resilience, timeout]
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# Async Global Timeout with Partial Results

A resilience pattern for async operations where individual steps may hang indefinitely and per-step timeouts are ineffective. Instead of timing out each operation, a single global timeout wraps the entire phase, and results are accumulated into mutable containers passed as parameters so that work completed before the timeout is preserved and usable.

## Key Points

- When individual async operations cannot be cancelled (e.g., Playwright's `page.evaluate()`), per-operation timeouts are unreliable — the timeout fires but the operation continues blocking
- A global `asyncio.wait_for()` around the entire phase reliably cancels at the coroutine level even when individual calls block
- Mutable containers (dicts, lists) are passed as parameters to the coroutine rather than used as local variables, so partial results survive cancellation
- The pattern trades completeness for reliability: the system proceeds with whatever data was collected before the hang
- In the bet365 adapter, a 4-minute global timeout on `build_runner_map()` preserves partial venue scans (e.g., 10/14 venues) when one venue causes a hang

## Details

### The Problem

Some async operations in Python are not truly cancellable. When `asyncio.wait_for()` times out on such an operation, it raises `asyncio.TimeoutError` but the underlying coroutine may continue executing (or remain blocked). This means per-operation timeouts give a false sense of safety — the timeout fires, but the event loop is still blocked on the uncancellable call.

This pattern was discovered in the bet365 racing adapter, where `page.evaluate()` calls to Playwright hang indefinitely when a venue's browser JavaScript context becomes unresponsive. Wrapping individual `page.evaluate()` calls in `asyncio.wait_for()` raised the timeout exception but did not actually free the event loop. See [[concepts/playwright-evaluate-uncancellable]] for details.

### The Solution

The pattern has two components:

**1. Global timeout:** Instead of timing out each venue scan individually, wrap the entire `build_runner_map()` coroutine in a single `asyncio.wait_for(build_runner_map(...), timeout=240)`. When any single venue hangs, the global timeout eventually fires and cancels the entire coroutine. This works because `asyncio.wait_for()` at the outer level can cancel the wrapper coroutine even if the inner call blocks — the cancellation propagates when the event loop regains control.

**2. Mutable containers as parameters:** The coroutine signature accepts mutable containers — `participant_map: dict` and `fixture_participants: dict` — as parameters rather than building them as local variables. As the coroutine scans each venue, it populates these containers incrementally. When the global timeout cancels the coroutine, the containers retain all data from successfully completed venues. The caller can then proceed with partial data (e.g., streaming odds for 10 out of 14 venues).

### Tradeoffs

- **Completeness vs. reliability:** The adapter proceeds with partial data rather than hanging indefinitely. For odds streaming, 10/14 venues with live data is far more valuable than 0/14 venues due to a hang.
- **Debugging opacity:** When the global timeout fires, the specific venue that caused the hang may not be logged unless the coroutine tracks its current operation before each potentially-blocking call.
- **Timeout calibration:** The global timeout (4 minutes in the bet365 case) must be long enough for the normal case (all venues scan successfully) but short enough that a hang doesn't waste excessive time. This requires empirical tuning.

### Generality

This pattern applies to any situation where: (1) you're iterating through a list of operations, (2) individual operations may hang and can't be reliably timed out, and (3) partial completion is acceptable. Examples include batch web scraping, multi-endpoint health checks against unreliable services, and parallel API calls where some providers may be down.

## Related Concepts

- [[concepts/playwright-evaluate-uncancellable]] - The specific uncancellable operation that motivated this pattern
- [[concepts/bet365-racing-adapter-architecture]] - The adapter that implements this pattern for venue scanning
- [[connections/browser-automation-reliability-cost]] - The broader reliability challenges of browser-mediated architectures

## Sources

- [[daily/lcash/2026-04-12.md]] - Implementation of 4-minute global timeout on `build_runner_map()` with mutable `participant_map` and `fixture_participants` containers to preserve partial scan results when Toowoomba venue hangs (Session 15:37)
