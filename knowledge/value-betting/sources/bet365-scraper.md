# Bet365 Scraper

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Direct scraping of Bet365 game pages via Chrome DevTools Protocol.

---

## What It Does

Scrapes player prop odds directly from Bet365's web SPA by controlling a Chrome browser via CDP (Chrome DevTools Protocol). This gets Bet365 odds that aren't available through OpticOdds.

**Source:**
- `ev_scanner/bet365_game.py` (~31KB) — NBA game scraper
- `ev_scanner/bet365_mlb_game.py` (~41KB) — MLB game scraper

---

## How It Works

1. **Browser:** Uses AdsPower anti-detect browser profiles (one per account) via Playwright CDP connection
2. **Navigation:** Navigates Bet365's hash-based SPA to the sport → game → player props / bet builder sections
3. **Parsing:** Extracts player names, prop types, lines, and odds from the rendered DOM
4. **Output:** ~2,000 odds per scrape cycle (NBA), unified to the same `ScrapedOdds` format as OpticOdds

---

## NBA vs MLB Differences

| Aspect | NBA (`bet365_game.py`) | MLB (`bet365_mlb_game.py`) |
|--------|----------------------|---------------------------|
| Browser | AdsPower headless OK | **Must be non-headless** (Cloudflare blocks headless) |
| Navigation | Direct to game page | Hash-nav to sport, then per-game |
| Complexity | Simpler (standard props) | More complex (pitcher stats, game props) |
| Size | 31KB | 41KB |

---

## Betstamp Fallback

When AdsPower/CDP scraping times out or fails, the scanner falls back to [[betstamp]] (Betstamp Pro WebSocket) for Bet365 odds. Betstamp is more reliable but is a paid service with its own limitations.

---

## Known Issues

- **AdsPower dependency:** Requires Electron app for IPC bridge. Web build can't use it.
- **Cloudflare:** MLB requires non-headless Chrome, making it harder to run in background.
- **SPA fragility:** Bet365 regularly changes their DOM structure, requiring selector updates.
- **Rate limiting:** Too many requests can trigger Bet365's bot detection.

---

## Related Pages
- [[betstamp]] — Fallback Bet365 odds source
- [[direct-scrapers]] — Other AU bookie scrapers
- [[deployment]] — Where scrapers run (mini PC)
