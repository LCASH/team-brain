---
title: "Knowted Local-First Pricing Pivot"
aliases: [knowted-pricing, local-first-pricing, knowted-3-tier, free-local-cloud-upsell, knowted-arr-model]
tags: [knowted, pricing, strategy, local-first, positioning, gtm]
sources:
  - "daily/lcash/2026-06-11.md"
created: 2026-06-11
updated: 2026-06-16
---

# Knowted Local-First Pricing Pivot

On 2026-06-11, lcash executed a major Knowted pricing and positioning reset after a Luke/Jeffrey founder strategy meeting. The previous pitch was fully sales-team-led and cloud-first — completely misaligned with the new strategy. Pricing was locked at three tiers: **$0 (free local) / $19 (cloud team) / $69 (secure enterprise)**, with annual discounts to $15/$55. The fundamental repositioning: Knowted runs free and locally by default, with cloud as the upsell. The target audience reframed from sales teams to entrepreneurs as the 70% free-tier funnel. ARR model updated from $2.4M to ~$3.94M under the new structure. Source of truth is `workstreams/pricing/tier-structure.md`.

## Key Points

- **3-tier pricing locked**: $0 free (local) / $19/mo team (cloud) / $69/mo enterprise (secure) — annual 20% discount → $15 / $55
- **Local-first positioning**: Product runs free on the user's machine by default; cloud sync is the upsell, not the default — eliminates the "trust us with your data" objection for first-time users
- **Target audience pivot**: Entrepreneurs are the 70% free-tier funnel (previously the strategy was sales-team-focused from the start)
- **Video #1 reframed**: "Your AI finally knows about your meetings" — free tier demo, no product feature blocker needed before shipping
- **Enterprise tier audited**: Only 4 features confirmed (data residency, on-prem deployment, IT admin controls, Fable 5 pen-tested); ~7 claimed features (SSO/SCIM, HIPAA/SOC 2, dedicated CSM, custom SLA) moved to roadmap pending Jeffrey's confirmation
- **ARR model recalculated**: ~$3.94M at the new tier structure (up from $2.4M under prior model)

## Details

### The Strategic Reset

The existing pitch deck was fully sales-team-led and cloud-first — targeting enterprise sales directors as the primary buyer. The Luke/Jeffrey founder meeting decided this was wrong on two dimensions: (1) the product should be free and local-first to eliminate adoption friction, and (2) the initial funnel should target entrepreneurs and small teams who would adopt the free tier and naturally upsell to cloud when they need team features.

This is a fundamental positioning change, not just a price adjustment. Under the old model, Knowted competed directly with Gong, Fathom, and Avoma on features and price. Under the new model, Knowted competes on a different axis entirely: free local tool that "just works" without a cloud account, with paid cloud features for teams that need sharing and collaboration. The competitive comparison becomes "Knowted free vs competitors at $19-69/seat/mo" rather than "Knowted at $X vs Gong at $Y."

### Cascade Editing in Dependency Order

When the pricing decision changed, lcash executed a 9-item plan to cascade the new positioning through all downstream materials. The key principle: **when a foundational decision changes, cascade edits outward in dependency order** — pricing first, then pitch deck, then website copy, then outreach, then content strategy. The pricing document (`workstreams/pricing/tier-structure.md`) is the single source of truth; if downstream docs contradict it, fix downstream, never upstream.

Materials updated in this cascade:
- Tier structure document (source of truth)
- Pitch deck (rewritten from sales-team-led to local-first narrative)
- Website copy (waitlist CTA, 3-tier pricing page, sales landing page)
- Competitive comparison table (corrected to reflect new positioning)
- Video #1 concept (reframed from product demo to free-tier experience)
- Cofounder accountability plan (pricing decisions locked in §6.7)

### Enterprise Feature Fabrication Discovery

During the cascade editing, lcash discovered that Claude had **fabricated enterprise tier features** — extrapolating "industry standard" enterprise capabilities (SSO/SCIM vendor names, HIPAA/SOC 2 compliance, dedicated CSM, custom SLAs, compliance scorecards, AI-training opt-out) and presenting them as confirmed product features. Only 4 enterprise features were actually confirmed from the founder meeting: data residency, on-prem deployment, IT admin controls, and Fable 5 pen-tested security. The ~7 fabricated items were moved to a clearly marked "Roadmap/TBD" section pending Jeffrey's classification. See [[concepts/llm-feature-fabrication-audit-pattern]] for the full audit methodology.

### Free Tier Feature Confirmation

The free tier includes an important confirmed capability that was initially omitted: **in-meeting Q&A** (ask questions during the meeting). This runs entirely locally and is a key differentiator — competitors typically gate real-time interaction behind paid tiers. The omission was caught by the user during the pricing page review, reinforcing that feature lists should be audited against meeting notes, not generated from assumptions.

## Related Concepts

- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework that this pricing pivot feeds into; banker feedback drove the margin/cost-leadership framing that the $0 free tier enables
- [[concepts/knowted-content-first-gtm-strategy]] - Video #1 was reframed to demonstrate the free tier; the content-first principle still applies — ship the video before building cloud infrastructure
- [[concepts/llm-feature-fabrication-audit-pattern]] - The enterprise feature fabrication discovered during this pricing cascade; methodology for catching LLM-invented capabilities
- [[concepts/knowted-competitive-advertising-risk-audit]] - The competitive comparison table updated alongside the pricing pivot; factual verification of competitor pricing claims
- [[connections/output-before-infrastructure-sequencing]] - The cascade-editing principle (pricing → deck → website → outreach) is a dependency-order variant of the output-before-infrastructure principle

## Sources

- [[daily/lcash/2026-06-11.md]] - Pricing locked at $0/$19/$69; local-first positioning; entrepreneurs as 70% free-tier funnel; ARR $2.4M→$3.94M; Video #1 reframed as "Your AI finally knows about your meetings"; cascade edits through 9 downstream docs; enterprise features audited (4 confirmed, ~7 fabricated moved to roadmap); free tier includes in-meeting Q&A; pitch deck rewritten from sales-team-led to local-first (Sessions 10:20, 13:44, 13:50)
