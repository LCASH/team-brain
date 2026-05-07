---
title: "News Agent Stage 2 Production Scaling"
aliases: [stage2-optimization, news-agent-parallelism, odds-jsonl, progressive-picks, stage2-timeout, cmd-truncation]
tags: [value-betting, news-pipeline, ai-agent, performance, architecture, windows]
sources:
  - "daily/lcash/2026-05-01.md"
created: 2026-05-01
updated: 2026-05-01
---

# News Agent Stage 2 Production Scaling

On 2026-05-01, three independent bottlenecks in the news agent's Stage 2 (Sonnet research agent) were identified and fixed, reducing per-event wall time from 600-790s to ~400s, cost from $0.85-1.03 to $0.60/event, and eliminating silent pick loss from subprocess timeouts. The fixes were: (1) replacing serial tweet processing with fire-and-forget `asyncio.create_task` parallelism, (2) bumping the subprocess timeout from 600s to 900s after discovering picks were silently lost, and (3) converting the 50KB odds.md markdown workspace to a bash-queryable odds.jsonl format that reduced context window burn by 70%. A fourth fix addressed Windows `.CMD` wrapper truncation of multi-line `-p` arguments.

## Key Points

- `process_tweet` was blocking the polling loop serially — `async for` over an async generator blocks the generator's `__anext__` while awaiting the consumer; polling literally paused during each 7-minute Stage 2 analysis
- Subprocess timeout at 600s was silently killing Stage 2 sessions and losing all picks — the Conley test case wrote "Session timed out" in `analysis_reasoning` but stored 0 picks, making it look like a classification miss rather than a crash
- `odds.md` → `odds.jsonl` conversion: 50KB markdown table replaced with bash-queryable JSONL; agent uses targeted `grep` returning 5-15KB of relevant rows instead of scanning entire table; 33% wall-time reduction
- Windows `.CMD` npm wrapper truncates multi-line `-p` arguments at first newline — Stage 2 prompt was being silently truncated; fix: single-line `-p` arg with full instructions in workspace files the agent reads
- Sonnet hallucinated file writes: agent's `analysis_reasoning` described writing 3 picks to `output/picks.json` but the file was empty — agent narrated the write instead of executing the Write tool

## Details

### Serial Processing Bottleneck

The news agent's polling loop used `async for` to iterate over an async generator that yielded classified tweets. When a tweet was yielded, `process_tweet()` was called inline — an awaited coroutine that spawned a Claude CLI subprocess for Stage 2 analysis. This created a fundamental blocking pattern: while the subprocess ran (~7 minutes per event), the async generator's `__anext__` was never called, meaning the Twitter polling loop was completely paused. During tweet clustering events (multiple injury reports within minutes), subsequent tweets were missed entirely.

The fix replaces the inline await with fire-and-forget `asyncio.create_task(process_tweet(event))`. Each classified tweet spawns an independent task that runs concurrently. There is no semaphore cap — unlimited parallelism was chosen over bounded concurrency because: (1) tweet clustering events are rare (2-3 simultaneous at most), (2) each task's cost is fixed regardless of parallelism, and (3) the total API cost is the same, just distributed across time differently. The polling loop confirmed working: Murray + Harris events ran simultaneously (11 seconds apart, each ~10 minutes), with no missed tweets.

### Silent Timeout Pick Loss

The 600-second subprocess timeout in `analyst.py:197` was the most damaging bug. When a Stage 2 session exceeded 600s — which happened routinely, as sessions averaged 600-790s before optimization — the subprocess was killed. The agent had typically completed its analysis and formulated picks by this point but hadn't yet written them to the output file. The kill occurred during the write phase, producing an event record with `picks_generated=0` and `analysis_reasoning="Session timed out"`.

This failure was invisible in aggregate monitoring: the event appeared to have been classified correctly (Stage 1 passed), analyzed (Stage 2 ran), but produced no picks (which looks like "market was efficient, no edge found" — a valid outcome). Only manual inspection of `analysis_reasoning` text revealed the timeout pattern. The Conley test case was the canary: the agent's reasoning described 3 specific picks with odds and rationale, but the output file was empty.

The immediate fix bumped the timeout from 600s to 900s. The structural fix — converting odds.md to odds.jsonl — reduced typical session time to ~400s, providing comfortable margin below the 900s limit.

### Odds Format Conversion: Markdown to JSONL

