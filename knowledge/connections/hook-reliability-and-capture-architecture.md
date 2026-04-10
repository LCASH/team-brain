---
title: "Connection: Hook Reliability and Capture Architecture"
connects:
  - "concepts/claude-code-hook-reliability"
  - "concepts/stop-hook-periodic-capture"
  - "concepts/team-knowledge-base-architecture"
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-10
---

# Connection: Hook Reliability and Capture Architecture

## The Connection

The reliability characteristics of Claude Code's hook system directly determined the capture architecture of the team knowledge base. A behavioral observation about how developers actually end sessions (they don't) cascaded into a fundamental architectural choice: polling via Stop hook instead of event-driven capture via SessionEnd.

## Key Insight

The non-obvious insight is that the most natural hook for "end of session" capture — SessionEnd — is the worst choice for reliable capture. This is because the hook's firing condition (explicit session close) doesn't match the user behavior it's meant to capture (finishing work). The gap between "user is done" and "user closes the session" is where data loss lives. The Stop hook, despite being semantically unrelated to session completion, is the reliable alternative because it fires on every interaction, guaranteeing coverage as long as the session is active.

This is an instance of a broader pattern: **design for observed behavior, not intended behavior.** The SessionEnd hook works as designed — it fires when sessions end. But sessions don't end the way the designers assumed. The Stop hook works because it aligns with what actually happens (the user interacts with Claude) rather than what should happen (the user closes the session).

## Evidence

During the initial team-brain pipeline setup on 2026-04-10, lcash discovered that SessionEnd rarely fires in practice. The solution — a Stop hook with a 30-minute timer check — added less than 50ms of overhead per response while providing near-perfect capture coverage. This single reliability observation reshaped the entire capture layer of the architecture, influencing decisions about local vs. CI compilation (since capture timing became unpredictable) and the nightly fallback mechanism.

## Related Concepts

- [[concepts/claude-code-hook-reliability]] - The reliability analysis that surfaced this connection
- [[concepts/stop-hook-periodic-capture]] - The architectural pattern that emerged from it
- [[concepts/team-knowledge-base-architecture]] - The system-level design shaped by this insight
- [[concepts/local-compilation-strategy]] - Downstream architectural decision influenced by capture unpredictability
