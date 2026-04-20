---
title: "Claude Code Cron Idle-Only Constraint"
aliases: [cron-idle-only, cron-repl-idle, cron-firing-limitation, idle-cron]
tags: [claude-code, cron, monitoring, gotcha, tooling]
sources:
  - "daily/lcash/2026-04-20.md"
created: 2026-04-20
updated: 2026-04-20
---

# Claude Code Cron Idle-Only Constraint

Claude Code crons only fire when the REPL is idle — they do not trigger during an active conversation. This makes crons unsuitable for real-time monitoring or feedback loops during interactive debugging sessions, despite their apparent suitability for periodic tasks.

## Key Points

- Crons require the REPL to be in an idle state (no active conversation) before they will fire — active conversation blocks all cron execution
- A 5-minute cron set up during a debugging session never fired because the operator was continuously chatting with Claude throughout the monitoring window
- Direct polling scripts (e.g., 10-second interval loops) or remote triggers are the correct alternatives for real-time monitoring during active sessions
- Crons ARE suitable for background monitoring when no conversation is active — the 5-minute trail health cron (`31eaf5da`) fires correctly between sessions
- The remote trigger approach was attempted as an alternative but hit a 401 auth error, suggesting credential refresh may be needed

## Details

### Discovery

On 2026-04-20, lcash was debugging the Bet365 2.0 odds trail pipeline and needed real-time feedback on whether trail entries were being written as odds changed. The natural approach was to set up a cron — first at hourly intervals, then tightened to every 5 minutes for faster feedback. Despite multiple cycles passing, the cron never fired. The root cause was that lcash was actively conversing with Claude throughout the monitoring window, and Claude Code's cron system requires the REPL to be idle before firing.

This led to three successive monitoring strategy pivots within a single session:

1. **Hourly cron** — too slow for real-time feedback, and wouldn't fire during conversation anyway
2. **5-minute cron** — tightened interval, but still blocked by active conversation
3. **Direct 10-minute polling script** — ran via Bash tool with 10-second check intervals, bypassing the cron system entirely

The direct polling script worked immediately, providing real-time output within the conversation. This confirmed the cron limitation was the blocker, not the monitoring logic itself.

### Why This Matters

The idle-only constraint creates a blind spot in Claude Code's automation capabilities: the scenarios where a developer most wants real-time monitoring feedback (during active debugging) are precisely the scenarios where crons cannot fire. The developer is engaged in a conversation, iteratively debugging, and wants a background check to report results — but the conversation itself prevents the background check from running.

This is distinct from the Stop hook behavior documented in [[concepts/stop-hook-periodic-capture]], where the hook fires after every assistant response. The Stop hook fires during conversation (it is triggered by conversation activity). Crons are the inverse — they fire only in the absence of conversation activity.

### Workarounds

Three alternatives exist for real-time monitoring during active sessions:

1. **Direct Bash scripts** — run a monitoring loop via the Bash tool. This executes within the conversation context and provides output directly. The tradeoff is that it blocks further conversation until the script completes (unless run in the background).

2. **Background Bash commands** — use `run_in_background: true` on the Bash tool to start a monitoring script that runs independently. The operator is notified when it completes, and output can be read asynchronously.

3. **Remote triggers** — Claude Code's remote trigger system can execute tasks externally. However, on 2026-04-20 this approach hit a 401 authentication error, suggesting that trigger credentials may need periodic refresh.

### Crons vs. Hooks for Periodic Tasks

The cron idle constraint reinforces the design decision documented in [[concepts/claude-code-hook-reliability]]: for tasks that must run reliably during active usage, hooks (especially the Stop hook) are the correct mechanism. Crons are appropriate for background maintenance tasks that should run between sessions — compilation, cleanup, health checks that don't need immediate attention. The knowledge base's own compilation trigger (nightly after 6 PM via flush.py) is a cron-appropriate use case because it does not require active-session feedback.

## Related Concepts

- [[concepts/stop-hook-periodic-capture]] - Stop hooks fire during conversation (on every response), complementing crons which only fire when idle
- [[concepts/claude-code-hook-reliability]] - The broader hook reliability analysis that established Stop hook > SessionEnd; crons have their own reliability constraint (idle-only)
- [[concepts/self-evolving-operational-skill]] - The /checkup skill is invoked on-demand, avoiding the cron idle constraint entirely
- [[concepts/game-scraper-chrome-crash-recovery]] - The trail monitoring cron (`31eaf5da`) works correctly between sessions but would not fire during active debugging

## Sources

- [[daily/lcash/2026-04-20.md]] - Hourly cron → 5-minute cron → direct polling script progression; cron never fired during active conversation; remote trigger 401 auth error; direct 10-minute monitor (10s intervals) used as workaround (Sessions 08:09, 08:28, 11:54)
