---
title: "BetIT 123bet Direct Scraper"
aliases: [betit-scraper, 123bet-api, betit-v3-port, book-961]
tags: [value-betting, sportsbook, scraper, api, integration, betit]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# BetIT 123bet Direct Scraper

BetIT (book_id 961) was identified on 2026-05-18 as never having been ported from the legacy `direct_scrapers.py` to the v3 architecture — a gap, not a deliberate exclusion. The 123bet.com.au API works without authentication, returning JSON responses for NBA player props. Brain memory initially suggested BetIT/123bet was redundant with other Black Stream brands, but live probing confirmed **210 unique markets across 8 prop types** — genuine incremental coverage. The scraper was ported to v3, gated behind `ENABLE_BETIT=1` env var following the same pattern as Betr/TAB/TabTouch.

## Key Points

- BetIT (book 961) was in the legacy `direct_scrapers.py` but never ported to v3 — a migration gap discovered during coverage audit
- **Brain memory was wrong**: claimed BetIT/123bet was redundant with other brands; live probe showed 210 unique NBA markets across 8 prop types
- `https://123bet.com.au/api/...` — no auth needed, plain JSON responses, same integration simplicity as Betr/BlueBet
- Legacy parser regexes were outdated: market type naming had evolved (e.g., `Player points + assists 25+` vs legacy `Pts + Ast Over X`)
- Gated behind `ENABLE_BETIT=1` env var — same deployment pattern as other direct scrapers
- Currently NBA-only — MLB coverage not yet confirmed (matches legacy behavior where only NBA was scraped)
- v3 log writes to pty after restart, not to `v3.log` — can mislead operators checking if the new scraper is active

## Details

### Discovery and Verification

During a coverage audit on 2026-05-18, lcash identified that BetIT (book_id 961) appeared in the legacy `direct_scrapers.py` configuration but had no corresponding v3 module. The initial investigation consulted the brain memory system, which returned an assessment that BetIT/123bet was redundant with other Black Stream platform brands — implying no unique data was lost.

This assessment was **verified as incorrect** via live API probing. The 123bet.com.au API returned 210 markets across 8 NBA player prop types, with data that was not available from other scrapers. This is a general lesson about cached intelligence: brain memory and prior assessments can become stale, and must be validated against live data before making exclusion decisions.

### API Architecture

The 123bet API follows a straightforward REST pattern similar to the Betr/BlueBet API (see [[concepts/betr-bluebet-api-integration]]): plain JSON responses, no authentication required, and no anti-bot protection beyond basic request formatting. The market type naming convention evolved between the legacy scraper's era and the current API — regexes that matched `Pts + Ast Over X` now need to handle `Player points + assists 25+`. The parser was updated during the v3 port.

### Integration Pattern

The v3 integration follows the established direct scraper pattern:
- Scraper module in `v3/scrapers/betit/`
- Gated behind `ENABLE_BETIT=1` environment variable
- Polling at regular intervals via the direct scraper worker framework
- Output merged into the v3 DataStore alongside other soft book data

### MLB Coverage Gap

The legacy scraper only scraped NBA from BetIT. Whether 123bet offers MLB player props is unconfirmed — the API endpoints for other sports need probing. Given that the scanner's primary focus is NBA + MLB, confirming MLB coverage would approximately double BetIT's value to the pipeline.

## Related Concepts

- [[concepts/betr-bluebet-api-integration]] - Same integration simplicity: no auth, plain JSON, no anti-bot; Betr is the closest architectural analog
- [[concepts/configuration-drift-manual-launch]] - BetIT requires `ENABLE_BETIT=1` in env/batch files; same drift risk as all other enable flags
- [[concepts/v3-scanner-centralized-architecture]] - The v3 architecture that BetIT was ported into; follows the modular scraper pattern
- [[concepts/tab-scraper-threshold-markets]] - Another direct scraper (TAB, book 908) that went through a similar port process to v3

## Sources

- [[daily/lcash/2026-05-18.md]] - BetIT (961) never ported from legacy to v3; brain memory incorrectly claimed redundancy; 123bet API works without auth, 210 unique NBA markets across 8 prop_types; legacy parser regexes outdated; gated behind ENABLE_BETIT=1; MLB coverage unconfirmed; v3 log writes to pty not v3.log (Session 10:06)
