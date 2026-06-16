---
title: "Knowted Waitlist Website Copy Iteration and Middle-Section Critique"
aliases: [knowted-waitlist-redesign, hero-copy-iteration, middle-section-critique, bento-card-analysis, demo-screenshot-anti-pattern]
tags: [knowted, website, ux, marketing, copy, iteration]
sources:
  - "daily/lcash/2026-06-12.md"
  - "daily/lcash/2026-06-13.md"
created: 2026-06-12
updated: 2026-06-16
---

# Knowted Waitlist Website Copy Iteration and Middle-Section Critique

On 2026-06-12 (session 22:27), lcash finalized the Knowted waitlist hero copy and delivered the first middle-section critique, continuing iteration on 2026-06-13 via local Vite preview (port 8081). The hero was locked to H1 "Botless, Private, Free, Unlimited AI Meeting Assistant" with a sub-headline covering the product's core proposition. The middle-section analysis identified that 4 of 6 bento cards repeat the hero, a phone demo screenshot showing "no evidence found" actively undermines trust, and the "Plug into Claude Code" card assumes audience knowledge. The em-dash sweep rule (zero em dashes anywhere in copy) was enforced site-wide, with collateral damage from bulk replacement requiring prose cleanup.

## Key Points

- **Hero copy locked**: H1 "Botless, Private, Free, Unlimited AI Meeting Assistant" — sub covers unlimited recording/transcripts/search across 6 platforms, no bot, free forever
- **Middle section diagnosis**: 4/6 bento cards repeat hero messaging; phone demo shows "no evidence found" (trust-killer); "Never miss a meeting" unreadable; diagrams sell nothing; Claude MCP card assumes knowledge
- **Recommended collapse to 2-3 cards** around the only-us differentiator: "ask your meetings anything in Claude" — the MCP integration wedge, reframed for non-technical audiences
- **Demo screenshot anti-pattern**: A product screenshot showing an empty or failed search result actively undermines the page — worse than no screenshot at all
- **Em-dash sweep collateral damage**: Bulk perl replacement broke the pricing table's "not included" glyph and created comma splices — verify prose after mechanical text sweeps
- **Deploy safety gate worked correctly**: Ambiguous user "yes" about live site rollback was NOT treated as authorization to push to main (auto-deploys to production); Vercel Instant Rollback recommended instead

## Details

### Hero Copy Evolution

The hero section evolved from a sales-team-focused pitch (from the earlier GTM strategy documented in [[concepts/knowted-content-first-gtm-strategy]]) to a product-capability-focused statement that leads with the four key differentiators: botless, private, free, unlimited. The sub-headline provides specifics: unlimited recording, transcripts, and search across Zoom, Teams, Google Meet, FaceTime, Discord, and WhatsApp — with "no bot" and "free forever" as closing anchors.

User-supplied copy was lightly edited for mechanics (it's, WhatsApp capitalization, Knowted branding, list grammar) with an offer to revert any changes — respecting that founder-voice copy should be minimally altered. Specific removals requested by the user: the eyebrow pill above the H1, "For sales teams" button and links, "free because it runs locally" line, and slimming of the "Join waitlist" header button.

### Middle-Section Bento Analysis

The bento grid section was analyzed card-by-card against three criteria: does it say something the hero doesn't? Does it build trust? Does it sell a capability the visitor can't get elsewhere?

| Card | Assessment | Recommendation |
|------|-----------|----------------|
| "Capture every meeting" | Repeats hero (unlimited + 6 platforms) | Merge into hero sub |
| Phone demo | Shows "no evidence found" result | **Remove or replace** — actively harmful |
| "Never miss a meeting" | Unreadable text, unclear value | Remove |
| AI diagrams | Abstract visualization, sells nothing | Remove |
| "Plug into Claude Code" | Only-us feature but assumes "Claude Code" means something to the audience | **Keep and reframe** as "Ask your meetings anything in Claude" |
| Local-first privacy | Repeats hero "private/botless" | Merge into hero sub or trust badges |

The recommended collapse reduces 6 cards to 2-3 that communicate genuinely differentiated capabilities: the Claude MCP integration ("your meeting knowledge, inside your AI tools"), a trust/privacy proof point (local processing, no data leaves device), and optionally a social proof element (if waitlist numbers or early user feedback exist).

### The Demo Screenshot Anti-Pattern

A product screenshot showing an empty result state ("no evidence found" in the phone demo) is worse than no screenshot because it provides visual evidence that the product doesn't work. Visitors scan images before reading copy — a screenshot showing failure creates a negative first impression that the surrounding text cannot overcome. The general rule: product screenshots on marketing pages should always show the product in its best state (rich results, populated dashboards, successful interactions), never empty states.

### Em-Dash Enforcement

The standing rule "no em dashes anywhere in copy" (established 2026-06-12, see [[concepts/knowted-production-deploy-safety-rule]]) was enforced site-wide via bulk perl replacement. This exposed a general risk with mechanical text sweeps: the replacement converted the pricing table's "not included" em-dash glyph to a comma (breaking the visual indicator) and created comma splices throughout the prose where em dashes had been serving as parenthetical separators. Both required manual cleanup — the pricing glyph was replaced with a Minus icon component, and comma splices were converted to periods.

### Deploy Safety Validation

During this session, the deploy safety rule from [[concepts/knowted-production-deploy-safety-rule]] was tested organically: the user gave an ambiguous "yes" when discussing live site rollback, which was correctly NOT interpreted as authorization to push to main (which auto-deploys via Vercel). The assistant recommended Vercel Instant Rollback as the safer mechanism and requested explicit "push the rollback" confirmation. This validates that the standing rule is functioning as intended — ambiguous signals default to "don't deploy."

## Related Concepts

- [[concepts/knowted-content-first-gtm-strategy]] - The GTM strategy that the waitlist site supports; hero copy reframed from founder-POV to product-capability-focused after the local-first pricing pivot
- [[concepts/knowted-production-deploy-safety-rule]] - The deploy safety rule that correctly blocked an ambiguous push authorization in this session; em-dash rule also from this article
- [[concepts/knowted-local-first-pricing-pivot]] - The $0/$19/$69 pricing that the website reflects; "free because it runs locally" was removed from hero per user request
- [[concepts/knowted-competitive-advertising-risk-audit]] - Comparison claims on the website must trace to the factual audit; the middle-section revamp will need the same verification
- [[concepts/knowted-launch-decision-register]] - The decision register that gates when this waitlist version can go live; languages claim ("12+" vs "100+") is an open decision

## Sources

- [[daily/lcash/2026-06-12.md]] - Hero copy first locked in session 22:27: "Botless, Private, Free, Unlimited AI Meeting Assistant"; user-supplied copy lightly edited for mechanics; eyebrow pill, "For sales teams" button, "free because it runs locally" line removed per user; middle-section critique delivered: 4/6 cards repeat hero, phone demo shows "no evidence found" (trust-killer), Claude MCP card assumes audience knowledge; recommended collapse to 2-3 cards around Claude wedge; em-dash sweep rule established; Vercel Instant Rollback recommended over git revert for production incidents (Session 22:27)
- [[daily/lcash/2026-06-13.md]] - Continued iteration: deploy safety gate validated organically (ambiguous "yes" correctly NOT treated as push authorization); em-dash sweep collateral damage (pricing glyph broken, comma splices from bulk replacement); languages claim 12+ vs 100+ pending confirmation; middle-section revamp directions proposed (Session 11:09)
