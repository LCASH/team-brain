---
title: "Puppeteer Branded Social Image Generation Pipeline"
aliases: [social-image-pipeline, puppeteer-html-png, branded-image-generator, headless-chrome-image-render, logo-placeholder-system]
tags: [knowted, tooling, content-strategy, puppeteer, image-generation, marketing]
sources:
  - "daily/lcash/2026-06-11.md"
  - "daily/lcash/2026-06-12.md"
created: 2026-06-11
updated: 2026-06-16
---

# Puppeteer Branded Social Image Generation Pipeline

On 2026-06-11, lcash built a full social media image generation pipeline for Knowted using headless Chrome (Puppeteer) to render HTML/CSS templates into PNGs. The pipeline produces pixel-perfect branded text cards — not AI-generated photographic images. 10 templates generate 31 concepts across 3 sizes each (1080×1080 feed, 1080×1350 stories, 1200×628 LinkedIn) for 90+ total PNGs. A logo placeholder system uses brand-colored chips (first letter + hex color) by default, with auto-replacement when real SVG/PNG logos are dropped into `social-images/logos/`. A React preview UI at localhost:5180 provides browsable grid, clickable thumbnails, modal with all sizes, and a logo library status tab.

## Key Points

- **HTML/CSS → headless Chrome → PNG via Puppeteer** — pixel-perfect text and brand colors, not AI/diffusion image generation; deliberate choice for text-heavy branded ad cards
- **10 templates**: statement, metric, comparison, product mockup, quote, anti-pattern + 4 logo-based (integrationRow, logoGrid, vsLogo, stackPile)
- **31 concepts / 90+ PNGs** across 3 sizes: 1080×1080 (feed), 1080×1350 (stories), 1200×628 (LinkedIn)
- **Logo placeholder system**: Brand-colored chips render by default; drop real SVGs into `social-images/logos/` and templates auto-pick them up — no code changes needed
- **20 brands registered**: zoom, teams, meet, slack, claude, fathom, granola, otter, gong, sybill, avoma, fireflies, tldv, loom, notion, hubspot, salesforce, calendly, linear, obsidian
- **Preview UI**: Vite + React + Tailwind at `social-images/ui/` on port 5180 — sidebar with template counts, clickable thumbnails, modal with all sizes, logo library status tab
- **All competitor claims in ad concepts must trace back to validated factual audit** — no unverified stats

## Details

### Why Puppeteer Over AI Image Generation

The social image pipeline deliberately uses headless Chrome rendering rather than AI image models (Flux, DALL-E, Ideogram). The reasoning is domain-specific: Knowted's social media needs are text-heavy branded comparison cards, metric statements, and integration showcases where exact text rendering, consistent brand colors, and repeatable output matter more than photographic or illustrative quality. Puppeteer provides:

1. **Pixel-perfect text** — font rendering matches design spec exactly, no AI text-generation artifacts
2. **Brand color fidelity** — hex values render exactly as specified; AI models approximate colors
3. **Deterministic output** — same template + same data = same image every time; enables automated regeneration when content updates
4. **Fast iteration** — HTML/CSS changes reflect in seconds; no model inference latency

If photographic or illustrative hero shots are needed later, Flux or GPT-Image-1 can be wired in via API as a complementary pipeline. The Puppeteer pipeline handles the 80% case (text cards) while leaving the 20% case (photography) for future expansion.

### Gemini Image Generation Attempt (2026-06-12)

On 2026-06-12, lcash attempted to integrate Google's Gemini/Imagen models for background/scene generation (text and brand elements would remain HTML-rendered). A `gemini.js` wrapper was built handling both endpoint patterns: Imagen uses the `predict` endpoint while Gemini-N image models use `generateContent`. However, **all image models are blocked on Google AI's free tier** — quota is set to zero across every model:

- `gemini-3-pro-image`, `gemini-3.1-flash-image`, `gemini-2.5-flash-image`: HTTP 429 with `limit: 0`
- `imagen-4.0`: HTTP 400 "paid plans only"

Gemini-N models don't accept aspect ratio as a parameter (must be injected into the prompt text), unlike Imagen which has a dedicated field. The wrapper handles both patterns with fallback. Three paths forward were identified: (A) enable billing on Google AI project (~$0.02-0.04/image), (B) Replicate/Flux adapter (~$0.003/image), or (C) stay text-only. The hybrid architecture decision stands: diffusion models for backgrounds/scenes only, with explicit prompts saying "no text, no logos" — HTML/CSS owns all text and brand elements.

### Template Architecture

Each template is an HTML file with embedded CSS that receives data via JSON. The `generate.js` script iterates all concepts (data entries), applies each to its designated template, launches headless Chrome, renders at each size, and captures screenshots. The 10 templates cover distinct visual patterns:

