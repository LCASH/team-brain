---
title: "Knowted Launch Decision Register and Marketing Blockers"
aliases: [launch-decisions, marketing-blockers, decision-register, knowted-launch-gates, decision-gating]
tags: [knowted, strategy, marketing, legal, decision-making, launch]
sources:
  - "daily/lcash/2026-06-13.md"
  - "daily/lcash/2026-06-16.md"
created: 2026-06-13
updated: 2026-06-16
---

# Knowted Launch Decision Register and Marketing Blockers

On 2026-06-13, lcash produced a ranked decision register (`launch-decisions.md`) identifying that Knowted's marketing launch is blocked by **unmade decisions, not missing content** — all assets (website, 90+ social images, comparison tables) are built but cannot ship until legal, truth, and pricing claims are locked. The register organizes blockers into 3 gates and identifies 4 moves that clear approximately 70% of all blockers: a Jeffrey call (product truth + Team-tier confirmation), 10 minutes of solo pricing defaults, one $200 lawyer hour (recording consent + comparison ad risk), and one cofounder call (Enterprise honesty + waitlist-vs-live).

## Key Points

- **Marketing is blocked by decisions, not content**: Website, 90+ social images, comparison tables all built — cannot ship until claims are verified and legal position is locked
- **3 gates in priority order**: (1) Legal & truth — recording-consent position, product-truth matrix, Enterprise honesty; (2) Pricing completeness — annual discount, seat minimums, trial terms; (3) Sequencing — waitlist-vs-live, comparison-ad aggressiveness
- **4 moves clear ~70%**: Jeffrey call (D2 product truth + D5 Team-at-launch), 10-min solo pricing (D4 edge cases), $200 lawyer hour (D1 consent + comparison ads), cofounder call (D3 Enterprise + D6 waitlist-vs-live)
- **D1 (recording consent) is the longest dependency**: Requires external lawyer engagement; gates the entire "captures everywhere / in-person meetings" marketing wedge and has Fireflies BIPA class action as cautionary precedent
- **D2 (product truth) RESOLVED 2026-06-16**: Jeffrey confirmed all 7 product claims TRUE in a 30-min call; language support corrected to 12 (not 100+); unblocks website copy and ad library
- **Product-truth matrix**: 7 claims need Jeffrey confirmation — unlimited recording, 95% accuracy, 7-speaker support, 100+ languages, no-bot architecture, MCP auto-install, in-meeting Q&A
- **Saved to `launch-decisions.md`** and wired into STATUS.md; each decision has a `Decision:` line that is filled in as calls are made — the doc itself is the trigger to flip marketing live

## Details

### The Decision-Blocked-Not-Content-Blocked Insight

A recurring pattern in the Knowted admin work had been building marketing assets (social images, website copy, comparison tables) then discovering that specific claims in those assets were unverified. The 2026-06-13 session crystallized this into a structural diagnosis: the blocking factor is not production capacity but decision velocity. Every marketing artifact contains claims about the product, competitors, or pricing that require explicit founder decisions before public use.

This reframes the marketing timeline: it is not gated by "when will we finish building X?" but by "when will we decide Y?" Decisions are cheaper and faster than production — a 30-minute Jeffrey call and a $200 lawyer hour would unblock more marketing output than two weeks of additional content creation.

### The Three-Gate Framework

**Gate 1 — Legal & Truth (highest priority, longest lead time):**
- D1: Recording-consent legal position — Can Knowted legally record in-person meetings, phone calls, and FaceTime without explicit consent? This gates the "captures everywhere" wedge and the "no bot, records your screen as you" positioning. The Fireflies BIPA class actions (Fricker and Cruz, N.D. Ill.) are the cautionary precedent.
- D2: Product-truth matrix — 7 specific capability claims need Jeffrey's confirmation before going on the website: unlimited recording (no caps?), 95% transcription accuracy (measured how?), 7-speaker diarization (tested?), 100+ languages (which engine?), no-bot architecture (technical accuracy of claim), MCP auto-install (works reliably?), in-meeting Q&A (runs locally?).
- D3: Enterprise tier honesty — Only 4 features confirmed (data residency, on-prem, IT admin, pen-tested); ~7 were fabricated by Claude and moved to roadmap (see [[concepts/llm-feature-fabrication-audit-pattern]]). Must resolve before Enterprise tier goes on the website.

**Gate 2 — Pricing Completeness (medium priority, fast to resolve):**
- D4: Pricing edge cases — Annual discount percentage (20% proposed), team seat minimum (3 proposed), enterprise seat minimum (10 proposed), free trial terms (if any). These are solo decisions that take ~10 minutes.
- D5: Team tier at launch — Does the Team tier ($19/mo) ship at launch, or is launch free-only with Team as a waitlist for later? Gates the pricing page structure and the waitlist CTA copy.

