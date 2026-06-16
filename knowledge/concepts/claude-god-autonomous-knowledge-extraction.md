---
title: "Claude God Autonomous Knowledge Extraction System"
aliases: [claude-god, god-pulse, autonomous-brain-extraction, eve-knowledge-indexer, session-jsonl-extractor]
tags: [ai-agent, architecture, knowledge-management, claude-sdk, eve, automation]
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Claude God Autonomous Knowledge Extraction System

On 2026-06-03, lcash built and deployed "Claude God" on Eve VPS — an automated knowledge extraction system that pulses hourly, reads Claude Code session JSONLs, extracts findings/decisions/skills via Claude Agent SDK, and writes them to a shared team brain. The core pipeline flows through five stages: JSONL scanner, transcript renderer, Claude SDK extractor, brain indexer, and systemd timer orchestration.

## Key Points

- Hourly systemd timer pulses with delta-only processing: only JSONL files with 500+ bytes of growth since the last pulse trigger extraction, preventing redundant re-processing of unchanged sessions
- A critical recursion bug was discovered and fixed — God's own SDK calls spawn new session JSONLs that would be scanned on the next pulse, creating an infinite extraction loop. The fix uses a dedicated `god-sdk-cwd` path that is excluded from the scan directory list
- Claude SDK `usage` is a dict not an object (requires `.get()` not `getattr`), and the SDK requires a valid `cwd` for its subprocess — missing directories cause silent failures with no error output
- Pulse idle cost is genuinely zero ($0): when no new chat activity is detected, the pulse performs only `stat()` calls and a state.json read/write; three sequential guards prevent any unnecessary LLM calls
- Brain output uses slug-keyed deduplication so future sessions compound into existing findings rather than creating duplicates; output is identity-detached, referencing session UUIDs only with no developer names

## Details

The recursion prevention mechanism was one of the trickiest aspects of the deployment. God's extraction calls use the Claude Agent SDK, which itself creates session JSONL files. Without isolation, these new JSONLs would appear as "new activity" on the next pulse, triggering extraction of extraction sessions ad infinitum. The solution — a dedicated `god-sdk-cwd` excluded from scan paths — mirrors a similar guard already present in `flush.py`, which uses a `CLAUDE_INVOKED_BY=memory_flush` environment variable to prevent the flush process from capturing its own output. Both approaches solve the same recursive self-observation problem but at different layers of the stack.

The brain format prioritizes provenance: every extracted claim includes inline provenance linking back to the specific session UUID and timestamp. The output follows a table-of-claims format where each finding is a discrete, addressable entry rather than a prose paragraph. This structure enables downstream consumers (MCP agents, search tools, dashboards) to cite specific claims with full traceability. A Gitea webhook integration was also deployed, running as a separate systemd service (`god-webhook.service` on port 9000), which ingests PR discussion threads into the brain — capturing review decisions and architectural discussions that happen outside of Claude Code sessions.

Phase 2 introduced an ask-session skill using `claude --resume <uuid> --fork-session -p` for agent-to-agent queries. The fork approach gives the querying agent access to the full Claude Code runtime of the target session — including tools, hooks, MCP servers, skills, and CLAUDE.md context — without mutating the original session's history. This enables a knowledge graph where God can not only extract from sessions passively but actively interrogate them for deeper context when a finding is ambiguous or incomplete.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The shared brain that God writes extracted knowledge into
- [[concepts/stop-hook-periodic-capture]] - The hook-based capture mechanism that creates the session JSONLs God reads
- [[concepts/eve-team-development-environment]] - The Eve VPS infrastructure where God runs as a systemd service

## Sources

- [[daily/lcash/2026-06-03.md]] - Sessions 09:12, 10:01 (God deployment and debugging of recursion bug, SDK usage quirks), 09:52 (ask-session skill design and fork-based agent-to-agent queries)
