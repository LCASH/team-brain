---
title: "News Agent Odds Movement Persistence"
aliases: [odds-movement-tracking, compare-snapshots, snapshot-key-bug, odds-movement-jsonb, news-agent-market-movement]
tags: [value-betting, news-pipeline, data-quality, architecture, bug]
sources:
  - "daily/lcash/2026-05-01.md"
created: 2026-05-01
updated: 2026-05-01
---

# News Agent Odds Movement Persistence

The news agent pipeline's `compare_snapshots()` function computed valuable odds movement data (before/after prices and magnitude of line shifts) during Stage 2 analysis but discarded it — the data was held in local variables that were garbage collected after each event. On 2026-05-01, an `odds_movement` JSONB column was added to `news_agent_events` to persist this data for backtesting whether the pipeline correctly predicts market direction. A critical snapshot comparison key bug was simultaneously discovered and fixed: the key `(player, prop, side)` omitted `line`, causing alt-line markets to conflate and report phantom 50+ percentage point movements.

## Key Points

- `sharp_snapshot` (per-pick sharp book odds at pick time) was already persisted to Supabase, but `odds_before`/`odds_after`/`moves` from `compare_snapshots()` were computed in-memory then garbage collected — valuable predictive-edge backtesting data was being thrown away
- Storage approach: one JSONB column on `news_agent_events` (option 2) rather than a separate `news_agent_odds_movements` table — lighter weight, one row per event
- **Snapshot key bug**: key was `(player, prop, side)` without `line` — comparing Over @0.5 against Over @1.5 and reporting 50+ pp shifts; dict assignment silently overwrote alt-line entries
- After line-keyed fix: 130 bogus movements → 0-1 real movements; diagnostic 90s back-to-back comparison showed 307 real book×market movements with 424/426 markets stable
- Code is deployed and gracefully handles the column not existing yet (migration applied same session via Supabase SQL Editor)

## Details

### The Data Loss Problem

The news agent's Stage 2 analysis fetches live odds before and after the Sonnet research agent runs (~7-10 minutes of analysis time). The `compare_snapshots()` function diffs these two snapshots to identify which markets moved during the analysis window — critical data for validating whether the news event actually caused market movement and whether the pipeline's picks were ahead of or behind the movement.

This comparison was computed correctly but stored nowhere. The `odds_before` dict, `odds_after` dict, and `moves` list were local variables in the processing function. After the function returned and the event was stored in Supabase (with `picks_generated` count and `analysis_reasoning` text), the movement data was garbage collected. Every event's market movement data was irretrievably lost.

The `sharp_snapshot` field — capturing the sharp book odds at the moment each individual pick was created — was already persisted by `pick_writer.py`. But this per-pick snapshot is different from the per-event movement data: `sharp_snapshot` tells "what were sharp odds when this pick was made?" while `compare_snapshots()` tells "how did the entire market move during the analysis window?"

### Storage Architecture Decision

Two approaches were considered:

**Option 1 — Separate table (`news_agent_odds_movements`):** One row per market per event, enabling fine-grained querying ("show me all events where Rebounds moved >5pp"). Requires a foreign key to `news_agent_events` and produces many rows per event (100+ markets × every event).

**Option 2 — JSONB column on `news_agent_events` (chosen):** One column per event containing the full movement data as structured JSON. Lighter weight — no join needed, no additional table, single-row reads. Querying specific market movements requires JSONB path operators but the primary use case is per-event review, not cross-event market analysis.

Option 2 was chosen because the immediate need is event-level backtesting ("did markets move as the agent predicted?") rather than cross-event aggregation. The JSONB column stores the top movers and their before/after prices, which is sufficient for validating the pipeline's predictive accuracy.

### The Snapshot Key Bug

The `compare_snapshots()` function built dictionaries keyed by `(player, prop, side)` — omitting `line`. This caused two distinct failure modes:

**Alt-line conflation:** When a player has props at multiple lines (e.g., Rebounds Over 5.5 and Rebounds Over 9.5 on Kalshi), the dict key `("Player", "rebounds", "Over")` maps to both. The second entry silently overwrites the first. If the "before" snapshot happened to capture line 5.5 and the "after" snapshot captured line 9.5 (due to iteration order instability between fetches), the comparison showed a massive phantom movement from the 5.5 odds to the 9.5 odds — completely unrelated to any actual market shift.

**Scale of the problem:** Before the fix, a single event produced 130 "movements" — most of them phantom alt-line conflation artifacts. After adding `line` to the key, the same comparison produced 0-1 real movements. A diagnostic 90-second back-to-back comparison (two snapshots of the same moment) confirmed: 307 real book×market price changes (from normal market microstructure activity), with 424 of 426 unique markets showing zero change. This validated both that the fix eliminated phantom movements and that the remaining movements were genuine.

### Discord Message Enhancement

The odds movement data was also wired into the Discord notification format. Stage 2 pick notifications now include per-pick odds + book name + confidence, plus the top 5 market movers during the analysis window. This gives operators immediate visibility into whether the detected news event actually moved markets — a key validation signal that was previously unavailable without querying Supabase.

### Windows Encoding Crash

During deployment of the odds movement persistence, a `Path.write_text()` crash was discovered on Windows when writing workspace files containing Unicode characters (e.g., `č` in Croatian/Serbian player names like Dončić). Windows defaults `write_text()` to cp1252 encoding, which cannot handle these characters. The fix is to always pass `encoding="utf-8"` to every `write_text` call. This is the same family as the previously documented "Windows cp1252 encoding crashes on Unicode arrows" bug in the bet365 headless detection article.

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The pipeline architecture that the odds movement tracking enhances; the JSONB column is part of the event data model
- [[concepts/news-driven-pre-sharp-ev-thesis]] - The thesis that the pipeline beats sharps to news; odds movement data validates this thesis by measuring whether markets actually moved in the predicted direction after the event
- [[concepts/alt-line-mismatch-poisoned-picks]] - The snapshot key bug (missing `line`) is the same root cause as alt-line interpolation issues: treating different lines as the same market produces phantom signals
- [[connections/silent-type-coercion-data-corruption]] - The snapshot key bug is another instance of plausible wrong output — 130 "movements" looked like a highly responsive market, not a data bug
- [[concepts/sharp-clv-theory-ranking]] - Sharp CLV measures whether picks beat the closing line; odds movement data measures whether the market moved as predicted — complementary validation metrics

## Sources

- [[daily/lcash/2026-05-01.md]] - sharp_snapshot already saved but odds_before/odds_after/moves garbage collected; JSONB column chosen over separate table; snapshot key `(player, prop, side)` missing `line` caused 130 bogus movements from alt-line conflation; after fix 0-1 real movements; 90s diagnostic: 307 real book×market changes, 424/426 stable; Windows cp1252 crash on Path.write_text with Unicode player names; Discord message enhanced with per-pick odds + top 5 movers (Sessions 08:18, 08:53)
