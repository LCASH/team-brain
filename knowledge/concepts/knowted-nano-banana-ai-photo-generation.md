---
title: "Knowted Nano Banana AI Photo Generation Pipeline"
aliases: [nano-banana, gemini-3-pro-image, ai-photo-ads, photo-statement-template, ai-lifestyle-photos]
tags: [knowted, marketing, image-generation, gemini, ai-agent, content-strategy]
sources:
  - "daily/lcash/2026-06-16.md"
created: 2026-06-16
updated: 2026-06-16
---

# Knowted Nano Banana AI Photo Generation Pipeline

On 2026-06-16, lcash integrated AI-generated lifestyle photography into the Knowted social media pipeline using Nano Banana Pro (Gemini 3 Pro Image) via the existing `gemini.js` wrapper — bypassing the free-tier quota=0 block that killed all image generation on Jun 12. A new `photoStatement` template composites full-bleed AI photos with gradient scrim overlays + headline/CTA text, producing ad-ready hero cards where the photo is AI-generated but all text is HTML-rendered for pixel-perfect fidelity. User chose "Both" — template-based text cards AND AI photo cards for a mixed posting cadence.

## Key Points

- **Nano Banana Pro = Gemini 3 Pro Image** accessed via the `generateContent` endpoint — confirmed working on the user's API key, bypassing the Jun 12 free-tier block
- **`photoStatement` template**: Full-bleed AI photo background + CSS gradient scrim (bottom 50%, black-to-transparent) + HTML headline/CTA overlay — photo is AI-generated, text is pixel-perfect
- **AI text rendering is garbled**: On-screen UI elements and small text in generated photos are gibberish (known Gemini limitation) — gradient scrim hides garbled text and HTML overlay provides real text
- **Ran through existing `gemini.js`** without MCP server setup — simpler path than Nano Banana's 10-file skill which assumes MCP
- **Brand green threads through AI generations**: Specifying brand hex (#00ff88) in prompts causes the color to appear naturally in generated scenes (walls, clothing, UI accents)
- **macOS sandbox blocks `~/Downloads/`**: CLI tools can't read from Downloads; user copied nano-banana folder into project directory as workaround
- **Generated assets are gitignored** (treated as regenerable from committed prompts/code); user can force-add approved images

## Details

### The Hybrid Architecture in Practice

The Jun 12 session established the hybrid architecture principle: diffusion models for backgrounds/scenes only, HTML/CSS owns all text and brand elements (see [[concepts/html-css-ad-creative-renderer]]). The Jun 16 session implemented this concretely with the `photoStatement` template:

1. **AI generates the photo** via Gemini 3 Pro Image — lifestyle scene (person in meeting, coffee shop workspace, team huddle) with prompts explicitly saying "no text, no logos, no UI overlays"
2. **CSS gradient scrim** covers the bottom 50% of the photo with a black-to-transparent gradient — hides any garbled AI text that appears in the lower portion of the image
3. **HTML text overlay** renders the headline, body text, and CTA button with exact fonts, colors, and positioning — deterministic, pixel-perfect, matches brand spec exactly

This produces images where the emotional/lifestyle layer is AI-generated (unique, varied, on-brand) while the communication layer is HTML-rendered (exact, consistent, legally defensible).

### Nano Banana Skill Integration

The user acquired the Nano Banana skill (10 files) which provides a conversational image generation interface via MCP tools (`gemini_generate_image`, `gemini_edit_image`, `continue_editing`). Rather than setting up the full MCP server, lcash routed image generation through the existing `gemini.js` wrapper that was already proven during the Jun 12 Gemini integration attempt. The `generateContent` endpoint with `responseModalities: ["IMAGE", "TEXT"]` works on the user's API key for `gemini-3-pro-image`, confirming that the Jun 12 free-tier block was either model-specific or has since been lifted.

### Quality Assessment

AI-generated photos were assessed as on-brand for lifestyle/ad backgrounds:
- **Strengths**: Realistic meeting environments, natural lighting, diverse subjects, brand green appearing organically when specified in prompts
- **Limitations**: Any text within the generated scene (laptop screens, whiteboards, phone displays) is garbled — a known limitation of current diffusion models including Gemini
- **Mitigation**: The gradient scrim pattern + HTML overlay completely solves the text limitation for ad cards; for clean photos (organic posts without text overlay), prompts must explicitly exclude screens and text-bearing surfaces

### 4-Week Posting Rollout Plan

A content calendar was drafted alongside the photo generation work: 70/20/10 organic posting schedule with one content lane per avatar. The photo cards serve the "organic post" category where no text overlay is needed — clean lifestyle images with brand association. The text card templates (statement, metric, comparison) serve the "ad" category where specific claims and CTAs are required.

### Two-Pipeline Production Strategy and Copy Bank (Session 22:20)

Later on 2026-06-16, lcash iterated on the ad creative pipeline and formalized a **two-pipeline production strategy** for distinct content roles:

| Pipeline | Tool | Content Role | Text Quality | Use Case |
|----------|------|-------------|-------------|----------|
| **Pipeline A** | Nano Banana Pro | Hero/scroll-stopper images | Text baked into AI image — unreliable, needs QA | Organic feed posts, hero cards |
| **Pipeline B** | HTML/CSS + Puppeteer | Workhorse ad cards | Pixel-perfect, fully editable | Ads with sub-headline, reasons strip, URL |

Nano Banana **must use Pro model** — Flash works but Pro gives crisper text. Always generate 2-3 variants and pick the best; text reliability is never guaranteed. Shorter headlines dramatically reduce AI text duplication errors (a student ad had "taking taking notes" until the headline was shortened).

A key creative discovery: **"Knowted ≈ noted" is the core brand-ownable wordplay asset.** Two lines emerged as brand anchors: "Let Knowted note it" and "Consider it noted." The hero line was refined to: "Stop stressing about notes. Let Knowted note it, undetected." — weaving "undetected" into the sentence rather than dangling it as a standalone adjective.

An **image generation rule** was formalized: nano banana = human/lifestyle scenes (no screens, no fake UI); HTML mockUI templates = actual product interface. Never use AI to fake the product interface — it produces garbled text that actively undermines trust.

A structured **copy bank** (`copy-bank.md`) was built covering ads and organic content across all four ICPs (Solopreneur Sam, Student Sophie, Corporate Heavy-Caller, IT Ian). The bank separates ad copy (requires image pairing) from organic lines (must work standalone without an image) — a different constraint set for each format. The initial "be present" concept was killed as too abstract; direct outcome lines performed better.

## Related Concepts

- [[concepts/html-css-ad-creative-renderer]] - The Puppeteer HTML→PNG pipeline that the photoStatement template extends; established the principle that HTML/CSS owns all text while diffusion handles backgrounds
- [[concepts/puppeteer-branded-social-image-pipeline]] - The broader social image pipeline (10 templates, 31 concepts, 90+ PNGs) that AI photo generation adds a new template type to
- [[concepts/knowted-content-first-gtm-strategy]] - The content-first GTM strategy that the social media posting cadence serves; photo ads are content assets
- [[concepts/knowted-icp-voc-avatar-derivation]] - The four ICP avatars that the 4-week posting plan targets with one lane per avatar

## Sources

- [[daily/lcash/2026-06-16.md]] - Nano Banana Pro (Gemini 3 Pro Image) confirmed working via existing gemini.js; photoStatement template built (full-bleed AI photo + gradient scrim + HTML overlay); AI text garbled but hidden by scrim; brand green threads through prompts; macOS sandbox blocks ~/Downloads/; user chose "Both" (template text cards + AI photo cards); 4-week posting rollout 70/20/10; generated assets gitignored; MCP server setup bypassed for simpler direct API path (Session 20:32). Two-pipeline strategy formalized: Nano Banana Pro for hero/scroll-stoppers, HTML template for workhorse ads; "Knowted ≈ noted" wordplay as brand-ownable asset; shorter headlines reduce AI text duplication; copy bank built across 4 ICPs; "be present" concept killed as too abstract; image rule: nano banana = human/lifestyle (no screens), HTML = product UI; Pro > Flash for ad quality (Session 22:20)