The Stage 2 workspace included a 50KB `odds.md` file containing all sportsbook odds for the affected game as a markdown table (~764 lines). The Sonnet agent had to scan this entire table to find relevant markets — burning tokens on irrelevant rows and adding 30-60s of processing time per session.

The replacement `odds.jsonl` format stores one market per line as JSON, enabling targeted bash `grep` patterns. The agent's `instructions.md` now includes grep patterns for common queries (e.g., `grep "player_name" odds.jsonl | grep "rebounds"` to find a specific player's rebound props). This returns 5-15KB of relevant rows instead of the full 50KB, reducing context window consumption by ~70% and session time by ~33%.

This is a general pattern for analytical agents working with large reference datasets: JSONL + bash grep outperforms wholesale markdown dumps because it shifts the filtering burden from the LLM (expensive, slow) to bash (free, instant).

### Windows .CMD Wrapper Truncation

npm-installed CLI tools on Windows use `.CMD` wrapper scripts. These wrappers truncate arguments passed via `-p` at the first newline character. The Stage 2 invocation was passing a multi-line prompt string via `-p`, which was silently truncated to just the first line. The agent received a partial prompt missing critical instructions about pick format, output location, and evaluation criteria.

The fix collapses the `-p` argument to a single line containing only "Read instructions.md and workspace files, then analyze the event." All substantive instructions are placed in workspace files that the agent reads during execution. This pattern should be applied to all Claude CLI invocations on Windows mini PC deployments.

### Sonnet Hallucinated Tool Execution

During the McDaniels test case, the Sonnet agent's `analysis_reasoning` described writing 3 picks to `output/picks.json` — including specific player names, odds, and confidence values — but the file was empty or missing. The agent narrated the write action in its reasoning text without actually executing the Write tool. This is a known Sonnet failure mode where the model confuses describing an action with performing it.

The fix strengthens `instructions.md` to emphasize that the agent MUST use the Write tool for picks JSON — describing picks in markdown reasoning is not sufficient. A markdown-fallback parser was discussed as defense-in-depth (parsing picks from the reasoning text when the JSON file is missing) but not yet built.

### Production Metrics After Fixes

Post-optimization metrics from the mini PC deployment:

| Metric | Before | After |
|--------|--------|-------|
| Stage 2 wall time | 600-790s | ~400s |
| Cost per event | $0.85-1.03 | $0.60 |
| Pick loss from timeouts | Frequent (Conley case) | Zero |
| Concurrent events | 1 (serial blocking) | Unlimited (fire-and-forget) |
| Workspace context | 50KB (full odds.md) | 5-15KB (grep-filtered odds.jsonl) |

The system processed 12 events and generated 33 picks in 8 hours on 2026-05-01 — the highest sustained rate in the pipeline's history.

### Future: Progressive Picks

The remaining latency bottleneck is that all picks are written at the end of the Stage 2 session (~400s). A "progressive picks" architecture would have the agent write `pick_001.json`, `pick_002.json` as it identifies them (turn 2, not turn 10), shipping first picks in ~90-120s instead of 400s. This is architecturally significant because every second of deliberation is a second where Polymarket participants may be ahead. The progressive approach is scoped but not yet built.

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The pipeline architecture that these optimizations target; production validation (12 events, 33 picks in 8h) confirms the fixes
- [[concepts/news-driven-pre-sharp-ev-thesis]] - The strategic thesis that makes speed critical: beating sharps to news requires minimizing time from tweet to pick
- [[concepts/news-agent-classifier-vocabulary-gaps]] - Stage 1 classifier fixes deployed in the same production window; Stage 1 quality gates Stage 2 — fixed classifiers mean fewer wasted Stage 2 runs
- [[connections/silent-type-coercion-data-corruption]] - The subprocess timeout is another "plausible wrong output" pattern: 0 picks looks like "no edge" rather than "session killed mid-write"
- [[concepts/podcast-pick-extraction-pipeline]] - The podcast pipeline's JSONL extraction pattern influenced the odds.jsonl design; same principle of structured queryable format over wholesale text dump

## Sources

- [[daily/lcash/2026-05-01.md]] - Serial processing blocking polling loop; subprocess timeout 600→900s after Conley pick loss; odds.md→odds.jsonl 33% wall-time reduction; fire-and-forget asyncio.create_task parallelism; Windows .CMD truncation of multi-line -p args; Sonnet hallucinated file writes on McDaniels test; production metrics: 12 events, 33 picks, $0.60/event, 400s baseline; progressive picks concept for 90-120s first-pick latency (Sessions 08:18, 09:58, 13:01, 15:37, 15:41)