**Gate 3 — Sequencing (lower priority, depends on Gate 1-2):**
- D6: Waitlist-vs-live launch — Does the site go live with a waitlist CTA (current) or with actual product access? Depends on D5 (Team at launch).
- D7: Comparison ad aggressiveness — How explicitly does the marketing name competitors? The legal risk assessment from [[concepts/knowted-competitive-advertising-risk-audit]] recommends a $200 AU lawyer review before going aggressive.

### The Four Unblocking Moves

The decision register's power is in identifying which small actions clear the most blockers:

| Move | Time | Cost | Decisions Cleared | % of Total |
|------|------|------|-------------------|------------|
| Jeffrey call (D2 + D5) | 30 min | $0 | Product truth + Team tier | ~30% |
| Solo pricing defaults (D4) | 10 min | $0 | Annual/seat/trial terms | ~15% |
| Lawyer hour (D1 + D7) | 1 hour | ~$200 | Consent + comparison risk | ~20% |
| Cofounder call (D3 + D6) | 30 min | $0 | Enterprise + launch mode | ~15% |

Total: ~2 hours of meetings and one external engagement to clear ~80% of marketing blockers. The remaining ~20% (ongoing competitor monitoring, edge-case pricing scenarios) resolves organically.

### Decision Register as Launch Trigger

The `launch-decisions.md` file serves a dual purpose: it tracks which decisions are pending (empty `Decision:` lines) and serves as the launch gate (when all `Decision:` lines are filled, marketing can ship). This is deliberately mechanical — no subjective judgment about "readiness," just a checklist of filled-in decision fields. The doc is wired into `STATUS.md` so the cofounder sync always surfaces the current blocker count.

## Related Concepts

- [[concepts/knowted-content-first-gtm-strategy]] - The content-first principle that produced the assets now blocked by unmade decisions; the decision register is the complement — content is built, now decisions must catch up
- [[concepts/knowted-competitive-advertising-risk-audit]] - The factual audit that gates D7 (comparison ad aggressiveness); all claims in marketing assets trace back to this audit
- [[concepts/llm-feature-fabrication-audit-pattern]] - The fabrication incident that gates D3 (Enterprise honesty); ~7 fabricated features must be resolved before Enterprise tier goes live
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework that the decision register operationalizes; Jeffrey's investor intros (3 days overdue as of Jun 12) are a separate P0 tracked there
- [[concepts/knowted-local-first-pricing-pivot]] - The pricing structure ($0/$19/$69) that D4 and D5 finalize edge cases for
- [[concepts/knowted-expert-knowledge-base-architecture]] - The expert/ directory where resolved decisions are logged in per-area decision logs for future reference

### D2 Resolution (2026-06-16)

On 2026-06-16, a 30-minute Jeffrey call resolved D2 (product-truth matrix) — the second-highest leverage move from the original 4-move plan. All 7 claimed capabilities were confirmed TRUE by Jeffrey:

| Claim | Status | Notes |
|-------|--------|-------|
| Unlimited recording | ✅ Confirmed | No caps |
| Transcription accuracy | ✅ Confirmed | — |
| Multi-speaker support | ✅ Confirmed | — |
| No-bot architecture | ✅ Confirmed | Local screen recording, user is participant |
| MCP auto-install | ✅ Confirmed | — |
| In-meeting Q&A | ✅ Confirmed | Runs locally |
| Language support | ✅ Corrected to **12** | Was "100+" in earlier drafts |

The language correction (100+ → 12) is the only factual change — all other claims survived verification. This unblocks website copy, the ad library, and the competitive comparison table. D2's `Decision:` line in `launch-decisions.md` can now be filled in, moving the decision register from 0/8 to 1/8 resolved.

The remaining highest-leverage moves are unchanged: D1 (lawyer hour on recording consent) and D4 (10-min solo pricing defaults).

## Sources

- [[daily/lcash/2026-06-13.md]] - Produced ranked decision register (launch-decisions.md) with 3 gates (legal/truth → pricing → sequencing); marketing blocked by decisions not content; 4 moves clear ~70% (Jeffrey call, solo pricing, lawyer hour, cofounder call); D1 recording-consent is longest dependency (external lawyer); product-truth matrix with 7 claims needing confirmation; wired into STATUS.md; pending offer to draft product-truth checklist and consent-law brief (Session 11:09, second session)
- [[daily/lcash/2026-06-16.md]] - Jeffrey call resolved D2: all 7 product claims confirmed TRUE; language support corrected to 12 (not 100+); unblocks website copy and ad library (Session 15:23)
