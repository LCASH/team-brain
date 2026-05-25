---
title: "Discord Brain Army Research Pipeline"
aliases: [army-pipeline, multi-worker-research, bookie-research-pipeline, discord-army, synth-compression, vocab-sharding]
tags: [architecture, ai-agent, discord, research-pipeline, claude, multi-worker]
sources:
  - "daily/lcash/2026-05-23.md"
created: 2026-05-23
updated: 2026-05-23
---

# Discord Brain Army Research Pipeline

On 2026-05-23, lcash iterated the Discord Brain "Army" pipeline from v5→v6→v7, a multi-worker parallel research framework that deploys 2-7 Opus agents per bookie to deep-dive a corpus of 808,707 Discord messages across 11 servers. Each Army run shards research into primary workers (broad topic exploration), followup workers (broadening on zero-hit queries), and a synth2 consolidation pass — producing 12,000-22,000 char intelligence reports on bookie operations, promotions, and community sentiment. The v6 iteration solved a dominant failure mode where synth1-generated FTS queries (full-sentence strings) returned 0 hits by constraining queries to 1-3 token FTS-friendly terms with a `fallback_query` field.

## Key Points

- **Multi-worker architecture**: 2-7 primary workers + 2-5 followup workers + 1 synth2 consolidation pass per bookie; each worker is a separate Claude Opus subprocess with MCP search tools
- **v5→v6 progression**: v5 validated safe/noisy vocab split (cost $7.36→$6.33, rescued 8rain); v6 fixed synth1 full-sentence FTS queries (0 hits dominant failure mode) with 1-3 token constraint + followup self-broadening, jumping followup success rate from 25%→60%
- **Synth2 prompt compression**: Each worker capped at 1,800 chars (Summary + Key Findings + best quotes), followups at 1,200 chars, dropping <500 char workers → prompt drops from ~60K to ~18K chars — critical for staying within Opus rate limits
- **7-bookie battery test**: betr, tabtouch, pointsbet, sportsbet/sportys, tab, unibet, boostbet run in parallel (~70 simultaneous Opus calls, ~$40-50 total); orchestrators handle API throttling gracefully
- **FTS query design is critical**: Full-sentence queries → 0 hits; 1-3 token AND-joined queries → 60%+ success — FTS5 needs individually high-recall tokens, not precision phrases
- **Turn management as fix**: Remaining followup failures (2/5) are workers searching to budget exhaustion without writing synthesis — fixed by explicit "stop searching, write now" instruction at turn N-2

## Details

### The Iterative Bottleneck Discovery Pattern

The Army pipeline's evolution follows a predictable pattern: each fix exposes the next bottleneck layer.

**v3 (sharding)**: Split research across multiple workers instead of one monolithic query → exposed vocab classification problem (noisy terms like "tab" matching everywhere).

**v5 (safe/noisy vocab split)**: A vocab classification agent separates safe search terms (unique to bookie) from noisy ones (common words like "tab", "bet") → cost dropped $7.36→$6.33, rescued 8rain server which was producing garbage from noisy queries. But exposed new failure: synth1 generating FTS queries as complete sentences ("What is the current status of betr promotional offers?") that match zero FTS5 rows.

**v6 (broader queries + followup broadening)**: Three simultaneous fixes: (1) user-injected aliases override noisy classification (b3 now classified as safe), (2) synth1 constrained to 1-3 token FTS-friendly queries with `fallback_query` field, (3) followup workers self-broaden on zero hits via 5-step strategy (relax AND→OR, drop modifiers, try synonyms, widen date range, try partial names). Followup success rate jumped from 25% to 60%.

**v7 (validated on TABtouch)**: Workers 3/2, followups 5/5 (best ever — broader-queries fix confirmed), synth output 12,835 chars. But synth2 was silently rate-limited ($0 output) — the Anthropic OAuth 5-hour window was drained by the parallel battery.

### FTS5 Query Design

SQLite FTS5's full-text search is token-based: queries are AND-joined by default, meaning every token must appear in the document. A query like `"current status betr promotional offers"` requires ALL six words to appear in a single message — which virtually never happens in casual Discord chat. The fix constrains synth1 to generate 1-3 token queries like `"betr promo"` or `"cashback offer"`, which have high individual recall and combinatorially reasonable AND-join probability.

