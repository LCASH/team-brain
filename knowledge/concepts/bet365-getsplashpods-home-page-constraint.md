---
title: "bet365 getsplashpods Home Page Constraint"
aliases: [getsplashpods-home-only, splash-home-page, discovery-url-constraint, ho-navigation, pullpodapi-capture-gap]
tags: [value-betting, bet365, scraping, discovery, architecture, reverse-engineering]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 getsplashpods Home Page Constraint

The bet365 `getsplashpods` API — the primary game discovery mechanism for the V3 scanner — only fires when the browser navigates to the home page (`#/HO/`). Navigating to sport-specific URLs (`#/AS/B18/AC/`, `#/AS/AC/B18/`, `#/AS/D48/F10/`) does NOT trigger getsplashpods, regardless of URL format. This was discovered on 2026-05-07 after multiple incorrect URL formats were tested and all failed, until brain docs and July 2025 working logs revealed that the discovery signal has always come from the home page, not sport pages.

## Key Points

- `getsplashpods` only fires from `#/HO/` (home page navigation) — no sport-specific URL triggers it
- Multiple wrong URL formats tested: `#/AS/AC/B18/`, `#/AS/B18/AC/`, `#/AS/D48/F10/` — all failed silently (page loaded, no API call fired)
- The hash-nav to sport URLs was introduced to work around an "empty home page on re-entry" bug, but this was the wrong fix — it eliminated the signal entirely
- The correct fallback for empty home page results is `page.reload()` on `#/HO/`, not navigation to sport pages
- `pullpodapi` responses were also being missed — production filter only captured `contentapi` but not `pullpodapi`, silently dropping getsplashpods responses
- Discovery found 104 total games (12 NBA + 15 MLB + others) once the correct `#/HO/` navigation was restored
- The `BC` (broadcast/date) field in discovery responses stores **midnight of game date** (local time), NOT actual tip-off time — comparing `BC` to `now_utc` incorrectly skips afternoon/evening US games

## Details

### The URL Investigation Chain

On 2026-05-07, NBA and MLB discovery was failing with "no game signal within 20s" errors. The investigation went through multiple incorrect URL formats before finding the root cause:

1. **`#/AS/AC/B18/`** — tried first based on pattern assumption; loaded the sport listing page but triggered zero API calls
2. **`#/AS/B18/AC/`** — based on July 2025 working logs that showed this format; also failed to trigger getsplashpods
3. **`#/AS/D48/F10/`** — DraftKings-style format; failed identically
4. **Brain doc analysis** — revealed getsplashpods fires on the **home page** (`#/HO/`), not any sport page
5. **`#/HO/` navigation** — immediately triggered getsplashpods and returned 104 games

The critical insight was that all the sport-specific URL formats are valid SPA routes (the page loads and renders) but they don't trigger the `getsplashpods` API call. Only the home page (`#/HO/`) fires this API because getsplashpods is the home page's data source — it populates the "featured games" and "next to start" widgets on bet365's landing page.

### Why Sport URLs Were Used (Incorrectly)

The sport-specific hash-nav was introduced to work around an "empty home page on re-entry" bug: when the browser was already on bet365 and navigated back to `#/HO/`, the SPA sometimes served cached/empty splash results instead of making a fresh API call. The developer reasoned that navigating to a sport page first, then back to home, would force a fresh load. Instead, the sport-page navigation itself became the discovery step — eliminating the `#/HO/` navigation entirely and losing the getsplashpods signal.

The correct fix for the empty home page bug is `page.reload()` on `#/HO/`, which forces a full page reload including the API call. This is simpler and more reliable than the sport-page detour.

### pullpodapi Capture Gap

A secondary discovery bug was found simultaneously: the response capture filter in `discovery.py` only matched `contentapi` URLs but getsplashpods responses come from `pullpodapi/gethomepagepods`. This meant that even when navigation to `#/HO/` was correct, the getsplashpods response was silently dropped by the URL filter. Adding `pullpodapi` to the captured endpoint patterns fixed this gap.

### BC Field Midnight Semantics

The `BC` field in getsplashpods responses was being used as a grace check to filter "too early" games. Investigation revealed that `BC` stores midnight of the game date in local time — not the actual tip-off time. For US evening games (e.g., 7:30 PM ET = 09:30 UTC next day), comparing `BC` (midnight UTC) against `now_utc` incorrectly classified afternoon and evening games as "not yet available" because the midnight timestamp had already passed. The `BC` grace check was removed entirely — the `ES=2` live-state filter is sufficient to exclude already-started games.

### CDPSession Interaction

The discovery hang was compounded by CDPSession pipe contention (see [[concepts/bet365-cdpsession-pipe-contention]]): even when the correct URL was used, the hash-nav `page.evaluate("location.hash = '#/HO/'")` hung because the orchestrator's CDPSession was consuming the Playwright pipe. The combined fix required both the correct URL (`#/HO/`) AND a dedicated discovery page (free from CDPSession contention).

### Single-Game-Per-Sport Limitation

The getsplashpods API returns the next/featured game per sport from bet365's splash widget — not all scheduled games. When two games have the same tip-off time (e.g., MIN@SA and BOS@MIL both at 12:30 PM ET), only one appears in the splash. The second game is only discoverable once the first finishes or when bet365 rotates the featured game. This is a fundamental limitation of splash-based discovery.

For comprehensive game coverage, the scanner would need to also parse `gethomepageadditionalpods` (which contains all upcoming events) or navigate to the sport-specific listing page after discovery to capture games not featured in the splash.

## Related Concepts

- [[concepts/bet365-cdpsession-pipe-contention]] - CDPSession pipe contention compounded the discovery failure; even correct URLs hung when the CDPSession was active on the same page
- [[concepts/spa-navigation-state-api-access]] - The broader SPA navigation constraint system; getsplashpods home-page exclusivity is a specific instance of bet365's navigation-state-dependent API access
- [[concepts/bet365-splash-timing-dependency]] - The splash endpoint's time-of-day population delay (0 meetings before ~09:00 AEST); the home-page constraint is a separate issue (wrong URL) from the timing dependency (right URL, no data yet)
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS orchestrators whose discovery phase depends on getsplashpods; the home-page fix was deployed as part of the V3 scraper integration
- [[concepts/v3-scanner-centralized-architecture]] - The V3 architecture where this discovery constraint was resolved

## Sources

- [[daily/lcash/2026-05-07.md]] - Multiple wrong URL formats tested (#/AS/AC/B18/, #/AS/B18/AC/, #/AS/D48/F10/) — none triggered getsplashpods; brain docs revealed signal only fires from #/HO/; pullpodapi not in capture filter dropped responses; BC field is midnight not tipoff — grace check removed; 104 games found after fix (12 NBA, 15 MLB); CDPSession Network.disable/enable during hash-nav eliminated WS flood delay; single-game-per-sport splash limitation identified (Sessions 09:51, 11:22, 13:56)
