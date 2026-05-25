---
title: "Discord Message Corpus Management"
aliases: [discord-corpus, discord-indexer, server-whitelisting, fts5-contentless-delete, corpus-backup]
tags: [discord, architecture, sqlite, fts5, data-management, infrastructure]
sources:
  - "daily/lcash/2026-05-23.md"
created: 2026-05-23
updated: 2026-05-23
---

# Discord Message Corpus Management

On 2026-05-23, lcash built corpus management infrastructure for the Discord Brain message indexer: date cutoffs (2025-01-01), server whitelisting with gateway filtering, database backup, and pruning of pre-cutoff messages. The final corpus reached **808,707 messages** across 742 channels in 11 servers. Key operational lessons include FTS5 contentless table delete syntax, SQLite BUSY errors under concurrent gateway+backfill writes, and the "empty array = no filter" UI ambiguity that caused runaway ingestion.

## Key Points

- **808,707 messages indexed** across 742 channels, 11 servers, all post-2025-01-01 — balances recency with corpus size for betting-community intelligence
- **FTS5 contentless tables reject standard `DELETE`** — must use `INSERT INTO fts_table(fts_table, rowid) VALUES('delete', ?)` syntax for the shadow table
- **SQLite BUSY under concurrent writes**: Gateway (live messages) + backfill (historical messages) hammering DB simultaneously causes lock contention and crashes; both auto-restart but UX is confusing
- **"Empty array = no filter" footgun**: UI's "select all" toggle → unchecking all → save as `[]` → server interprets as "ingest all" (not "ingest nothing") — caused runaway backfill
- **Server whitelist controls live ingestion only**: Unchecked servers stop receiving new messages but retain existing indexed data (no auto-purge on deselect)
- **Backup is raw SQLite file copy** (~1 GB per snapshot) stored at `data/backups/` — simple and fully restorable; automatic daily backup deferred to manual/UI for now

## Details

### Date Cutoff Implementation

The 2025-01-01 cutoff was implemented to stop indexing pre-2025 messages. This required a stop→prune→restart sequence because a running backfill process doesn't pick up config changes mid-run — the backfill must be stopped, the cutoff date updated, existing pre-cutoff messages pruned from the database, and the backfill restarted.

The FTS5 contentless table pruning was the trickiest part. SQLite FTS5 in contentless mode (where the FTS index doesn't store the original content, only tokenized terms) doesn't support standard SQL `DELETE FROM fts_table WHERE rowid = ?`. Instead, deletions use a special "delete" command: `INSERT INTO fts_table(fts_table, rowid) VALUES('delete', ?)`. This counter-intuitive syntax is documented in SQLite FTS5 docs but easy to miss, and the error message when using standard DELETE is unhelpful.

### Server Discovery and Whitelisting

A `GET /actions/list-guilds` endpoint was added that queries the Discord gateway for all servers the bot has joined, presenting them as a checklist UI in the Settings page. The gateway filter drops messages from non-whitelisted guilds at ingestion time — the message handler checks the server ID against the whitelist before writing to the database.

11 servers were whitelisted: Bonusbank, Unabated, ProfitDuel, EndGame, Boosts Server, BetIQ, 8rain Station, Diamond Squid, SEVA Sports Betting, red pill, and [ ∴ ]. TAKEOVER and MB Summit were intentionally excluded.

### The Empty Array Footgun

A subtle UI state ambiguity caused a runaway backfill: unchecking the "select all" toggle sent an empty array `[]` to the server. The server's whitelist filter treated `[]` as "no filter applied" (semantically "allow all") rather than "nothing selected" (semantically "allow none"). This caused the backfill to ingest from ALL servers regardless of the UI state.

The fix added an explicit status indicator and amber warning when zero servers are selected, distinguishing "all selected" (save as full array) from "none selected" (save as empty with warning, interpret as "block all"). The `409 "already running"` response on duplicate backfill triggers was also surfaced in the UI — previously it looked like a real error rather than an expected state.

### SQLite Concurrent Write Contention

The Discord gateway (receiving live messages via WebSocket) and the backfill process (fetching historical messages via REST API) both write to the same SQLite database. Under heavy concurrent write load, SQLite's single-writer locking produces BUSY errors that crash both processes. Both auto-restart, but the interleaved crash/restart cycle is operationally confusing — it looks like systematic instability rather than a simple lock contention issue.

WAL (Write-Ahead Logging) mode or explicit write serialization (queueing writes through a single writer process) would resolve this. For now, the operational workaround is to avoid running backfill during high-traffic gateway periods.

### Conversation History and Chat Features

In the same session, a chat history sidebar was built (`/conversations` and `/conversations/:sessionId` endpoints) enabling browsing of past `/ask` research sessions. Per-conversation logging at `data/ask-logs/<session_id>.jsonl` captures the full tool-call chain for post-query analysis of search strategy and synthesis quality.

The default model was switched from Sonnet to **Opus 4.7** for deeper multi-step research queries (~$0.50-$1.50 vs ~$0.30 per deep dive). A smoke test showed 31 tool calls, 0 auto-scoped searches (a prior bug where Claude incorrectly filtered to a single server), and proper breadth exploration with query rephrasing on empty results.

## Related Concepts

- [[concepts/discord-brain-mcp-agent-architecture]] - The MCP agent that searches this corpus; model upgraded to Opus 4.7 with improved research quality patterns
- [[concepts/discord-brain-army-research-pipeline]] - The Army pipeline that performs deep-dive research across this corpus; corpus size directly affects research quality
- [[concepts/discord-cdn-attachment-refresh-proxy]] - Attachment URLs within the corpus expire; the refresh proxy keeps them clickable

## Sources

- [[daily/lcash/2026-05-23.md]] - Date cutoff 2025-01-01 implemented; FTS5 contentless delete syntax discovered; SQLite BUSY from concurrent gateway+backfill; server whitelist with 11 servers; empty array = no filter footgun fixed; 808,707 messages / 742 channels / 11 servers; backup to data/backups/ (~1GB snapshots) (Session 09:34). Server discovery UI + gateway filter; backfill process doesn't pick up config changes mid-run (Session 11:06). Select-all toggle bug fixed; SQLITE_BUSY crashes from dual-write; Opus 4.7 default for research; conversation history sidebar; per-conversation JSONL logging; Claude auto-scoping search fix ("DO NOT pass server argument"); min 8 searches for deep dive, target 10-15 (Session 11:36)
