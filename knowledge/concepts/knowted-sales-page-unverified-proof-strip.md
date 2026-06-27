---
title: "Knowted Sales Page Unverified Proof-Strip Statistics"
aliases: [proof-strip-unverified, sales-page-stats, unverified-social-proof, knowted-proof-strip]
tags: [knowted, website, data-quality, marketing, copy, verification]
sources:
  - "daily/lcash/2026-06-18.md"
created: 2026-06-18
updated: 2026-06-18
---

# Knowted Sales Page Unverified Proof-Strip Statistics

On 2026-06-18, during a full homepage copy pass, lcash identified that the `/sales` landing page's proof strip contains three statistics — "2-3 hrs saved", "240+ meetings captured", and "+11%" — but only "+11%" has been confirmed by Jeffrey. The other two statistics were carried forward from earlier drafts without independent verification. This follows the same pattern as the enterprise feature fabrication (see [[concepts/llm-feature-fabrication-audit-pattern]]): plausible-sounding claims that propagated through multiple document iterations without being validated against a primary source.

## Key Points

- `/sales` page proof strip shows three stats: "2-3 hrs saved", "240+ meetings captured", and "+11%" — only "+11%" is confirmed by Jeffrey
- The unverified stats were not flagged by prior copy audits because they appeared alongside the confirmed stat, inheriting its credibility by proximity
- This is the same propagation pattern as the enterprise feature fabrication: plausible claims surviving multiple revision cycles unchallenged
- The page should not go wide with unverified social proof — either verify with Jeffrey or remove the unconfirmed stats before any promotional push
- Proof-strip statistics are particularly high-risk for legal exposure in comparative advertising because they are presented as factual claims, not aspirational positioning

## Details

### The Proof-Strip Verification Gap

The `/sales` landing page (built as part of the waitlist site iteration documented in [[concepts/knowted-waitlist-website-iteration]]) includes a proof strip — a horizontal bar of statistics designed to build credibility with visitors. The strip presents three numbers as factual claims about the product's impact. During the June 18 homepage copy pass, the Pricing and Sales pages were reviewed and left untouched because they appeared "already on-vision." However, closer inspection revealed that only one of the three statistics had been verified with the product team.

The "+11%" figure was confirmed during the D2 product-truth resolution (see [[concepts/knowted-launch-decision-register]]). The "2-3 hrs saved" and "240+ meetings captured" figures have no documented verification trail. They may be accurate — Knowted may well save 2-3 hours per week for typical users — but they have not been confirmed as true by either Jeffrey or any usage data.

### Why This Matters

Unverified social proof on a public-facing sales page carries two risks:

**Legal risk**: Under Australian Consumer Law (ACL §18) and US FTC guidelines, factual claims on commercial pages must be substantiated. "240+ meetings captured" implies measured real-world usage data. If the number was estimated or fabricated during a copy drafting session, it constitutes a misleading claim. The competitive advertising risk audit (see [[concepts/knowted-competitive-advertising-risk-audit]]) already recommended careful sourcing of all claims; the proof strip was not included in that audit scope.

**Credibility risk**: If a prospect or competitor challenges any single statistic and it cannot be substantiated, the credibility of all claims on the page is undermined — including the verified "+11%" figure. The proximity halo that made the unverified stats appear credible works in reverse when any one stat is challenged.

### Recommended Action

The most conservative approach: remove "2-3 hrs" and "240+ meetings" from the proof strip immediately, leaving only "+11%" (confirmed) until the other two stats are verified with Jeffrey. The proof strip can operate with a single strong statistic — one verified number is more credible than three where two are questionable.

Alternatively, a 5-minute Jeffrey verification call could resolve both stats. If confirmed, they should be annotated with their source and measurement methodology in the site's internal documentation for future audits.

## Related Concepts

- [[concepts/knowted-launch-decision-register]] - D2 (product truth) resolved all 7 product claims; the proof strip stats were NOT part of the D2 matrix and were never explicitly verified
- [[concepts/llm-feature-fabrication-audit-pattern]] - The same propagation pattern: plausible claims surviving revision cycles unchallenged; proof-strip stats may have been LLM-generated during an earlier copy session
- [[concepts/knowted-competitive-advertising-risk-audit]] - The factual audit of competitor claims; the `/sales` proof strip was not in scope but carries the same legal risk profile
- [[concepts/knowted-waitlist-website-iteration]] - The website iteration where the proof strip was reviewed and the unverified stats were flagged

## Sources

- [[daily/lcash/2026-06-18.md]] - During full homepage copy pass, `/sales` page proof strip identified with 3 stats: "2-3 hrs", "240+ meetings", "+11%" — only "+11%" confirmed by Jeffrey; other two unverified; Pricing and Sales pages initially left untouched ("already on-vision") but proof strip flagged as needing verification before page goes wide (Session 15:29)
