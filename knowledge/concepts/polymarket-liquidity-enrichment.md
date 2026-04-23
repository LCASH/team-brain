---
title: "Polymarket Liquidity Enrichment"
aliases: [polymarket-api, polymarket-liquidity, prediction-market-liquidity, poly-enrichment, clob-api]
tags: [value-betting, polymarket, prediction-markets, liquidity, data-enrichment]
sources:
  - "daily/lcash/2026-04-23.md"
created: 2026-04-23
updated: 2026-04-23
---

# Polymarket Liquidity Enrichment

OpticOdds does not expose liquidity or volume data — it is purely a price aggregator. Polymarket's public CLOB (Central Limit Order Book) API provides rich liquidity metadata: `liquidity`, `volume24hr`, `volume1wk`, `volume1mo`, `orderMinSize`, and top-of-book `best_bid`/`best_ask`. This data is now captured at pick creation time in the value betting tracker, enabling future analysis of whether liquidity correlates with edge reliability. Additionally, creating NBA Pinnacle and NBA Crypto Edge theories in Supabase immediately generated **20 new NBA picks** that were previously invisible due to missing SOFT_IDS.

## Key Points

- OpticOdds API does NOT expose liquidity/volume — it's purely a price aggregator; Polymarket CLOB API is the only source for market depth data
- Polymarket CLOB API is public, no auth required; provides `liquidity`, `volume24hr`, `volume1wk`, `volume1mo`, `best_bid`, `best_ask`, `orderMinSize`, and `condition_id`
- Polymarket game-level markets have real volume ($4M-$13M) but individual player prop liquidity varies wildly ($2 to $228k) — very high EV picks (87%, 65%) likely indicate thin liquidity, not real edge
- **95% match rate** (57/60 props) between Polymarket CLOB data and the scanner's market keys; all 3 misses were name suffix issues (`Wendell Carter Jr` → `Jr` stripped by normalizer) — one-liner regex fix gets 100%
- NBA was missing from Pinnacle/Crypto Edge theories — creating them instantly generated **20 new NBA picks** that were completely invisible before
- Six new columns added to `nba_tracked_picks`: `poly_liquidity`, `poly_volume_24h`, `poly_volume_1wk`, `poly_best_bid`, `poly_best_ask`, `poly_condition_id`
- Enrichment is forward-only (no backfill of existing picks); columns are nullable so tracker degrades gracefully if migration hasn't been applied

## Details

### The Liquidity Gap

The value betting scanner uses OpticOdds for odds data across all bookmakers including prediction markets (Kalshi, Polymarket). While OpticOdds provides comprehensive price coverage, it functions purely as a price aggregator — it does not expose any market microstructure data such as liquidity pools, trading volume, order book depth, or bid-ask spreads. This means the scanner can identify +EV opportunities against prediction markets but cannot assess whether those opportunities are realistically executable.

Very high EV picks (87%, 65%) from prediction markets likely indicate thin liquidity rather than genuine edge. A market with $2 of liquidity showing +87% EV is not a real betting opportunity — the price would move against the bettor on any meaningful stake. Without liquidity data, the scanner cannot distinguish between genuine edges in liquid markets and phantom edges in illiquid ones.

### Polymarket CLOB API Integration

Polymarket operates a CLOB (Central Limit Order Book) model where individual orders create a visible order book. The CLOB API exposes this data publicly without authentication:

| Field | Description | Example |
|-------|-------------|---------|
| `liquidity` | Total market liquidity pool | $254,000 |
| `volume24hr` | 24-hour trading volume | $45,000 |
| `volume1wk` | 7-day trading volume | $180,000 |
| `volume1mo` | 30-day trading volume | $500,000 |
| `best_bid` | Top bid price | 0.42 |
| `best_ask` | Top ask price | 0.58 |
| `orderMinSize` | Minimum order size | $1 |
| `condition_id` | Polymarket's internal market ID | `0x1a2b...` |

The fetcher uses 3-letter lowercase team codes in Polymarket's slug format to match props. For example, Cade Cunningham Rebounds Over 5.5 maps to a Polymarket slug containing `det` (Detroit) and `rebounds`. Testing confirmed 30 props matched successfully with accurate liquidity data returned.

### Market Key Matching

