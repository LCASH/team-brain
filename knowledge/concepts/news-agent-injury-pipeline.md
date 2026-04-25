---
title: "News Agent Injury-to-Pick Pipeline"
aliases: [news-agent, injury-pipeline, injury-classification, betting-news-agent, sga-injury-agent, multi-sport-news-agent]
tags: [value-betting, ai-agent, news, injury, pipeline, claude-sdk, twitter, mlb, nba]
sources:
  - "daily/lcash/2026-04-24.md"
  - "daily/lcash/2026-04-25.md"
created: 2026-04-24
updated: 2026-04-25
---

# News Agent Injury-to-Pick Pipeline

A multi-sport AI pipeline for the value betting scanner that scrapes Twitter/X for injury tweets, classifies them, and generates conviction-based betting picks using full sportsbook odds. Stage 1 uses Haiku for binary gate classification (injury, trade, lineup change). Stage 2 uses Sonnet analyst with pre-computed full odds workspace (~48KB/game) to reason about which markets will shift. On 2026-04-25, the pipeline was significantly overhauled: EV validation gate removed (picks based on conviction, not current EV — see [[concepts/news-driven-pre-sharp-ev-thesis]]), expanded from NBA-only to NBA + MLB (22 Twitter sources), deployed to Dell mini PC for residential IP advantage, and wired to Supabase dashboard for source management.

## Key Points

- **Stage 1 (Haiku classifier)**: Pure binary gate — "worth analyzing?" + extract sport/team/player/event_type; no impact scoring (Stage 2 handles that)
- **Stage 2 (Sonnet analyst)**: Receives pre-computed full sportsbook odds workspace (~48KB/game, 764 lines) with ALL odds grouped by player; 600s timeout (300s too tight for 100KB workspace + web searches)
- **EV gate removed**: Agent picks based on conviction, not current sharp EV. A -3% EV pick is valid if agent explains it's "ahead of the market." Resolver validates over time via CLV.
- **Multi-sport**: NBA (10 insiders) + MLB (12 national insiders + beat writers); live mode auto-detects sport from tweet source
- **22 Twitter sources**: Shams, Haynes, FantasyLabs (NBA); Passan, Rosenthal, Feinsand, MLBTradeRumors (MLB); account enable/disable via Supabase dashboard toggle
- **Deployed to mini PC** (`Bowler014` / `100.67.233.95`): residential IP less likely to be flagged by Twitter; Claude CLI authenticated via npm global install
- Every pick stores `news_source`, `agent_id`, `ai_reasoning`, `ai_impact_chain` for multi-agent A/B testing

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

### Multi-Sport Expansion (2026-04-25)

On 2026-04-25, the pipeline was extended from NBA-only to NBA + MLB:

- **MLB team resolution**: 30 MLB teams hardcoded for sport-aware classifier
- **MLB event types**: `scratched`, `il_placement`, `pitching_change`, `injury_out`, `injury_questionable`
- **Sport auto-detection**: Live mode determines sport from tweet source — Passan/Rosenthal → MLB pipeline, Shams/Haynes → NBA pipeline
- **Same architecture**: No separate MLB/NBA codepaths; sport parameter threads through classifier → odds → workspace → analysis

The Twitter source list expanded from 10 NBA accounts to 22 total (10 NBA + 12 MLB). MLB insiders include Jeff Passan, Ken Rosenthal, Mark Feinsand, Jon Heyman, Bob Nightengale, and MLB Trade Rumors. However, lcash discovered that MLB injury news is primarily broken by **team beat writers** (DiComo, Matheson, Sharma), not national insiders — see [[connections/sport-specific-news-intelligence-architecture]]. A beat writer crawl job is planned to build per-team source lists.

### Pipeline Overhaul (2026-04-25)

Seven flaws were identified and fixed:

1. **EV mismatch**: Workspace EV computation differed from pick_writer's; resolved by pre-computing ALL EV in workspace using Pinnacle devig
2. **EV validation gate removed**: Core thesis is "beating sharps to news" — current -EV is expected and valid
3. **Hardcoded CLI path**: Fixed with `shutil.which("claude")`; Windows mini PC path: `C:\Users\Dell\AppData\Roaming\npm\claude.CMD`
4. **Fake freshness check**: `freshness.py` was redundant since Claude Code session can web search during Stage 2 analysis — killed
5. **Fragile output parsing**: Agent instructions didn't request `ev_pct` output, so `triggered_ev` was always 0 — instructions must explicitly request every field
6. **Double-prefix bug**: `agent_id` already contains `news_` so `triggered_by` became `news_news_v1_injury_out` — fixed
7. **Workspace too large**: 90KB → 48KB trimming fixed Sonnet 300s timeout; increased to 600s for safety

