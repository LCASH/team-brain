---
title: "Knowted Brand Identity and Campaign System"
aliases: [knowted-brand-book, consider-it-noted, knowted-typography, knowted-campaign, brand-identity-system, before-after-creative]
tags: [knowted, brand, marketing, campaign, creative, typography, identity]
sources:
  - "daily/lcash/2026-06-23.md"
created: 2026-06-23
updated: 2026-06-27
---

# Knowted Brand Identity and Campaign System

On 2026-06-23, lcash finalized the Knowted brand identity system: a brand book committed to `workstreams/brand/brandbook.md`, a locked typography system (Fraunces serif display for headings, Public Sans for body), canonical color tokens (Brunswick Green `#1D503A`, Classic Linen `#F9F4ED`), and the "Consider it noted" campaign built around the Knowted/noted wordplay. The campaign uses a before/after creative device — "frazzled before" images paired with existing "calm after" lifestyle shots — with four ICP-matched executions and an organic-first rollout cadence of 2 posts/week plus build-in-public plus POV content.

## Key Points

- **"Consider it noted"** chosen as the ownable signature phrase across all four ICPs — the Knowted/noted pun is the core brand-ownable wordplay asset identified on Jun 16
- **Typography locked**: Fraunces (serif display) for headings, Public Sans for body — replacing Plus Jakarta Sans; fixes the "hero feels thin" problem from prior website iterations
- **Color tokens**: Brunswick Green `#1D503A` and Classic Linen `#F9F4ED` as canonical brand colors — documented in the brand book as the authoritative reference
- **Before/after creative device**: Generate 4 "frazzled before" images to pair with existing 4 "calm after" lifestyle shots, plus 1 signature "noted" motif (phone face-down, mid-conversation) — a scroll-stopping format that turns static images into a narrative
- **Organic-first rollout**: 2 posts/week + build-in-public + POV content; campaign creative is designed to feel native in a social feed, not ad-like — caption carries any CTA, not the image

## Details

### The Brand Book

The brand book was committed to `workstreams/brand/brandbook.md` as a single source of truth for visual identity decisions. Prior to this, typography, colors, and campaign direction were scattered across multiple session notes, copy banks, and ad-hoc creative briefs. The consolidation into one committed file means any future creative work (ad templates, website redesign, investor deck visuals) can reference the brand book rather than reconstructing decisions from session history.

The typography choice — Fraunces for headings, Public Sans for body — addresses a specific problem identified during website copy iterations: Plus Jakarta Sans produced headers that felt "thin" and lacked the gravitas needed for a product positioning itself against enterprise competitors like Gong and Fathom. Fraunces, a variable serif display typeface with a high x-height and strong stroke contrast, provides the editorial weight needed for headlines like "Consider it noted" and "Just relax. Knowted quietly takes the notes." Public Sans (a neutral grotesque sans-serif) provides clean readability for body copy and UI text.

### The "Consider it Noted" Campaign

The campaign is built around four ICP-matched executions of the same core concept — the Knowted/noted wordplay identified in Session 22:20 of Jun 16 (see [[concepts/knowted-nano-banana-ai-photo-generation]]). Each execution targets a specific avatar from the ICP research (see [[concepts/knowted-icp-voc-avatar-derivation]]):

| ICP | Execution Angle | Before Image | After Image |
|-----|----------------|-------------|------------|
| Solopreneur Sam | Client calls without notes | Frazzled on phone, papers everywhere | Calm meeting, Knowted running |
| Student Sophie | Lecture note panic | Stressed in lecture hall | Relaxed listening, laptop open |
| Closer Chloe | CRM admin drowning | Post-call data entry marathon | Post-call, everything captured |
| IT Ian | Tool sprawl | 6 tabs of meeting tools | Single clean interface |

The before/after device transforms what would be a static ad card into a visual narrative: the viewer sees themselves in the "before" state (the universal pain hook — "I can either listen or take notes, but not both") and aspires to the "after" state. This is a standard direct-response creative technique, but the specific execution with Nano Banana Pro lifestyle photography (see [[concepts/knowted-nano-banana-ai-photo-generation]]) and brand-overlay.js logo compositing (see [[concepts/puppeteer-branded-social-image-pipeline]]) makes it producible at scale without a photographer.

### PhantomBuster Integration Attempt

In the same session, PhantomBuster MCP connector was authorized via claude.ai but could not bind mid-session — MCP connectors only register at session start, not during an active conversation. This means integrating PhantomBuster's LinkedIn campaign data (who's been messaged, accepted, replied) requires starting a fresh Claude Code session with the connector pre-configured. The planned use was pulling engagement metrics from the LinkedIn outreach pipeline (see [[concepts/linkedin-adspower-inbox-bot]]) to inform which ICP resonates most with organic content.

### Session Consolidation

A comprehensive handoff document (`handoff-2026-06-18.md`) was saved covering the state of all Knowted workstreams: website copy (built but uncommitted), data room (complete, missing infra cost figure), accountability run (3 sends completed), images (6 post-ready with logo overlay), and brand brief (locked in brand book). This document enables any session — including sessions with different team members — to pick up where the current one left off without re-deriving context.

## Related Concepts

- [[concepts/knowted-nano-banana-ai-photo-generation]] - The AI photo generation pipeline that produces the "calm after" lifestyle images; "Knowted ≈ noted" wordplay first identified in Session 22:20 of Jun 16
- [[concepts/knowted-icp-voc-avatar-derivation]] - The four ICP avatars (Sam, Sophie, Chloe, Ian) that the campaign's four executions are matched to
- [[concepts/knowted-waitlist-website-iteration]] - The website copy iterations that exposed the "hero feels thin" typography problem; Fraunces/Public Sans is the fix
- [[concepts/puppeteer-branded-social-image-pipeline]] - The Puppeteer HTML→PNG pipeline and brand-overlay.js logo compositing that produce campaign assets
- [[concepts/knowted-content-first-gtm-strategy]] - The content-first GTM strategy that the campaign serves; organic-first rollout aligns with "ship content before outreach infrastructure"
- [[concepts/linkedin-adspower-inbox-bot]] - The LinkedIn outreach pipeline whose PhantomBuster data would inform campaign targeting

## Sources

- [[daily/lcash/2026-06-23.md]] - Brand book committed to `workstreams/brand/brandbook.md`; typography locked (Fraunces headings, Public Sans body); colors locked (Brunswick Green #1D503A, Classic Linen #F9F4ED); "Consider it noted" campaign designed with before/after creative device and 4 ICP-matched executions; organic-first rollout (2/week + build-in-public); PhantomBuster MCP binding limitation (connectors attach at session start only); session consolidation saved to handoff-2026-06-18.md (Session 11:33)
