---
title: "Twitter Multi-Account Cookie Rotation"
aliases: [cookie-rotation, twitter-cookie-pool, multi-account-scraping, adspower-mass-login, twitter-account-rotation]
tags: [value-betting, twitter, scraping, architecture, rate-limiting, news-pipeline]
sources:
  - "daily/lcash/2026-04-26.md"
created: 2026-04-26
updated: 2026-04-26
---

# Twitter Multi-Account Cookie Rotation

A mass-scale approach to bypassing Twitter/X's per-account rate limits by maintaining a pool of authenticated cookies across many accounts and rotating through them round-robin. Each account gets ~300 requests per 15-minute window, so 3-4 accounts provide uninterrupted polling for the news agent's 22+ Twitter sources. On 2026-04-26, lcash built an automated AdsPower-based login pipeline to onboard 100 Twitter accounts, with each login taking ~25s (full pipeline ~40 minutes). The system uses `.twitter_cookies_pool.json` for the cookie pool and `CookieRotator` in `twitter_auth.py` for rotation logic.

## Key Points

- Round-robin cookie rotation across accounts instead of single-account polling — eliminates rate limits as a practical constraint with enough accounts
- AdsPower anti-detect browser (profile `k19yb91n`) is the primary login method — defeats Twitter's client-side anti-automation JavaScript that clears typed input in Playwright
- Each account login takes ~25s via AdsPower: username → email challenge → password → 2FA → cookie export; 100 accounts ≈ 40 min
- `ctx.clear_cookies()` for browser-side logout so exported `auth_token` + `ct0` server-side tokens survive — browser logout doesn't invalidate server-side sessions
- Cookie validation switched from deprecated `verify_credentials` (returns 404) to GraphQL `UserByScreenName` with full `features` params
- Twitter silently renamed `timeline_v2` to `timeline` in GraphQL responses — fragile API that requires monitoring
- Architecture files: `.twitter_accounts.json` (credentials), `.twitter_cookies_pool.json` (cookie pool), `twitter_auth.py` (CookieRotator), `twitter_scraper.py` (auto-rotation)

## Details

### The Rate Limit Problem

The news agent pipeline (see [[concepts/news-agent-injury-pipeline]]) polls 22+ Twitter accounts for breaking injury news. With a single authenticated account, Twitter's GraphQL rate limits (~50 requests per 15-minute window for `user_tweets`, ~300 for general endpoints) constrain how frequently sources can be polled. During development, batch-fetching 100 tweets per user across multiple accounts rapidly burned through the limit, triggering extended lockouts that lasted hours (see [[concepts/twitter-x-api-scraping-constraints]]).

Multi-account rotation solves this by distributing requests across N accounts. Each request uses a different account's cookies, so no single account hits its rate limit. With 3-4 accounts, the news agent can poll all 22 sources every 60 seconds without approaching any individual account's limit. With 100 accounts, rate limiting becomes effectively impossible for the polling volume required.

### AdsPower Login Pipeline

Twitter's anti-automation defenses block programmatic login through two mechanisms: Cloudflare blocks `curl_cffi` API login from Australian IPs, and client-side JavaScript detects Playwright automation and clears typed input fields. AdsPower's anti-detect browser fingerprinting bypasses both defenses — it presents as a genuine user browser, defeating Twitter's detection at every level.

The login flow per account:
1. Open AdsPower browser with profile `k19yb91n`
2. Navigate to `x.com/login`
3. Enter username → handle email challenge if prompted → enter password → complete 2FA
4. Export `auth_token` and `ct0` cookies from the browser session
5. Call `ctx.clear_cookies()` to log out the browser without invalidating the server-side tokens
6. Close the browser tab and proceed to the next account

The `clear_cookies()` step is critical: it ensures the browser session is clean for the next account login while preserving the exported cookies' validity. Server-side `auth_token` cookies are not invalidated by client-side cookie clearing — they persist for months under normal operation.

### Cookie Validation

The `validate_cookies` function was initially using Twitter's `verify_credentials` REST endpoint, which Twitter deprecated (returns HTTP 404 as of 2026-04-26). The replacement is the GraphQL `UserByScreenName` query, which requires a full `features` parameter object to return valid responses. Without the `features` param, the query returns empty results or errors — a silent failure mode that can make valid cookies appear invalid.

### API Schema Fragility

