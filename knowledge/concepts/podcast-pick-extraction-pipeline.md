---
title: "Podcast Pick Extraction Pipeline"
aliases: [newsbets, podcast-picks, youtube-transcript-extraction, podcast-backtesting, mlb-podcast-pipeline, nba-podcast-pipeline]
tags: [value-betting, podcast, extraction, backtesting, mlb, nba, pipeline]
sources:
  - "daily/lcash/2026-04-22.md"
  - "daily/lcash/2026-04-23.md"
created: 2026-04-22
updated: 2026-04-23
---

# Podcast Pick Extraction Pipeline

A multi-sport system for extracting structured betting picks from YouTube podcast transcripts, resolving outcomes against sports stats APIs, and backtesting profitability. The pipeline uses `yt-dlp` for transcript fetching (no API keys), Claude Agent SDK `query()` for LLM-based extraction with tool-use, and a 4-table Supabase data model. Expanded from MLB-only to NBA on 2026-04-23 with Action Network as a new source. Full dataset: **3,899 picks across 12 shows and 2 sports, 2,639 resolved**. MLB remains breakeven (-1.7% ROI); NBA varies dramatically by show: Action Network +58.6% (moneyline-skewed), JuiceBox -5.6% (only player prop overs profitable).

## Key Points

- `yt-dlp` fetches YouTube auto-captions (VTT format) without API keys; strict pattern matching requires subject + prop + side + line co-occurrence to filter noise from conversational transcripts
- Claude Agent SDK `query()` with tool-based extraction (`record_pick` tool) produces structured JSON; `ClaudeSDKClient` class does NOT work — use `query()` directly
- Sonnet is 8x faster than Haiku for extraction (~16s vs ~124s/episode) because Agent SDK CLI startup overhead dominates per-token savings; same accuracy, lower total cost despite higher per-token price
- **Critical finding:** Prop type misclassification (HRR classified as Home Runs) completely inverted backtest results — 43.5% WR / -15.2% ROI became 58.8% WR / +15.4% ROI after fixing. Extraction accuracy is the #1 variable
- Podcast confidence signals are **inverted**: "best bets" (80-100 confidence) produce -9.2% ROI; host enthusiasm correlates with long-shot props that lose more
- Full backtest: 810 episodes, 2,650 picks, 2,104 graded → 51.0% WR, -1.7% ROI (breakeven); profitable niches: team totals over (+35.7%), strikeouts (+12.3%), game unders

## Details

### Architecture

The pipeline has four phases:

**Phase 1 — Fetch:** `yt-dlp` downloads auto-generated VTT captions from YouTube. The VTT parser strips timestamps and deduplicates overlapping subtitle segments, producing clean text (~46K chars for a typical 30-min episode). YouTube dynamic rendering blocks Playwright selectors for video list scraping, making `yt-dlp` the only reliable transcript path. Channel handle format matters: `@Wagertalk` works, `@WagerTalkTV` does not.

**Phase 2 — Extract:** The Claude Agent SDK's `query()` function (NOT `ClaudeSDKClient`) processes transcripts with a sport-config-driven prompt (`build_extraction_prompt("mlb")`) containing per-sport prop vocabulary, example picks, and extraction rules. The agent uses a `record_pick` tool to output structured JSON with player names, prop types, lines, odds, confidence scores, and host attribution. The `ANTHROPIC_API_KEY` is not available in the Claude Code CLI environment — the Agent SDK uses Claude Code's internal auth, so direct Anthropic API calls fail.

**Phase 3 — Resolve:** The MLB Stats API provides box score data for grading. Fuzzy player name matching handles auto-caption mangling: exact match → strip suffix → last name only → first initial + last name. Known failure modes include garbled names (no match → skip), doubleheaders (wrong game selected), and ambiguous last names.

