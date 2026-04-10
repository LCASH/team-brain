# Team Brain

Shared team knowledge base that builds itself from your Claude Code conversations.

Everyone works locally on their own stuff. The system captures what you learn, syncs it across the team, and compiles it into structured knowledge articles. Next time anyone opens Claude Code, they already know what the rest of the team figured out.

## How It Works

```
╔══════════════════════════════════════════════════════════════╗
║                    SESSION STARTS                            ║
║                                                              ║
║  1. PULL — latest team knowledge from GitHub                 ║
║  2. INJECT — Claude sees what the whole team has learned     ║
║                                                              ║
║  You work normally. Claude already has team context.         ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                    WHILE YOU WORK                            ║
║                                                              ║
║  3. CAPTURE — every 30 min, AI extracts what's worth saving  ║
║     (also captures before auto-compaction + on session close) ║
║  4. PUSH — your daily log syncs to the shared repo           ║
║  5. COMPILE — once a day, all logs become knowledge articles ║
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

Each person writes to their own `daily/<name>/` folder — no merge conflicts. Knowledge compilation reads everyone's logs and produces shared articles in `knowledge/`.

---

## Setup (2 minutes)

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Access to this GitHub repo

### Step 1: Download the skill file

Download `setup-kb.md` from this repo and put it in your Claude Code skills folder:

```bash
# Create the skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Download the skill file
curl -o ~/.claude/skills/setup-kb.md https://raw.githubusercontent.com/LCASH/team-brain/main/setup-kb.md
```

### Step 2: Run the skill

Open Claude Code in whatever project you want team knowledge on, and type:

```
/setup-kb
```

That's it. Claude will:
1. Clone this repo into your project
2. Install Python dependencies
3. Detect your name from git config
4. Create your daily log folder
5. Configure the hooks
6. Verify everything works

### Step 3: Work normally

There is no step 3. Just use Claude Code like you always do. Everything happens in the background.

---

## What You'll See

When you start a session, Claude gets injected with:

```
## Knowledge Base Index
| [[concepts/auth-middleware]] | JWT verification patterns | daily/alice/2026-04-09.md | 2026-04-09 |
| [[concepts/webhook-retry]]  | Exponential backoff       | daily/luke/2026-04-08.md  | 2026-04-08 |

## Your Recent Activity
### Session (14:30) - Webhook retry logic
Decisions Made: Chose exponential backoff with jitter...

## Team Recent Activity
### alice (2026-04-09)
### Session (11:15) - Auth middleware refactor
Context: Refactoring JWT verification to support multiple issuers...
```

So when you ask Claude "how does our auth work?", it knows about Alice's middleware refactor from this morning — even though you never discussed it.

---

## CLI Commands

Run these from inside the `claude-memory-compiler/` directory:

```bash
# Manually compile daily logs into knowledge articles
uv run python scripts/compile.py

# Compile everything (force recompile)
uv run python scripts/compile.py --all

# Ask the knowledge base a question
uv run python scripts/query.py "What auth patterns do we use?"

# Ask + save the answer back into the KB
uv run python scripts/query.py "How does our error handling work?" --file-back

# Run health checks (free)
uv run python scripts/lint.py --structural-only

# Run all health checks including AI contradiction detection
uv run python scripts/lint.py
```

---

## Repo Structure

```
team-brain/
├── daily/                    # Per-developer conversation logs
│   ├── luke/                 #   Luke's daily logs
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
│   ├── compile.py            #   Compile daily logs → knowledge articles
│   ├── flush.py              #   Extract knowledge from conversations
│   ├── query.py              #   Ask the knowledge base
│   ├── lint.py               #   7 health checks
│   ├── sync.py               #   Git pull/push with retry
│   ├── config.py             #   Paths + developer identity
│   └── utils.py              #   Shared helpers
├── .github/workflows/
│   └── compile.yml           # Nightly fallback compilation
├── setup-kb.md               # Skill file — copy to ~/.claude/skills/
├── setup.sh                  # Alternative: shell script onboarding
├── AGENTS.md                 # Full technical reference
└── pyproject.toml            # Python dependencies
```

---

## How Compilation Works

Daily logs are "source code". The AI compiler reads them and produces structured knowledge articles.

```
daily/          = source code    (your conversations)
LLM             = compiler       (extracts and organizes)
knowledge/      = executable     (structured, queryable knowledge)
```

Compilation happens two ways:
- **Automatic**: First developer to finish a session after 6 PM triggers compilation locally
- **Fallback**: GitHub Action runs at 4 AM UTC if anything was missed

The compiler uses the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) — runs on your Claude Code subscription, no separate API key needed.

---

## Costs

| Operation | Cost |
|-----------|------|
| Session capture (flush) | ~$0.03 |
| Compile one daily log | ~$0.50 |
| Query the knowledge base | ~$0.15-0.25 |
| Health check (structural) | Free |
| GitHub usage | Free (just git push/pull) |

Estimated team of 4, ~3 sessions/day: **~$2.50/day, ~$50/month**.

---

## FAQ

**Does this capture every project or just the one I set it up on?**
Just the project where you ran `/setup-kb`. Each project is independent.

**What if I'm offline?**
Daily logs accumulate locally. They sync next time you have connectivity.

**Can two people compile at the same time?**
No — a lock file prevents concurrent compilation. Second person skips it.

**Can I browse the knowledge base in Obsidian?**
Yes. Point a vault at `knowledge/` — the `[[wikilinks]]` work natively.

**What if someone leaves the team?**
Their `daily/<name>/` stays as historical record. Knowledge compiled from it persists.

---

## Technical Reference

See [AGENTS.md](AGENTS.md) for the complete technical spec: article formats, hook architecture, script internals, JSONL transcript parsing, and customization options.
