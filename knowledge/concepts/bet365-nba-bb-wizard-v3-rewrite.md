---
title: "bet365 NBA BB Wizard v3 Rewrite"
aliases: [nba-v3, bb-wizard-v3, nba-bb-wizard-reload, nba-v3-rewrite, nba-v3-scraper]
tags: [bet365, nba, scraping, architecture, value-betting, cdp]
sources:
  - "daily/lcash/2026-04-30.md"
created: 2026-04-30
updated: 2026-04-30
---

# bet365 NBA BB Wizard v3 Rewrite

The NBA game scraper was rewritten as v3 on 2026-04-30, porting the MLB v3 architecture (raw CDP, persistent pages, partial-result shield) while leveraging the BB wizard's structural advantage: all 17 player prop categories in a single ~258 KB HTTP response. This makes NBA v3 dramatically simpler than MLB v3 — each refresh is a single `Page.reload` instead of MLB's 25 partial hash-nav fetches across market groups. A CDP race condition pattern was documented as a universal v3 requirement: attach WebSocket + enable Network domain BEFORE navigating, or the wizard response fires before the listener is ready. Deployed with `NBA_V3` environment toggle for instant rollback.

## Key Points

- BB wizard returns **all 17 player prop categories in one ~258 KB response** — NBA's structural advantage over MLB's 25 partial fetches per game
- Single-fetch refresh: one `Page.reload` captures the entire prop surface; no MG catalogue, no hash-nav loop, no market expansion clicks needed
- **CDP race condition pattern**: must open tab on `about:blank`, attach WebSocket, enable `Network` domain, THEN navigate to BB URL — otherwise wizard response fires before listener is ready
- CDN cache TTL ~5+ min observed: `cache_stuck=3` on HOU@LAL (3 consecutive identical body hashes) — bounds minimum useful refresh interval
- `MAX_CONCURRENT_REFRESHES=5` for NBA (vs MLB's 2) since no per-MG hash-nav loop needed — each refresh is a single fast reload
- `NBA_V3` env toggle: `1` for v3 (default), `0` for instant rollback to legacy scraper; `run_v3()` and `run_legacy()` coexist
- ~720 lines mirroring MLB v3 structure — same patterns (raw CDP, persistent pages, partial-result shield) with NBA-specific simplifications
- All 14 known EV prop names confirmed in BB wizard response; 10 "unknown" names are main markets (Money Line, Spread, Total) — correctly excluded

## Details

### The BB Wizard Single-Fetch Advantage

The NBA BB wizard endpoint (`betbuilderpregamecontentapi/wizard`) returns the complete player prop surface in a single HTTP response. This contrasts sharply with MLB's `batchmatchbettingcontentapi`, which requires navigating to each Market Group individually via hash-nav URLs (see [[concepts/bet365-mlb-hash-nav-mg-fetching]]). The architectural implications:

| Dimension | NBA v3 (BB Wizard) | MLB v3 (Batch API) |
|-----------|-------------------|-------------------|
| Responses per game | 1 | ~25 (one per MG) |
| Refresh method | `Page.reload` | Hash-nav per MG |
| Max concurrent refreshes | 5 | 2 (MG loop is sequential) |
| Per-game setup | Navigate to BB URL once | Navigate + discover MG catalogue |
| Data per response | ~258 KB, 17 prop categories | ~30-50 KB per MG partial |

This advantage was documented in `docs/BET365_SCRAPER_V3_LEARNINGS.md` — a 12-section guide created during the MLB v3 build covering architecture, dead ends, surfaces tested, and the 13-capability ladder, with NBA-specific differences noted in each section.

### CDP Race Condition Pattern

A universal v3 requirement: Chrome DevTools Protocol response interception must be set up BEFORE the page navigates to the target URL. The correct sequence:

1. Open a new tab navigated to `about:blank` via CDP `json/new`
2. Connect to the tab via CDP WebSocket
3. Send `Network.enable` to start capturing network events
4. Navigate the tab to the BB wizard URL (with `/I99/` tab suffix for BB wizard, or `/I0/` for main props)
5. Listen for `Network.responseReceived` events matching the wizard endpoint

If navigation happens before `Network.enable`, the BB wizard HTTP response fires immediately on page load, and the listener misses it entirely. This produces a "0 odds" result that looks like a bet365 blocking issue but is actually a local timing bug. The fix is to always open tabs on blank first, attach all listeners, then navigate — the same pattern used in MLB v3 game page setup.

### CDN Cache Behavior

bet365's CDN caches BB wizard responses with a TTL of approximately 5+ minutes. During development, `cache_stuck=3` was observed on HOU@LAL — three consecutive page reloads returned identical response body hashes, confirming the CDN served cached content. This is consistent with the MLB CDN caching documented in [[concepts/bet365-mlb-hash-nav-mg-fetching]] (identical 32,241-byte responses 30 minutes apart).

The cache TTL bounds the minimum useful refresh interval: refreshing faster than ~5 minutes produces identical cached responses, wasting Chrome resources without gaining fresh data. The production NBA legacy scraper already operated within this constraint (15s refresh interval but only detecting changes when the CDN cache invalidated). The v3 scraper's `MAX_CONCURRENT_REFRESHES=5` is set to cycle through all games quickly but the effective data freshness is bounded by bet365's CDN, not the scraper's speed.

### Environment Toggle Deployment

The v3 deployment uses an `NBA_V3` environment variable (default `1`) to select between v3 and legacy scraper paths:

- `NBA_V3=1` → `run_v3()` — new raw CDP architecture
- `NBA_V3=0` → `run_legacy()` — old Playwright-based scraper

This enables instant rollback without code redeployment: set `NBA_V3=0` in the batch file and restart the server. Both code paths coexist in the same module. This pattern was validated during the MLB v3 deployment where the toggle provided a safety net during initial production bake-in.

### L3 Marker and Prop Identification

The L3 marker for NBA was confirmed as `NBA` (this was an open question from the rewrite plan). All 14 known EV-relevant prop names are present in the BB wizard response. The 10 "unknown" names (`Money Line`, `Spread`, `Total`, etc.) are main market types, not player props — they are correctly excluded from prop parsing. This means the BB wizard delivers the complete EV-relevant prop surface in a single response with no missing categories.

### Relationship to Prior NBA Optimization

The NBA v3 rewrite supersedes the coupon endpoint dual-capture strategy (see [[concepts/bet365-nba-coupon-endpoint]]) that was built as an HTTP-poll optimization. The coupon approach used alternating I99/I0 tab navigation to capture from two endpoints. The v3 BB wizard reload approach is simpler (single endpoint, single reload) and achieves equivalent data coverage. The coupon branch remains dormant as a fallback if BB wizard cache TTL proves too long for time-sensitive markets.

## Related Concepts

- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - MLB v3 hash-nav architecture that NBA v3 simplifies; BB wizard eliminates MG catalogue discovery
- [[concepts/bet365-v3-scraper-capability-ladder]] - The 13-capability test ladder developed for MLB v3; NBA v3 tested against the same capabilities
- [[concepts/persistent-page-chrome-scraper-architecture]] - The persistent-page pattern reused in NBA v3 for per-game tab management
- [[concepts/playwright-node-pipe-crash-vector]] - Raw CDP eliminates the Playwright EPIPE crash vector; NBA v3 uses raw CDP for game pages
- [[concepts/mlb-parallel-scraper-workers]] - The MLB v3 architecture that NBA v3 mirrors; the learnings doc provides the reference blueprint
- [[concepts/bet365-nba-coupon-endpoint]] - Prior NBA optimization superseded by v3; dormant coupon branch remains as fallback
- [[concepts/cdp-browser-data-interception]] - Raw CDP response interception is the foundation; the race condition pattern is a v3-specific requirement

## Sources

- [[daily/lcash/2026-04-30.md]] - NBA v3 built on MLB v3 patterns: BB wizard returns 17 prop categories in one ~258 KB response; L3 marker confirmed as `NBA`; cache_stuck=3 observed on HOU@LAL (CDN TTL ~5+ min); all 14 EV names present, 10 "unknown" are main markets; CDP race condition: open blank → attach WS → Network.enable → navigate; MAX_CONCURRENT_REFRESHES=5; NBA_V3 env toggle with run_v3()/run_legacy() coexistence; ~720 lines mirroring MLB v3; local Chrome 9228 session expired independently from production (Session 11:09). Learnings doc referenced: `docs/BET365_SCRAPER_V3_LEARNINGS.md` — 12-section guide with NBA-specific differences (Session 10:36)
