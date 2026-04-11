# Team Brain

**Your team's Claude Code conversations automatically become shared knowledge.**

You work on your stuff, your teammates work on theirs. In the background, the system captures what everyone learns — decisions, gotchas, patterns, discoveries — and compiles it into a shared knowledge base. Next time anyone starts a Claude Code session, they already have the full team context. No standups needed for knowledge transfer.

---

## How It Works

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  SESSION STARTS                                              ║
║  → Pulls latest team knowledge from GitHub                   ║
║  → Claude sees what the whole team has learned               ║
║                                                              ║
║  YOU WORK NORMALLY                                           ║
║  → Every 30 min, AI quietly extracts what's worth saving     ║
║  → Each entry is tagged with which project it came from      ║
║                                                              ║
║  ONCE A DAY                                                  ║
║  → All team logs get compiled into structured articles        ║
║  → Pushed to GitHub so everyone gets them next session       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

```
 ┌──────────┐                        ┌──────────────────┐
 │  Luke     │ ── push daily/luke/ ─►│                  │
 │           │ ◄─ pull knowledge/  ──│                  │
 └──────────┘                        │   GitHub Repo    │
 ┌──────────┐                        │   (team-brain)   │
 │  Alice    │ ── push daily/alice/ ►│                  │
 │           │ ◄─ pull knowledge/  ──│  daily/luke/     │
 └──────────┘                        │  daily/alice/    │
 ┌──────────┐                        │  daily/bob/      │
 │  Bob      │ ── push daily/bob/ ──►│  knowledge/      │
 │           │ ◄─ pull knowledge/  ──│                  │
 └──────────┘                        └──────────────────┘
```

Each person writes to their own `daily/<name>/` folder — no merge conflicts ever. The compiled `knowledge/` is shared by everyone.

---

## Setup

### What you need

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Collaborator access to this repo (ask the admin to add you)

### One-time install (do this once, ever)

```bash
# 1. Clone the repo to your Documents folder
git clone https://github.com/LCASH/team-brain.git ~/Documents/claude-memory-compiler

# 2. Install the /setup-kb skill into Claude Code
mkdir -p ~/.claude/skills
cp -r ~/Documents/claude-memory-compiler/setup-kb ~/.claude/skills/setup-kb
```

That's it for the install. The repo lives at `~/Documents/claude-memory-compiler/` and never needs to be cloned again.

**What is `~/.claude/skills/`?** Claude Code looks here for custom slash commands. Each folder with a `SKILL.md` file becomes a command. Copying `setup-kb/` there gives you `/setup-kb` globally — in any project.

### Per-project setup (do this for each project you want knowledge sharing on)

Open Claude Code in your project and type:

```
/setup-kb
```

Claude will:
1. Find the installation at `~/Documents/claude-memory-compiler/`
2. Install dependencies if needed
3. Detect your name from git config
4. Create your daily log folder
5. Configure this project's hooks
6. Verify everything works

That's it. Work normally from here. Everything happens in the background.

---

## What You'll See

When you start a session, Claude gets injected with context like this:

```
## Knowledge Base Index
| [[concepts/auth-middleware]]  | JWT verification patterns          | daily/alice/... | 2026-04-09 |
| [[concepts/webhook-retry]]   | Exponential backoff with jitter    | daily/luke/...  | 2026-04-08 |
| [[concepts/mlb-line-gaps]]   | Sharp/soft line mismatch fix       | daily/bob/...   | 2026-04-10 |

## Your Recent Activity
### Session (14:30) [TAKEOVER]
Decisions Made: Chose exponential backoff with jitter...

### Session (16:15) [value-betting]
Lessons Learned: AU soft books use different lines than US sharps...

## Team Recent Activity
### alice (2026-04-09)
### Session (11:15) [TAKEOVER]
Context: Refactoring JWT verification to support multiple issuers...
```

Every entry is tagged with which project it came from — `[TAKEOVER]`, `[value-betting]`, etc. So Claude knows the context of each piece of knowledge, even across different projects.

When you ask Claude "how does our auth work?", it knows about Alice's middleware refactor from yesterday — even though you never discussed it.

---

## Capture Strategy

The system uses multiple hooks to make sure nothing gets lost:

| Hook | When it fires | What it does |
|------|--------------|-------------|
| **Stop** | After every Claude response | Checks a timer — flushes every 30 min of active conversation. The timer check takes <50ms, so you won't notice it. |
| **PreCompact** | Before context auto-compaction | Captures context before Claude summarizes and discards detail. Critical for long sessions. |
| **SessionEnd** | When you explicitly close | Final capture. Rarely fires since most people just walk away. |

