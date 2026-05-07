---
title: "Unabated Auth Architecture Analysis"
aliases: [unabated-security, auth0-rs256-jwt, isblurred-pattern, unabated-api, competitive-intelligence]
tags: [value-betting, competitive-intelligence, authentication, architecture, security]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# Unabated Auth Architecture Analysis

On 2026-05-07, lcash reverse-engineered Unabated's authentication and authorization architecture to understand their security model for informing the value betting scanner's own dashboard security design. Unabated uses Auth0 with RS256 JWT tokens, a 3-layer permission system (JWT claims → server-side user roles → per-market `isBlurred` flags), and AWS WAF bot protection. The user's $199/month Premium subscription has full access — 37 permissions granted, `isBlurred: false` on every market. Successfully pulled 1,729 live odds lines from their API.

## Key Points

- **Auth0 RS256 JWT** — cannot be tampered with (signature tied to Auth0 private key); two cookies: `unabated` (httpOnly session) + `unabated_at_prod` (JS-readable access token with permissions array)
- **3-layer permission system**: JWT `permissions[]` array → `userRolePermissions` from `/api/users/settings` (37 granular flags) → `isBlurred` per market in odds feed
- **`isBlurred` pattern**: Server returns full data with a `isBlurred` flag per market — UI hides blurred markets, but data is present in the response. This is elegant for UX but only secure because Unabated enforces server-side (tampered JWT → rejected before response)
- **1,729 lines pulled** from `api-k.unabated.com/api/markets/playerProps/changes` — MLB (1,261), NBA (356), WNBA (7), lg8/futures (105); zero blurred entries for Premium
- **Player IDs are opaque** (P39221 etc.) — `people` dict in response is empty; separate player lookup endpoint needed to decode
- **Available add-ons discovered**: NBA Projections (Justin Phan, $249/mo), NBA DFS ($69/mo), Tennisform ($55/mo, included in Premium), and locked: THE BAT X (MLB), THE BLITZ + 4FOR4 (NFL)
- For own dashboard: **Supabase RLS is the correct equivalent** — gate at API layer, never rely on client-side hiding

## Details

### Authentication Architecture

Unabated uses Auth0 as their identity provider with RS256 (asymmetric) JWT signing. Two cookies manage the session:

| Cookie | Type | Purpose |
|--------|------|---------|
| `unabated` | httpOnly | Server-side session cookie — not accessible to JavaScript |
| `unabated_at_prod` | JS-readable | RS256 access token containing permissions array and user metadata |

The RS256 signing means the JWT is signed with Auth0's private key and verified with the public key. Unlike HS256 (shared secret), the signing key is never exposed to the client or to Unabated's servers — only Auth0 possesses it. This makes JWT manipulation impossible: modifying any field (permissions, user ID, expiry) invalidates the signature, and the correct signature can only be produced by Auth0.

### 3-Layer Permission System

The permission model operates at three levels:

**Layer 1 — JWT Claims**: The `permissions` array in the JWT token lists high-level capabilities (e.g., `read:odds`, `read:projections`). These are set by Auth0 at login time based on the user's subscription tier.

**Layer 2 — Server-Side User Roles**: The `/api/users/settings` endpoint returns `userRolePermissions` — 37 granular flags controlling feature access. These are more fine-grained than JWT claims and can be updated without re-issuing the JWT (e.g., adding a trial feature without requiring re-login).

**Layer 3 — Per-Market isBlurred**: Each market in the odds feed carries an `isBlurred` boolean. For Premium subscribers, all 1,729 markets returned `isBlurred: false`. For lower tiers, specific markets would have `isBlurred: true` — the UI renders them with a blur overlay, but the underlying data IS in the response.

The `isBlurred` pattern is noteworthy: rather than filtering blurred markets server-side (which would require different response schemas per tier), Unabated returns the full dataset with a flag. The UI hides flagged markets, creating the paywall appearance. This only works because JWT validation is enforced server-side — a tampered JWT claiming Premium access would be rejected by Auth0's signature verification before the API processes the request.

### Implications for Scanner Dashboard

The Unabated analysis informed the scanner's own security approach:

- **Supabase RLS (Row-Level Security)** is the correct equivalent of Unabated's server-side permission enforcement — it gates data access at the database query layer, not the API response layer
- **Never rely on client-side hiding** (the `isBlurred` approach without server enforcement would be trivially bypassable)
- The scanner's current Supabase RLS policies (service_role full access, authenticated read-only) already follow this pattern

### AWS WAF Bot Protection

AWS WAF triggers on fresh navigations to Unabated's `/pricing` page — a Cloudflare-equivalent bot challenge specific to AWS infrastructure. Authenticated sessions are not affected — the WAF challenge only fires on unauthenticated or suspicious-pattern requests. This is consistent with the defense-in-depth approach: WAF for network-layer bot protection, Auth0 JWT for application-layer authentication, server-side roles for authorization.

### Odds Data Format

The `api-k.unabated.com/api/markets/playerProps/changes` endpoint returns a structured odds feed:
- 1,729 total lines across 4 sport categories
- MLB dominates with 1,261 lines (73% of feed)
- Player IDs use opaque internal format (P39221) rather than names — the `people` dict that should map IDs to names is empty in the response, requiring a separate lookup endpoint
- Market structure includes book-specific odds, true probability estimates, and the `isBlurred` flag per entry

## Related Concepts

- [[concepts/value-betting-operational-assessment]] - The scanner's operational weaknesses include dashboard security (bus factor, no auth); Unabated's architecture provides a reference model
- [[concepts/polymarket-liquidity-enrichment]] - Polymarket's public CLOB API requires no auth; Unabated's gated API represents the opposite end of the access spectrum
- [[concepts/pinnacle-mlb-player-prop-coverage-gap]] - Unabated's 1,261 MLB lines suggest broader MLB prop coverage than Pinnacle's ~zero; potential cross-reference for coverage gap analysis
- [[concepts/podcast-pick-extraction-pipeline]] - Derek Carty / THE BAT X (locked in Unabated's add-ons) is the same model-driven tipster being tracked in the podcast pipeline

## Sources

- [[daily/lcash/2026-05-07.md]] - Auth0 RS256 JWT analysis; two-cookie system (unabated httpOnly + unabated_at_prod JS-readable); 37 permissions all granted for Premium; 1,729 lines from playerProps/changes (MLB 1,261, NBA 356, WNBA 7, lg8/futures 105); isBlurred=false on all markets; player IDs opaque P39221 format; add-ons: NBA Projections $249/mo, Tennisform included, THE BAT X/BLITZ locked; AWS WAF on /pricing; Supabase RLS as equivalent for own dashboard (Session 11:46)