**Phase 4 — Report:** A dashboard at `http://170.64.213.223:8802/podcasts.html` shows per-show, per-prop-type, per-host, and per-confidence breakdowns with ROI calculations using odds-weighted profit and decimal odds conversion (`_to_decimal_odds` helper). The ROI calculation was upgraded from simple even-money `(w-l)/n` to odds-weighted profit using real decimal odds (assumes -110 when odds are unavailable) — the old calculation overstated a +25.6% episode as +33.3%. Dashboard features include expandable quote rows, Prop x Side breakdown (Over vs Under per prop type), and Avg Odds columns across all breakdown tables.

### Data Model

Four Supabase tables with `pick_hash` (subject+prop+side+line+game_date) for cross-episode deduplication:

| Table | Purpose |
|-------|---------|
| `sources` | Podcast channels (WagerTalk, JuiceBox, etc.) |
| `episodes` | Individual episodes with YouTube IDs, transcripts, extraction status |
| `picks_extracted` | Structured picks with player, prop, line, odds, confidence, host |
| `pick_mentions` | Cross-references: same pick mentioned across multiple episodes |

### Sport-Agnostic Design

The extraction prompt is generated from a sport config dict — adding NBA/NFL requires only a new config entry with sport-specific prop vocabulary, resolution API, and channel list. The game_date is derived from transcript context by the extraction agent (not from `published_at` or title parsing), because podcast publish dates are unreliable and one episode can span multiple game days. This was identified as the most critical flaw in the initial design — 10 critical flaws were documented including name mangling, no host attribution, "preview picks" wrong-date problem, and doubleheader ambiguity.

### Backtest Results

**Overall (810 episodes, 2,104 graded):** 51.0% WR, -1.7% ROI — following podcast picks blindly loses money or at best breaks even.

**By prop type:**

| Prop Type | ROI | WR | Assessment |
|-----------|-----|----|------------|
| Team Totals | **+35.7%** | — | Profitable niche |
| Strikeouts | **+12.3%** | — | Profitable niche |
| Earned Runs Over | **+55.0%** | — | Strong but small sample |
| Moneyline | **+5.0%** | — | Marginal |
| Home Runs | **-80.3%** | 10.3% | Likely still has misclassification issues |
| Total Bases | **-60.5%** | — | Catastrophic |
| Game Totals | **-13.2%** | — | Losing |

**By show:** JuiceBox MLB was the only show with positive ROI — initial analysis showed +9.6% on 98 picks, updated to **+10.5% ROI on 139 picks (59.7% WR)** after full extraction. JuiceBox's edge is in moneylines and strikeout overs; run lines are a weakness; counterintuitively, "leans" outperform "best bets" (+26.2% vs lower ROI). Total Bases and Drew's Daily Diamond were near breakeven. MLB Gambling Podcast was the biggest loser (-18.6%).

**By confidence:** Confidence signals don't help. "Best bets" (80-100) still -9.2% ROI. This is because hosts like Prop Hitters label long-shot HR/total bases plays as "best bets" due to big potential payouts — but these props lose at high rates. Leans and speculative picks are worse (-18.6% to -64.1%).

### Data Quality Issues

Three resolution bugs were found and fixed during backtesting:

1. **Game total resolution:** `_resolve_game_total` was partial-matching one team's runs instead of summing both teams' scores. This made losses look like wins, inflating ROI by ~14 percentage points (initial -11.6% was really -35.9% before the fix).
2. **F5 (First 5 Innings) picks:** 136 F5 picks were being graded against full-game stats — a fundamental mismatch. All F5 picks were voided since partial-game box score data isn't available.
3. **HRR misclassification:** "Hits, Runs, RBIs" props were classified as Home Runs by the extractor. Fixing this single classification flipped Prop Hitters' ROI from -59.9% to +10.9%.

The 31% unresolved rate (299 picks) stems from auto-caption name mangling and missing player matches. YouTube auto-captions produce player name errors that vary each time — "Kahana wits" for Khanawitz, "Stallings Stewart" for unknown players.

### Supabase Deployment Gotchas

Two Supabase platform issues were discovered during dashboard deployment:

1. **PostgREST 1000-row pagination cap:** Supabase's PostgREST silently caps results at 1,000 rows even when `limit=5000` is passed. The dashboard initially showed only ~131 picks instead of 2,650 because the default "Last 14 days" filter combined with the 1,000-row cap hid most data. The fix requires client-side pagination — fetching in 1,000-row pages and concatenating results.

