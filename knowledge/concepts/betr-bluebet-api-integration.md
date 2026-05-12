---
title: "Betr BlueBet API Integration"
aliases: [betr-api, bluebet-api, betr-scraper, betr-orchestrator, bluebet-polling]
tags: [value-betting, sportsbook, scraper, api, integration, betr, bluebet, soft-book]
sources:
  - "daily/lcash/2026-05-12.md"
created: 2026-05-12
updated: 2026-05-12
---

# Betr BlueBet API Integration

Betr runs on the BlueBet platform with a public JSON API at `https://web20-api.bluebet.com.au`. The API has no anti-bot protection, no WebSockets or SSE — it is 100% HTTP polling with plain JSON responses. It sustains 30+ QPS with zero throttling; earlier 403 errors were caused by Python's default `Python-urllib/x.x` User-Agent being on a blocklist, not volume-based rate limiting. Betr was already in the system as `book_id=910` via OpticOdds but classified as `AU_SHARP` (not `SOFT`), meaning it fed consensus devigging but the EV engine never found +EV against it. OpticOdds only delivers approximately 3% of Betr's actual markets (9 NBA selections vs hundreds available), making direct API integration essential for coverage.

## Key Points

- Plain JSON API at `https://web20-api.bluebet.com.au` — no anti-bot protection, no browser/AdsPower needed at runtime, massive simplification vs bet365
- 30+ QPS sustained with zero throttling — 403 errors were User-Agent blocklist (Python default), not rate limiting
- Already in system as `book_id=910` via OpticOdds classified as `AU_SHARP` not `SOFT` — feeds consensus but EV engine never finds +EV against it; needs reclassification to `SOFT` book sets
- OpticOdds coverage is approximately 3% of actual Betr markets (9 NBA selections vs hundreds); per-game endpoint returns only "Popular Markets" — player props require a separate per-category fetch endpoint using `GroupTypeCode` values from `GroupLinks` in MasterEvent response
- BetrOrchestrator + `discovery.py` + `mappings.py` skeleton built (160 lines discovery); wired into `startup.py` gated by `ENABLE_BETR` env var; 285 odds across 11 prop types parsed in smoke test

## Details

### API Architecture and Access

The BlueBet API powering Betr is a straightforward REST API returning JSON. Unlike bet365 which requires persistent Chrome sessions via AdsPower, WebSocket interception, and complex session management, Betr's entire data pipeline can be driven by simple HTTP requests. The API has three key layers:

1. **League listing**: Returns available competitions with league IDs (NBA=39251, MLB=29431, AFL=43735)
2. **MasterEvent per game**: Returns game-level "Popular Markets" plus a `GroupLinks` array listing all available prop categories with their `GroupTypeCode` values — NBA has 16 player-prop categories
3. **Per-category fetch**: A separate endpoint (not yet fully discovered) that returns player props for a specific `GroupTypeCode` within a game

The per-game endpoint only returns "Popular Markets" (game-level totals, spreads, moneylines). Player props — where the value betting edge exists — require iterating through the `GroupLinks` categories and fetching each one individually. This discovery-then-drill pattern is similar to the bet365 wizard navigation but without any of the browser automation complexity.

### Sport Coverage Assessment

Coverage varies dramatically by sport on Betr:
- **NBA**: 16 player-prop categories available, strong coverage — the primary target for integration
- **AFL**: Valuable markets including Disposals and Goals — worth pursuing as a secondary sport
- **MLB**: Zero player props available on Betr — completely worthless for the value betting pipeline

This sport-specific coverage profile means the Betr integration adds the most value for NBA and AFL, complementing the existing bet365 scraper which has the widest overall coverage at 59.7% of markets.

### Integration Architecture

The initial integration consists of:
- **BetrOrchestrator**: Main orchestration class managing the polling loop and market state
- **discovery.py**: 160-line module handling league discovery, game enumeration, and prop category iteration
- **mappings.py**: Prop type and market name mapping from BlueBet's naming conventions to the scanner's canonical `EV_NAME_MAP` format

The integration is wired into `startup.py` behind an `ENABLE_BETR` environment variable gate, allowing gradual rollout. Betr has been added to the `SOFT` book sets (reclassified from `AU_SHARP`), meaning the EV engine will now evaluate Betr odds as potential +EV opportunities rather than just using them for consensus devigging.

The CO milestone conversion was completed, and a smoke test parsed 285 odds across 11 prop types successfully.

### User-Agent Blocklist Discovery

The initial 403 errors during API exploration were not caused by rate limiting or IP blocking. The BlueBet API maintains a User-Agent blocklist that rejects requests from Python's default `Python-urllib/x.x` agent string. Setting a standard browser User-Agent immediately resolved all 403s, and subsequent testing at 30+ queries per second showed no throttling whatsoever. This is a common pattern with Australian sportsbook APIs — minimal bot protection beyond basic User-Agent filtering.

## Related Concepts

- [[concepts/tab-scraper-threshold-markets]] - Tab/Betr threshold market format where props are offered at line 0.5 instead of the standard sharp line; Betr likely uses similar threshold formatting for some prop types
- [[connections/anti-scraping-driven-architecture]] - Betr's open API is the opposite extreme from bet365's anti-scraping measures; the absence of protection makes Betr the simplest possible sportsbook integration

## Sources

- [[daily/lcash/2026-05-12.md]] - Betr runs on BlueBet platform at `https://web20-api.bluebet.com.au`; no anti-bot protection, 100% HTTP polling, 30+ QPS zero throttling; 403s were User-Agent blocklist not rate limiting; already book_id=910 via OpticOdds as AU_SHARP (only ~3% coverage); NBA 16 prop categories, AFL valuable, MLB zero player props; BetrOrchestrator + discovery.py + mappings.py built (160 lines); wired into startup.py gated by ENABLE_BETR; 285 odds across 11 prop types in smoke test; league IDs NBA=39251 MLB=29431 AFL=43735 (Sessions 11:03, 14:22)
