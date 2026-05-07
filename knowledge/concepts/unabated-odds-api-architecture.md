---
title: "Unabated Odds API Architecture"
aliases: [unabated-api, unabated-auth, unabated-reverse-engineering, unabated-security-model]
tags: [value-betting, competitive-intelligence, auth, security, odds-data, architecture]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# Unabated Odds API Architecture

On 2026-05-07, lcash reverse-engineered Unabated's authentication and data architecture via an authenticated browser session ($199/month Premium subscription). Unabated uses Auth0 with RS256 JWT tokens, a 3-layer permission system (JWT permissions → userRolePermissions → per-market isBlurred flag), and serves 1,729 live player prop lines from `api-k.unabated.com/api/markets/playerProps/changes`. The investigation was conducted to understand Unabated's security model as a reference architecture for the value betting scanner's own dashboard, not to exploit it.

## Key Points

- **Auth0 RS256 JWT** — two-cookie system: `unabated` (httpOnly session cookie) + `unabated_at_prod` (JS-readable RS256 access token with permissions array); cannot be tampered with (signature tied to Auth0 private key)
- **3-layer permission model**: JWT permissions array → `userRolePermissions` from `/api/users/settings` (37 granular flags) → `isBlurred` per market in odds feed; all enforced server-side
- **1,729 live lines pulled** from `playerProps/changes` endpoint: MLB (1,261), NBA (356), WNBA (7), lg8/futures (105); zero blurred entries on Premium subscription
- **Player IDs are opaque** (P39221 etc.) — `people` dict in response is empty; separate player lookup endpoint needed to decode
- **Premium subscription has full access** — initial "paywall" appearance was optional add-on CTAs (NBA Projections $249/mo, THE BAT X for MLB, etc.), not restrictions; all 37 permissions granted
- **`isBlurred` pattern**: server returns full data structure with `isBlurred: true/false` per market — elegant for UI (show greyed-out preview) but only secure because Unabated enforces server-side; tampered JWT gets rejected before response is generated
- **AWS WAF bot protection** triggers on fresh navigations to `/pricing` — doesn't affect authenticated API sessions

## Details

### Authentication Architecture

Unabated's auth flow uses Auth0 as the identity provider with RS256 (RSA-SHA256) JWT signing. RS256 means the token is signed with Auth0's private key and verified with the public key — unlike HS256, the signing key is never exposed to the client, making token forgery mathematically impossible.

Two cookies manage the session:

| Cookie | Type | Purpose |
|--------|------|---------|
| `unabated` | httpOnly | Server-side session identifier — cannot be read by JavaScript |
| `unabated_at_prod` | JS-readable | RS256 access token containing permissions array, user ID, expiry |

The access token contains a `permissions` array listing all API actions the user is authorized to perform. The server validates both the token signature (is it from Auth0?) and the permissions array (does this user have access to this endpoint?) on every API call.

### Permission Enforcement

Unabated uses a 3-layer permission model, with each layer building on the previous:

**Layer 1 — JWT permissions**: The access token contains a static permissions array set at login time. This defines the broad scope of what the user can access (e.g., "can read player props," "can access NBA data").

**Layer 2 — userRolePermissions**: A separate `/api/users/settings` endpoint returns 37 granular permission flags that may differ from the JWT permissions (e.g., dynamic feature flags, trial access, add-on subscriptions). The Premium subscription showed all 37 flags as `true`.

**Layer 3 — per-market isBlurred**: Each market in the odds feed includes an `isBlurred` boolean. For Premium users, all markets have `isBlurred: false`. For lower tiers, specific markets are blurred in the UI while the data structure is still returned — the server sends the shape of the data (market exists, has X books) but withholds the actual odds values.

This `isBlurred` pattern is architecturally elegant: the UI can render a preview of blurred markets (showing the market exists, encouraging upgrade) without a second API call. However, it is only secure because Unabated enforces the blurring server-side — if `isBlurred: true` markets still contained real odds data, client-side JS could simply ignore the flag.

### Odds Data Structure

The `playerProps/changes` endpoint returns a stream of player prop changes with the following structure:

- **1,729 lines** across 4 sports: MLB (1,261), NBA (356), WNBA (7), lg8/futures (105)
- **Player IDs** use opaque internal identifiers (P39221, P44012, etc.) — the `people` dict in the response body is empty, meaning player name resolution requires a separate lookup endpoint
- **Book coverage** appears comprehensive — multiple sportsbooks per market with odds, lines, and timestamps
- **Zero blurred entries** on Premium ($199/mo) — confirms full data access without add-ons

### Available Add-Ons

The Premium subscription includes full odds access, but several projection/analytics add-ons are separately priced:

| Add-On | Price | Content |
|--------|-------|---------|
| NBA Projections (Justin Phan) | $249/mo | Player prop projections |
| NBA DFS | $69/mo | Daily fantasy lineup optimization |
| Tennisform | $55/mo | Tennis analytics (included for Premium) |
| THE BAT X (MLB) | Locked | Derek Carty's MLB projection model |
| THE BLITZ + 4FOR4 (NFL) | Locked | NFL projection models |

THE BAT X is particularly relevant as Derek Carty was identified in [[concepts/podcast-pick-extraction-pipeline]] as a model-driven MLB tipster whose picks showed potential calibration advantage over conversational podcast picks.

### Relevance to Scanner Architecture

The investigation's purpose was to inform the value betting scanner's own dashboard security model, not to exploit Unabated. Key architectural lessons:

1. **Supabase RLS** (already in use by the scanner) is the right equivalent to Auth0 + server-side isBlurred enforcement — gate at the API layer, never rely on client-side hiding
2. **Per-market permission flags** (isBlurred) are a good UX pattern for premium vs free tiers — show the shape of data to encourage upgrades without exposing actual values
3. **Opaque player IDs** require a separate resolution layer — the scanner's own player name normalization challenges (see [[concepts/data-integrity-audit-pipeline-validation]]) are a parallel problem

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - The scanner's own operational maturity assessment; Unabated's auth model is a reference for weakness #7 (bus factor) mitigation via proper auth
- [[concepts/podcast-pick-extraction-pipeline]] - Derek Carty / THE BAT X identified as a model-driven MLB tipster; Unabated hosts his projection model as a premium add-on
- [[concepts/data-integrity-audit-pipeline-validation]] - Player name normalization challenges in the scanner parallel Unabated's opaque player ID resolution problem
- [[concepts/dashboard-client-server-ev-divergence]] - The scanner's dashboard security is less mature than Unabated's; Supabase RLS is used but per-market access control is not implemented

## Sources

- [[daily/lcash/2026-05-07.md]] - Auth0 RS256 JWT reverse-engineered; 3-layer permission model documented; 1,729 live lines pulled (MLB 1,261, NBA 356, WNBA 7); all 37 permissions granted on Premium; isBlurred pattern analyzed; AWS WAF on /pricing; opaque player IDs (P39221) with empty people dict; available add-ons mapped including THE BAT X; investigation for reference architecture, not exploitation (Session 11:46)