During the same session, Twitter silently renamed `timeline_v2` to `timeline` in GraphQL API responses. This broke the scraper's response parsing with no error — the expected field simply wasn't present, producing empty results. The fix was a simple field name change in the parser, but the fragility is notable: Twitter makes breaking API changes without versioning or deprecation notices. The scraper needs resilient field lookup (checking for both field names) or monitoring for unexpected empty responses.

### Architecture

The cookie rotation system has four components:

| File | Purpose |
|------|---------|
| `.twitter_accounts.json` | Credentials for all accounts (username, password, email, 2FA secret) |
| `.twitter_cookies_pool.json` | Pool of authenticated cookies (`auth_token` + `ct0` per account) |
| `twitter_auth.py` | `CookieRotator` class: picks next account round-robin, validates cookies, refreshes expired ones via AdsPower |
| `twitter_scraper.py` | Uses `CookieRotator` transparently — auto-rotation is invisible to the scraping logic |

The `CookieRotator` in `twitter_auth.py` handles the rotation transparently: the scraper calls `get_cookies()` and receives the next account's credentials. If the returned cookies are expired (validation fails), the rotator triggers an AdsPower login refresh for that account before returning fresh cookies. This makes the rotation invisible to the scraping logic — it sees a single interface that always returns valid cookies.

### Duplicate Init Code Bug

A subtle bug was encountered during development: duplicate initialization code in `_do_login` caused failures where the login flow appeared to work but produced invalid cookies. This was a copy-paste artifact from merging the `curl_cffi` and AdsPower login paths. The lesson: authentication flows with multiple code paths for different login methods are prone to duplication bugs that produce plausible but wrong output (valid-looking cookies that don't actually work).

### Mass Login Pipeline Monitoring (Sessions 20:37, 21:09)

The 100-account login pipeline was monitored across two sessions. Key operational findings:

- **60-second cooldown** between logins eliminated throttle issues — zero throttling observed across the entire run
- **~27 of ~30 initial accounts** succeeded; ~3 failed as single-streak failures (streak counter resets to 1 immediately), confirming bad account credentials rather than rate limiting
- **Throttle vs bad-account diagnostic**: consecutive failure streaks indicate throttling (increase cooldown); single failures that reset are account-quality issues (skip and continue)
- **Empty page title** on login (title blank instead of "Home / X") is benign — cookies still export successfully. Title variations ("Home / X", "X", empty) are all valid login confirmations
- By session 21:09, the pipeline had processed ~40 of ~80 accounts with consistent ~25s per login and no throttle-induced failure streaks

## Related Concepts

- [[concepts/twitter-x-api-scraping-constraints]] - The rate limits, anti-automation defenses, and extended lockout feedback loop that necessitate multi-account rotation; the single-account constraints that this system overcomes
- [[concepts/news-agent-injury-pipeline]] - The news pipeline that consumes Twitter data via this rotation system; 22+ sources require reliable, high-frequency polling
- [[concepts/bet365-auto-login-session-recovery]] - A parallel self-healing authentication pattern: bet365 uses CDP for auto-login when sessions expire, Twitter uses AdsPower for cookie refresh — both automate authentication lifecycle management
- [[connections/anti-scraping-driven-architecture]] - AdsPower defeats Twitter's anti-automation just as it defeats bet365's Cloudflare and headless detection — the same tool solves authentication challenges across multiple platforms

## Sources

- [[daily/lcash/2026-04-26.md]] - AdsPower as primary login for mass Twitter account onboarding; `verify_credentials` returns 404 (deprecated), switched to GraphQL `UserByScreenName`; `timeline_v2` silently renamed to `timeline`; round-robin rotation across 100 accounts (~25s per login, ~40 min total); `ctx.clear_cookies()` preserves server-side tokens; `CookieRotator` in `twitter_auth.py`; duplicate init code in `_do_login` caused subtle failures; architecture: `.twitter_accounts.json`, `.twitter_cookies_pool.json`, `twitter_auth.py`, `twitter_scraper.py` (Sessions 15:58, 16:31). Mass login monitoring: 60s cooldown confirmed as throttle-free sweet spot; ~27/30 initial accounts succeeded, 3 failed as bad credentials (single-streak failures); empty page title benign; ~40/80 processed by end of monitoring (Sessions 20:37, 21:09)
