---
title: "Playwright Locator Hang on Heavy SPAs"
aliases: [playwright-locator-hang, get-by-text-hang, dom-scan-materialization, live-nodelist-hang, array-from-dom-fix]
tags: [value-betting, playwright, bet365, browser-automation, bug, reliability]
sources:
  - "daily/lcash/2026-05-08.md"
created: 2026-05-08
updated: 2026-05-08
---

# Playwright Locator Hang on Heavy SPAs

On 2026-05-08, lcash discovered that Playwright's `page.get_by_text("MLB", exact=True).first.count()` hangs indefinitely on bet365's heavy SPA — even with a 3-second timeout wrapper — despite the target `<span>` element being visible in the DOM at known coordinates (50, 438). The fix replaces Playwright locators with raw JavaScript DOM traversal via `page.evaluate()`, using `Array.from()` to materialize live NodeList collections before iteration. A secondary finding: live `querySelectorAll()` iteration can also hang when the DOM mutates during `getBoundingClientRect()` calls, triggering SPA observers that modify the collection being iterated.

## Key Points

- `page.get_by_text()` hangs on bet365's SPA even when the element is visible and clickable — the locator resolution itself gets stuck, not the element interaction
- `locator.count()` has no implicit timeout (unlike `bbox()` which has 3s) — always wrap Playwright CDP/locator calls with explicit timeouts
- Raw `page.evaluate()` with JS DOM traversal is more reliable: walk `querySelectorAll('span,a,div')`, check `textContent.trim()`, return center coordinates
- **Live NodeList iteration hangs**: `querySelectorAll()` returns a live collection; if the DOM mutates during `getBoundingClientRect()` (which triggers layout recalc → SPA observers → DOM mutation), the iterator gets stuck in an infinite loop
- **Fix**: `Array.from(document.querySelectorAll(...))` materializes the live collection into a static array before walking; add per-element `try/catch`, 8000-element cap, and early break on 5 matches
- When multiple DOM elements match a text selector, iterate candidates and verify post-click URL rather than taking first match — bet365 sidebar had 2 elements matching "MLB"

## Details

### The Playwright Locator Problem

Playwright's locator API (`page.get_by_text()`, `page.locator()`) provides high-level element resolution with built-in auto-waiting and retry logic. On typical web pages, this works reliably. On bet365's heavy SPA — which has thousands of DOM elements, continuous JavaScript execution for odds streaming, and mutation observers triggering on layout recalculation — the locator resolution process itself becomes stuck.

The failure mode is distinctive: the locator never throws a timeout error, never returns false, and never completes. It enters an internal retry/polling loop that Playwright's auto-waiting mechanism doesn't escape. This is different from the `page.evaluate()` hang documented in [[concepts/playwright-evaluate-uncancellable]] (where the browser's JS context is unresponsive) — here, the browser is responsive (CDP commands work), but Playwright's internal locator resolution machinery gets stuck.

The investigation traced the issue to bet365's sidebar navigation: the `<span>` element with text "MLB" was confirmed visible at coordinates (64, 446) via CDP screenshot analysis, and a direct `page.mouse.click(64, 446)` succeeded immediately. Only Playwright's locator API failed to resolve it.

### The Live NodeList Mutation Hang

When the Playwright locator was replaced with raw `page.evaluate()` using `document.querySelectorAll('span,a,div')`, a second hang was discovered. The JavaScript `querySelectorAll` returns a **live NodeList** — if the DOM changes while iterating, the collection's internal state can become inconsistent. On bet365's SPA, calling `getBoundingClientRect()` on an element triggers layout recalculation, which fires mutation observers, which modify the DOM, which invalidates the collection being iterated — an infinite cycle.

The fix materializes the live collection before iterating:

```javascript
const els = Array.from(document.querySelectorAll('span,a,div'));
for (const el of els) {
  try {
    if (el.textContent.trim() === targetText) {
      const r = el.getBoundingClientRect();
      return { x: r.x + r.width/2, y: r.y + r.height/2 };
    }
  } catch (e) { continue; }
}
```

`Array.from()` creates a static snapshot of the collection at that moment. Subsequent DOM mutations don't affect the array. The per-element `try/catch` handles elements that are removed from the DOM between snapshot and access. The 8000-element cap and early break on 5 matches prevent scanning the entire bet365 DOM (which can have 20,000+ elements).

### Post-Click URL Verification

A related sidebar click bug was discovered: `matched=2` for "MLB" — two DOM elements contained the text "MLB". Taking the first match clicked the wrong element (a parent container or unrelated label). The fix iterates all candidates, clicks each one, and verifies the post-click URL contains the expected competition ID (`C20525425` for MLB). If the URL doesn't match, the click is undone and the next candidate is tried.

### SPA Hash Routing Requirement

A third discovery: bet365's SPA requires `#/HO/` (hash-based routing) to render sidebar navigation elements. When the page boots to bare `bet365.com.au/` without the hash, only a minimal shell renders — no sidebar, no sport links, no discovery targets. The fix force-navigates to `#/HO/` after boot if the URL is bare. This is the same SPA routing requirement documented in [[concepts/bet365-getsplashpods-home-page-constraint]] but applied to the sidebar DOM rendering, not just API call triggering.

## Related Concepts

- [[concepts/playwright-evaluate-uncancellable]] - A different Playwright hang mode: `page.evaluate()` blocks when the browser's JS context is unresponsive. The locator hang occurs even when evaluate works fine
- [[concepts/bet365-cdpsession-pipe-contention]] - Another Playwright interaction failure: CDPSession consuming the pipe blocks evaluate/goto. The locator hang is a higher-level API failure, not a pipe contention issue
- [[concepts/spa-navigation-state-api-access]] - SPA requires `#/HO/` for sidebar rendering; the locator hang is compounded by missing hash routing
- [[concepts/bet365-getsplashpods-home-page-constraint]] - `#/HO/` requirement for API calls mirrors the sidebar rendering requirement
- [[connections/playwright-elimination-scraper-reliability]] - Progressive Playwright elimination: locator hangs on heavy SPAs add another reliability argument for raw JS/CDP over Playwright abstractions

## Sources

- [[daily/lcash/2026-05-08.md]] - `page.get_by_text("MLB", exact=True).first.count()` hangs indefinitely on bet365; element confirmed at (50, 438) via CDP; `locator.count()` has no implicit timeout; replaced with `page.evaluate()` JS DOM scan (Session 10:44). Live NodeList iteration hang from `getBoundingClientRect()` triggering SPA observers during DOM walk; fix: `Array.from()` materialization + per-element try/catch + 8000-element cap + early break; `matched=2` for "MLB" — iterate candidates + verify post-click URL (Session 12:11). SPA boots to bare URL without `#/HO/` → sidebar never renders → DOM scan timeout; force-navigate to `#/HO/` after boot (Session 11:17). bet365's `marketscontentapi` returns 0 fixtures on single-game MLB days — the game only appeared when sidebar click actually navigated to competition root (Session 10:44)
