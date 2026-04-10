---
title: "Local Compilation Strategy"
aliases: [local-compile, no-ci-compilation, nightly-fallback]
tags: [architecture, compilation, cost-optimization, ci-cd]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-10
---

# Local Compilation Strategy

Knowledge base compilation runs locally on each developer's machine rather than in a CI/CD pipeline like GitHub Actions. A nightly fallback mechanism ensures compilation still happens even if a developer's local environment misses it.

## Key Points

- Compilation runs locally to avoid burning CI minutes and API costs on every push
- Each compile of a daily log costs approximately $0.45-0.65 in API usage
- A nightly fallback catches any daily logs that weren't compiled during the day
- The end-of-day auto-compilation triggers after 6 PM local time when flush.py detects uncompiled changes
- This approach trades real-time compilation for significant cost savings and simpler infrastructure

## Details

The decision to compile locally rather than in CI was driven by practical cost and infrastructure concerns. Each daily log compilation requires a Claude Agent SDK call that costs $0.45-0.65, and the cost scales with the size of the existing knowledge base (since all current articles are loaded into context for deduplication and cross-referencing). Running this in GitHub Actions on every push would multiply costs by the number of developers and push frequency, while also requiring API key management in CI secrets.

Local compilation also provides a better developer experience. The compilation process uses the developer's existing Claude Code credentials (stored at `~/.claude/.credentials.json`), eliminating the need for separate API key provisioning. Developers can run `compile.py` manually when they want immediate results, or rely on the automatic end-of-day trigger built into flush.py.

The nightly fallback is implemented as a simple check in flush.py: after 6 PM local time (`COMPILE_AFTER_HOUR = 18`), if the current day's daily log has changed since its last compilation (tracked via SHA-256 hash in `state.json`), flush.py spawns compile.py as a detached background process. This ensures that even if a developer never explicitly compiles, their day's knowledge is processed before the next morning. The hash-based change detection prevents redundant compilations.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The broader system architecture this strategy supports
- [[concepts/stop-hook-periodic-capture]] - The capture mechanism that produces the daily logs compiled by this strategy
- [[concepts/claude-code-hook-reliability]] - Hook reliability considerations that influence when compilation can be triggered

## Sources

- [[daily/lcash/2026-04-10.md]] - Decision to use local compilation over GitHub Actions to avoid CI burn, with nightly fallback for missed compilations