Polymarket's CLOB API uses structured naming (`"Player: Prop O/U Line"`) that regex-parses cleanly to the scanner's market keys. The 95% match rate (57/60) on initial testing indicates strong alignment. The 3 mismatches were all player name suffix issues — the scanner's normalizer strips suffixes like `Jr`, `Sr`, `III`, `II`, `IV` while Polymarket includes them. A one-liner regex normalization fix resolves this to 100%.

### NBA SOFT_IDS Discovery

During the Polymarket investigation, lcash discovered that prediction market book IDs (950 for Kalshi, 970 for Polymarket) were missing from the NBA dashboard's `SOFT_IDS` configuration. This meant ~600+ NBA markets with Polymarket/Kalshi odds were completely ignored by the dashboard's EV computation. This is a recurrence of the same SOFT_IDS gap pattern documented in [[concepts/trail-capture-soft-ids-gap]] — hardcoded book ID sets that silently exclude new book types.

Creating **NBA Pinnacle** and **NBA Crypto Edge** theory rows in Supabase (with Polymarket/Kalshi as soft books) instantly generated 20 new NBA picks. MLB and NHL already had Pinnacle/Crypto Edge theories; NBA was the gap. The prediction market books should remain as **soft books** (bet targets), NOT added to sharp weights for true-line computation — their thin liquidity makes them unreliable as sharp signal.

### Tracker Integration

The enrichment is wired into `tracker.py` at pick creation time. When a new pick is created for a Polymarket or Kalshi soft book, the tracker calls the Polymarket fetcher to snapshot liquidity metadata and stores it alongside the pick. Six nullable float columns were added to `nba_tracked_picks` via Supabase SQL Editor migration.

The tracker strips poly columns gracefully if the migration hasn't been applied yet — a defensive pattern that allows deployment before and after the DB migration independently. Existing picks are not backfilled; only new picks receive enrichment.

### Deployment Gotchas

Two deployment issues were encountered:
1. Running `ALTER TABLE` against the wrong Supabase project — `ADD COLUMN IF NOT EXISTS` made this harmless (empty nullable columns with zero impact), but reinforces the need to verify project context before migrations
2. VPS deploy hit a missing import error — the tracker crashed silently on the missing `import` statement, requiring log inspection to diagnose

### Future Analysis

With enriched picks accumulating, the planned analysis includes:
- Filter trail-ROI by `poly_liquidity > 1000` to identify the minimum liquidity threshold where edge is real
- Correlate `poly_volume_24h` with CLV accuracy
- Compare bid-ask spread with pick accuracy to find signal quality thresholds
- Establish whether high-liquidity prediction market picks outperform low-liquidity ones

## Related Concepts

- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle pipeline whose NBA gap was exposed; NBA Pinnacle/Crypto Edge theories created alongside this enrichment
- [[concepts/trail-capture-soft-ids-gap]] - The same SOFT_IDS exclusion pattern: hardcoded book ID sets silently excluding new book types (prediction market IDs missing from NBA dashboard)
- [[concepts/crypto-edge-non-pinnacle-strategy]] - The Crypto Edge strategy that targets non-Pinnacle prediction market gaps; liquidity enrichment adds a data quality dimension
- [[concepts/opticodds-critical-dependency]] - OpticOdds provides prices but not liquidity; Polymarket CLOB API fills this gap for one platform
- [[concepts/pinnacle-prediction-market-roi-breakdown]] - ROI analysis that could be stratified by liquidity tier once enriched picks accumulate

## Sources

- [[daily/lcash/2026-04-23.md]] - OpticOdds has no liquidity data; Polymarket CLOB API public, no auth; game-level volume $4M-$13M, player props $2-$228k; 95% match rate (57/60), suffix normalization needed for 100%; NBA Pinnacle + Crypto Edge theories created → 20 new picks instantly; 6 poly columns added to nba_tracked_picks; forward-only enrichment; SOFT_IDS 950/970 missing from NBA dashboard (Session 13:46). Polymarket fetcher built with 3-letter team code matching; Cade Cunningham Rebounds $254k liquidity confirmed; columns nullable for graceful degradation; wrong-project ALTER TABLE harmless; VPS missing import error on deploy (Sessions 15:22, 15:41)
