---
title: "TAB Cold-Start Akamai Discovery Thrashing"
aliases: [tab-akamai-thrashing, tab-cold-start, discovery-thrashing, akamai-warmup, tab-discovery-overload, asyncio-cancelled-error-backoff]
tags: [superwin, tab, scraping, akamai, reliability, architecture, cold-start]
sources:
  - "daily/lcash/2026-05-30.md"
  - "daily/lcash/2026-05-31.md"
created: 2026-05-30
updated: 2026-05-31
---

# TAB Cold-Start Akamai Discovery Thrashing

TAB sportsbook's adapter exhibited a cold-start failure pattern where DISCOVERY_INTERVAL=60s with no backoff caused 60 Akamai requests per hour during failure windows, triggering cookie/fingerprint-layer throttling. The real root cause of TAB going offline was not a code bug but anti-bot behavioural gating by Akamai — the system reliably recovered after 10-15 minutes of warmup. The WebSocket pipeline is the real odds delivery mechanism; REST discovery only bootstraps the initial proposition_id list.

## Key Points

- DISCOVERY_INTERVAL=60s with no backoff created 60 Akamai requests/hour during failure, triggering cookie/fingerprint throttling — not IP-level blocking (homepage loads fine throughout)
- REST detail-fetch tried all 578 races in a single 120s cycle on cold start, exceeding timeout (121-123s) and cascading to kill WS subscriptions
- The `needs_discovery` flag created a vicious cycle: timeout before assignment completes → flag stays true → next cycle retries all 578 races again
- Discovery itself works fine (Tier 3 rescue via page.evaluate), but the volume of detail-fetches in one window is the bottleneck
- "Works after 10-15 min warmup" is the signature of anti-bot behavioural gating — don't chase code bugs when this symptom appears
- Fix: discovery interval 60s→3600s, exponential backoff on failure, interceptor wait 15s→60s, COLD_CHUNK=80 backfill pattern

## Details

### The Thrashing Pattern

TAB's adapter runs a REST discovery cycle to enumerate available racing propositions, then subscribes to WebSocket channels for live odds updates. On cold start or after a failure, DISCOVERY_INTERVAL was set to 60 seconds with no backoff. Each failed discovery attempt hit Akamai's anti-bot layer, which tracks behavioural patterns at the cookie and browser fingerprint level rather than by IP address. After enough rapid-fire failures, Akamai escalated its challenge responses, making subsequent requests increasingly likely to fail — a positive feedback loop.

The key diagnostic clue was that TAB's homepage loaded perfectly in manual browser testing while the scraper was blocked. This rules out IP-based blocking and points specifically to cookie/fingerprint behavioural gating. The system consistently recovered after 10-15 minutes of idle time, which is the characteristic cooldown pattern for behavioural anti-bot systems.

### Detail-Fetch Overload

Beyond discovery frequency, the cold-start detail-fetch pattern compounded the problem. When the adapter starts fresh, it has no cached proposition data, so it attempts to fetch details for all 578 races in a single 120-second cycle. REST timeouts at 121-123 seconds cascade and kill WebSocket subscriptions that depend on the proposition_id list populated by detail-fetch.

The `needs_discovery` flag was the core of the vicious cycle: if the detail-fetch times out before the proposition list is fully assigned, `needs_discovery` remains true. The next cycle then re-attempts all 578 races rather than just the delta, guaranteeing another timeout. This is structurally identical to the kind of retry storm that causes cascading failures in distributed systems.

### Architecture Insight: WS Is What Matters

A critical realization is that WebSocket is the real odds pipeline for TAB — discovery and detail-fetch only bootstrap the initial proposition_id list. Once WS subscriptions are established, odds flow in real-time without further REST requests. Therefore, discovery does not need to be fast or frequent. The user's insight captures it precisely: "as long as odds are quick... discovery doesn't have to be so quick because WS is what matters."

### The Fix

The solution addressed multiple layers. Discovery interval moved from 60s to 3600s (once per hour instead of once per minute). Exponential backoff was added on discovery failure so repeated failures produce geometrically increasing delays rather than hammering Akamai at a fixed rate. The interceptor wait increased from 15s to 60s, giving Akamai's challenge-response cycle time to settle.

For the cold-start overload, a COLD_CHUNK=80 backfill pattern was introduced. Instead of fetching all 578 races in one cycle, the adapter processes 80 races per cycle, spreading the load across multiple windows and staying well within the 120s timeout. This eliminates the `needs_discovery` vicious cycle because each chunk completes before timeout, allowing partial progress to persist.

