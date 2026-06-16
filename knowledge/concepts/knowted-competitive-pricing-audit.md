---
title: "Knowted Competitive Pricing Audit"
aliases: [pricing-audit, competitive-analysis, knowted-pricing, meeting-tool-pricing]
tags: [knowted, competitive-analysis, pricing, positioning, legal]
sources:
  - "daily/lcash/2026-06-12.md"
created: 2026-06-12
updated: 2026-06-12
---

# Knowted Competitive Pricing Audit

On 2026-06-11 (documented 2026-06-12), lcash conducted a live-verified competitive pricing analysis across the AI meeting tool landscape. The audit covered Fathom, Avoma, Sybill, and Gong via direct verification, with Granola, Otter, Fireflies, Loom, and tl;dv priced via third-party sources. Knowted's locked tiers (Free $0 / Team $19 / Enterprise $69) position it 24-80% cheaper than coaching-parity competitors, with only Granola Business ($14) undercutting on price but lacking the coaching layer.

## Key Points

- **Live-verified pricing**: Fathom Business $34/$25; Avoma Startup $19 + CI add-on $29 = $48 coaching parity; Sybill Pro $30; Gong quote-only (~$100+/seat per G2/Vendr); Otter Pro minutes cut 6,000 to 1,200; Granola capped free tier after $125M Series C at $1.5B; tl;dv Business $59
- **Knowted tiers**: Free $0 / Team $19 / Enterprise $69 -- 24-80% cheaper than coaching-parity competitors
- **Gong sourcing rule**: Pricing claims must cite G2/Vendr reviews, never gong.io (publishes nothing)
- **Legal differentiator**: Fireflies.AI has two pending federal BIPA class actions (Fricker N.D. Ill., Cruz C.D. Ill.) over meeting-bot voiceprint collection; Knowted's local-first, no-bot architecture is safest in category
- **Privacy boundary for teams**: No team/free tier = fully local; Team tier requires login which gates cloud sync

## Details

### Pricing Landscape

The audit revealed significant pricing dispersion in the AI meeting tool market. At the low end, Granola Business sits at $14/month but offers no coaching layer -- it is purely a meeting notes tool. Knowted's Team tier at $19 is the cheapest option with coaching capabilities. Avoma appears cheap at $19/month (Startup tier) but requires a $29/month Conversation Intelligence add-on to reach coaching parity, bringing the effective price to $48. Fathom Business ranges from $25-34/month. Sybill Pro is $30/month. At the high end, tl;dv Business is $59/month and Gong is quote-only, with G2 and Vendr reviews suggesting $100+ per seat.

Notable market movements were captured: Otter cut its Pro tier recording minutes from 6,000 to 1,200, suggesting margin pressure or a strategic shift toward enterprise. Granola capped its previously generous free tier following a $125M Series C at a $1.5B valuation, signaling the typical post-fundraise monetization squeeze.

Several claims were deliberately removed from the positioning materials during the audit. "5-15%/yr renewal increases" and "50-100% early-termination penalty" attributed to Gong were dropped because they came from anecdotal review claims rather than primary sources. The sourcing rule was established: Gong pricing claims must cite G2 or Vendr reviews specifically, never gong.io, which publishes no pricing information.

### Legal Positioning

The audit surfaced a material legal differentiator for Knowted. Fireflies.AI faces two pending federal class actions under the Illinois Biometric Information Privacy Act: Fricker (N.D. Ill.) and Cruz (C.D. Ill.), both alleging unauthorized voiceprint collection via the Fireflies meeting bot. This legal exposure is inherent to the "bot joins your meeting" architecture used by most competitors.

Knowted's architecture is fundamentally different: it records the screen on the user's device as a participant in the meeting, with nothing leaving the laptop unless the user explicitly shares it. This local-first, no-bot design was assessed as materially stronger than assumed per counsel brief (documented as D1: Legal posture). The privacy boundary is enforced at the tier level: the free tier is fully local with no account required, while the Team tier requires login, which gates cloud sync. This means users can get full value from the free tier without any data ever leaving their machine.

### Strategic Implications

The 24-80% price advantage against coaching-parity competitors gives Knowted a strong cost-leadership narrative -- the exact positioning the banker recommended in the cofounder accountability framework. The combination of lowest-price-with-coaching and strongest-legal-posture-in-category creates a defensible positioning that is difficult for incumbents to replicate without fundamental architectural changes to their meeting-bot models.

The D5 question (Team at launch) was resolved YES with the privacy boundary as the mechanism: team functionality requires login, which is the gate for cloud sync. This preserves the local-first promise for individual users while enabling collaboration features for paying teams.

## Related Concepts

- [[concepts/knowted-content-first-gtm-strategy]] - The GTM strategy that uses this pricing data in competitive positioning content
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The banker's recommendation to lead with cost leadership, which this audit validates
- [[concepts/knowted-sales-prospecting-tool-stack]] - The outreach tools used to communicate this competitive positioning to prospects

## Sources

- [[daily/lcash/2026-06-12.md]] - Live-verified pricing (Fathom $34/$25, Avoma $19+$29, Sybill $30, Gong ~$100+, Otter minutes cut, Granola free tier capped, tl;dv $59), Knowted tiers locked (Free/Team $19/Enterprise $69), Gong sourcing rule (G2/Vendr only), removed Gong renewal/termination claims, Fireflies BIPA class actions (Fricker + Cruz), local-first no-bot legal posture (D1), Team tier privacy boundary (D5), 24-80% cheaper positioning (Session times)
