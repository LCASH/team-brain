# Betstamp

## Status: current
## Last verified: 2026-04-08 (seeded from codebase exploration)

> Betstamp Pro WebSocket client for real-time Bet365 odds.

---

## What It Is

Betstamp Pro is a paid odds comparison service that provides real-time Bet365 odds via WebSocket. It serves as the primary fallback (and often primary source) for Bet365 odds when direct CDP scraping is unavailable or unreliable.

**Source:** `ev_scanner/betstamp_bet365.py` (~18KB)

---

## How It Works

1. **Auth:** Logs in with email/password credentials (from `.env`)
2. **WebSocket:** Establishes persistent WebSocket connection to Betstamp servers
3. **Subscription:** Subscribes to Bet365 player prop markets
4. **Streaming:** Receives real-time odds updates as they change
5. **Output:** Converts to unified `ScrapedOdds` format

---

## Advantages Over Direct Scraping

| Aspect | Betstamp | Direct CDP |
|--------|----------|------------|
| Reliability | Very high | Fragile (DOM changes, bot detection) |
| Speed | Real-time (WebSocket push) | Cycle-based (20s polls) |
| Coverage | All Bet365 markets | Only markets you navigate to |
| Headless | Yes | MLB requires non-headless |
| Cost | Paid subscription | Free (but labor-intensive) |

---

## Provider 999

Betstamp also exposes a "provider 999" no-vig true line. This is Betstamp's own devigged estimate. It's used for **comparison only** (not in EV calculation) — visible in the dashboard comparison tab alongside our EV and BetIQ's EV.

---

## Related Pages
- [[bet365-scraper]] — Primary Bet365 source (CDP)
- [[opticodds]] — Primary sharp book source
- [[direct-scrapers]] — Other AU bookie sources
