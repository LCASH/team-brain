---
title: "SuperWin Dual BookieOdds Model Shim Deployment Crash"
aliases: [dual-model-shim, bookieodds-shim, stale-shim-crash, dual-model-definition, server-models-shim]
tags: [superwin, deployment, bug, architecture, reliability, operations]
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# SuperWin Dual BookieOdds Model Shim Deployment Crash

The SuperWin racing scanner has two independent definitions of `BookieOdds`: the canonical `app/core/models.py` and a stale shim at `server/models.py`. Bookies using `from models import BookieOdds` (betfair, tab, tabtouch, tab_browser, bet365) hit the shim; those using `from app.core.models import BookieOdds` (betr, sportsbet) hit the canonical definition. When commit `254e7c7` added the `bsp_near` field to the canonical `BookieOdds` in 4 files but not the shim, every Betfair tick crashed with `BookieOdds.__init__() got an unexpected keyword argument 'bsp_near'` — causing a full Betfair odds freeze with no obvious alert.

## Key Points

- **Two `BookieOdds` definitions exist** on the production server: `server/models.py` (shim, used by 5 bookies) and `app/core/models.py` (canonical, used by 2 bookies)
- **Commit `254e7c7` (bsp_near) updated 4 files** but the shim `server/models.py` was never deployed to production — stale shim caused every Betfair price tick to crash with `unexpected keyword argument`
- **5 bookies on shim path** (betfair, tab, tabtouch, tab_browser, bet365) vs 2 on canonical path (betr, sportsbet) — the shim path covers the majority of bookies
- **Any new field on `BookieOdds` MUST be added to both files** or shim-path bookies crash silently — a recurring deployment landmine
- Fix: refactor `server/models.py` to re-export from `app.core.models` so dual-definition can't recur
- Betfair odds froze with no obvious alert — the crash happened inside the streaming tick handler, producing silent data absence rather than a visible process death

## Details

### The Shim Architecture

The SuperWin scanner evolved from a simpler architecture where `server/models.py` was the sole model definition. When the codebase was reorganized into `app/core/`, the canonical `BookieOdds` moved to `app/core/models.py`, but the old `server/models.py` was kept as a **shim** for backward compatibility. Some adapter modules were migrated to import from `app.core.models`, while others retained the old `from models import BookieOdds` import path.

This creates a split where the import path — not the model definition — determines which version of `BookieOdds` a bookie adapter uses. The split is invisible in normal operation because both definitions are functionally identical. It only surfaces when a new field is added to one definition but not the other.

### The bsp_near Crash

The `bsp_near` field (Betfair Starting Price near indicator) was added to the canonical `BookieOdds` in commit `254e7c7`, updating 4 files including `app/core/models.py`. The Betfair adapter passes `bsp_near=value` when constructing `BookieOdds` instances. Since the Betfair adapter imports from the shim (`server/models.py`) which lacked the `bsp_near` parameter, every `BookieOdds(bsp_near=...)` call raised `TypeError: __init__() got an unexpected keyword argument 'bsp_near'`.

The crash occurred inside the Betfair streaming tick handler — a callback that fires on every odds update from the Betfair Exchange. The error was caught and logged at the stream level, preventing a full process crash, but the Betfair adapter stopped processing all subsequent ticks. From the operator's perspective, Betfair odds simply stopped updating — no Discord alert, no health endpoint degradation, just silent data staleness.

### Which Bookies Use Which Path

| Import Path | Bookies | Definition |
|-------------|---------|------------|
| `from models import BookieOdds` (shim) | Betfair, TAB, TabTouch, tab_browser, bet365 | `server/models.py` |
| `from app.core.models import BookieOdds` (canonical) | Betr, Sportsbet | `app/core/models.py` |

The shim path covers 5 of 7 bookies, including the most critical ones (Betfair for fair-value reference, bet365 for soft book data). Any field added to the canonical definition without updating the shim breaks the majority of the scraping pipeline.

### Prevention

The correct fix is to make the shim a re-export rather than an independent definition:

```python
# server/models.py (fixed)
from app.core.models import BookieOdds  # re-export, no independent definition
```

This ensures both import paths resolve to the same class definition. New fields added to `app/core/models.py` automatically propagate to all consumers regardless of which import path they use. The re-export pattern is zero-cost at runtime and eliminates the class of dual-definition drift entirely.

## Related Concepts

- [[concepts/deploy-file-dependency-mismatch]] - A related deployment failure: deploying code without its dependencies. The shim crash is the inverse: deploying the dependency without updating all consumers
- [[concepts/configuration-drift-manual-launch]] - Dual model definitions are a code-level analog of configuration drift: the "intended" definition and the "actual" definition diverge without anyone noticing
- [[connections/stale-process-state-phantom-liveness]] - Betfair odds freezing silently while the process appears healthy is another phantom-liveness variant
- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal requires Betfair data for BSP/LTP CLV; the Betfair odds freeze directly impacts backtesting quality

## Sources

- [[daily/lcash/2026-05-25.md]] - Commit `254e7c7` (bsp_near) updated 4 files but shim `server/models.py` was never deployed; every Betfair tick crashed with `unexpected keyword argument 'bsp_near'`; 5 bookies on shim path (betfair, tab, tabtouch, tab_browser, bet365) vs 2 on canonical (betr, sportsbet); fix: refactor shim to re-export from `app.core.models`; Betfair odds froze with no alert (Sessions 16:45, 18:16)
