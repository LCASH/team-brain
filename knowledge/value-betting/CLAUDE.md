# VB Scanner Brain — LLM Knowledge Wiki

> Karpathy-pattern knowledge base for the Value Betting Scanner project.
> Every Claude instance that touches VB Scanner should read this wiki for domain context.

---

## What This Is

A structured, LLM-maintained knowledge base for the VB Scanner — a multi-sport expected value (EV) betting scanner that identifies +EV player prop bets by devigging sharp book odds and comparing them against soft Australian bookmakers.

**Location:** `brain/` folder inside `LCASH/value-betting-scanner`
**Obsidian:** Open the `brain/` folder as a vault, or open the whole repo and navigate to `brain/`
**Codebase:** Same repo — `ev_scanner/`, `server/`, `dashboard/`, `docs/`
**Supabase project:** `gpvyyyirrswmfirfwyli` (ap-southeast-2)
**Dashboard:** `http://170.64.213.223:8802/`
**Mini PC:** `Dell@192.168.0.114` (NBA :8800, MLB :8803)

---

## Relationship to Scanner Repo Docs

The scanner repo (`LCASH/value-betting-scanner`) has its own `docs/` folder with detailed technical documentation:

| Scanner `docs/` | Brain `wiki/` |
|-----------------|---------------|
| **How** things work (code, architecture, APIs) | **Why** decisions were made and what we learned |
| Sport-specific params and market mappings | Cross-cutting insights and research findings |
| Theory implementation details | Theory performance analysis and calibration findings |
| Bug lists and issue tracking | Active investigations and open questions |
| Data pipeline specifics | Domain knowledge and betting concepts |

**Rule:** Don't duplicate content that lives in the scanner docs. Reference it with `→ See docs/path/file.md in scanner repo`. The brain carries the institutional knowledge, research findings, and decision context that the code and docs alone don't capture.

**Key scanner docs to know about:**
- `docs/clv-analysis-findings.md` — 1,000 pick CLV analysis (essential reading)
- `docs/methodology/margin_removal_updated.md` — Devig methods with decision tree
- `docs/methodology/sports/nba/context.md` — NBA sharp books, biases, scanner params
- `docs/methodology/sports/mlb/` — MLB context bank (context, markets, data sources)
- `docs/methodology/theories/alt_line_*.md` — Alt line theory (Phase 1 live)

---

## Folder Structure

```
brain/
├── CLAUDE.md              ← You are here. Schema + rules.
├── index.md               ← Master index (start here)
├── hot.md                 ← Active investigations, open questions
├── log.md                 ← Append-only changelog
│
├── wiki/                  ← Domain knowledge (betting concepts, algorithms)
│   ├── devig-engine.md    ← Core devig: 4 methods, aggregation, sport/market differences
│   ├── ev-calculation.md  ← EV% formula, confidence weighting
│   ├── interpolation.md   ← Line adjustment: logit vs Poisson
│   ├── confidence-scoring.md ← Per-book data quality scores
│   ├── theories.md        ← Theory system: configs, evaluation, promotion
│   ├── calibration.md     ← Weight sweeps, Brier score, optimizer
│   ├── market-matcher.md  ← Cross-book market grouping
│   ├── clv.md             ← CLV concepts, soft vs sharp, convergence rates
│   ├── performance-tracking.md ← Segmented analysis design
│   └── glossary.md        ← Domain terms
│
├── sports/                ← Per-sport context and findings
│   ├── nba.md             ← Sharp books, prop performance, timing, biases
│   ├── mlb.md             ← MLB context (research phase)
│   ├── nrl.md             ← NRL stub
│   └── afl.md             ← AFL stub
│
├── sources/               ← Data pipeline (how we get odds)
│   ├── opticodds.md       ← OpticOdds API: endpoints, book IDs, rate limits
│   ├── bet365-scraper.md  ← Bet365 game scraping via CDP/AdsPower
│   ├── betstamp.md        ← Betstamp Pro WebSocket: Bet365 fallback
│   └── direct-scrapers.md ← AU bookies: Sportsbet, Neds, TAB
│
├── infra/                 ← Infrastructure (how we run things)
│   ├── server.md          ← FastAPI server: SSE, state, multi-sport
│   ├── tracker.md         ← Pick tracking: trail_entries, odds changes
│   ├── resolver.md        ← Auto-resolution: player results, CLV
│   ├── database.md        ← Supabase schema: tables, RLS, migrations
│   ├── deployment.md      ← Mini PC + VPS setup, ports, deploy script
│   ├── dashboard.md       ← Frontend: SSE, data.json, results tab
│   └── sport-config.md    ← Per-sport registry
│
├── findings/              ← Time-stamped research and analysis
│   └── YYYY-MM-DD-title.md ← Each finding dated with implications
│
├── patterns/              ← Reusable how-to guides
│   ├── data-flow.md       ← Full pipeline cycle
│   ├── adding-a-sport.md  ← How to add a new sport
│   ├── adding-a-book.md   ← How to add a new bookmaker
│   ├── theory-lifecycle.md ← Create → calibrate → promote → retire
│   └── debugging-ev.md    ← Common EV issues and tracing
│
└── raw/                   ← Immutable source documents (never modify)
    ├── articles/          ← Web clips
    ├── calibration-reports/ ← Calibration outputs
    └── data-exports/      ← CSV dumps, snapshots
```

