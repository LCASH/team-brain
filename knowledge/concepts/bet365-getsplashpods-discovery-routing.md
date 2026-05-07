---
title: "bet365 getsplashpods Discovery Routing"
aliases: [getsplashpods-routing, discovery-home-page, pullpodapi-capture, bc-grace-check, discovery-url-routing, dynamic-df-segments]
tags: [bet365, scraping, discovery, architecture, value-betting, reverse-engineering]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 getsplashpods Discovery Routing

bet365's `getsplashpods` API — the primary game discovery endpoint — only fires when the SPA is navigated to `#/HO/` (the home page). Navigating to sport-specific URLs (`#/AS/B18/AC/`, `#/AS/AC/B18/`, `#/AS/D48/F10/`) does NOT trigger getsplashpods, regardless of URL format. This was discovered on 2026-05-07 after multiple failed URL format attempts for NBA discovery. Additionally, `pullpodapi` responses must be captured alongside `contentapi` — games visible in the browser were invisible to the scanner because only `contentapi` was in the capture filter. The `BC` (broadcast/calendar) field stores midnight of game date, not actual tip-off time, making BC-based grace checks unreliable for US afternoon/evening games.

## Key Points

- **`getsplashpods` only fires from `#/HO/`** (home page) — sport-specific URLs (`#/AS/B18/AC/`, `#/AS/AC/B18/`, `#/AS/D48/F10/`) never trigger it regardless of format
- **`pullpodapi` must be captured** alongside `contentapi` — getsplashpods responses route through `pullpodapi`, not `contentapi`; silently dropped games when only `contentapi` was filtered
- **BC field = midnight UTC of game date**, not tip-off time — comparing `BC > now_utc` incorrectly skips afternoon/evening US games that haven't started yet; `ES=2` (live state) filtering is sufficient
- **D/F segments must be derived dynamically** from `PD=` field in getsplashpods response stored in `GameInfo.page_path` — hardcoding D48/F10 breaks when bet365 changes routing (playoffs vs regular season use different D/F values)
- **`allsportsmenu`** (left-nav API on homepage boot) surfaces tomorrow's playoff games before `getsplashpods` does — multiple discovery endpoints are needed for complete coverage
- **Single-game splash limitation**: `getsplashpods` may show only the "next game" per sport; simultaneous games (e.g., two 12:30 PM ET NBA tips) require additional discovery from competition pages

## Details

### The URL Format Investigation

On 2026-05-07, NBA discovery was failing with "no game signal within 20s." Investigation traced the issue through multiple wrong URL formats:

| URL Attempted | Result | Why It Failed |
|--------------|--------|---------------|
| `#/AS/AC/B18/` | No getsplashpods | Reversed path segments |
| `#/AS/B18/AC/` | No getsplashpods | Correct format per July 2025 logs but doesn't trigger getsplashpods |
| `#/AS/D48/F10/` | No getsplashpods | DraftKings format — wrong for Australian bet365 |
| `#/HO/` | **getsplashpods fires** | Home page is the only trigger URL |

The confusion arose because: (1) hash-navigation to sport URLs was introduced as a workaround for the "empty home page on re-entry" bug, but it was solving the wrong problem — the real fix for empty home pages is `page.reload()` on `#/HO/`, not navigating to sport URLs; (2) July 2025 working logs showed `#/AS/B18/AC/` format being used successfully, but that format worked for a different API endpoint, not getsplashpods.

### pullpodapi Capture Gap

Games were visible in the browser but invisible to the scanner because the production capture filter only matched `contentapi` endpoints. The `getsplashpods` response routes through `pullpodapi` — a different API namespace. Adding `pullpodapi` to the capture filter immediately surfaced events (E25635191, E25648962) that were previously silently dropped.

This is a recurring pattern in the scanner: capture filters that work for the primary data flow silently miss secondary endpoints. The same class of issue appeared with `batchmatchbettingcontentapi` vs `matchbettingcontentapi` during the MLB batch API migration (see [[concepts/bet365-mlb-batch-api-co-format]]).

### BC Grace Check Removal

