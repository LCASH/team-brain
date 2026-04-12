---
title: "Betstamp to Bet365 Game Scraper Migration"
aliases: [betstamp-removal, bet365-scraper-consolidation, book-id-365-366]
tags: [value-betting, migration, architecture, scraping, bet365]
sources:
  - "daily/lcash/2026-04-12.md"
created: 2026-04-12
updated: 2026-04-12
---

# Betstamp to Bet365 Game Scraper Migration

A planned migration to remove the Betstamp adapter from the value betting scanner and consolidate all Bet365 odds scraping under the Bet365 game scraper. The migration involves changing the game scraper's book ID from 366 to 365 so downstream systems receive data under the expected identifier, requiring only 3 file changes for functional equivalence.

## Key Points

- Betstamp is no longer available as a service — the adapter is dead weight that cannot produce data
- The Bet365 game scraper (`bet365_game_worker.py`) supersedes Betstamp with richer market depth (spreads, totals, moneylines, player props) via direct browser automation
- The critical architectural detail is book IDs: Betstamp emitted `book_id=365` (expected everywhere downstream), while the game scraper emits `book_id=366` (a temporary coexistence ID)
- Only 3 files require changes for functional migration: `sport_config.py` (remove betstamp from enabled_scrapers), `bet365_game_worker.py` (366→365), `server/main.py` (tracker waits for `bet365_game` instead of `betstamp`)
- All downstream code (tracker, resolver, CLV tracker, theories, comparator, EVPick defaults) already handles betstamp being absent via None checks and empty list handling

## Details

### Book ID Architecture

The coexistence of Betstamp and the Bet365 game scraper was enabled by assigning them different book IDs: Betstamp used `365` (the canonical Bet365 identifier used throughout the codebase) while the game scraper used `366` (a synthetic ID for side-by-side comparison). This dual-ID scheme allowed both scrapers to run simultaneously without data collisions, enabling comparison dashboards and gradual validation of the game scraper's output against Betstamp's.

With Betstamp's service no longer available, the comparison purpose is moot. The migration changes `BET365_2_BOOK_ID` from `366` to `365` in `bet365_game_worker.py`, making the game scraper's output appear under the canonical Bet365 identifier. All downstream systems — the resolver, tracker, CLV tracker, theories engine, and EVPick defaults — reference `365` and will seamlessly consume the game scraper's data without any changes.

### Dependency Trace Methodology

The migration was preceded by a full dependency trace through the codebase to assess blast radius. lcash traced: (1) what data Betstamp provides and under which keys (`bet365` key, `book_id=365`), (2) what the Bet365 game scraper provides and under which keys (`bet365_game` key, `book_id=366`), (3) whether any downstream component depends specifically on Betstamp-only data. The trace confirmed that all Betstamp-specific references either have graceful None handling or are in comparison/testing code that can be cleaned up separately.

### Minimum Change vs Full Cleanup

The migration is designed as a two-phase approach. Phase 1 (minimum viable, 3 files) makes the system functionally correct: Betstamp is disabled, the game scraper takes over the canonical book ID, and the tracker startup sequence is updated. Phase 2 (cleanup, optional) removes dead code: `betstamp_bet365.py`, `betstamp_worker.py`, `compare_scrapers.py`, test files, dead functions in `server/main.py`, betstamp fields from config and `.env.example`, the `366` entry from `SOFT_BOOK_IDS`/`BOOK_NAMES`, and the comparison dashboard tab.

This phased approach minimizes risk — phase 1 can be deployed and validated before any code deletion.

### Betstamp EV Field

Betstamp provided its own EV calculation (`betstamp_ev`) derived from its internal true line. With Betstamp removed, this field will always be `None` across all downstream systems. All code already handles this gracefully — the dashboard comparison tab will simply show no data, and EV calculations fall back to the scanner's own devigging pipeline via OpticOdds sharp odds.

## Related Concepts

- [[concepts/opticodds-critical-dependency]] - Removing Betstamp further concentrates dependency on OpticOdds as the sole sharp odds provider
- [[concepts/bet365-racing-adapter-architecture]] - The other Bet365 scraping system (racing, separate from game scraper)
- [[connections/scraper-consolidation-provider-dependency]] - How this migration interacts with the single-provider risk

## Sources

- [[daily/lcash/2026-04-12.md]] - Full dependency trace and migration plan: book ID 366→365, 3-file minimum change, phased cleanup approach; Betstamp confirmed no longer available as a service (Session 21:15)
