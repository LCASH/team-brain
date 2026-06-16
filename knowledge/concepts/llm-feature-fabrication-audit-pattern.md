---
title: "LLM Feature Fabrication Detection and Audit Pattern"
aliases: [llm-fabrication, feature-fabrication, claude-invented-features, enterprise-feature-hallucination, confirmed-vs-assumed-features]
tags: [ai-agent, methodology, anti-pattern, knowted, audit, data-quality]
sources:
  - "daily/lcash/2026-06-11.md"
created: 2026-06-11
updated: 2026-06-16
---

# LLM Feature Fabrication Detection and Audit Pattern

On 2026-06-11, lcash discovered that Claude had fabricated enterprise tier features for the Knowted pricing page — extrapolating "what enterprise SaaS usually offers" (SSO/SCIM, HIPAA/SOC 2, dedicated CSM, custom SLAs, compliance scorecards, AI-training opt-out, custom data retention) and presenting them as confirmed product capabilities. The user caught this because only 4 features were actually confirmed in the founder meeting. The incident established an audit pattern: always separate "confirmed by founders/specs" from "industry standard assumptions" when building feature lists, and never let LLM-generated content represent unbuilt features as committed in investor-facing or customer-facing documents.

## Key Points

- Claude confidently fabricated ~7 enterprise features by extrapolating industry norms — presented as confirmed product capabilities, not aspirational roadmap items
- Only **4 enterprise features were actually confirmed**: data residency, on-prem deployment, IT admin controls, Fable 5 pen-tested security
- Claude also **omitted a confirmed Free-tier feature** ("ask questions during the meeting") — fabrication and omission happened simultaneously
- The fabrication propagated across 5 files (tier-structure.md, pricing-page-copy.md, homepage-copy.md, pitch-deck.md, master-comparison-2026-06.md) before the user caught it
- **Audit methodology**: Compare every feature claim against meeting notes, product specs, and existing codebase — never trust LLM-generated feature lists as confirmed without explicit human verification
- The same pattern appeared in competitor claims: existing docs had founder-claimed capabilities (SOC 2, HIPAA) from the knowted.io website that weren't actually built — these propagated into new docs unchecked

## Details

### The Fabrication Mechanism

When asked to build pricing page copy with enterprise tier features, Claude applied a pattern: "what does an enterprise SaaS tier normally include?" This produced a plausible, comprehensive feature list that included SSO/SCIM integration (with specific vendor names), HIPAA/SOC 2 compliance certifications, a dedicated Customer Success Manager, custom data retention policies, compliance scorecards, AI-training opt-out controls, and custom SLAs — none of which were discussed in the founder meeting or exist in the product.

The fabrication was particularly dangerous because:

1. **The features were plausible** — every invented feature is something an enterprise SaaS product SHOULD eventually have. This made them pass a quick glance review.
2. **Specific details were included** — mentioning vendor names for SSO/SCIM integration made the claims look researched, not assumed.
3. **The format matched confirmed features** — fabricated and confirmed features were interleaved in the same list with identical formatting, making them indistinguishable at a glance.
4. **Propagation was immediate** — the fabricated features were written into the pricing source-of-truth document, then cascaded through 4 downstream files before the user reviewed.

### The Dual Failure

The user's audit caught both fabrication (features added that don't exist) and omission (features removed that do exist) in the same document:

| Category | Items | Status |
|----------|-------|--------|
| **Confirmed enterprise** | Data residency, on-prem deployment, IT admin controls, Fable 5 pen test | Kept |
| **Fabricated enterprise** | SSO/SCIM, HIPAA/SOC 2, dedicated CSM, custom SLA, compliance scorecards, AI-training opt-out, custom data retention | Moved to "Roadmap/TBD" |
| **Omitted free tier** | In-meeting Q&A (ask questions during the meeting) | Restored |

The omission is arguably worse than the fabrication: a confirmed product capability was silently dropped, making the Free tier appear weaker than it actually is. This likely happened because in-meeting Q&A doesn't fit the standard "meeting recording AI" feature taxonomy that Claude was working from.

### The Audit Pattern

The incident established a three-step audit pattern for any LLM-generated feature documentation:

**Step 1 — Source verification**: For every claimed feature, identify the source: meeting notes, product specs, existing code, or "assumed from industry norms." Mark each explicitly.

**Step 2 — Confirmed vs roadmap separation**: Split features into "Confirmed — shipping at launch" and "Roadmap — requires founder classification." Never present roadmap items with the same visual treatment as confirmed items (checkmarks, green badges, etc.).

**Step 3 — Completeness check**: Compare the generated feature list against the original meeting notes or spec document to catch omissions. LLMs are biased toward "what should be there" (standard features) over "what was actually discussed" (specific decisions).

### Broader Applicability

This pattern applies beyond pricing pages to any context where an LLM generates claims about a product's capabilities: investor pitch decks, sales collateral, comparison tables, integration documentation, and API capability docs. The risk is proportional to the audience: fabricated features in an internal planning doc are a minor issue; fabricated features in an investor-facing pitch deck are a credibility disaster.

The same fabrication mechanism appeared in the competitive comparison: the existing knowted.io website had founder-claimed capabilities (SOC 2, HIPAA compliance) that aren't actually built. These legacy claims propagated into the new pricing docs unchecked, creating a second source of unverified features beyond Claude's extrapolation. Source documents need audit flags — not just LLM output.

## Related Concepts

- [[concepts/knowted-local-first-pricing-pivot]] - The pricing pivot during which the fabrication was discovered; enterprise tier had to be audited and split into confirmed vs roadmap
- [[concepts/knowted-competitive-advertising-risk-audit]] - The same verification methodology (check claims against primary sources) applied to competitor features rather than own-product features
- [[connections/output-before-infrastructure-sequencing]] - Fabricated features are a form of "infrastructure without output" — claiming capabilities that don't exist is the documentation equivalent of building systems for non-existent signals

## Sources

- [[daily/lcash/2026-06-11.md]] - Claude fabricated ~7 enterprise features by extrapolating industry norms; only 4 confirmed from meeting; also omitted confirmed Free-tier feature (in-meeting Q&A); propagated across 5 files before user caught it; audit separated confirmed vs roadmap; 5 Knowted competitive comparison rows changed from ✅ to 🟡 Roadmap; existing knowted.io site had founder-claimed capabilities not actually built (Sessions 13:44, 13:50)
