---
title: "Connection: Pricing Cascade and Dependency-Order Editing"
connects:
  - "concepts/knowted-local-first-pricing-pivot"
  - "concepts/knowted-content-first-gtm-strategy"
  - "concepts/llm-feature-fabrication-audit-pattern"
sources:
  - "daily/lcash/2026-06-11.md"
created: 2026-06-11
updated: 2026-06-16
---

# Connection: Pricing Cascade and Dependency-Order Editing

## The Connection

When a foundational business decision changes (like pricing tier structure), all downstream documents must be updated in dependency order — pricing first, then pitch deck, then website copy, then outreach, then content strategy. This is the inverse of the "output before infrastructure" principle documented in [[connections/output-before-infrastructure-sequencing]]: that connection says "don't build amplification before the signal exists"; this connection says "when the signal changes, update dependents in topological order." Both are applications of the same underlying principle: respect the dependency graph.

## Key Insight

The non-obvious insight is that **LLM-assisted document generation amplifies cascade failures.** When Claude rewrites a pitch deck from a changed pricing brief, it can propagate the new pricing correctly while simultaneously fabricating features that were never decided. The cascade creates a false sense of completeness — "all documents are updated" — while the LLM has silently introduced new claims (enterprise features, competitor comparisons, positioning statements) that weren't in the source-of-truth document. Human review at each cascade step is essential, not just at the leaf documents.

On 2026-06-11, lcash's 9-item cascade plan correctly ordered the updates: pricing tier document → pitch deck → website copy → competitive comparison → content strategy → accountability plan. However, the LLM introduced fabricated enterprise features during the pitch deck step (see [[concepts/llm-feature-fabrication-audit-pattern]]) that propagated through 4 more downstream documents before the user caught them. The dependency ordering was correct; the per-step verification was missing.

## Evidence

The Knowted pricing pivot cascaded through these documents in this order:

1. `workstreams/pricing/tier-structure.md` (source of truth — $0/$19/$69)
2. `pitch-deck.md` (rewritten from sales-team-led to local-first) ← **fabrication introduced here**
3. `pricing-page-copy.md` (website copy) ← fabrication propagated
4. `homepage-copy.md` (website hero/CTAs) ← fabrication propagated
5. `master-comparison-2026-06.md` (competitive table) ← fabrication propagated + competitor claims needed independent verification
6. Video #1 concept (content reframed)
7. Cofounder accountability plan (pricing decisions locked)

Documents 2-5 all contained the fabricated enterprise features. The user caught the fabrication during review of document 2 (pitch deck), but documents 3-5 had already been written with the fabricated claims. The correction required going back through documents 3-5 to strip the fabricated features — a reverse cascade.

## The General Pattern

Cascade editing has three failure modes:

1. **Wrong ordering** — editing downstream docs before the source of truth is stable (changes propagate incorrectly then need reverting)
2. **LLM fabrication during cascade** — the LLM adds plausible new claims during each rewrite step that weren't in the source (caught on 2026-06-11)
3. **Incomplete propagation** — some downstream docs are missed, creating inconsistency (the original configuration drift pattern from [[concepts/configuration-drift-manual-launch]])

The prevention for mode 2 is: **at each cascade step, diff the output against the input + the source of truth. Any claim in the output that isn't traceable to either the source or the input should be flagged for human verification.** This is the document-editing equivalent of the "theorize → test → verify" discipline from [[concepts/unverified-fix-deployment-anti-pattern]].

## Related Concepts

- [[concepts/knowted-local-first-pricing-pivot]] - The pricing decision that triggered this cascade; the cascade methodology was established during this pivot
- [[concepts/llm-feature-fabrication-audit-pattern]] - The fabrication discovered mid-cascade; the audit pattern is the per-step verification mechanism
- [[connections/output-before-infrastructure-sequencing]] - The inverse principle: don't amplify before the signal exists. This connection says: when the signal changes, update amplifiers in dependency order
- [[concepts/configuration-drift-manual-launch]] - Incomplete propagation (cascade failure mode 3) is the configuration-management equivalent of batch-file drift

