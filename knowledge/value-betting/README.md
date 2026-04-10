# VB Scanner Brain

LLM-maintained knowledge wiki for the [Value Betting Scanner](https://github.com/LCASH/value-betting-scanner). Open in [Obsidian](https://obsidian.md) as a vault.

## What This Is

A structured knowledge base that carries the **why** behind the VB Scanner — domain context, research findings, calibration insights, and decision history that code alone doesn't capture. Every Claude session that works on the scanner reads this for context.

## Quick Start

1. Already in the scanner repo — `brain/` folder
2. Open in Obsidian: Open Vault → select the `brain/` folder
3. Start at `index.md` — master index of all pages
4. Check `hot.md` — current investigations and open questions

## Structure

```
├── CLAUDE.md       # Schema, rules, and references for LLM sessions
├── index.md        # Master index — start here
├── hot.md          # Active work, bugs, investigations
├── log.md          # Append-only changelog
├── wiki/           # Living knowledge pages
│   ├── devig-engine.md, ev-calculation.md, interpolation.md  (core algorithms)
│   ├── opticodds.md, bet365-scraper.md, betstamp.md          (data sources)
│   ├── server.md, tracker.md, resolver.md, database.md       (infrastructure)
│   ├── performance-tracking.md                                (analytics design)
│   └── glossary.md                                            (domain terms)
├── patterns/       # Reusable patterns and how-to guides
│   ├── data-flow.md, theory-lifecycle.md, debugging-ev.md
│   └── adding-a-sport.md, adding-a-book.md
└── raw/            # Immutable source documents (never edit)
```

## How to Contribute

- **Add domain knowledge** — If you know something about how a market works, why a bookmaker behaves a certain way, or what a scanner parameter should be, write it down in the relevant wiki page.
- **Record findings** — After a calibration run, CLV analysis, or debugging session, update the relevant wiki page with what you learned.
- **Update `hot.md`** — When you start or finish an investigation, update the status.
- **Append to `log.md`** — Every wiki operation gets a line in the changelog.
- **Don't duplicate scanner docs** — Technical details live in `docs/` (same repo). The brain carries context and insights that code and docs alone don't capture.
