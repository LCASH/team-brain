---
title: "Knowted Content-First GTM Strategy"
aliases: [content-before-infrastructure, knowted-gtm, ship-first-build-later, knowted-positioning]
tags: [knowted, gtm, content-strategy, positioning, founder-discipline]
sources:
  - "daily/lcash/2026-06-04.md"
  - "daily/lcash/2026-06-11.md"
  - "daily/lcash/2026-06-12.md"
  - "daily/lcash/2026-06-13.md"
  - "daily/lcash/2026-06-23.md"
  - "daily/lcash/2026-06-27.md"
created: 2026-06-04
updated: 2026-06-27
---

# Knowted Content-First GTM Strategy

On 2026-06-04, lcash's Knowted planning sessions crystallised a sequencing principle for founder-led GTM: **ship public content before building outreach infrastructure.** Building a LinkedIn automation system (Sales Navigator filters, HeyReach sequences, proxy warmup) without having public content to point prospects toward is the classic founder trap — infrastructure without output. The recommended order is: (1) ship Video #1 tonight, (2) build LinkedIn outreach system Thursday, (3) then activate paid prospecting tools once both content and sequences exist.

## Key Points

- **"Infrastructure without output is the classic founder trap"** — building a LinkedIn outreach system before having a single public video to reference is backwards
- **Positioning guardrail**: Frame Knowted as "tell each rep what to do on the NEXT call" not "find what's wrong" — differentiate from Gong-clone messaging in all outreach and content
- **Video #1 is founder POV, no product demo** — lowers the production bar so it actually ships; a personal perspective video is publishable in one evening while a product demo requires polished UI
- **Shorts cut from longs** (3 shorts/week from 2 YouTube videos) — no independent short-form production, which would double the content burden for marginal incremental reach
- **LinkedIn-only cold sequence** over multi-channel — dropped email component entirely for initial outreach; LinkedIn InMail and connection requests have higher response rates for founder-to-founder selling than cold email

## Details

### The Sequencing Principle

When the question arose whether to prioritise building the LinkedIn outreach system (Sales Navigator saved filters, HeyReach account setup, prospect list building) versus shipping the first YouTube video, the recommendation was unambiguous: **ship the video first.** The reasoning is structural, not motivational:

A LinkedIn cold outreach sequence that references "our latest video on [topic]" in Touch 2 is dramatically more effective than one that links to a bare website. The video serves as social proof ("this founder is publicly building and sharing"), as a content hook ("here's a 90-second demo"), and as a conversation starter ("curious what you thought about X point"). Without it, the outreach sequence has one fewer touch point and every remaining touch must carry more persuasion burden.

Conversely, the outreach infrastructure (tool accounts, saved filters, sequence templates) doesn't become more valuable by existing earlier. It provides value only when activated with prospects — and activation without content is a weaker version of itself.

This is a general founder sequencing rule: **external-facing output should precede internal-facing infrastructure** when both are needed for the same initiative. The infrastructure exists to amplify output; without output, there is nothing to amplify.

### Knowted Positioning

A key positioning constraint was established during the outreach sequence design: Knowted should be framed as **"tell each rep what to do on the NEXT call"** rather than **"find what's wrong with your calls."** This distinction matters because:

1. **Defensive vs offensive framing**: "Find what's wrong" positions Knowted as a diagnostic/audit tool — the same space as Gong, Chorus, and Clari. These are established players with massive market share. "Tell them what to do next" positions Knowted as a coaching/enablement tool — a forward-looking, action-oriented frame that is differentiated.

2. **Buyer psychology**: Sales leaders buying "find what's wrong" tools are in a diagnostic mindset — they suspect a problem and want data. Sales leaders buying "tell reps what to do" tools are in an enablement mindset — they want their team to perform better. The enablement buyer is typically more willing to invest because the ROI narrative is clearer (more closed deals vs fewer identified problems).

3. **Margin/cost leadership alignment**: The banker's feedback (see [[concepts/knowted-cofounder-accountability-banker-feedback]]) recommended leading with margin/cost leadership. "AI coaching at a fraction of human coaching cost" aligns with the "what to do next" frame (coaching). "AI analysis at a fraction of Gong's cost" aligns with the "what's wrong" frame (diagnostic) — and invites a direct feature-by-feature comparison that Knowted would lose at this stage.

### Workstream Organisation

All Knowted admin work was segmented into workstream-based folders with a central `STATUS.md` tracker file serving as the single source of truth across ~10 workstreams. Each workstream (content-strategy, outreach-gtm, pitch-deck, co-founder-search, etc.) gets its own directory with a README and working artifacts. The `STATUS.md` file provides a one-screen overview of progress, blockers, and next actions across all workstreams — designed for the weekly cofounder sync where both Luke and Jeffrey need to see the full picture without drilling into individual workstream files.

### Expected LinkedIn Outreach Economics

With 100 connection requests per week via HeyReach, realistic economics based on category benchmarks:

| Stage | Conversion Rate | Weekly Volume |
|-------|----------------|---------------|
| Connection requests sent | 100% | 100 |
| Connections accepted | 20-30% | 20-30 |
| Replies to sequence | 5-10% of accepted | 1-3 |
| Meetings booked | 50% of replies | 1-2 |

The 1-2 meetings per week from LinkedIn outreach supplements the 3 investor + 3 grant conversations targeted in the accountability framework. Together, these channels aim to produce 5-8 external conversations per week — sufficient for a pre-Series A founder to build pipeline while also producing content.

### Video #1 Reframed After Pricing Pivot (2026-06-11)

