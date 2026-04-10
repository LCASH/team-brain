---
title: "Stop Hook Periodic Capture"
aliases: [periodic-capture, stop-hook-timer, 30-min-capture]
tags: [claude-code, hooks, capture, architecture]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-10
---

# Stop Hook Periodic Capture

A pattern for reliably capturing conversation context at regular intervals using Claude Code's Stop hook combined with a lightweight timer check. Adopted as the primary capture mechanism for the team knowledge base after discovering that SessionEnd is unreliable.

## Key Points

- The Stop hook fires after every assistant response, providing a reliable trigger point for periodic tasks
- A timer check gates the actual capture work behind a configurable interval (default: 30 minutes)
- The timer check overhead is less than 50 milliseconds per invocation, making it negligible despite running on every response
- This replaces SessionEnd as the primary capture mechanism since users rarely close sessions explicitly
- The captured context is flushed to daily log files via a background process (flush.py)

## Details

The periodic capture pattern works by intercepting the Stop hook — which fires reliably after every assistant response — and comparing the current time against a stored "last flush" timestamp. If the elapsed time exceeds the configured interval (30 minutes by default), the hook triggers a full context flush. Otherwise, it exits immediately after the sub-50ms timer check.

This design is a pragmatic response to a behavioral observation: developers don't close their Claude Code sessions cleanly. They switch tasks, close laptops, or let terminals idle. Since SessionEnd depends on explicit closure, any pipeline relying on it will have poor coverage. The Stop hook sidesteps this by checking on every interaction, guaranteeing that no active session goes more than 30 minutes (plus one response cycle) without a capture.

The actual flush operation is spawned as a fully detached background process to avoid blocking the user's workflow. The hook itself returns almost instantly — the expensive work (reading the transcript, calling the Claude Agent SDK for extraction, appending to the daily log) happens asynchronously. Deduplication logic in flush.py prevents redundant captures if the same session is flushed within 60 seconds.

## Related Concepts

- [[concepts/claude-code-hook-reliability]] - The reliability analysis that motivated this pattern
- [[concepts/team-knowledge-base-architecture]] - The broader system this capture mechanism feeds into
- [[concepts/local-compilation-strategy]] - Downstream compilation of the captured daily logs

## Sources

- [[daily/lcash/2026-04-10.md]] - Implementation of Stop hook for 30-minute periodic capture; timer check benchmarked at <50ms