### Where things go

| Question | Folder |
|----------|--------|
| "How does devig work?" | `wiki/` |
| "What did we learn from the CLV analysis?" | `findings/` |
| "How is NBA different from MLB?" | `sports/` |
| "How does OpticOdds work?" | `sources/` |
| "How do we deploy?" | `infra/` |
| "How do I add a new sport?" | `patterns/` |
| "I clipped an article" | `raw/articles/` |

---

## Domain Terminology

| Term | Meaning |
|------|---------|
| **EV (Expected Value)** | The mathematical edge on a bet. EV% = (bookOdds / trueOdds - 1) × 100 |
| **Devig / Devigging** | Removing the bookmaker's margin (vig) from odds to estimate true probabilities |
| **Vig (Vigorish)** | The bookmaker's built-in margin — the reason both sides sum to >100% |
| **Sharp book** | A bookmaker with accurate, low-margin odds (BetRivers, Hard Rock, DraftKings) |
| **Soft book** | A bookmaker with higher margins / slower line movement (Bet365, Sportsbet) |
| **True odds** | The estimated fair probability after devigging sharp book lines |
| **CLV (Closing Line Value)** | How much the line moved in your favor after you would have bet |
| **Interpolation** | Adjusting true probability when sharp and soft books offer different lines |
| **Theory** | A named configuration of devig method weights, sharp book weights, and thresholds |
| **Confidence** | A 0–5.0 score reflecting how much sharp book data supports a pick |
| **Trail** | The sequence of odds changes for a tracked pick over time |
| **Prop** | A player proposition bet (e.g., "LeBron James Over 25.5 Points") |
| **Line** | The threshold number in a prop bet (e.g., 25.5 in "Over 25.5 Points") |
| **Brier score** | Calibration metric: mean((predicted_prob - actual_outcome)²). Lower = better |
| **Multiplicative devig** | Proportional vig removal: p = (1/odds) / sum(1/odds) |
| **Additive devig** | Equal margin removal: p = 1/odds - margin/2 |
| **Power devig** | Favorite-longshot bias correction via exponent k |
| **Shin devig** | Insider-trading model (equivalent to additive for 2-way markets) |
| **Logit interpolation** | Line adjustment for continuous props via sigmoid transform |
| **Poisson interpolation** | Line adjustment for count props via Poisson distribution |
| **Consensus** | Broad book agreement used as fallback when no sharp books available |

---

## Wiki Rules

### Reading
1. **Start with `index.md`** to find relevant pages
2. **Follow `[[backlinks]]`** to understand connections between concepts
3. **Check `hot.md`** for current investigations and open questions
4. **Read wiki pages before modifying VB Scanner code** — they contain context the code alone doesn't show

### Writing
1. **Never modify files in `raw/`** — they are immutable source documents
2. **Always append to `log.md`** after any wiki create/update/delete
3. **Update `index.md`** when adding or removing pages
4. **Update `hot.md`** when investigations start, progress, or resolve
5. **Use `[[page-name]]` links** between wiki pages for cross-referencing
6. **Include a `## Status` section** at the top of each wiki page:
   - `current` — reflects the codebase as of last review
   - `stale` — known to be out of date (note what changed)
   - `stub` — placeholder, needs expansion
7. **Include `## Last verified`** with date and what was checked

### What to Document
- **Why** decisions were made (not just what the code does)
- **Calibration findings** — which methods/weights work best and why
- **Known gaps** — where the scanner is weak or data is missing
- **Operational knowledge** — deployment gotchas, common failures, debugging steps
- **Domain insights** — betting market behavior, bookmaker patterns, sport-specific quirks

### What NOT to Document
- Code that speaks for itself (function signatures, import lists)
- Ephemeral state (current pick count, today's ROI)
- Secrets or credentials
- Anything better served by git history

---

## Key Relationships

```
OpticOdds API ──→ engine.py (devig) ──→ ev_calc.py ──→ tracker.py ──→ Supabase
                      ↑                      ↑              ↓
              sharp book weights      confidence.py    trail_entries
              from theories.py             ↑               ↓
                      ↑              per-book scores   resolver.py
              nba_optimization_runs                        ↓
                      ↑                              nba_resolved_picks
              calibrate_weights.py                         ↓
                                                     analytics.py
```

---

## Sports Supported

| Sport | Port | Sharp Books | Soft Books | Status |
|-------|------|-------------|------------|--------|
| NBA | 8800 | BetRivers, Hard Rock, PropBuilder, DraftKings | Bet365, Sportsbet, Neds | Production |
| MLB | 8803 | Same as NBA | Same (non-headless Chrome required) | Production |
| NRL | 8801 | OpticOdds only | AU bookies | Production |
| AFL | 8802 | OpticOdds only | AU bookies | Production |
