---
title: "AU Direct Scraper Coverage Expansion"
aliases: [au-scraper-expansion, sportsbet-pointsbet-greenfield, bet365-monopoly-props, bmapollo-migration, au-soft-book-coverage-map]
tags: [value-betting, scraping, architecture, coverage, au-soft-books, infrastructure]
sources:
  - "daily/lcash/2026-05-28.md"
created: 2026-05-28
updated: 2026-05-28
---

# AU Direct Scraper Coverage Expansion

On 2026-05-28, lcash performed a comprehensive audit of AU soft-book scraper coverage and built 5 standalone adapter modules for PointsBet, TAB, Neds, TabTouch, and BetIT — discovering that bet365 holds 9 MLB monopoly prop types (no AU soft-book competition) and that BetIT had silently migrated from the `123bet` platform to `bmapollo` (breaking the existing scraper). The audit revealed 381 unique player+prop+side keys across 5 AU bookies, with 135 covered by 3+ bookies (strong devig signal), and identified Sportsbet and PointsBet as the two biggest blind spots — both have MLB props but the scanner only receives them via OpticOdds relay with lag.

## Key Points

- **bet365 has 9 MLB monopoly prop types** with zero AU competition — 7 are "CO" milestone variants (Hits CO, Bases CO, etc.) where devig accuracy has no cross-book validation
- **BetIT silently migrated from 123bet to bmapollo platform** — existing scraper kept running but returned only 42 markets vs 523 possible; no alerting caught the regression
- **PointsBet's real endpoint is `/api/mes/v3/events/{event_id}`** (2.9 MB, 978 outcomes) not the league feed (80 KB) — the per-event endpoint is 36x richer
- **5 adapter modules built**: pure parsers (raw JSON → ScrapedOdds) with 7 passing tests; each bookie gets isolated `adapter.py` (parser) + `scraper.py` (orchestrator)
- **Coverage priority order**: Betr MLB → TAB MLB → TabTouch MLB → Neds MLB → Sportsbet greenfield → PointsBet greenfield
- **381 unique keys**, 135 covered by ≥3 bookies — DD/TD props have different outcome shapes (eventClass carries market type, outcome name = player)
- **BlackStream (book 960) dead since at least 2026-04-13** — no data from this scraper for 45+ days

## Details

### Coverage Gap Analysis

The scraper fleet audit identified two tiers of opportunity:

**Tier 1 — Props that AU bookies offer but we lack direct scrapers for:**
Sportsbet and PointsBet are the primary blind spots. Both have MLB player props, but the scanner receives them only through OpticOdds relay — which introduces 30-60s latency, misses alt lines, and depends on OO's book coverage. A direct scraper would capture odds at the source with sub-second freshness.

| Bookie | MLB Coverage | Status | Priority |
|--------|-------------|--------|----------|
| Betr (910) | MLB props confirmed in API | Existing scraper, needs MLB extension | High |
| TAB (908) | 19 new combo threshold specs found | Existing scraper, needs prop additions | High |
| TabTouch/Kambi (909) | MLB betOffers confirmed | Existing scraper, needs MLB routing | Medium |
| Neds (902) | Unknown — API returns 500 to curl | Needs browser-context recon | Medium |
| BetIT (961) | Broken — platform migrated | Rewrite needed | Medium |
| Sportsbet (900) | ~200 extra MLB markets/cycle | No direct scraper exists | High (greenfield) |
| PointsBet (911) | ~400 markets per event endpoint | No direct scraper exists | High (greenfield) |

**Tier 2 — bet365 monopoly props needing devig accuracy focus:**
9 MLB prop types exist only on bet365 with no AU soft-book competition. Of these, 7 are CO milestone variants whose devig relies entirely on the scanner's interpolation accuracy — no cross-book validation is possible.

### BetIT Platform Migration

BetIT silently migrated from the `123bet.com.au` API to a `bmapollo` platform. The existing v3 scraper (`v3/scrapers/betit/`) continued running against the old API, receiving 42 markets instead of the 523 available on the new platform. No market-count alerting exists to catch this class of silent degradation — the scraper reported success with a reduced but non-zero market count.

The lesson: **platform migrations happen silently.** Sportsbook technology stacks change (acquisitions, white-label swaps, API version deprecations) without notice. Market-count monitoring with historical baselines would catch these regressions automatically.

### Adapter Architecture Pattern

Each bookie gets an isolated two-file architecture:
- **`adapter.py`** — pure parser: raw JSON → list of `ScrapedOdds` objects. No I/O, no state, no configuration. Testable with saved JSON fixtures.
- **`scraper.py`** — orchestrator: discovery (find active games), fetch (HTTP/WS per game), parse (call adapter), merge (into DataStore).

This separation enables easy platform migration: when BetIT switches APIs, only `adapter.py` changes. The orchestrator's discovery/fetch/merge logic is stable across platform changes. The pattern was validated by the BetIT migration — the old adapter parsed `123bet` JSON; the new one parses `bmapollo` JSON; the orchestrator interface is identical.

### TAB Threshold Spec Expansion

19 new combo threshold specification IDs were added to the TAB scraper for Points+Rebounds, Points+Assists, Rebounds+Assists ladders, and 45+ Points milestones. These were present in TAB's API but not in the scanner's `betOptionSpectrumId` mapping — silent coverage loss from an incomplete API reverse-engineering during the original TAB integration.

### Player Name Reconciliation

BetIT uses abbreviated format ("D. Vassell") while all other bookies use full names ("Devin Vassell"). This requires a reconciliation layer — either a fuzzy matcher in the adapter or a lookup table from abbreviated → canonical names. The TAB scraper solved the same problem using its own threshold market full names (see [[concepts/tab-scraper-threshold-markets]]); BetIT may need a similar self-contained resolution approach if the bmapollo API includes both formats.

## Related Concepts

- [[concepts/betit-123bet-direct-scraper]] - The original BetIT integration that is now broken from the bmapollo migration
- [[concepts/betr-bluebet-api-integration]] - Betr's existing scraper that needs MLB extension; same no-auth, plain JSON pattern
- [[concepts/tab-scraper-threshold-markets]] - TAB's threshold market architecture; 19 new specs added in this session
- [[concepts/opticodds-critical-dependency]] - AU soft books received via OO relay have 30-60s lag; direct scrapers eliminate this dependency for covered books
- [[concepts/coverage-first-dashboard-orientation]] - The coverage dashboard that exposed bet365's 59.7% monopoly; this audit extends that analysis to per-prop-type coverage
- [[concepts/opticodds-no-live-bet365-feed]] - OO has zero live bet365 feed; combined with bet365's 9 MLB monopoly props, this means those props have exactly one data source with no validation path

## Sources

- [[daily/lcash/2026-05-28.md]] - Session 15:38: 7/8 direct scrapers green, BlackStream dead since 2026-04-13; bet365 14 prop types / 2,062 MLB markets no other direct scraper captures; 9 monopoly CO variants; Sportsbet + PointsBet biggest blind spots. Session 17:45: 5 adapter modules built; PointsBet `/api/mes/v3/events/{event_id}` = 2.9 MB / 978 outcomes; BetIT migrated 123bet→bmapollo silently (42 vs 523 markets); 381 unique keys, 135 at ≥3 bookies; TAB 19 new combo threshold specs; DD/TD different outcome shapes; 7 passing tests. Session 16:09: per-scraper extension map with priority order; AdsPower browser recon started for API capture

