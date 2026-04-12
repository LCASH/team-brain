---
title: "Connection: Scraper Consolidation and Provider Dependency"
connects:
  - "concepts/betstamp-bet365-scraper-migration"
  - "concepts/opticodds-critical-dependency"
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# Connection: Scraper Consolidation and Provider Dependency

## The Connection

Removing the Betstamp adapter from the value betting scanner simultaneously simplifies the scraping architecture and deepens the system's dependency on OpticOdds. Betstamp was the only external odds provider independent of both OpticOdds and the custom Bet365 scrapers — its removal means the scanner's entire data pipeline now flows through exactly two sources: OpticOdds (sharp + Australian soft books) and in-house Bet365 browser automation (NBA soft books).

## Key Insight

The non-obvious insight is that Betstamp's removal eliminates a **data diversity benefit** that was no longer accessible. Betstamp provided its own EV calculation (`betstamp_ev`) derived from an independent true line — a second opinion on value that didn't depend on OpticOdds' sharp odds. With Betstamp's service discontinued, this independent signal is gone regardless of whether the adapter code remains. Removing the dead adapter code is the right operational decision (less complexity, fewer failure modes), but it's worth recognizing that the system's intellectual diversity — multiple independent assessments of true odds — has narrowed to a single pipeline.

This creates a subtle risk asymmetry: the Bet365 game scraper is a **better** replacement for Betstamp's soft book data (richer markets, direct source), but it provides **zero** replacement for Betstamp's independent EV assessment. The scanner now relies entirely on OpticOdds for the "true odds" reference used in devigging. If OpticOdds' sharp lines are wrong or delayed, every EV calculation in the system is affected with no cross-check available.

## Evidence

The dependency concentration was exposed on the same day (2026-04-12) through two events:

1. **OpticOdds key expiry (Session 20:15):** When the API key expired, NRL, AFL, and MLB went completely dark — 100% dependent on OpticOdds. NBA retained soft book data from Bet365 scrapers but lost all devigging capability. This demonstrated the single-provider risk in practice.

2. **Betstamp removal analysis (Session 21:15):** The dependency trace confirmed that only the Bet365 game scraper and OpticOdds provide data. With Betstamp removed, the architecture has exactly two data providers: one for sharp reference data (OpticOdds, irreplaceable) and one for NBA soft books (Bet365 game scraper, self-operated). The `betstamp_ev` field — the last vestige of independent EV calculation — will permanently return `None`.

The juxtaposition of these two events on the same day makes the dependency structure especially visible: the morning showed what happens when OpticOdds fails, and the evening planned the removal of the only other external data provider.

## Related Concepts

- [[concepts/betstamp-bet365-scraper-migration]] - The migration that consolidates scraping under the game scraper
- [[concepts/opticodds-critical-dependency]] - The single-provider dependency that deepens after Betstamp removal
- [[concepts/parlay-ev-calculation]] - EV calculations that depend on the true odds pipeline affected by this consolidation