### asyncio.CancelledError Backoff Bypass (2026-05-31)

On 2026-05-31, lcash discovered that the exponential backoff deployed on May 30 was being silently bypassed. The 120-second wrapper timeout throws `asyncio.CancelledError`, which is **NOT a subclass of `Exception`** in Python. The backoff code used `except Exception:` to catch failures and increment the backoff counter — but `CancelledError` (a subclass of `BaseException`) passed right through, meaning every wrapper timeout appeared as a clean exit rather than a failure. The backoff counter never incremented.

A second compounding issue: the backoff logic was placed inside `_do_rest_poll` (the inner function), but the outer `_rediscovery_loop` in `app/adapters/tab.py` re-invoked `_do_rest_poll` every 60 seconds regardless of the inner backoff state. Even if the inner backoff had worked, the outer loop bypassed it by simply calling the function again on a fixed schedule.

The fix moved backoff gating to the **outermost loop level** (`_rediscovery_loop`) where the `CancelledError` from the wrapper timeout is actually visible. A 1→5→15→30 minute ratchet (capped at 30 min) was implemented at this level. The result was a 10x reduction in Akamai pressure: 9 attempts in 3h11min vs the previous ~95 attempts in the same window.

The Tier 2 interceptor wait was also reduced from 60s to 30s to fit within the 120s wrapper timeout budget: Tier 2 (30s) + Tier 3 (15s) + Tier 4 (~30s) = 75s, comfortably within 120s.

Key lesson: **when fixing retry/backoff logic, the gating must happen at the outermost loop that controls re-invocation, not inside the function being retried.** And `asyncio.CancelledError` must be caught explicitly (`except (Exception, asyncio.CancelledError):` or `except BaseException:`) in any timeout-wrapped async code.

### Cookie-Mint Tier 2.5 (2026-05-31)

After the backoff fix reduced Akamai pressure, a faster discovery path was deployed: Tier 2.5 harvests the `AKA_A2=A` cookie from the Playwright page and calls the API directly with curl_cffi chrome131, bypassing the 30s interceptor wait entirely. See [[concepts/tab-akamai-cookie-minter-bypass]] for the full analysis.

TAB eventually self-recovered via Tier 3 (page.evaluate) once the Akamai cooldown expired (~10 hours after the thrashing), confirming that patience + reduced retry pressure is the correct strategy during Akamai lockout.

## Related Concepts

- [[concepts/tab-global-ws-rotation-pattern]] - The WebSocket rotation strategy that TAB's real-time odds pipeline uses; discovery thrashing blocks WS setup by failing to populate proposition_id lists
- [[concepts/scanner-warmup-false-ev-guard]] - Warmup guard pattern that prevents false picks during the same cold-start window where Akamai thrashing occurs
- [[concepts/betr-sticky-proxy-cloudflare-sessions]] - Parallel anti-bot session management pattern for Cloudflare-protected bookies; same class of problem as Akamai behavioural gating
- [[concepts/tab-scraper-threshold-markets]] - TAB scraper market thresholds that depend on stable discovery data; thrashing undermines the data these thresholds rely on
- [[concepts/tab-akamai-cookie-minter-bypass]] - The Tier 2.5 cookie-mint approach deployed on May 31 that eliminates the 30s interceptor wait when Akamai cookies are available

## Sources

- [[daily/lcash/2026-05-30.md]] - REST timeouts (121-123s) cascading to kill WS subscriptions; DISCOVERY_INTERVAL=60s with no backoff causing 60 Akamai requests/hour; needs_discovery vicious cycle; Akamai throttling at cookie/fingerprint layer not IP; "works after 10-15 min warmup" = anti-bot behavioural gating; discovery interval 60s→3600s; COLD_CHUNK=80 backfill pattern; interceptor wait 15s→60s
- [[daily/lcash/2026-05-31.md]] - Backoff bypassed by asyncio.CancelledError (not subclass of Exception); inner backoff bypassed by outer 60s loop; fix: backoff at outermost loop level with 1→5→15→30 min ratchet; 10x reduction (9 attempts/3h11min vs ~95); Tier 2 wait 60s→30s; Akamai cooldown confirmed ~10 hours; CookieMinter Tier 2.5 deployed (Sessions 18:36, 19:11, 20:01, 21:05)
