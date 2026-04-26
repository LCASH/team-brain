---
title: "Twitter/X API Scraping Constraints"
aliases: [x-api-rate-limits, twitter-scraping, twscrape-blocking, graphql-rate-limits, twitter-anti-bot, twitter-auth, self-healing-auth, adspower-login]
tags: [value-betting, twitter, scraping, rate-limiting, anti-bot, news-pipeline]
sources:
  - "daily/lcash/2026-04-25.md"
  - "daily/lcash/2026-04-26.md"
created: 2026-04-25
updated: 2026-04-26
---

# Twitter/X API Scraping Constraints

The value betting scanner's news agent pipeline requires scraping Twitter/X for real-time injury tweets from NBA and MLB insiders. Three layers of anti-bot defenses were discovered on 2026-04-25: Cloudflare blocking programmatic login from Australian IPs, X's anti-automation JavaScript detecting and defeating Playwright-driven login, and GraphQL API rate limits that are tracked per endpoint-type + auth-token (not per IP or per query ID). Extended rate limits (hours, not the standard 15-minute window) appear to trigger from repeated 429 responses, creating a feedback loop where checking rate limit status extends the lockout.

## Key Points

- **twscrape programmatic login blocked**: Cloudflare returns 403 from Australian IPs for X.com login endpoints — same ASN-level blocking pattern as bet365
- **Playwright anti-automation detected**: X.com's client-side JavaScript detects Playwright automation and clears typed input fields even in real Chrome mode (`channel: "chrome"`) — more aggressive than bet365's headless detection
- **GraphQL rate limits are per endpoint-type + auth-token**, NOT per query ID — swapping GraphQL query IDs (`naBcZ4al` vs `V7H0Ap3_Hh2FyS75OCDO3Q`) does not bypass limits
- **Extended lockout feedback loop**: Hitting 429 responses resets the cooldown window; checking "when does the limit reset?" burns a call and pushes the window out further — must do a **complete hard blackout** with zero API calls
- **50 requests per 15-minute window** for the `user_tweets` endpoint; `resolve_user_id` shares or has its own limited pool
- Manual browser login + cookie extraction (`auth_token` + `ct0`) was the initial viable path; now automated via `twitter_auth.py` with curl_cffi API login (username → email challenge → password → TOTP 2FA → cookie export) and AdsPower anti-detect browser as the reliable fallback
- **AdsPower bypasses all fingerprinting** where Playwright fails — `twitter_auth.py` integrates `login_if_expired()` auto-refresh so cookie renewal is transparent to the scraper

## Details

### Three Defense Layers

Twitter/X employs three independent anti-bot layers that each block a different scraping approach:

**Layer 1 — Cloudflare IP Reputation (Network):** The `twscrape` library's built-in `login_all()` function attempts to authenticate via X.com's login API endpoints. From Australian IPs (both residential and datacenter), Cloudflare returns HTTP 403 before the request reaches X's servers. This is the same ASN-level blocking pattern documented for bet365 in [[connections/anti-scraping-driven-architecture]], but applied to X.com's authentication endpoints specifically.

**Layer 2 — Anti-Automation JavaScript (Application):** Attempting to bypass Cloudflare via Playwright with a real Chrome instance (`channel: "chrome"`) initially loads the login page successfully. However, X's client-side JavaScript detects the automation context and actively interferes: typed input is cleared from username and password fields even as characters are being entered. This is more aggressive than bet365's headless detection (which serves empty data) — X actively defeats the interaction rather than passively withholding data.

**Layer 3 — GraphQL Rate Limiting (API):** The Twitter GraphQL API enforces rate limits per endpoint type (e.g., `UserTweets`) combined with the authentication token. The limit is approximately 50 requests per 15-minute window for the `user_tweets` endpoint. Browser-rendered queries use different GraphQL query IDs than programmatic scripts, but testing confirmed the QID is irrelevant — X tracks limits by the endpoint classification and the bearer/auth token pair, not by the specific query hash.

