---
title: "HTML/CSS Ad Creative Renderer"
aliases: [ad-creative-renderer, html-to-png, knowted-ad-system, creative-renderer]
tags: [knowted, marketing, creative, tooling, architecture]
sources:
  - "daily/lcash/2026-06-12.md"
  - "daily/lcash/2026-06-16.md"
created: 2026-06-12
updated: 2026-06-16
---

# HTML/CSS Ad Creative Renderer

On 2026-06-12, lcash built an ad creative pipeline that renders HTML+CSS to PNG using headless Chrome (Puppeteer), deliberately choosing this over AI image generation models. The architecture was selected because diffusion models (Midjourney, DALL-E, Flux) cannot reliably deliver pixel-perfect text rendering or exact brand colors for text-heavy ad cards. A hybrid architecture was adopted: diffusion models (Gemini/Imagen) generate backgrounds and scenes only, while HTML+CSS owns all text and brand elements.

## Key Points

- **Architecture**: Headless Chrome (Puppeteer) renders HTML+CSS to PNG -- NOT an AI image model; chosen for pixel-perfect text and exact brand colors
- **Hybrid image pipeline**: Diffusion models (Gemini/Imagen) for backgrounds/scenes ONLY with prompts explicitly saying "no text, no logos"; HTML+CSS owns all text and brand elements
- **Templates and concepts**: 4 logo-based templates (integrationRow, logoGrid, vsLogo, stackPile), ~10 concepts (vs competitors, "captures everywhere", Claude MCP angle)
- **Google AI free tier limitation**: Image generation quota is ZERO across ALL models (gemini-3-pro-image, gemini-3.1-flash-image, gemini-2.5-flash-image all return 429 limit:0; imagen-4.0 returns 400 "paid plans only")
- **Preview UI**: Vite+React+Tailwind at localhost:5180; adding new output sizes is a one-liner in the SIZES array

## Details

### Why HTML+CSS Over Diffusion Models

The fundamental limitation of current diffusion models for ad creative is text rendering. Models like Midjourney, DALL-E, and Flux routinely produce misspelled words, inconsistent letterforms, and approximate-but-wrong brand colors. For marketing cards that are primarily text with brand elements -- competitor comparison tables, feature callouts, pricing grids -- these errors are unacceptable. HTML+CSS provides deterministic rendering: the text is exactly what you typed, the colors are exactly what you specified, and the layout is pixel-precise.

This does not mean AI image generation has no role. The hybrid architecture separates responsibilities cleanly: diffusion models handle photographic or illustrated backgrounds and scenes where approximate rendering is acceptable and creative variety is desirable, while the HTML+CSS layer composites text, logos, and brand elements on top with full fidelity. Prompts sent to image models explicitly specify "no text, no logos" to prevent the model from attempting to render elements that the HTML layer will handle.

### Template System and Preview

Four logo-based templates were built: integrationRow (horizontal strip of integration logos), logoGrid (grid layout for ecosystem visualization), vsLogo (head-to-head competitor comparison), and stackPile (stacked arrangement for feature grouping). Approximately 10 creative concepts were developed around these templates, including competitor comparisons, "captures everywhere" messaging, and a Claude MCP integration angle.

The logo system uses placeholder chips (brand color plus first letter of the company name) as defaults until real SVG logos are dropped into social-images/logos/. This allows rapid iteration on layout and messaging without blocking on asset collection. The preview UI runs on Vite+React+Tailwind at localhost:5180, providing instant feedback during template development. Adding new output dimensions (e.g., LinkedIn post, Instagram story, Twitter card) requires only adding an entry to the SIZES array.

### Google AI Free Tier Constraints

A significant discovery during development was that Google's AI free tier provides zero image generation quota. Every model tested -- gemini-3-pro-image, gemini-3.1-flash-image, gemini-2.5-flash-image -- returns a 429 error with limit:0. The dedicated imagen-4.0 model returns a 400 error stating "paid plans only." Notably, Imagen uses the predict endpoint while Gemini-N image models use the generateContent endpoint; the wrapper handles both API patterns. This means the hybrid architecture's background generation capability requires either a paid Google AI tier or an alternative image generation provider.

### Legal Posture

Competitor comparison cards use publicly known brand colors, which constitutes nominative use (referencing a brand to compare against it). All claims in the creative are sourced from the factual pricing and feature audit. A reference to the Fireflies.AI class action is included in relevant creative without naming the specific case details, maintaining factual accuracy while avoiding defamation risk.

### Gemini 3 Pro Image (Nano Banana) Integration (2026-06-16)

On 2026-06-16, the Google AI free-tier image generation quota issue was resolved — `gemini-3-pro-image` (Nano Banana Pro) now works on the `generateContent` API path through the existing `gemini.js` wrapper. This enables AI-generated lifestyle photography (meeting rooms, laptop setups, team collaborations) for use as full-bleed backgrounds in a new `photoStatement` template.

The `photoStatement` template composites three layers: (1) AI-generated full-bleed photo, (2) gradient scrim (semi-transparent dark overlay on the bottom third), (3) headline + CTA text rendered via Puppeteer HTML. The scrim serves dual purpose: hiding AI-generated garbled text artifacts in the photo and providing contrast for the overlaid real text.

Key findings from the integration:
- AI UI text rendering is garbled at small sizes — a universal limitation of diffusion models; fine for lifestyle/background photos but not for product screenshots
- Brand green (#00ff88) specified in prompts threads through AI generations (walls, knitwear, UI elements) — useful for brand coherence but can be excessive
- macOS sandbox blocks reading from `~/Downloads/` for CLI tools — assets must be in project directories or `~/Documents/`
- Generated assets are gitignored (regenerable from committed prompts); approved images can be force-added to git

A 4-week content posting plan was built around the combined pipeline: 70% educational (text templates), 20% product (photoStatement with AI backgrounds), 10% promotional (comparison templates).

## Related Concepts

- [[concepts/knowted-content-first-gtm-strategy]] - The GTM strategy that these ad creatives support as part of the content-first approach
- [[concepts/knowted-competitive-pricing-audit]] - The pricing data that feeds into competitor comparison creative
- [[concepts/shopify-ai-agent-optimization]] - Another instance of AI-assisted marketing tooling in a different domain
- [[concepts/knowted-gemini-nano-banana-photo-pipeline]] - The AI photo generation pipeline that produces backgrounds for the photoStatement template

## Sources

- [[daily/lcash/2026-06-12.md]] - Puppeteer HTML+CSS-to-PNG architecture, hybrid diffusion+HTML pipeline, 4 templates (integrationRow/logoGrid/vsLogo/stackPile), ~10 concepts, Vite+React+Tailwind preview at localhost:5180, Google AI free tier zero quota across all models, Imagen predict vs Gemini generateContent endpoints, logo placeholder system, SIZES array one-liner, legal posture on nominative use (Session times)