2. **Row Level Security (RLS) blocks anon key reads:** Supabase RLS blocks the `anon` key from reading tables by default. The `podcast_picks` and `podcast_episodes` tables needed explicit `FOR SELECT USING (true)` policies for the public dashboard to function. Without these policies, queries return empty results with no error message — a silent failure pattern consistent with the scanner's broader operational anti-patterns.

The full pipeline was committed as `6533340` (+4,155 lines, 10 files) with CLAUDE.md updated to include podcast pipeline architecture documentation.

### Scaling and Performance

- **Extraction speed:** ~16s/episode with Sonnet (Agent SDK CLI startup ~10s + generation ~6s), ~2 hours for 811 episodes with parallel batches of 20
- **Transcript fetching:** ~4s per transcript, sequential per show
- **Total pipeline:** ~3 hours for full 2025 season (fetch + extract + resolve) across 8 shows
- **66% odds extraction rate:** 85/128 picks had extractable odds from transcripts; auto-captions sometimes lose numeric values

### Podcast Sources

8 of 9 recommended MLB betting podcasts were included:

| Show | Source | Focus |
|------|--------|-------|
| Total Bases | WagerTalk | Game-level picks (ML, totals, run lines) |
| Drew's Daily Diamond | WagerTalk | Daily best bets (season record: 23-16, +6.5u) |
| Prop Hitters | WagerTalk | Player props (hits, HRs, total bases, K's) |
| Under the Radar | WagerTalk | Contrarian/underdog picks |
| MLB Double Picks | WagerTalk | Quick-fire daily selections |
| JuiceBox | JuiceBox MLB | Daily best bets with props in titles |
| Baseball Betting Show | Greg Peterson | Analysis-heavy game picks |
| Beating The Book | Gill Alexander | Line analysis |

"On Deck" (DFS CheatSheet) was excluded — too DFS-lineup focused for explicit betting pick extraction.

### NBA Expansion (2026-04-23)

On 2026-04-23, the pipeline was expanded to NBA with two shows: JuiceBox NBA and Action Network (86 NBA + 17 MLB episodes, fetched via `yt-dlp --dump-json --skip-download` since `--flat-playlist` doesn't return upload dates for streams). The sport-agnostic design proved out — adding NBA required only a new config entry with NBA-specific prop vocabulary and resolution API.

**JuiceBox NBA results (121 picks, 50.4% WR, -5.6% ROI, -6.7 units):** Not profitable overall unlike their MLB (+10.5% ROI). Profitable niche: **player prop overs at 80+ confidence** (~40 picks, projected +10-15% ROI). PRA +29%, rebounds +100% WR, points +1.1%. Spreads catastrophic at 29.6% WR / -43.4% ROI / -11.7 units. Game totals also terrible at -68.2%.

**Action Network NBA results (325 picks, +58.6% ROI):** Headline-grabbing but moneyline-skewed — +203% ROI on 73 moneyline picks from underdog wins. Player props genuinely profitable at **+16-17% ROI on 200+ picks**, making Action Network sharper at scale on NBA props than JuiceBox (+3% vs +17%).

**Action Network MLB (mediocre, -7.5% ROI):** Action Network's NBA strength does not transfer to MLB.

### New Tipster Source: Derek Carty / Unabated

Derek Carty (@UnabatedLive "The Bat: MLB Player Props" + @CoversSports "THE BAT X Release Show") was identified and fetch started. Key distinction: model-driven (THE BAT projection system) rather than gut feel — potentially better calibrated than conversational podcast picks. Results pending extraction and resolution.

### Updated Dataset Totals

| Metric | Value |
|--------|-------|
| Total picks | **3,899** |
| Resolved | **2,639** |
| Shows | **12** |
| Sports | **2** (MLB, NBA) |
| Episodes | **~920** (810 MLB + 104 Action Network + JuiceBox NBA) |

### Dashboard UX Improvements (2026-04-23)

- Default date range changed from "Last 14 days" to **"All time"** to avoid data visibility confusion
- Date range change **auto-reloads data** (no manual "Load Results" click needed)
- Replaced dropdown date ranges with **calendar date pickers** (From/To) plus quick-range dropdown for flexible timeframe analysis (e.g., single MLB season: March 27 – October 26, 2025)

### Extraction Methodology Refinements (2026-04-23)

Several extraction judgment calls were codified during NBA transcript processing:

- **Star ratings → confidence**: 3-star → 90, 2-star → 80, 1-star → 65, parlay components → 40
- **Odds source priority**: When host quotes one number but DraftKings/book price is given, use the verifiable book price
- **Attribution filtering**: Guest picks excluded from output — only host picks counted
- **Previously placed vs current**: Hosts reference past bets during recaps; only current recommendations extracted
- **Segment confidence**: "Plant the Flag" segments → 90 confidence; "best bets" → 80; softer mentions → 65
- **Missing odds**: Leave null rather than guess (e.g., "Mariners AL West at plus money")

### Batch Extraction Reliability

NBA batch extraction hit many CLI timeout errors ("Control request timeout: initialize") from parallelism, but episodes still processed — errors are noisy but not fatal. This is consistent with the Agent SDK CLI startup overhead issue documented for MLB extraction.

## Related Concepts

- [[concepts/value-betting-theory-system]] - The scanner's theory system that podcast picks could theoretically be cross-referenced against for EV validation
- [[concepts/opticodds-critical-dependency]] - OpticOdds could provide odds verification for extracted picks, enabling EV computation on podcast recommendations
- [[concepts/betting-window-roi-methodology]] - The ROI methodology (closing odds, dedup) applied to podcast backtest with decimal odds conversion
- [[connections/silent-type-coercion-data-corruption]] - HRR misclassification follows the same pattern: plausible wrong output from extraction errors with zero error signal

## Sources

- [[daily/lcash/2026-04-23.md]] - NBA expansion: JuiceBox NBA 121 picks, -5.6% ROI (spreads -43.4%, player prop overs profitable); Action Network 104 episodes fetched via yt-dlp --dump-json, 325 NBA picks +58.6% ROI (ML-skewed, props +16-17%); Action Network MLB -7.5%; Derek Carty/Unabated identified as model-driven tipster; full dataset 3,899 picks / 2,639 resolved / 12 shows / 2 sports (Sessions 09:30, 11:17). Dashboard UX: "All time" default, auto-reload on date change, calendar date pickers (Session 11:17). Extraction methodology: star rating mapping, DK price priority, guest exclusion, segment confidence inference, null odds preference (Sessions 09:50, 10:01, 10:06)
- [[daily/lcash/2026-04-22.md]] - Full pipeline design: 4-table data model, yt-dlp for YouTube captions, Claude Agent SDK `query()` for extraction (not ClaudeSDKClient), strict pattern matching, confidence scoring from language cues (Sessions 08:59, 09:55). Sonnet 8x faster than Haiku due to CLI startup overhead; HRR misclassification inverted backtest; game_date from transcript context not published_at; parallel batch extraction 7x faster than serial (Session 13:20). 10 critical pipeline flaws identified and sport-agnostic redesign with `build_extraction_prompt("mlb")` (Session 13:20). Full year backtest: 810 episodes, 2,650 picks, 2,104 graded → 51.0% WR, -1.7% ROI; team totals +35.7%, strikeouts +12.3%; confidence inverted; game total resolution bug inflated ROI by 14 points; F5 picks voided; JuiceBox only profitable show (+9.6%); dashboard deployed (Sessions 16:59, 17:33, 19:51). Dashboard iteration: Supabase PostgREST 1000-row cap required client-side pagination; RLS blocked anon key reads (explicit SELECT policies needed); JuiceBox updated to 139 picks / 59.7% WR / +10.5% ROI with moneylines and K overs as edge, "leans" outperform "best bets" (+26.2%); ROI switched from even-money to odds-weighted decimal odds; committed as `6533340` (+4,155 lines, 10 files) (Session 20:22)