### The Extended Lockout Feedback Loop

Standard rate limits on the Twitter GraphQL API expire after 15 minutes. However, continued requests during a rate-limited period appear to trigger an **extended lockout** that can last hours. The mechanism is that each 429 response (rate limit exceeded) is itself counted against the rate limit window, resetting the cooldown timer. This creates a feedback loop: the developer checks whether the limit has reset → the check counts as a request → the limit window extends → the developer checks again → cycle continues.

The only reliable recovery is a **complete hard blackout**: zero API requests of any kind for the full window duration. Any request — even a lightweight one to check status — extends the lockout. This was discovered empirically on 2026-04-25 when lcash's MLB insider speed analysis repeatedly triggered extended lockouts across multiple testing approaches over several hours.

### Viable Authentication Path

X/Twitter API access requires two cookies:

1. **`auth_token`** — the session authentication cookie, persists for weeks-months under normal operation
2. **`ct0`** — the CSRF token, rotates more frequently

These cookies bypass all three defense layers: no Cloudflare challenge (cookies prove prior human login), no anti-automation JS (no login interaction needed), and the API calls use a legitimate authenticated session. Initially, cookies were extracted manually from a browser DevTools session. On 2026-04-25, this was automated via `twitter_auth.py` (see below).

### Self-Healing Authentication System (2026-04-25)

On 2026-04-25, lcash built `twitter_auth.py` — a self-healing authentication module that automatically refreshes expired cookies without manual browser intervention. Three approaches were tested before arriving at a working solution:

**Approach 1 — Playwright with stealth patches (FAILED):** Even with `navigator.webdriver = undefined`, `AutomationControlled` disabled, human-like delays, and persistent Chrome profiles, X.com's client-side JavaScript detected the automation and cleared typed input from login fields. Multiple stealth configurations were attempted; all failed. This is more aggressive than bet365's detection — X actively interferes with input rather than passively serving empty data.

**Approach 2 — curl_cffi API-based login (PARTIALLY WORKS):** A headless HTTP login flow using `curl_cffi` (which provides Akamai-like TLS fingerprinting) that walks through X's multi-step authentication: username submission → email challenge verification → password submission → TOTP 2FA code → cookie extraction. This approach passed X's JavaScript instrumentation checks (unlike Playwright) and successfully authenticated in testing. However, it is fragile to IP-level rate limiting: too many failed login attempts trigger a ~15-30 minute IP-level lockout that blocks all subsequent attempts regardless of credential validity. The flow includes retry/backoff logic, but repeated failures during development burned through the tolerance window.

**Approach 3 — AdsPower anti-detect browser (RELIABLE):** AdsPower (profile `k19yb91n`) succeeded immediately where all other methods failed. AdsPower's anti-detect fingerprinting — which randomizes browser characteristics at a level deeper than Playwright's stealth patches — completely bypasses X's automation detection. The browser renders the login page normally, accepts typed credentials, and completes authentication without interference. This is the same tool used for bet365 scraping (see [[connections/anti-scraping-driven-architecture]]), confirming its effectiveness against multiple anti-bot systems.

The final `twitter_auth.py` module integrates both approaches:

