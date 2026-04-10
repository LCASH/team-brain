# Pattern: Debugging EV Calculations

> Common EV calculation issues and how to trace them.

---

## Symptom: EV is 0% or negative for a market you expect to be +EV

### Check 1: Are sharp books available?
- Look at the market in the dashboard — does it show sharp book data?
- If no sharp books: the market falls to consensus (lower confidence, lower weighted EV)
- If consensus also empty: the market can't be evaluated at all

### Check 2: Is interpolation working?
- If sharp_line != soft_line, interpolation must bridge the gap
- Check the prop type → is it using logit (continuous) or Poisson (count)?
- Check the beta value — too low and interpolation barely adjusts

### Check 3: Is the theory's threshold too high?
- A pick with 4% EV and 1.5 confidence has weighted EV of 1.2%
- If the theory requires min_weighted_ev > 1.5%, this pick is filtered out

---

## Symptom: Our EV is much lower than BetIQ's for the same pick

### Check 1: Devig method
- BetIQ likely uses additive (equal margin). Our default leans multiplicative.
- Additive tends to give slightly higher EV estimates for favorites.
- Compare all 4 methods side by side.

### Check 2: Sharp book selection
- We may weight different books than BetIQ
- Check which books have data for this market and their weights
- FanDuel at weight 0 means we ignore it — BetIQ may not

### Check 3: Interpolation delta
- If our sharp books are at a different line, interpolation can shift true odds
- Check the line difference and the applied beta

### Check 4: Timing
- BetIQ and our scanner sample odds at different times
- Odds can move 5-10% in minutes — timing explains some of the gap

---

## Symptom: Picks are being tracked that shouldn't be (stale or bad data)

### Check 1: Is the game live?
- The `is_live: false` filter should exclude live games
- If it's leaking through, check the OpticOdds fixture response

### Check 2: Are odds stale?
- Check the timestamp on the odds — if they're hours old, the book may have removed the market
- OpticOdds sometimes returns cached odds after a market closes

### Check 3: Is the player injured/out?
- The scanner doesn't check injury reports
- A player ruled out will have their props removed by sharp books first, then soft books later
- In the gap, you might see "phantom" +EV (soft book hasn't removed yet)

---

## Diagnostic Tools

| Tool | What It Does |
|------|-------------|
| `/syscheck` | Morning system health check — VPS, resolver, tracker, picks, results |
| `/vb health` | Quick health across all sport servers + push worker |
| `/reverse-betiq` | Compare our numbers against BetIQ's for parameter matching |
| Dashboard Comparison tab | Side-by-side EV: ours vs BetIQ vs Betstamp |
| `trail_entries` table | Full odds history for any tracked pick |

---

## System Health Debugging

### API Key Mismatch (Incident: 2026-04-08, blocked 12+ hours)

**Symptom:** Resolver reports 401 errors for all sports. Odds scraping works fine (uses different endpoint).

**Root cause:** VPS `.env` at `/opt/value-betting/.env` had an expired `OPTICODDS_API_KEY`. The key was rotated locally but not updated on VPS.

**Detection:**
```bash
# Check VPS health
curl http://170.64.213.223:8802/api/v1/health

# Compare API keys
ssh root@170.64.213.223 'grep OPTICODDS /opt/value-betting/.env'
grep OPTICODDS .env
```

**Fix:** Update VPS `.env` and restart:
```bash
ssh root@170.64.213.223 "sed -i 's/OPTICODDS_API_KEY=.*/OPTICODDS_API_KEY=<new_key>/' /opt/value-betting/.env && systemctl restart value-betting"
```

**Prevention:** After rotating any API key locally, immediately update VPS too.

### Resolver `last_result` is Misleading

The health endpoint's `resolver.last_result` only shows the **last sport processed** (afl, since order is nba → mlb → nrl → afl). An AFL error does NOT mean NBA failed. Check VPS journal logs for per-sport results:

```bash
ssh root@170.64.213.223 'journalctl -u value-betting --since "1 hour ago" | grep -i resolv'
```

### Manual Resolution Trigger

When auto-resolver missed picks or after fixing an error:
```
GET http://170.64.213.223:8802/api/v1/resolve?date=2026-04-08
```
Can take 30-90 seconds for large date sets. Check logs for progress.

### VPS Log Inspection

```bash
# Recent logs
ssh root@170.64.213.223 'journalctl -u value-betting -n 100'

# Errors only
ssh root@170.64.213.223 'journalctl -u value-betting --since "1 hour ago" | grep -iE "error|fail|401|500"'

# Service status
ssh root@170.64.213.223 'systemctl status value-betting'
```

### Null Player Name Constraint Bug

**Symptom:** Tracker logs show constraint violations inserting picks with `player_name = null`.

**Status:** Under investigation (as of 2026-04-09). Source is likely a scraper returning odds without player info, or a market matcher edge case.

### Supabase I/O Budget

If you see 522 errors from Supabase, the disk I/O budget is exhausted. Check Supabase dashboard. The trail_entries optimization (INSERT vs JSONB patch) reduced I/O by 90-95%, but high-volume days can still approach limits.
