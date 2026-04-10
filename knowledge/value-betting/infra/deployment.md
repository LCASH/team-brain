# Deployment

## Status: current
## Last verified: 2026-04-09 (corrected VPS architecture, ports)

> Two-tier deployment: mini PC (scraping) → VPS (tracking, resolving, serving dashboard).

---

## Architecture Overview

```
Mini PC (192.168.0.114)              VPS (170.64.213.223:8802)
├── NBA :8800 (all scrapers)         ├── Relay mode (ACTIVE_SPORTS=nba,mlb,nrl,afl)
├── NRL :8801 (opticodds only)       ├── Tracker (all sports, event-driven)
├── AFL :8802 (opticodds only)       ├── Resolver (hourly, nba→mlb→nrl→afl)
├── MLB :8803 (opticodds only)       ├── Dashboard served at :8802/
└── Push Worker (every 5s → VPS)     └── systemd: value-betting.service
```

---

## Mini PC (Windows 11)
- **IP:** 192.168.0.114 (local network)
- **User:** Dell (SSH: `ssh Dell@192.168.0.114`, no password)
- **Processes:** schtasks-based (persist after SSH disconnect)

### Directory Layout
```
C:\Users\Dell\Documents\
├── value-betting-scanner-new\    # NBA (port 8800, CDP 9223) + push worker + watchdog
├── value-betting-scanner-ms\     # NRL :8801, AFL :8802, MLB :8803
```

### Sport Ports (corrected)
| Sport | Port | Scrapers |
|-------|------|----------|
| NBA | 8800 | OpticOdds + Bet365 game + Betstamp + BlackStream + direct scrapers |
| NRL | 8801 | OpticOdds only |
| AFL | 8802 | OpticOdds only |
| MLB | 8803 | OpticOdds only |

---

## VPS (DigitalOcean)
- **IP:** 170.64.213.223, **port:** 8802
- **SSH:** `SSHPASS='TAkeover69$T' sshpass -e ssh root@170.64.213.223`
- **Service:** systemd `value-betting.service`
- **Code:** `/opt/value-betting/`
- **Env:** `/opt/value-betting/.env`
- **Mode:** `RELAY_MODE=1, ACTIVE_SPORTS=nba,mlb,nrl,afl`

### VPS runs:
- Tracker for all 4 sports (event-driven, triggered by push worker data)
- Resolver hourly (nba → mlb → nrl → afl sequential)
- Dashboard serving at `http://170.64.213.223:8802/`
- Push loop (receives data from mini PC)

### Critical: API Key Sync
The VPS `.env` must have the same `OPTICODDS_API_KEY` as local. If rotated locally, update VPS too — otherwise resolver gets 401 errors on all sports. This blocked resolution for 12+ hours on 2026-04-08.

---

## Deploy Script

**Source:** `scripts/deploy.sh`

```bash
./scripts/deploy.sh vps          # VPS only (tar + SCP + systemctl restart + health check)
./scripts/deploy.sh minipc       # Mini PC only (SCP + taskkill + pycache clear + restart)
./scripts/deploy.sh all          # Both
./scripts/deploy.sh vps --dry-run
```

Credentials sourced from `.deploy.env`. Health check retries 10x with 5s intervals.

### Dashboard Push (after HTML changes)
```bash
curl -X POST http://170.64.213.223:8802/push/dashboard --data-binary @dashboard/index.html -H "Content-Type: text/html"
```

---

## Health Checks

| Endpoint | What It Checks |
|----------|---------------|
| `/api/v1/health` | Status, markets, soft books, tracker, resolver, background tasks, mini PC |
| `/api/v1/health/full` | Sources, sharp books, soft books, prop types, summary |
| `/api/v1/health/deep` | Supabase connectivity, per-book odds counts |
| `/api/v1/results?sport=nba` | W/L/ROI by theory, prop, side, date, EV bucket |
| `/api/v1/resolve?date=YYYY-MM-DD` | Manual resolution trigger |

---

## Related Pages
- [[server]] — What runs on these ports
- [[dashboard]] — Frontend served by VPS
- [[resolver]] — Runs on VPS, needs API key sync
