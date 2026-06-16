---
title: "Knowted Competitive Advertising Risk Audit"
aliases: [competitive-advertising-audit, competitor-pricing-verification, knowted-factual-audit, comparative-advertising-legal-risk]
tags: [knowted, competitive-intelligence, legal-risk, marketing, website, pricing]
sources:
  - "daily/lcash/2026-06-11.md"
created: 2026-06-11
updated: 2026-06-16
---

# Knowted Competitive Advertising Risk Audit

On 2026-06-11, lcash performed a comprehensive factual audit of all competitor claims on the Knowted website's sales comparison page, using Perplexity MCP and live pricing page verification. Multiple pricing claims were wrong or unsubstantiated — Fathom was cited at "$28/seat" when actual pricing is $25-34/seat/mo, Avoma was missing the $29 CI add-on, and Gong pricing was presented as fact when it is quote-only. Unsubstantiated claims (multi-year lock-in, per-team annual cost, $10K setup fee) were removed. A three-paragraph sourcing disclaimer was added with date-stamped comparison and correction email. The audit also assessed comparative advertising legal risk for a pre-revenue startup.

## Key Points

- **Fathom price corrected**: "$28/seat" → "$25-34/seat/mo" ($19/seat Team, $34/seat Business on fathom.ai/pricing as of 2026-06-11)
- **Avoma price corrected**: "$29-39" → "$19 + $29 CI add-on" — the coaching-parity tier (comparable to Knowted) is actually $48/seat
- **Gong pricing changed to "Custom-quoted"**: Their site shows no numbers; all third-party sourced from G2/Vendr reports — citing these as Gong's pricing is the easiest C&D to write
- **Unsubstantiated claims removed**: Multi-year lock-in row, per-team annual cost row, $10K setup fee — Perplexity couldn't find primary source confirmation
- **Fireflies BIPA lawsuits strengthened**: Fricker v. Fireflies.AI (N.D. Ill.) + Cruz v. Fireflies.AI (C.D. Ill.) — docketed and citable, strongest defensible competitive claim
- **Pre-revenue C&D risk assessment**: Comparative advertising is legal (US/UK/AU) and industry-normal (Sybill and Avoma both publish Gong comparisons), but pre-revenue startups can't absorb C&D costs like funded competitors — Sybill has $12M funding for that risk
- **Granola $125M Series C confirmed**: $1.5B valuation, Mar 2026, Index Ventures — useful competitive intelligence

## Details

### Verification Methodology

The audit checked every competitor claim on the Knowted website's `SalesTeams.tsx` comparison page against three sources: (1) the competitor's live pricing page via browser, (2) Perplexity MCP deep search, and (3) third-party review sites (G2, Vendr, TrustRadius). Where sources conflicted, the competitor's own pricing page was treated as authoritative. Where pricing pages showed no numbers (Gong), the claim was reframed as third-party-sourced with explicit attribution.

A key limitation was discovered: Perplexity MCP can't reliably reach vendor pricing pages directly — the tool returns general knowledge rather than live page scrapes. Browser-based verification against actual pricing URLs was required for live price validation.

### Specific Corrections

**Fathom**: The most commonly cited Knowted competitor. Prior docs cited "$28/seat" which appears in older review articles. Actual pricing from fathom.ai/pricing (June 2026): Team plan $19/seat/mo (annual) or $25/seat/mo (monthly), Business plan $25/seat/mo (annual) or $34/seat/mo (monthly). The comparison table now shows "$25-34/seat/mo" spanning the monthly range.

**Avoma**: Prior docs cited "$29-39" which is the base Starter/Business range. However, Avoma's AI coaching intelligence — the feature comparable to Knowted — requires a "$29 CI add-on" on top of the Startup plan ($19). The coaching-parity comparison is therefore $48/seat, not $29. A "coaching-parity tier" row was added to the comparison table for apples-to-apples comparison.

**Gong**: The most legally sensitive claim. Gong deliberately hides pricing — their website shows no per-seat numbers. All public pricing figures ($20-30K/year, $100-150/seat) come from third-party reviews on G2 and Vendr. Citing these as "Gong's pricing" on a public comparison page is the easiest cease-and-desist to write because the claimant can't point to Gong's own published price. The comparison table now shows "Custom-quoted" with FAQ attribution to G2/Vendr reports.

### Legal Risk Assessment

Comparative advertising is legal in the US (Lanham Act §43(a)), UK (Business Protection from Misleading Marketing Regulations 2008), and Australia (ACL §18). It is industry-normal in the meeting intelligence space — both Sybill and Avoma publish explicit Gong comparison pages. However, the risk assessment for a pre-revenue startup is different from a funded competitor:

| Factor | Funded Competitor (Sybill) | Pre-Revenue Startup (Knowted) |
|--------|--------------------------|------------------------------|
| C&D response budget | $12M funding, legal team | Near-zero |
| Claims defensibility | Backed by verifiable data | Some claims were unsubstantiated |
| Reputational stakes | Established brand | Unknown brand — C&D is disproportionate damage |

The recommendation was to: (1) remove all unsubstantiated claims immediately, (2) add a sourcing disclaimer with date-locked comparison and correction email, (3) consider a $200 comparative-ad legal review with an Australian lawyer before going live, and (4) mark any forward-looking Knowted features (not yet shipped) with launch date caveats.

### Sourcing Disclaimer

A three-paragraph disclaimer was added under the comparison table:

1. Sources cited with dates (G2, Vendr, vendor websites)
2. Date-locked statement: "Pricing data verified as of 2026-06-11"
3. Correction email: "If any information is inaccurate, contact [email] and we'll update within 48 hours"

This disclaimer follows industry best practice for comparative advertising and provides a good-faith defense against C&D claims.

### Designer Hiring for Website Redesign

The same session included scoping a professional website redesign. The recommendation was **Framer over Figma-handoff** for faster, cheaper execution with strong visual quality from Framer-native designers. Budget locked at **$3-8K** on Upwork with 2-4 week timeline. Design direction: "Cluely energy, Linear restraint, Granola warmth — less SaaS template, more product-as-statement." For finding Cluely-tier designers, Read.cv and Cosmos are the right channels; Dribbble/Toptal/Upwork won't land that calibre.

## Related Concepts

- [[concepts/knowted-local-first-pricing-pivot]] - The pricing pivot that triggered the competitive comparison rewrite; the 3-tier structure needs accurate competitor pricing for positioning
- [[concepts/knowted-content-first-gtm-strategy]] - The GTM strategy that the website redesign serves; competitive advertising is part of the content surface
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - Banker feedback to lead with margin/cost leadership — the comparison table is the primary vehicle for this message
- [[concepts/llm-feature-fabrication-audit-pattern]] - The same audit methodology (verify claimed features against primary sources) applied to competitor claims rather than own-product claims

## Sources

- [[daily/lcash/2026-06-11.md]] - Full factual audit of competitor claims; Fathom corrected $28→$25-34; Avoma corrected to include $29 CI add-on ($48 coaching-parity); Gong changed to "Custom-quoted"; multi-year lock-in, per-team annual cost, $10K setup fee rows deleted; Fireflies BIPA lawsuits strengthened with Fricker + Cruz case citations; Granola $125M Series C confirmed; 3-paragraph disclaimer added; comparative advertising legal risk assessed ($200 AU legal review recommended); Framer recommended for redesign at $3-8K; designer channels Read.cv/Cosmos (Sessions 10:57, 11:31, 13:50)
