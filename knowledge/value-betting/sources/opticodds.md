# OpticOdds

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Primary data source for sharp and consensus book odds across 40+ bookmakers.

---

## What It Is

OpticOdds is a commercial odds API that aggregates odds from 40+ bookmakers worldwide. It's the backbone of the scanner's data pipeline — providing both sharp book odds (for devigging) and soft book odds (for EV comparison).

**Source:** `ev_scanner/opticodds.py` (~21KB)

---

## Key Endpoints

| Endpoint | Purpose | Polling Frequency |
|----------|---------|-------------------|
| `/fixtures/active` | List of upcoming games (filter `is_live: false`) | Every cycle (~20s) |
| `/odds/` | Current odds for a fixture across all books | Every cycle |
| `/player-results/` | Player stat outcomes (for resolution) | Hourly (by resolver) |

---

## Book ID Mapping

OpticOdds uses numeric IDs for bookmakers. The scanner maps 40+ books. Key ones:

### Sharp Books (for devigging)
| ID | Name | Devig Weight | Confidence Score |
|----|------|-------------|-----------------|
| 802 | BetRivers | 1.0 | — |
| 803 | Hard Rock | 0.9 | — |
| 125 | PropBuilder | 0.95 | 1.25 |
| 200 | DraftKings | 0.8 | — |
| 808 | Circa | 0.5 | — |
| 100 | FanDuel | 0.0 | 1.25 |
| 250 | Pinnacle | 0.0 | 0.75 |

### Soft Books (bet targets)
| ID | Name | Notes |
|----|------|-------|
| 365 | Bet365 | Primary target, AU-facing |
| — | Sportsbet | Via direct scrapers |
| — | Neds | Via direct scrapers |
| — | TAB | Via direct scrapers |

---

## Data Volume

Each scrape cycle fetches approximately **24,000 odds** across all active fixtures and markets. This is the bulk of the scanner's data.

---

## Rate Limits

OpticOdds has API rate limits (plan-dependent). The 20-second scrape interval is tuned to stay within limits while keeping data fresh enough for EV accuracy.

---

## Market Types

OpticOdds provides player prop markets including:
- Points, Rebounds, Assists, Steals, Blocks, Turnovers, 3-Pointers
- Points+Rebounds, Points+Assists, Rebounds+Assists, Points+Rebounds+Assists
- First basket, double-double, triple-double
- MLB: Hits, RBIs, Home Runs, Strikeouts, etc.
- NRL/AFL: Tries, Disposals, etc.

Market types are mapped per sport in [[sport-config]].

---

## Related Pages
- [[devig-engine]] — Consumes OpticOdds data
- [[sport-config]] — Per-sport market mappings
- [[resolver]] — Uses OpticOdds player-results for resolution