You don't need to remember to save or close anything. The Stop hook is the workhorse — it captures while you work.

---

## CLI Commands

Run from `~/Documents/claude-memory-compiler/`:

```bash
# Manually compile daily logs into knowledge articles
uv run python scripts/compile.py

# Force recompile everything
uv run python scripts/compile.py --all

# Ask the knowledge base a question
uv run python scripts/query.py "What auth patterns do we use?"

# Ask + save the answer as a permanent Q&A article
uv run python scripts/query.py "How does our error handling work?" --file-back

# Run health checks (free, instant)
uv run python scripts/lint.py --structural-only

# Run all health checks including AI contradiction detection
uv run python scripts/lint.py
```

---

## Repo Structure

```
team-brain/
├── daily/                    # Per-developer conversation logs
│   ├── luke/                 #   Luke's daily logs (tagged by project)
│   │   └── 2026-04-10.md
│   ├── alice/                #   Alice's daily logs
│   └── bob/                  #   Bob's daily logs
├── knowledge/                # Compiled team knowledge (AI-maintained)
│   ├── index.md              #   Master catalog — loaded every session
│   ├── log.md                #   Build log — history of every compile
│   ├── concepts/             #   Atomic knowledge articles
│   ├── connections/          #   Cross-cutting insights
│   └── qa/                   #   Filed Q&A answers
├── hooks/                    # Claude Code hooks (auto-trigger)
│   ├── session-start.py      #   Pulls team updates, injects context
│   ├── stop.py               #   Periodic capture (every 30 min)
│   ├── session-end.py        #   Final capture on explicit close
│   └── pre-compact.py        #   Safety net before auto-compaction
├── scripts/                  # CLI tools
│   ├── compile.py            #   Daily logs → knowledge articles
│   ├── flush.py              #   Extract knowledge from conversations
│   ├── query.py              #   Ask the knowledge base
│   ├── lint.py               #   7 health checks
│   ├── sync.py               #   Git pull/push with retry
│   ├── config.py             #   Paths + developer identity
│   └── utils.py              #   Shared helpers
├── .github/workflows/
│   └── compile.yml           # Nightly fallback compilation
├── setup-kb/
│   └── SKILL.md              # The /setup-kb skill — copy to ~/.claude/skills/
├── setup.sh                  # Alternative: shell script onboarding
├── AGENTS.md                 # Full technical reference
└── pyproject.toml            # Python dependencies
```

---

## How Compilation Works

Daily logs are "source code". The AI compiler reads them and produces structured knowledge articles.

```
daily/          = source code    (your conversations, tagged by project)
LLM             = compiler       (extracts, organizes, cross-references)
knowledge/      = executable     (structured, queryable knowledge base)
```

Compilation happens automatically:
- **After 6 PM**: First developer to finish a session compiles all team logs locally
- **Nightly fallback**: GitHub Action at 4 AM UTC catches anything missed

The compiler uses the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) — covered by your existing Claude Code subscription (Max, Team, or Enterprise). No separate API key or billing needed.

---

## FAQ

**Does this cost money?**
No. The Claude Agent SDK runs on your existing Claude Code subscription. The "cost" numbers in the technical docs are informational metrics, not bills — like your phone showing data usage on an unlimited plan.

**Does it capture every project or just the ones I set up?**
Only projects where you've run `/setup-kb`. Each project is independent. Entries are tagged with the project name so the knowledge base knows which project each insight came from.

**What if I'm offline?**
Daily logs accumulate locally. They sync next time you have connectivity.

**Can two people compile at the same time?**
No — a lock file prevents concurrent compilation. Second person skips, gets the results next session.

**Can I browse the knowledge base in Obsidian?**
Yes. Point a vault at `knowledge/` — the `[[wikilinks]]` work natively with Obsidian's graph view, backlinks, and search.

**What if someone leaves the team?**
Their `daily/<name>/` stays as historical record. Knowledge compiled from their conversations persists in the articles.

**Does it capture conversations where I just walk away?**
Yes. The Stop hook captures every 30 minutes of active conversation. You don't need to explicitly close anything.

---

## Technical Reference

See [AGENTS.md](AGENTS.md) for the complete technical spec: article formats, hook architecture, JSONL transcript parsing, compilation prompts, and customization options.
