---
title: "Odds Staleness Pipeline Diagnosis"
aliases: [source-captured-at, odds-drift, staleness-causes, layer-a-diagnostic, odds-age]
tags: [value-betting, data-quality, latency, dashboard, diagnosis]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# Odds Staleness Pipeline Diagnosis

A systematic investigation into why bet365 odds displayed on the VPS dashboard didn't match live bet365 odds at the time of bet placement. Six distinct causes of odds drift were identified, and a diagnostic approach ("Layer A") was designed — plumbing `source_captured_at` timestamps end-to-end from scraper parse-time through the entire pipeline to the dashboard. The diagnostic work was initially reverted in favor of a WS-only strategy, then recommended for reinstatement after the WS probe proved NBA prop streaming non-viable.

## Key Points

- Six distinct causes identified: snapshot lag (5–65s pipeline), scraper missed updates, different bet365 surfaces (BB wizard vs Match tab), book 365 vs 366 disagreement, account-specific pricing, and SSE ghost markets
- `source_captured_at` plumbs the scraper's parse-time timestamp end-to-end: scraper → worker → server ingest → state → SSE → dashboard, using ratchet-only logic (never moves backwards)
- The existing `captured_at` field was re-stamped with `now()` at each pipeline layer (worker, server ingest, VPS relay), hiding true scraper-to-display latency
- Color-coded odds age on dashboard: green ≤30s, yellow ≤90s, orange ≤180s, red >180s — only shown for bet365 rows
- `datetime.utcnow()` produces naive datetimes whose `.timestamp()` method assumes local timezone — a latent bug fixed by switching to `datetime.now(timezone.utc)`
- The 30s hash-skip blackout in `server/main.py` adds up to 30s of unnecessary staleness — identified as the single biggest quick-win to remove

## Details

### The Problem

Users reported that bet365 odds displayed on the dashboard didn't match what bet365 actually showed when they went to place a bet. This could mean the scanner was finding phantom +EV that didn't exist at bet time — a serious reliability issue for a system whose value proposition depends on odds accuracy.

Initial investigation revealed two distinct issues. First, "stale picks showing" on the dashboard was partly a display issue: games already tipped off were still showing because picks await resolver grading. This can be fixed with a `game_start > now()` filter. Second, actual data freshness problems — the scraped odds were genuinely stale relative to bet365's live prices.

### Six Causes of Odds Drift

Systematic analysis identified six independent mechanisms that cause the dashboard to show stale or mismatched bet365 odds:

1. **Snapshot lag (5–65s)**: The scraping → ingest → push → VPS pipeline introduces 5–65 seconds of latency depending on sport server serialization time and push cycle timing. Even with the snapshot cache fix (see [[concepts/server-side-snapshot-cache]]), the minimum lag is the scraper's refresh interval plus push cycle time.

2. **Scraper missed updates**: The HTTP-polling scraper fetches odds on an interval. If bet365 changes a line between polls, the update is missed until the next poll cycle. High-frequency line movements on popular markets may produce consistent lag.

3. **Different bet365 surfaces**: bet365 displays odds differently depending on which page surface is viewed. The BB wizard (same-game multi builder) and the Match tab show slightly different odds for the same market. The scraper fetches from BB wizard; the user may be viewing the Match tab.

4. **Book 365 vs 366 disagreement**: The legacy book_id coexistence (Betstamp emitting 365, game scraper emitting 366) can produce disagreements when both sources report the same market at slightly different times. See [[concepts/betstamp-bet365-scraper-migration]].

5. **Account-specific pricing**: bet365 may show different odds to different accounts based on betting history, account age, or jurisdiction. The scraper's account may see different lines than the user's account.

6. **SSE ghost markets**: The SSE (Server-Sent Events) delta protocol merges new markets into the dashboard but never deletes old ones. When a market disappears from bet365 (e.g., a prop is pulled), the dashboard continues showing the last known odds until the full polling fallback runs. Long-lived dashboard tabs accumulate ghost markets over time.

### The source_captured_at Approach

The diagnostic fix ("Layer A") instruments the pipeline with a `source_captured_at` field that represents when the scraper actually parsed the odds from the bet365 page — the true observation time. This is distinct from `captured_at`, which was being re-stamped with `now()` at each pipeline stage (worker, server ingest, VPS relay), making it measure when the VPS received the data rather than when it was observed.