### Mini PC Deployment (2026-04-25)

The news agent was deployed to the Dell mini PC (`Bowler014` via Tailscale at `100.67.233.95`) for residential IP advantage — same reasoning as bet365 scraping (datacenter VPS IPs get flagged by Twitter). Deployment required:

- Node.js installed via portable extraction (MSI/RunAs don't work over SSH on Windows)
- Claude Code CLI installed via `npm install -g @anthropic-ai/claude-code`
- Claude CLI authenticated via interactive OAuth on the mini PC (required in-person access — delegated via `MINI_PC_SETUP.md`)
- `curl_cffi` installed for Twitter scraping (Akamai-like anti-bot on X.com)
- Scraper wired to read enabled accounts from Supabase (dashboard toggle) instead of hardcoded config

The dashboard Sources tab (`news.html`) provides account management: add/remove accounts, tier toggle (T1/T2), enable/disable individual sources. The `030_twitter_accounts.sql` migration seeds 9 accounts (6 T1, 3 T2).

### Deployment Status

As of 2026-04-25, the news agent is deployed on the mini PC with all 22 Twitter accounts **disabled** — waiting for MLB validation before enabling. The live mode command is: `python3 scripts/news_agent_run.py --live --vps http://170.64.213.223:8802`. Each event costs ~$0.65 (Sonnet), ~3-4 min per event. The Supabase migration `029_news_agent.sql` was run successfully.

## Related Concepts

- [[concepts/news-driven-pre-sharp-ev-thesis]] - The strategic thesis that the news agent implements: beating sharps to news, conviction-based picks validated retroactively by CLV
- [[concepts/twitter-x-api-scraping-constraints]] - Twitter/X API rate limits and anti-bot defenses constraining the scraping architecture
- [[connections/sport-specific-news-intelligence-architecture]] - NBA vs MLB news sourcing hierarchies requiring different source strategies
- [[concepts/podcast-pick-extraction-pipeline]] - The podcast pipeline that established the `@tool` + `create_sdk_mcp_server()` + `query()` Claude Agent SDK pattern reused here
- [[concepts/value-betting-theory-system]] - The theory system whose picks the news agent can cross-reference via CLV history
- [[concepts/sharp-clv-theory-ranking]] - CLV history (132 SGA picks, +1.23% avg CLV) provides the analyst with historical edge context per player
- [[concepts/opticodds-critical-dependency]] - Live odds data flows through the VPS endpoint, which depends on OpticOdds for sharp book pricing

## Sources

- [[daily/lcash/2026-04-24.md]] - SGA ruled out for Game 2 vs Phoenix — high-impact injury event (Session 17:51). Full pipeline built: odds fetcher (347 PHX-OKC markets, 8 sharp + 4 soft books), Haiku classifier (correctly classified injury_out), Sonnet analyst with SDK tools (CLV history: 132 SGA picks, +1.23% avg CLV); refactored from Anthropic SDK to Agent SDK matching podcast.py pattern; ~40s cold start; `exec_sql` RPC unavailable; pick_writer handles missing news columns gracefully; VPS only reachable via remote URL not localhost (Session 17:53)
- [[daily/lcash/2026-04-25.md]] - Major pipeline overhaul: EV validation gate removed (thesis: beating sharps to news, not reacting to current EV); 7 flaws identified and fixed; workspace trimmed 90KB→48KB fixing Sonnet timeout; timeout increased 300s→600s; Stage 1 reduced to pure binary gate; full sportsbook odds workspace pre-computed with Pinnacle devig (Sessions 08:32, 09:08). Multi-sport expansion: MLB support added (30 teams, sport-aware classifier, MLB event types); 22 Twitter sources (10 NBA + 12 MLB); live mode auto-detects sport from source; national insiders first, beat writers planned (Session 14:48). Mini PC deployment: residential IP advantage; Node.js portable install; Claude CLI authenticated; curl_cffi installed; scraper reads enabled accounts from Supabase; `030_twitter_accounts.sql` migration with 9 seed accounts; all accounts disabled pending MLB validation (Sessions 10:46, 11:55, 12:26, 14:15, 15:43). Jalen Williams (OKC) ruled out Game 3, KD (Rockets) questionable Game 3 — live injury events processed (Sessions 08:41, 08:50). MLB beat writer hierarchy: DiComo (Mets), Matheson (Blue Jays), Sharma (Cubs) break news before national insiders; beat writer crawl job planned (Sessions 16:16, 20:45)