- **Primary path:** curl_cffi API login (fast, headless, no browser overhead)
- **Fallback path:** AdsPower browser login (reliable, handles edge cases curl_cffi can't)
- **Auto-refresh:** `login_if_expired()` is wired into `twitter_scraper.py._load_cookies()` so cookie refresh is transparent — the scraper never needs to know about authentication state
- **Credentials:** Stored in `.env` (`TWITTER_USERNAME`, `TWITTER_PASSWORD`, `TWITTER_2FA_SECRET`) — same pattern as other API keys in the scanner

Since `auth_token` cookies persist for months under normal operation, the login flow only fires when sessions actually die — a rare event that the auto-refresh handles without operator intervention. This eliminates the manual cookie extraction step that was previously the only viable path.

### Rate Limit Strategy for Live Mode

The news agent's live polling mode is designed to avoid rate limit issues by construction: it polls only 1 tweet per user per cycle (checking for new tweets since the last poll), using hardcoded Twitter user IDs (e.g., JeffPassan=33857883, Ken_Rosenthal=25053298) to avoid wasting rate-limited calls on `resolve_user_id` lookups. With 22 accounts polled per cycle and a ~60 second cycle time, this consumes approximately 22 requests per minute — well within the 50-per-15-minute limit for each individual user's timeline, since each user only uses 1 request per cycle.

The rate limit issues arose during development/testing when batch-fetching 100 tweets per user across multiple accounts for historical analysis — a pattern that burns through the limit rapidly.

### IP Independence

Rate limits are per auth-token, NOT per IP address. Switching from laptop (residential IP) to mini PC (different residential IP via Tailscale) does not reset the rate limit window. This means having multiple machines scrape with the same Twitter account credentials provides no rate limit benefit — only additional Twitter accounts would increase throughput.

## Related Concepts

- [[connections/anti-scraping-driven-architecture]] - bet365's six-layer defense stack parallels X's three-layer approach; both use Cloudflare at the network layer, but X's anti-automation JS is more aggressive (active interference vs passive data withholding); AdsPower bypasses both platforms' detection
- [[concepts/bet365-headless-detection]] - bet365 serves empty data to headless browsers; X actively clears input fields — two different anti-automation strategies, but AdsPower defeats both
- [[concepts/news-agent-injury-pipeline]] - The news pipeline that consumes Twitter data; rate limit constraints directly impact polling architecture and source selection
- [[concepts/news-driven-pre-sharp-ev-thesis]] - The strategic thesis that requires fast tweet ingestion — rate limits bound the achievable speed
- [[concepts/bet365-auto-login-session-recovery]] - Parallel self-healing auth pattern: bet365 uses CDP-based auto-login for session recovery, Twitter uses curl_cffi/AdsPower — both automate authentication lifecycle management

## Sources

- [[daily/lcash/2026-04-25.md]] - twscrape login blocked by Cloudflare 403 from AU IPs; Playwright with real Chrome detected by X anti-automation JS (clears typed input); GraphQL rate limits tracked by endpoint+token not QID; 50 req/15min for user_tweets; extended lockout from repeated 429s — checking status resets window, must do hard blackout; manual browser login + cookie extraction is viable path; rate limits per auth_token not per IP (Sessions 10:10, 15:43, 20:45). Hardcoded user IDs (JeffPassan=33857883, Ken_Rosenthal=25053298) to avoid wasting rate-limited resolve_user_id calls; live mode polls 1 tweet/user/cycle avoiding limits; second X account recommended for development/testing (Sessions 14:48, 15:43). Self-healing auth system built: Playwright stealth patches all fingerprintable by X (webdriver, automation flags); curl_cffi API login flow (username→email challenge→password→TOTP 2FA→cookie export) works but fragile to IP-level rate limits (~15-30 min lockout from failed attempts); AdsPower anti-detect browser (profile k19yb91n) succeeded immediately; `twitter_auth.py` integrates both with `login_if_expired()` auto-refresh wired into scraper; auth_token cookies persist months; credentials in .env (Session 21:48)
- [[daily/lcash/2026-04-26.md]] - `verify_credentials` endpoint deprecated (returns 404); switched cookie validation to GraphQL `UserByScreenName` with full `features` params; Twitter silently renamed `timeline_v2` to `timeline` in GraphQL responses — scraper needed patching; multi-account cookie rotation implemented: 100 accounts via AdsPower mass login (~25s per login, ~40 min total), round-robin `CookieRotator` in `twitter_auth.py`; `ctx.clear_cookies()` for browser logout preserves server-side auth tokens; `pycache` can cause stale code to persist; architecture: `.twitter_accounts.json`, `.twitter_cookies_pool.json` for pool storage (Sessions 15:58, 16:31)
