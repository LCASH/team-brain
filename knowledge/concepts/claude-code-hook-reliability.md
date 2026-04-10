---
title: "Claude Code Hook Reliability"
aliases: [hook-reliability, session-end-behavior, hook-firing]
tags: [claude-code, hooks, reliability, capture]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-10
---

# Claude Code Hook Reliability

Claude Code provides several hook points (SessionStart, SessionEnd, Stop, PreCompact) for running custom scripts during a coding session. These hooks have significantly different reliability characteristics that directly impact system design decisions for any pipeline that depends on capturing conversation data.

## Key Points

- SessionEnd only fires when the user explicitly closes the session — it does not fire when users simply walk away, close their laptop, or let the terminal idle
- The Stop hook fires after every assistant response, making it highly reliable for periodic tasks when combined with a timer check
- The timer overhead for a Stop hook check is less than 50 milliseconds, making it negligible even though it runs frequently
- PreCompact fires before context window auto-compaction, capturing intermediate state in long sessions
- The unreliability of SessionEnd is the primary reason the Stop hook was adopted as the main capture mechanism

## Details

The most important lesson discovered during the team-brain pipeline setup is that SessionEnd is unreliable as a capture mechanism. In typical developer workflows, users don't explicitly close their Claude Code sessions — they switch to another window, close their laptop, or simply walk away. The SessionEnd hook only fires on deliberate close actions, meaning a capture pipeline that relies solely on it will miss the majority of sessions.

The Stop hook provides a reliable alternative. It fires after every assistant response, which initially seems excessive for periodic tasks like flushing conversation context. However, by implementing a lightweight timer check (comparing the current time against the last flush timestamp), the hook can gate expensive operations behind a time interval (e.g., every 30 minutes) while the check itself completes in under 50 milliseconds. This approach transforms an unreliable event-driven architecture into a reliable polling-based one with negligible overhead.

The combination of Stop hook (frequent, reliable) and PreCompact hook (fires before context summarization) provides comprehensive coverage. PreCompact is particularly important for long sessions where auto-compaction would otherwise discard intermediate context before SessionEnd ever fires.

## Related Concepts

- [[concepts/stop-hook-periodic-capture]] - The periodic capture pattern built on top of Stop hook reliability
- [[concepts/team-knowledge-base-architecture]] - The system architecture shaped by these reliability constraints
- [[concepts/local-compilation-strategy]] - Compilation timing also influenced by hook behavior

## Sources

- [[daily/lcash/2026-04-10.md]] - Discovery that SessionEnd rarely fires because users walk away; Stop hook timer check measured at <50ms overhead