The `fallback_query` field provides a backup: if the primary query returns zero hits, the agent tries the fallback (typically a single high-recall token like the bookie name). This two-tier approach maximizes precision (multi-token primary) with guaranteed coverage (single-token fallback).

### Synth2 Compression

The synth2 pass consolidates findings from all workers into a single intelligence report. With 7 workers producing 3,000-5,000 chars each, the synth2 prompt can reach 60K+ chars — expensive for Opus and prone to hitting the 5-hour rate limit window. The compression scheme caps each worker summary at 1,800 chars (keeping Summary, Key Findings, and 2-3 best quotes), followups at 1,200 chars, and drops workers that produced <500 chars of output. This reduces the synth2 prompt to ~18K chars — a 3.3x reduction that fits comfortably within rate limits.

### Attachment URL Capture

Phase 1 of a 3-phase attachment strategy was shipped: MCP `search_messages` and `get_thread` now surface up to 3 attachment URLs per message (agent-judged relevance, not firehose). Primary worker prompts include a `## Relevant attachments` section, and synth2 consolidates/dedupes URLs across workers. Discord CDN URLs expire after ~24h (signed params), so a `/attachment/refresh?url=...` proxy endpoint was built that calls Discord's `/attachments/refresh-urls` API and 302-redirects to freshly-signed URLs. All synth output URLs are auto-rewritten client-side to use this proxy.

### Betr Army Validation

The betr Army test completed successfully: 7/2 workers, 3/1 followups, synth2 produced 21,780 chars, total cost $6.91. Synth2 successfully output a `## Relevant attachments` section with 62 categorized Discord CDN URLs — validating the end-to-end attachment capture and refresh proxy chain.

### 4-Tier Fix Plan

A prioritized fix plan was established:

| Tier | Fix | Effort | Impact |
|------|-----|--------|--------|
| 1 | Followup maxTurns 6→8 + "write by N-2" | Quick | Prevents search-to-exhaustion |
| 1 | Skip workers for thin-corpus servers (<15 hits) | Quick | Eliminates wasted Opus calls |
| 1 | skipVocab toggle for non-bookie queries | Quick | Bypasses noisy classification |
| 2 | Quote verification pass | Medium | Catches hallucinated citations |
| 2 | Sub-sharding by topic cluster | Medium | Better coverage on large corpora |
| 3 | Semantic embedding pre-pass ($10 one-time) | High | Highest-leverage if daily usage justifies |

## Related Concepts

- [[concepts/discord-brain-mcp-agent-architecture]] - The MCP agent architecture that the Army pipeline builds on; Army uses the same stdio MCP server and search tools but orchestrates multiple agents in parallel
- [[concepts/news-agent-stage2-production-scaling]] - Parallel pattern: Stage 2's serial→parallel fix and synth prompt compression solve the same class of problems (sequential bottleneck + prompt size limits) in a different domain
- [[concepts/anthropic-max-plan-opus-rate-drain]] - The rate limit pattern that forced synth2 compression; ~70 parallel Opus calls drained the 5-hour budget
- [[concepts/discord-cdn-attachment-refresh-proxy]] - The attachment refresh proxy that enables Army reports to include clickable Discord CDN images

## Sources

- [[daily/lcash/2026-05-23.md]] - v5→v6 iteration: synth1 full-sentence FTS queries fixed with 1-3 token constraint + followup broadening (25%→60% success); v6 validated with user-injected aliases (b3 safe), followup self-broadening strategy; 7-bookie battery launched ~70 simultaneous Opus calls ~$40-50; 4-tier fix plan established (Session 13:14). TABtouch v7 validated: workers 3/2, followups 5/5, synth2 rate-limited from Opus budget drain; attachment URL Phase 1 shipped; betr Army test: 7/2 workers, 21,780 chars, $6.91, 62 attachment URLs (Sessions 14:18, 14:49). Synth2 prompt compression: 1,800 char cap per worker, 1,200 for followups, <500 dropped; prompt 60K→18K chars (Session 14:49)