The `source_captured_at` field uses ratchet-only logic: if a new ingest produces an older timestamp than the one already stored, the field is not updated. This prevents stale data from overwriting a fresher timestamp during out-of-order processing.

On the dashboard, odds age is color-coded: green (≤30s, fresh), yellow (≤90s, slightly stale), orange (≤180s, caution), red (>180s, likely stale). This gives users immediate visual feedback about whether to trust the displayed odds before placing a bet. The age display is only shown for bet365 rows; OpticOdds rows don't have `source_captured_at` yet and display blank.

### The Revert-Reinstate Narrative

Layer A was implemented across 4+ files but then reverted in the same day (2026-04-15) when lcash decided to commit fully to WebSocket streaming as the sole bet365 architecture. The reasoning was sound: if WS provides sub-second live odds, diagnosing HTTP polling staleness is pointless.

However, the WS probe (see [[concepts/bet365-ws-topic-authorization]]) discovered that NBA prop streaming via WS is not viable due to session-bound topic authorization. WS only works for main markets (spread/total/moneyline), not player props. This meant HTTP polling remains the production path for prop data, and Layer A's diagnostic approach is needed after all.

The recommended reinstatement includes Layer A plus four HTTP-poll optimizations: reduce `_REFRESH_INTERVAL` from 15s to 8s, kill the 30s hash-skip blackout, parallelize per-game fetching, and add a coupon endpoint as a dual-capture data source (see [[concepts/bet365-nba-coupon-endpoint]]). The coupon endpoint provides 5-15s of additional freshness improvement by catching cache invalidations at offset moments from the BB wizard endpoint. Expected improvement: 15–65s lag reduced to ~5–10s.

By end of day, the Layer A reinstatement and all four optimizations were organized into a three-commit feature branch (`bet365-nba-coupon-endpoint`), awaiting deployment.

### Additional Staleness Observations

bet365 continues serving pre-game-style lines on some markets after tipoff (bet-builder props, stale cache), so the scanner keeps ingesting them as if they're valid. This is a bet365-side quirk, not a scanner bug, but it contributes to confusion when tipped-off games show "fresh" odds.

The 30s hash-skip blackout in `server/main.py` was identified as the single biggest quick-win: it adds up to 30 seconds of unnecessary staleness by skipping data ingests when the hash hasn't changed, even if the underlying odds have shifted. Removing this alone would meaningfully improve freshness.

### The datetime.utcnow() Bug

A latent timezone bug was discovered during implementation: `datetime.utcnow()` returns a naive datetime (no timezone info). When `.timestamp()` is called on a naive datetime, Python assumes it's in the local timezone, not UTC. On a server in AEST (UTC+10), this produces timestamps 10 hours off. The fix is `datetime.now(timezone.utc)`, which returns a timezone-aware datetime whose `.timestamp()` correctly converts to Unix epoch.

## Related Concepts

- [[concepts/server-side-snapshot-cache]] - The push cycle optimization that reduced one component of snapshot lag
- [[concepts/bet365-ws-topic-authorization]] - The WS probe finding that forced reinstatement of HTTP-poll optimization
- [[concepts/betstamp-bet365-scraper-migration]] - Book 365 vs 366 disagreement as a staleness cause
- [[connections/push-latency-trail-quality-cascade]] - A related cascade where pipeline latency degraded data quality
- [[concepts/value-betting-operational-assessment]] - The broader operational assessment context
- [[concepts/bet365-nba-coupon-endpoint]] - The dual-capture optimization built as part of the HTTP-poll reinstatement

## Sources

- [[daily/lcash/2026-04-15.md]] - 6 causes of odds drift identified; `source_captured_at` end-to-end plumbing with ratchet-only logic; `datetime.utcnow()` tz bug; `captured_at` re-stamped at each layer; 30s hash-skip as biggest quick-win; SSE ghost markets; Layer A reverted for WS commitment then recommended for reinstatement after WS probe; color-coded age display; Layer A + coupon endpoint dual-capture organized into 3-commit feature branch awaiting deploy (Sessions 13:06, 13:38, 14:17, 16:20, 22:36)