The discovery filter included a BC (broadcast/calendar) grace check: `if BC < now_utc: skip game`. This was intended to filter out games that had already started. However, BC values store midnight UTC of the game date, not the actual tip-off time. For US afternoon games (e.g., 12:30 PM ET = 04:30 UTC next day, but BC = 00:00 UTC of that day), the BC timestamp is already in the past by late morning — causing the filter to incorrectly skip games that haven't started yet.

The fix removes BC grace checking entirely from both Pass 1 and Pass 2 of discovery. Live-state filtering via `ES=2` (event status = live/in-play) is sufficient to exclude currently active games without incorrectly filtering pre-game events.

### Dynamic D/F Segment Derivation

URL path segments D (display context) and F (filter) vary between regular season and playoffs — D19/F19 for regular season NBA, D48/F10 for playoffs. Hardcoding these values breaks when the season transitions. The fix derives D/F segments dynamically from the `PD=` field in getsplashpods responses, stored in `GameInfo.page_path`. If bet365 changes routing tomorrow (new competition structure, new playoff round), discovery picks it up automatically without code changes.

This follows the same principle as the dynamic B-number discovery documented in [[concepts/bet365-multi-sport-dynamic-enumeration]]: only sport B-numbers are stable long-term; all other path segments (C, D, E, F) change seasonally or weekly.

### Single-Game Splash Limitation

The `getsplashpods` widget shows the "next game" or featured game per sport, not all upcoming games. When two games tip off simultaneously (e.g., MIN@SA and BOS@MIL both at 12:30 PM ET), only one appears in the splash. The other is discoverable only when the splash rotates (after the first game tips off) or from the competition page (`allsportsmenu` → competition listing).

This limitation means V3's discovery cannot guarantee coverage of all simultaneous games from `getsplashpods` alone. Complete coverage requires supplementary discovery from: (1) `allsportsmenu` on homepage boot (surfaces tomorrow's featured/playoff games), (2) competition-level pages that list all games for a league, or (3) manual event_id injection for known games.

### Windows Task Auto-Restart

In the same session, a `VB_V3_Restart` Windows scheduled task was created to ensure V3 restarts reliably after crashes: triggers on system startup plus every 5 minutes if the process is not running, executing `start_v3.bat`. Testing confirmed the restart preserves Chrome login sessions (Chrome processes are not killed — only the Python V3 process restarts). A prior EPIPE crash at 23:10:50 was not caught by the previous schtask, motivating the more robust 5-minute polling approach.

## Related Concepts

- [[concepts/spa-navigation-state-api-access]] - The broader SPA navigation constraints that getsplashpods routing is part of; `#/HO/` is now confirmed as the only discovery trigger URL
- [[concepts/bet365-multi-sport-dynamic-enumeration]] - Dynamic B-number discovery parallels the D/F segment derivation; both avoid hardcoded path segments that break on season changes
- [[concepts/cdpsession-playwright-pipe-contention]] - Discovery runs on a dedicated page to avoid CDPSession contention; the getsplashpods routing is the first operation on that page
- [[concepts/bet365-mlb-batch-api-co-format]] - The `pullpodapi` capture gap mirrors the `batchmatchbettingcontentapi` vs `matchbettingcontentapi` filter gap — same class of silent endpoint omission
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture whose discovery layer this article documents; `_do_rediscover` navigates to `#/HO/` on every cycle
- [[connections/anti-scraping-driven-architecture]] - The getsplashpods routing constraint is a facet of the SPA navigation state defense layer (layer 3)

## Sources

- [[daily/lcash/2026-05-07.md]] - Multiple URL formats tested (`#/AS/AC/B18/`, `#/AS/B18/AC/`, `#/AS/D48/F10/`) — all failed; only `#/HO/` triggers getsplashpods; pullpodapi capture gap silently dropped games; BC field = midnight UTC not tip-off; D/F segments derived dynamically from PD field; allsportsmenu surfaces future playoff games; two simultaneous games (MIN@SA + BOS@MIL) exposed single-game splash limitation; VB_V3_Restart schtask with 5-min polling deployed (Sessions 09:51, 11:22, 13:56)