On 2026-06-11, the pricing pivot to a $0 free local tier (see [[concepts/knowted-local-first-pricing-pivot]]) reframed Video #1 from "founder POV, no product demo" to **"Your AI finally knows about your meetings"** — a free tier demo. The new framing is stronger because it demonstrates a product the viewer can immediately use for free, rather than asking them to watch a founder talking about a product they'd need to pay for. The "no product blocker" constraint from June 4 is preserved — the free tier runs locally, so the demo can show real functionality without needing cloud infrastructure to be built first.

The website was also rewritten with a waitlist CTA, 3-tier pricing display, and a `/sales` landing page — giving Video #1 a destination to link to from day one.

### Waitlist Site Launch and Content Audit (2026-06-12)

On 2026-06-12, the knowted.io waitlist site was pushed live (commit `f5120cb`) with a full content audit verifying competitor claims (accurate Avoma $19+$29, Fathom pricing footnote, comparison disclaimers). The waitlist form initially had no endpoint — it fell back to localStorage, silently losing signups. Google Apps Script → Google Sheet was chosen over Formspree ($0 unlimited vs 50/month free cap), and the Sheet doubles as the CRM seed.

A critical legal/product positioning decision was made: local screen recording, no bot, user-is-a-participant is the safest architecture in the category (vs Otter/Fireflies bot litigation). The marketing line: "Records your screen, on your device, as you — no bot. Nothing leaves your laptop unless you share it." This aligns the privacy boundary with the pricing boundary: no-login = local-only, login = cloud sync. The same boundary serves legal, product, and marketing simultaneously.

The social ad creative system was also built — headless Chrome (Puppeteer) renders HTML+CSS to PNG for pixel-perfect brand control (see [[concepts/html-css-ad-creative-renderer]]), with ~10 comparison concepts ready for the posting cadence.

## Related Concepts

- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The broader accountability framework that this GTM strategy operates within; banker feedback shaped the positioning guardrail
- [[concepts/knowted-sales-prospecting-tool-stack]] - The specific tooling (Saleshandy + HeyReach + Apollo free) that executes this strategy; tool selection follows content shipping in the sequencing order
- [[concepts/knowted-local-first-pricing-pivot]] - The pricing pivot that reframed Video #1 from founder POV to free-tier demo; $0 local tier eliminates the "product blocker" problem for content creation
- [[concepts/knowted-competitive-advertising-risk-audit]] - The competitive comparison on the sales landing page that Video #1 can reference; all claims factually audited
- [[concepts/html-css-ad-creative-renderer]] - The Puppeteer-based ad creative system producing social assets for the content cadence
- [[concepts/knowted-competitive-pricing-audit]] - Live-verified competitor pricing that anchors the waitlist site's comparison claims
- [[concepts/knowted-launch-decision-register]] - The decision register revealing that marketing content is ready but blocked by unmade decisions (legal, truth, pricing)
- [[concepts/knowted-website-waitlist-ux-critique]] - The website UX critique identifying middle-section revamp needs; hero rewritten to "Botless, Private, Free, Unlimited"

## Sources

- [[daily/lcash/2026-06-04.md]] - "Infrastructure without output is the classic founder trap"; recommendation to ship Video #1 before building LinkedIn system; positioning guardrail "tell each rep what to do on NEXT call" not "find what's wrong"; LinkedIn-only cold sequence dropped email; shorts cut from longs (3/week from 2 YouTube); workstream folder structure with STATUS.md; 20-30% LinkedIn accept rates → 2-4 meetings/week; Perplexity MCP server installed (Sessions 13:41, 14:35, 15:31)
- [[daily/lcash/2026-06-11.md]] - Video #1 reframed from "founder POV" to "Your AI finally knows about your meetings" (free-tier demo); website rewritten with waitlist CTA + 3-tier pricing + sales landing page; designer hiring scoped for Framer redesign at $3-8K (Sessions 10:20, 10:57, 11:31)
- [[daily/lcash/2026-06-12.md]] - Waitlist site deployed (f5120cb); content audit verified; form endpoint was localStorage-only (fixed with Google Apps Script → Sheet); social ad creative system built (Puppeteer HTML+CSS→PNG); legal positioning: local-first no-bot is safest in category; login=cloud privacy boundary (Sessions 13:45, 16:46, 17:22, 22:27)
- [[daily/lcash/2026-06-13.md]] - Website middle-section revamp: 4/6 bento cards repeat hero, phone demo shows failure state, Claude Code card assumes MCP knowledge; hero rewritten to "Botless, Private, Free, Unlimited AI Meeting Assistant"; em-dash sweep; marketing confirmed blocked by unmade decisions not missing content — all assets built, decisions are the blocker (Session 11:09)
- [[daily/lcash/2026-06-23.md]] - Launch sequence locked: website + endpoint live → content drives traffic → data room closes investors; website confirmed as immediate next objective (demand lever over data-room polish); `VITE_WAITLIST_ENDPOINT` is the single gate before any content posting makes sense; "Consider it noted" campaign designed with before/after creative device, 4 ICP-matched executions, organic-first rollout (2 posts/week + build-in-public); brand book committed with Fraunces/Public Sans typography (Sessions 10:09, 11:33)
- [[daily/lcash/2026-06-27.md]] - Website confirmed as correct next objective; hero copy recommendation locked: "Stop stressing about notes. Let Knowted note it." with strip "Undetectable · Unlimited recordings & transcripts · Free"; P0 items 1-4 confirmed done (Jeffrey re-chase, investor update, Danny touch, D2 cleared); Jeff plan drafted for website go-live; VITE_WAITLIST_ENDPOINT remains single critical gate; investor outreach running in parallel via PhantomBuster (Sessions 14:13, 19:37)
