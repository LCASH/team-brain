# Direct Scrapers

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Scrapers for Australian soft bookmakers: Sportsbet, Neds, TAB, and others.

---

## What They Do

Scrape odds directly from AU-facing bookmakers via REST APIs and WebSockets. These are "soft books" — the targets for finding +EV bets (their odds are compared against devigged sharp book true odds).

**Source:** `ev_scanner/direct_scrapers.py` (~26KB)

---

## Supported Books

| Bookmaker | Method | Notes |
|-----------|--------|-------|
| Sportsbet | REST API | Reverse-engineered endpoints |
| Neds | REST API | Similar to Ladbrokes (same parent) |
| TAB | REST API | See also `BOOKIE API/tab_racing_api.py` for racing |
| Ladbrokes | REST API | Same parent as Neds |
| Pointsbet | REST/WebSocket | Player prop coverage varies |

All scrapers output unified `ScrapedOdds` format with a `market_key` for matching.

---

## BlackStream (AU Consensus)

When individual AU bookies lack coverage for a market, the "BlackStream" approach aggregates available AU book odds into a consensus view. This is separate from the sharp book consensus in [[devig-engine]] — it's specifically about soft book availability for bet placement.

---

## Related Pages
- [[opticodds]] — Sharp book data source
- [[bet365-scraper]] — Primary soft book (direct CDP)
- [[betstamp]] — Bet365 via WebSocket
- [[market-matcher]] — How scraped odds are grouped
