---
title: "Betr BlueBet API Integration"
aliases: [betr-api, bluebet-api, betr-scraper, betr-orchestrator, bluebet-polling]
tags: [value-betting, sportsbook, scraper, api, integration, betr, bluebet, soft-book]
sources:
  - "daily/lcash/2026-05-12.md"
  - "daily/lcash/2026-05-13.md"
  - "daily/lcash/2026-05-19.md"
created: 2026-05-12
updated: 2026-05-19
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

### Eve (VPS) Deployment and Operational Findings (2026-05-13)

On 2026-05-13, the Betr scraper was deployed to Eve (the VPS) as part of a native AU scraper rollout. Three operational findings emerged:

**No proxy needed:** Direct connections from Eve to `web20-api.bluebet.com.au` work without any proxy — Webshare proxies returned 407 (the account is in IP-allowlist mode and Eve's NAT IP isn't whitelisted), but this turned out to be irrelevant since direct connections succeed. The proxy infrastructure is a hypothetical defense that isn't currently needed.

**Empty-state staleness bug:** The Betr REST scraper had `if not self._games: return` in its `refresh()` method, which short-circuited without clearing `self._odds`. When games ended or weren't available (e.g., no NBA games during AU daytime), stale odds persisted as ghost markets — the push loop continued serving them with fresh `captured_at` timestamps, making them appear current. The fix lets refresh run but clears odds when discovery genuinely returns zero events, while preserving the game list on transient failures (429/network errors).

**Discovery throttle adjusted:** Betr discovery was bumped from 60s to 5-minute intervals after 429 rate-limiting was observed during rapid restart cycles. The 429s came from burst traffic during development restarts, not sustained production load.

Post-deployment verification: VPS showed 83% freshness for Betr data — slightly below TAB (100%) and TabTouch (100%) due to the discovery throttle and fewer available markets.

### Racing Integration and Transport Investigation (2026-05-19)

On 2026-05-19, betr was integrated as a racing bookie in the SuperWin scanner. The investigation definitively confirmed that betr has **zero WebSocket, SignalR, SSE, or Service Worker connections** for odds delivery — across logged-out, logged-in, and betslip-interaction sessions monitored via CDP. The web UI polls at ~13-15s intervals using React Query `refetchInterval: 13000` on `/Race?eventId=...`. Our 1Hz adapter is 14x faster than betr's own frontend.

**Cloudflare rate-limiting is IP-reputation based**: VPS datacenter IPs get 1015 errors at 1Hz polling, while residential IPs sustain 10 req/sec (6,000/6,000 requests, 100% success) with zero throttling. This forced a residential relay architecture via the Dell mini PC — same pattern as `bet365_stream.py`. WebShare proxy credentials were discovered to be stale (pool rotated, TabTouch silently running in DIRECT mode), and CRLF line endings in downloaded proxy lists broke shell scripts.

**BlueBoost** promotional pricing was deployed as a racing edge (`racing-blueboost`): betr applies per-runner boosted odds via `odds.tote_win`, with favourites getting ~3% boosts and longshots 20-25% — same convexity as TabTouch SuperPicks. See [[concepts/betr-blueboost-racing-edge]] and [[concepts/betr-no-websocket-xhr-only-architecture]] for the full analysis.

## Related Concepts

- [[concepts/tab-scraper-threshold-markets]] - Tab/Betr threshold market format where props are offered at line 0.5 instead of the standard sharp line; Betr likely uses similar threshold formatting for some prop types
- [[connections/anti-scraping-driven-architecture]] - Betr's open API is the opposite extreme from bet365's anti-scraping measures; Cloudflare IP-reputation rate-limiting applies to racing endpoints from datacenter IPs
- [[concepts/per-soft-book-temporal-lineage]] - Betr (book 910) is one of the 16 target books in the per-book temporal lineage system; its REST polling cadence creates a distinct freshness profile from SSE-based books
- [[concepts/betr-no-websocket-xhr-only-architecture]] - Exhaustive transport investigation confirming betr is XHR-only; 14x speed advantage over betr's own UI
- [[concepts/betr-blueboost-racing-edge]] - BlueBoost promotional pricing edge deployed for racing

## Sources

- [[daily/lcash/2026-05-12.md]] - Betr runs on BlueBet platform
- [[daily/lcash/2026-05-19.md]] - Racing integration: zero WebSocket/SignalR/SSE confirmed across 3 CDP capture sessions; XHR polling at ~13-15s via React Query; 1Hz adapter 14x faster; Cloudflare IP-reputation rate-limiting (VPS 1015'd, residential 100%); Dell mini PC residential relay architecture; BlueBoost edge deployed; WebShare credentials stale (Sessions 13:47, 14:18, 15:20, 16:47)
- [[daily/lcash/2026-05-13.md]] - Eve deployment: no proxy needed (Webshare 407 irrelevant, direct works); empty-state staleness bug (`if not self._games: return` preserves ghost markets); discovery throttle 60s→5min; VPS 83% freshness; push loop masks staleness with fresh captured_at (Session 14:41) at `https://web20-api.bluebet.com.au`; no anti-bot protection, 100% HTTP polling, 30+ QPS zero throttling; 403s were User-Agent blocklist not rate limiting; already book_id=910 via OpticOdds as AU_SHARP (only ~3% coverage); NBA 16 prop categories, AFL valuable, MLB zero player props; BetrOrchestrator + discovery.py + mappings.py built (160 lines); wired into startup.py gated by ENABLE_BETR; 285 odds across 11 prop types in smoke test; league IDs NBA=39251 MLB=29431 AFL=43735 (Sessions 11:03, 14:22)