| Template | Purpose | Example |
|----------|---------|---------|
| statement | Bold text on branded background | "Your AI finally knows about your meetings" |
| metric | Large number + context | "$0/seat vs $30K/year" |
| comparison | Side-by-side feature table | Knowted vs Gong vs Fathom |
| product mockup | UI screenshot frame | Meeting transcript view |
| quote | Testimonial or user quote | Customer feedback |
| anti-pattern | Problem statement | "Still paying per seat for AI coaching?" |
| integrationRow | Horizontal logo strip | "Works with Zoom, Teams, Meet..." |
| logoGrid | 3×3 logo matrix | Competitor landscape |
| vsLogo | 1-on-1 comparison with logos | "Knowted vs Gong" |
| stackPile | Overlapping logo pile | "Replaces your entire stack" |

### Logo Placeholder System

The logo system is designed for progressive enhancement. On initial generation, each brand renders as a colored chip — the brand's hex color as background with the first letter of the brand name centered. This produces visually coherent images even without real logos. When real SVGs or PNGs are placed in `social-images/logos/{brandname}.svg`, the next `node generate.js` run automatically substitutes the real logo — no template code changes needed.

20 brands are pre-registered with their hex colors. Nominative use of brand colors as identifiers (not as brand endorsement) is legally clean; real logos should come from vendors' official `/brand` or press kit pages.

### Content Validation

All competitor claims in the social image concepts are validated against the factual audit performed in the same day (see [[concepts/knowted-competitive-advertising-risk-audit]]). No concept references unverified pricing, unsubstantiated features, or unconfirmed competitor weaknesses. The vs-01 through vs-04 competitor comparison cards were rewritten against the audit findings.

### AI Photo Generation via Nano Banana (2026-06-16)

On 2026-06-16, AI-generated lifestyle photography was integrated via Nano Banana Pro (Gemini 3 Pro Image) — bypassing the free-tier quota=0 block from Jun 12. A new `photoStatement` template composites full-bleed AI photos with a CSS gradient scrim (bottom 50%, black-to-transparent) + HTML headline/CTA overlay. The photo is AI-generated for emotional/lifestyle impact; all text is HTML-rendered for pixel-perfect fidelity. This is the concrete implementation of the hybrid architecture (diffusion for backgrounds, HTML for text) established on Jun 12.

The user chose "Both" — template-based text cards for ads AND AI photo cards for organic posts — establishing a mixed content cadence. Brand green (#00ff88) threads naturally through AI generations when specified in prompts. AI-generated text within photos remains garbled (known diffusion limitation) but the gradient scrim hides it completely. See [[concepts/knowted-nano-banana-ai-photo-generation]] for the full analysis.

## Related Concepts

- [[concepts/knowted-competitive-advertising-risk-audit]] - The factual audit that all competitive social image concepts are validated against; no unverified stats in ad cards
- [[concepts/knowted-content-first-gtm-strategy]] - Social images are content assets that support the content-first GTM; ship visual content alongside video content
- [[concepts/knowted-local-first-pricing-pivot]] - The pricing pivot that changed all comparison metrics in social images; "$0/seat" is the hero number
- [[concepts/knowted-nano-banana-ai-photo-generation]] - The Nano Banana Pro (Gemini 3 Pro Image) integration for lifestyle photos; photoStatement template

## Sources

- [[daily/lcash/2026-06-11.md]] - Puppeteer HTML→PNG pipeline built; 10 templates, 31 concepts, 90+ PNGs; logo placeholder system with brand-colored chips; 20 brands registered; preview UI at port 5180 (Vite + React + Tailwind); Facebook Ads Library too JS-heavy without auth; Puppeteer right for text-heavy cards, Flux/Ideogram for photographic later; all competitor claims validated against factual audit (Sessions 13:12, 14:22)
- [[daily/lcash/2026-06-12.md]] - Gemini/Imagen integration attempted: all image models blocked on free tier (quota=0); Imagen uses `predict` endpoint, Gemini-N uses `generateContent`; wrapper handles both with fallback; hybrid architecture confirmed: diffusion for backgrounds only, HTML owns text/brand; metric template stacking fix; new output sizes trivial (one-liner in SIZES array) (Session 10:02)
- [[daily/lcash/2026-06-16.md]] - Nano Banana Pro (Gemini 3 Pro Image) confirmed working via existing gemini.js; photoStatement template (full-bleed AI photo + gradient scrim + HTML text overlay); brand green threads through prompts; user chose "Both" (text cards + AI photos); 4-week posting rollout 70/20/10; macOS sandbox blocks ~/Downloads/ (Session 20:32)
