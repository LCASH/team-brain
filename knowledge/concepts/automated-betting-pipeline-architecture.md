---
title: "Automated Betting Pipeline Architecture"
aliases: [betting-pipeline, superwin-warroom-venom, automated-betting, venom-architecture, warroom-pipeline]
tags: [superwin, takeover, architecture, automation, betting, deployment]
sources:
  - "daily/lcash/2026-05-30.md"
  - "daily/lcash/2026-05-31.md"
created: 2026-05-30
updated: 2026-05-31
---

# Automated Betting Pipeline Architecture

Full architecture for the SuperWin to WarRoom to Venom automated betting pipeline. SuperWin is the edge stream (detects +EV opportunities), WarRoom is the account preparer and session refresher (runs as a sibling systemd service), and Venom is the bet placer (documented but unbuilt). TAKEOVER is the source-of-truth settings configurator. The design uses a two-Supabase architecture (SuperWin separate from TAKEOVER), three plain JSONB columns for account configuration, and app-layer libsodium encryption for secrets.

## Key Points

- Three-service pipeline: SuperWin (edge detection) → WarRoom (session prep, sibling systemd service) → Venom (bet placement, unbuilt)
- TAKEOVER is source-of-truth/settings configurator; two-Supabase architecture stays (SuperWin DB separate from TAKEOVER DB)
- Three plain JSONB columns on betting_accounts: `settings`, `bookie_config`, `edge_config` — NOT normalized join tables
- App-layer libsodium encryption for secrets stored inside `bookie_config` JSONB; no multi-column encryption split
- `tags.settings` gets a JSONB field for bulk policy that merges into individual account settings at runtime
- TAB is the first bookie target; Jay owns 2FA infrastructure; 6-phase build plan
- Initial over-engineering (normalized eligibility table, multi-column encryption split) was wrong — user's original flat-JSONB brief was the correct approach

## Details

### Pipeline Architecture

The pipeline has three distinct services with clear boundaries. SuperWin runs continuously, scanning multiple bookmaker APIs and computing expected value against sharp lines. When it detects a +EV opportunity, it emits an edge event. WarRoom runs as a sibling systemd service on the same VPS, responsible for keeping betting account sessions alive — refreshing authentication tokens, managing cookies, handling session rotation. Venom is the execution layer that receives edge events and places bets through prepared sessions. Venom is currently documented but unbuilt; the architecture is designed so it can be developed independently once WarRoom is stable.

TAKEOVER serves as the configuration layer and source of truth. Operators use the TAKEOVER Electron app to manage betting accounts, set risk parameters, configure which edges to act on, and monitor pipeline health. The two-Supabase architecture is intentional: SuperWin's high-frequency odds data stays in its own database, while TAKEOVER's account management and configuration data lives in a separate Supabase instance. This prevents SuperWin's write volume from affecting TAKEOVER's responsiveness and keeps security boundaries clean.

### Data Model: JSONB Over Normalization

The `betting_accounts` table uses three plain JSONB columns rather than normalized join tables. `settings` holds account-level configuration (stake limits, timing preferences, cooldown periods). `bookie_config` holds bookie-specific data (login credentials, session tokens, proxy assignments). `edge_config` holds edge eligibility rules (which sports, minimum EV thresholds, market type filters).

This design was chosen after an initial attempt at normalization (a separate `account_edge_eligibility` table with foreign keys to edge types) proved over-engineered. The normalized approach created complex join queries for what is fundamentally a per-account configuration blob that changes infrequently and is always read as a whole. The user's original brief calling for flat JSONB was correct — the schema matches how the data is actually consumed.

### Tag-Level Bulk Policy

The `tags` table gains a `settings` JSONB field that defines bulk policy for all accounts sharing a tag. At runtime, tag-level settings merge into account-level settings with account-level taking precedence. This enables fleet-wide policy changes (e.g., "all TAB accounts: max stake $50, cooldown 30s") without touching individual accounts, while still allowing per-account overrides for special cases.

### Encryption Model

Secrets within `bookie_config` (passwords, API keys, session tokens) are encrypted at the application layer using libsodium before being written to Supabase. The encryption key lives in the service's environment variables, not in the database. This was chosen over Supabase's built-in column encryption because the secrets are embedded within JSONB structures — encrypting the entire column would prevent querying non-secret fields, while encrypting individual JSONB paths requires app-layer logic regardless.

### Build Plan and First Target

TAB is the first bookie target because its session management is well-understood from the scraper work and it has the highest volume of racing edges. Jay owns the 2FA infrastructure required for TAB's login flow. The 6-phase build plan progresses from account CRUD and session management through edge routing to automated bet placement, with each phase independently deployable and testable.

### Phase 1 Planning and Schema Refinements (2026-05-31)

On 2026-05-31, Phase 1 pre-flight planning revealed several refinements and operational findings:

**Column rename**: `bookie_config` renamed to `phone_automation` — confirmed no schema clashes with existing `phone_farm_*` infrastructure in TAKEOVER. `browser_automation` column (already exists on live DB) to be deprecated in favour of `phone_automation`.

**Live DB drift from migrations**: The live TAKEOVER Supabase already has `phone_automation`, `browser_automation`, and `run_2nd_3rd_bonus_balance` columns that aren't reflected in `database.types.ts` or migration files — these were added via the Supabase dashboard directly. This means `database.types.ts` must be regenerated from the live schema before Phase 1 can begin, and migrations must account for columns that already exist.

**dev/main branch divergence**: The `TAKEOVER-dev` repo's `dev/main` branch is 53 commits ahead of local `main`, containing WarRoom edge config, phone provisioning automation (QR + DPC + ADB + 2FA relay), war room personas, priming dashboard, and persistent allocations. Local work must branch off `dev/main`, not `origin/main`.

**`account_personas` already exists**: A 1:1 table with `betting_accounts`, wired into WarRoom for filtering — relevant for Phase 3+ when persona-based session management is needed.

**Phase plan files created**: `~/.claude/plans/automated-betting/00-master-overview.md` through `06-phase-6-bookie-expansion.md` — one file per phase with dependencies and deliverables.

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The edge detection output that feeds into this pipeline; backtesting validates which edges are worth automating
- [[concepts/superwin-execution-gap-price-band-discipline]] - Execution gap analysis that motivates automation; manual bet placement misses time-sensitive edges
- [[concepts/tabtouch-superpick-boost-fabrication-analysis]] - TAB/TabTouch boost analysis relevant to edge_config rules for the first bookie target
- [[concepts/takeover-shared-role-security-lockdown-collateral]] - TAKEOVER security model that applies to the settings configurator role in this pipeline
- [[concepts/configuration-drift-manual-launch]] - Live DB drifting from migration files is the database-level analog of batch file drift

## Sources

- [[daily/lcash/2026-05-30.md]] - SuperWin → WarRoom → Venom pipeline architecture; two-Supabase architecture decision; three JSONB columns (settings, bookie_config, edge_config) over normalized tables; tags.settings for bulk policy merge; app-layer libsodium encryption; TAB as first target; Jay owns 2FA; 6-phase build plan; initial over-engineering was wrong
- [[daily/lcash/2026-05-31.md]] - Phase 1 pre-flight: bookie_config renamed to phone_automation; live DB has columns not in migrations (phone_automation, browser_automation, run_2nd_3rd_bonus_balance); dev/main is 53 commits ahead of local main; account_personas already exists as 1:1 table; phase plan files created (Session 06:34)
