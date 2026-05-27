---
title: "OpticOdds Has No Live bet365 Feed"
aliases: [oo-no-bet365-live, bet365-wizard-only-source, opticodds-bet365-gap, bet365-historical-only-oo]
tags: [value-betting, opticodds, bet365, architecture, constraint]
sources:
  - "daily/lcash/2026-05-27.md"
created: 2026-05-27
updated: 2026-05-27
---

# OpticOdds Has No Live bet365 Feed

On 2026-05-27, lcash confirmed via direct API probes that OpticOdds (OO) has **no live bet365 feed**. The `/fixtures/odds?sportsbook=bet365` endpoint returns empty for live fixtures — bet365 data only exists in OO's historical archive (post-game CLV/OLV). The SSE stream covers 13 sharp/soft books but bet365 is NOT among them. This means the scanner's BB wizard scraper (running on Eve via AdsPower Chrome) is the **only source of live bet365 odds** in the entire pipeline.

## Key Points

- **OO `/fixtures/odds?sportsbook=bet365` returns empty** for live games — only historical data (post-game) exists
- **OO SSE stream covers 13 books**, bet365 NOT among them — no real-time bet365 data from OO at all
- **The wizard scraper is the only live bet365 source** — all live EV math (bet365 lag vs sharp moves) depends entirely on wizard cadence
- **OO's competitive moat is sharp-book SSE** (Pinnacle/DK/FD), NOT bet365 coverage — complementary, not overlapping
- **Our moat is live bet365 at high cadence** — no competitor with OO access can replicate this without their own browser scraper
- MLB wizard cadence dropped to 10s (from 60s) to exploit this exclusive data advantage; peak-season load test validated 5,400 requests/30min (30 parallel × 10s) with zero throttling

## Details

### Verification Method

Three probes confirmed the gap:

1. **REST API**: `GET /fixtures/odds?sportsbook=bet365&fixture_id={live_game}` → empty results for every active MLB fixture
2. **SSE stream audit**: Monitored all SSE book traffic for 30 minutes — bet365 never appeared among the streaming books
3. **Historical contrast**: `GET /fixtures/odds/historical?sportsbook=bet365&fixture_id={completed_game}` → data present (CLV/OLV objects) — confirms OO has bet365 data, just not live

### Architectural Implications

The bet365 wizard scraper's value is higher than previously understood. When evaluating the cadence improvement (60s → 30s → 10s), the implicit assumption was that OO provided a complementary bet365 data path that would catch anything the wizard missed. This is false — OO provides zero live bet365 data. Every second of additional wizard cadence latency directly translates to stale bet365 odds in the EV computation.

The wizard scraper's 10s cadence achieves ~6s wall-clock per sweep across 3 MLB games (varies with game count), producing odds that are at most ~10s old. This is dramatically fresher than the 60s cadence used previously and represents the scanner's primary competitive advantage: no OO-based competitor can evaluate bet365 soft book odds without building their own browser scraper.

### Relationship to CLV Computation

OO's bet365 historical endpoint DOES contain post-game data (CLV/OLV — closing/opening line values). The resolver's `backfill_closing_sharps.py` uses this for historical CLV computation. The gap is specifically about live/pre-game odds — the data needed for real-time EV evaluation, not post-hoc analysis.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - OO is the sole sharp odds provider; the bet365 live gap means OO's coverage is even narrower than previously understood — it provides sharps but not the primary soft book
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native scraper architecture that provides live bet365 odds; this is the only live source
- [[concepts/opticodds-clv-backfill-audit]] - OO DOES have bet365 historical data for CLV; the gap is live, not historical
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where Eve's wizard scraper is a queryable server; OO's live gap makes this server irreplaceable

## Sources

- [[daily/lcash/2026-05-27.md]] - OO `/fixtures/odds?sportsbook=bet365` returns empty for live games; SSE covers 13 books, bet365 not among them; wizard scraper is only live bet365 source; OO moat = sharp SSE, our moat = live bet365 at high cadence; 10s cadence validated at 5,400 req/30min zero throttling (Sessions 11:26, 12:29, 13:35)

```
