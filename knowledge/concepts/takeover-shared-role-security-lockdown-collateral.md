---
title: "TAKEOVER Shared Role Security Lockdown Collateral Damage"
aliases: [portal-lockdown-staff-breakage, shared-authenticated-role, supabase-column-revoke-cascade, safe-view-rpc-pattern]
tags: [takeover, security, supabase, architecture, deployment, incident]
sources:
  - "daily/lcash/2026-05-19.md"
created: 2026-05-19
updated: 2026-05-19
---

# TAKEOVER Shared Role Security Lockdown Collateral Damage

On 2026-05-19, lcash fixed the TAKEOVER staff app after 4 portal security lockdown migrations (from 2026-05-15) broke staff database access. Both the bowler portal and the staff app share the same Supabase project and `authenticated` PG role. When portal lockdown migrations revoked column-level SELECT access to prevent bowlers from reading sensitive data, the revocations also applied to staff users — breaking 8+ read sites (`SELECT *` on revoked columns) and 9 write sites across Bowlers, Inbox, OnboardingKanban, FinanceTotals, Dashboard, BookieHub, and PortalLeads.

## Key Points

- **Root cause**: Two apps (bowler portal + staff TAKEOVER) share one Supabase project and one `authenticated` PG role — column-level revocations for portal users also revoke staff access
- **Impact**: 8+ read sites silently failed (500 errors from `SELECT *` on tables with revoked columns) + 9 write sites broke across the staff app
- **Fix pattern**: `account_owners_safe` view (excludes sensitive columns) + `admin_update_bowler` SECURITY DEFINER RPC (bypasses column revocations for authorized writes) + rewritten trigger using `NEW.` instead of column references
- **Portal login preserved (Option A)**: Bowlers continue to self-serve via portal for KYC/status; staff get unblocked via safe view + RPC. Credentials show blank in BookieHub (write-only; reveal UI is V2)
- **`SELECT *` is the real landmine**: A single revoked column in a `SELECT *` kills the entire query — must use explicit column lists or views
- **Vercel `outputDirectory: "."` vs `"dist"`**: Portal served `"."` (leaks entire repo including migrations, edge function source); TAKEOVER correctly serves `"dist"` (build output only)

## Details

### The Incident Chain

On 2026-05-15, a portal security incident was discovered: the `anon` Supabase role could read all tables, and bowlers could PATCH their own `status='confirmed'` — bypassing the staff-managed onboarding flow. Four lockdown migrations were applied to fix this:

1. Revoked `anon` SELECT on sensitive tables
2. Revoked column-level SELECT on `account_owners` for the `authenticated` role (hiding credentials, internal notes)
3. Added restrictive RLS policies to prevent self-service status changes
4. Tightened UPDATE permissions on bowler-writable fields

Migrations 2 and 3 had collateral impact: the `authenticated` role is shared between bowlers (who use the portal) and staff (who use the TAKEOVER app). When column-level SELECT was revoked to hide credentials from bowlers, it also hid them from staff. Every `SELECT *` query in the staff app that touched the affected tables received a 500 error because the database rejected access to the revoked columns.

### Two-App Architecture Problem

The architectural root cause is that Supabase's `authenticated` role doesn't distinguish between app contexts. A bowler logged in via the portal and a staff member logged in via TAKEOVER both authenticate as `authenticated` and receive the same PG role permissions. Staff identity is determined by presence in the `organization_members` table with appropriate role flags, but PG-level column permissions don't check this — they apply uniformly to all `authenticated` users.

This means any column-level security change intended for one app's users automatically affects the other app's users. The only safe approaches are:

1. **Views** — create a view that excludes sensitive columns; the view's owner (typically `postgres`) has full access, so `authenticated` users querying the view get filtered columns regardless of direct table permissions
2. **SECURITY DEFINER RPCs** — stored procedures that execute with the function owner's permissions, not the caller's. Staff operations that need sensitive columns go through RPCs
3. **Separate roles** — create distinct PG roles for portal vs staff (requires Supabase custom claims or JWT-based role switching — more complex)

### The Fix Migration

A single idempotent migration (`20260519000000_unbreak_takeover_app.sql`) was applied containing:

- **`account_owners_safe` view**: Exposes all columns except credentials and internal notes. All 13 read sites in the staff app were swapped from direct table queries to this view.
- **`admin_update_bowler` SECURITY DEFINER RPC**: Accepts bowler updates (status, notes, assignments) and writes to the underlying table with elevated permissions. All 9 write sites were swapped to call this RPC.
- **Trigger rewrite**: The existing INSERT/UPDATE trigger referenced revoked columns directly; rewritten to use `NEW.` record syntax which doesn't require column-level SELECT.
- All operations use `CREATE OR REPLACE` for idempotency.

### App-Side Changes

| Component | Read Changes | Write Changes |
|-----------|-------------|---------------|
| Bowlers list | `account_owners_safe` view | N/A |
| BowlerDetail | `account_owners_safe` view, credential columns dropped | `adminUpdateBowler` RPC |
| Inbox thread | `account_owners_safe` view | `adminUpdateBowler` RPC |
| OnboardingKanban | `account_owners_safe` view | `adminUpdateBowler` RPC |
| FinanceTotals | `account_owners_safe` view | N/A |
| BookieHub | Credential fields show blank (V2: reveal UI) | N/A |
| PortalLeads | `account_owners_safe` view | `adminUpdateBowler` RPC |
| Dashboard | `account_owners_safe` view | N/A |

### Vercel Security Audit

During the investigation, the user asked whether `takeover-khaki.vercel.app` was compromised. The audit found:

- **TAKEOVER** (`outputDirectory: "dist"`): Safe — Vercel serves only the Vite build output. No source files, no service-role key, no migration files. The `anon` Supabase key in the browser bundle is expected/safe.
- **Portal** (`outputDirectory: "."`): This was the original leak vector — serving the entire repo including migration SQL files, edge function source, and potentially `.env` files. This was the portal security incident's root exposure.

Missing security headers (CSP, HSTS, X-Frame-Options, Permissions-Policy) were flagged as low-priority hygiene improvements.

### Credential Reveal UI (V2)

The V1 scope deliberately excludes a credential reveal UI. BowlerDetail and BookieHub credential fields show blank — this is graceful degradation (write-only), not a bug. The proper V2 implementation requires a "click to reveal" UI with audit logging (who viewed credentials and when), which is architecturally different from simply showing the field.

## Related Concepts

- [[concepts/unabated-auth-architecture-analysis]] - Unabated's 3-layer permission model (JWT → roles → isBlurred) is a reference for how to properly separate user tiers; Supabase RLS is the equivalent approach
- [[concepts/configuration-drift-manual-launch]] - The portal lockdown migrations are a database-level analog of batch file drift: changes intended for one context silently break another
- [[connections/operational-compound-failures]] - Portal lockdown + shared role + `SELECT *` compound to break the staff app from a security fix intended to protect bowlers

## Sources

- [[daily/lcash/2026-05-19.md]] - Portal lockdown migrations broke 8+ read + 9 write sites in TAKEOVER staff app; shared `authenticated` PG role means column revocations affect both bowlers and staff; fix: `account_owners_safe` view + `admin_update_bowler` SECURITY DEFINER RPC; Option A chosen (keep bowler portal login); Vercel audit confirmed TAKEOVER not compromised (`outputDirectory: "dist"` safe); portal's `"."` was the leak; credential reveal UI deferred to V2; Vite code-splits RPC wrappers into separate chunks (Sessions 13:16, 14:53)
