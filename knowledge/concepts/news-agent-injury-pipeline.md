---
title: "News Agent Injury-to-Pick Pipeline"
aliases: [news-agent, injury-pipeline, injury-classification, betting-news-agent, sga-injury-agent]
tags: [value-betting, ai-agent, news, injury, pipeline, claude-sdk]
sources:
  - "daily/lcash/2026-04-24.md"
created: 2026-04-24
updated: 2026-04-24
---

# News Agent Injury-to-Pick Pipeline

A two-stage AI pipeline for the value betting scanner that classifies injury tweets and generates betting picks using live odds data. Stage 1 uses Haiku to classify news events (injury, trade, lineup change) with player/team extraction. Stage 2 uses Sonnet with Claude Agent SDK tools to query live odds, fetch CLV history, and produce structured betting recommendations. Built on 2026-04-24 using the same `@tool` + `create_sdk_mcp_server()` + `query()` pattern as the podcast pipeline.

## Key Points

- **Stage 1 (Haiku classifier)**: Classifies injury tweets as `injury_out`, `injury_questionable`, `trade`, `lineup_change`, etc.; extracts player name, team, and impact assessment
- **Stage 2 (Sonnet analyst with tools)**: Uses Claude Agent SDK with `@tool` decorators → `create_sdk_mcp_server()` → `ClaudeAgentOptions` with `mcp_servers` to query live VPS odds (347 PHX vs OKC markets), fetch CLV history from Supabase (132 resolved SGA picks with +1.23% avg CLV), and generate structured pick recommendations
- **SDK cold start**: ~40s startup overhead (acceptable for event-driven pipeline, faster in persistent process)
- **No `ANTHROPIC_API_KEY` needed**: Claude Agent SDK uses Claude Code's own authentication — direct Anthropic API calls from `.env` fail in the Claude Code CLI environment
- **Supabase migration deferred**: `exec_sql` RPC unavailable on this Supabase instance; `pick_writer` gracefully handles missing `news_agent_events` columns by stripping and retrying

## Details

### Architecture

The pipeline has four components:

**1. Odds Fetcher** — queries the live VPS `/api/v1/odds` endpoint (remote URL, not localhost) to get current market data. Verified against live VPS: 347 markets returned for PHX vs OKC, with 8 sharp books and 4 soft books.

**2. Stage 1 — Haiku Classifier** — receives raw injury text (e.g., Shams Charania report: "SGA ruled out for Game 2") and classifies the event type, extracts structured fields (player, team, impact level). This is a lightweight, fast classification step. End-to-end test confirmed: correctly classified injury tweet as `injury_out`, extracted player/team/impact.

**3. Stage 2 — Sonnet Analyst** — a tool-equipped agent built on the Claude Agent SDK's `@tool` pattern. Tools include `fetch_odds` (live market data), `fetch_clv_history` (Supabase resolved picks for the affected player), and `write_pick` (Supabase insertion). The agent reasons about the injury's impact on spreads, totals, and player props, then generates specific betting recommendations with odds, expected edge, and confidence level.

**4. Pick Writer** — persists recommended picks to a `news_agent_events` Supabase table with event metadata (source, classification, player, timestamp) and pick details (market, side, odds, reasoning). Handles missing columns gracefully: if the migration hasn't been run yet, strips the news-specific columns and retries the insert.

### Claude Agent SDK Pattern

The pipeline was refactored from raw Anthropic SDK to Claude Agent SDK, matching the pattern established in `podcast.py`:

```
@tool(name, description, schema) → create_sdk_mcp_server() → pass as mcp_servers in ClaudeAgentOptions → query()
```

Tools accumulate results via closure variables rather than return values. The `ANTHROPIC_API_KEY` is not available in the Claude Code CLI environment — the Agent SDK handles auth through Claude Code's internal credentials at `~/.claude/.credentials.json`. Direct `anthropic.Client()` calls fail.

### Use Case: SGA Ankle Injury

The pipeline was built and tested against a real-world event: Shai Gilgeous-Alexander (ankle) ruled out for Game 2 of OKC vs Phoenix Suns on 2026-04-24. This is a high-impact negative event for the Thunder — SGA is their primary scorer and playmaker. The pipeline classified this correctly and had access to 132 resolved SGA picks showing +1.23% average CLV, providing historical context for the analyst's recommendations.

Key betting implications identified: Phoenix spread/ML value before full line adjustment, OKC total unders (offense drops significantly without SGA), and monitoring for overreaction in both directions.

### Deployment Status

As of 2026-04-24, Stage 1 (Haiku classifier) was tested end-to-end successfully. Stage 2 (Sonnet analyst) was still running at session end. The Supabase migration for `news_agent_events` table was deferred to the SQL editor since `exec_sql` RPC is not available. The VPS odds endpoint was confirmed reachable from local Mac via remote URL.

## Related Concepts

- [[concepts/podcast-pick-extraction-pipeline]] - The podcast pipeline that established the `@tool` + `create_sdk_mcp_server()` + `query()` Claude Agent SDK pattern reused here
- [[concepts/value-betting-theory-system]] - The theory system whose picks the news agent can cross-reference via CLV history
- [[concepts/sharp-clv-theory-ranking]] - CLV history (132 SGA picks, +1.23% avg CLV) provides the analyst with historical edge context per player
- [[concepts/opticodds-critical-dependency]] - Live odds data flows through the VPS endpoint, which depends on OpticOdds for sharp book pricing

## Sources

- [[daily/lcash/2026-04-24.md]] - SGA ruled out for Game 2 vs Phoenix — high-impact injury event (Session 17:51). Full pipeline built: odds fetcher (347 PHX-OKC markets, 8 sharp + 4 soft books), Haiku classifier (correctly classified injury_out), Sonnet analyst with SDK tools (CLV history: 132 SGA picks, +1.23% avg CLV); refactored from Anthropic SDK to Agent SDK matching podcast.py pattern; ~40s cold start; `exec_sql` RPC unavailable; pick_writer handles missing news columns gracefully; VPS only reachable via remote URL not localhost (Session 17:53)
