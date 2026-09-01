# KnowledgeMap — CLAUDE.md

Personal portal aggregating all side-projects under one unified dashboard. Each project gets a card on the dashboard; clicking it navigates to that project's dedicated page.

## Repository layout

Two layout conventions coexist by design. The portal's own code is grouped **by layer**
(`models/`, `schemas/`, `crud/`, `routers/`); each integrated project is a self-contained
**feature module** (`app/tradesim/`, `features/tradesim/`). Add new projects as feature
modules, not as new files in the by-layer directories.

```
KnowledgeMap/
├── backend/          # FastAPI app (Python)
│   ├── main.py       # Sole entry point — `python main.py` starts uvicorn on :8010
│   ├── requirements.txt
│   ├── tests/
│   │   └── tradesim_grid_strategy_cases.py   # plain-python runner, 8 cases
│   └── app/
│       ├── database.py       # MySQL engine + SessionLocal + get_db (single source)
│       ├── models/           # SQLAlchemy ORM models
│       │   └── bill.py       # Base, Tag, Bill, CalendarEvent, enums
│       ├── schemas/          # Pydantic v2 schemas (per-module files)
│       │   ├── bill.py
│       │   ├── calendar.py
│       │   └── tag.py
│       ├── crud/             # DB operations (per-module files)
│       │   ├── bill.py
│       │   ├── calendar.py
│       │   └── tag.py
│       ├── routers/          # FastAPI routers (per-module files)
│       │   ├── bill.py       # /api/bills
│       │   ├── calendar.py   # /api/calendar
│       │   ├── dashboard.py  # /api/dashboard
│       │   ├── tag.py        # /api/tags
│       │   └── weather.py    # /api/weather
│       └── tradesim/         # TradeSim feature module — see its section below
└── frontend/         # Vite + Vue 3 app
    ├── package.json
    └── src/
        ├── main.ts           # Single createApp + single Vue Router
        ├── App.vue           # Root component with Lenis smooth scroll
        ├── styles/main.css   # Tailwind v4 @theme directives + globals
        ├── api/              # fetch/axios wrappers per module
        │   └── tradesim.ts
        ├── types/            # shared TS interfaces per module
        │   └── tradesim.ts
        ├── composables/
        │   └── useScrollReveal.ts  # Intersection Observer scroll-reveal
        ├── components/       # reusable UI
        │   ├── KnowledgeMapBackground.vue
        │   └── StarfieldBackground.vue
        ├── features/         # integrated projects, namespaced
        │   └── tradesim/
        └── views/            # portal pages
            ├── Dashboard.vue # Home — project cards grid
            ├── Bills.vue     # Billing tracker page
            └── Notes.vue     # Notes pages (shared by 4 routes)
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend (portal) | Vue 3 `<script setup>`, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Vue Router 4, Lenis |
| Frontend (TradeSim) | Element Plus + icons, ECharts 6, axios, marked, DOMPurify, `github-markdown-css` |
| Backend | FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2 |
| Database | MySQL 8 via `pymysql`; MongoDB via `motor` (TradeSim large objects only) |
| Data / quant | polars, pandas, pyarrow, akshare, openai |
| Runtime | Python: conda env `desheng`; Node: system npm |

Alembic is listed in `requirements.txt` but **deliberately not used** — schema comes from
`Base.metadata.create_all()`. Decision recorded in
`docs/3_KnowledgeMap集成TradeSim正式迁移计划.txt` §13; revisit only if schema churn increases.

## Running the project

**Backend** — `KM_BACKEND_PORT` overrides the port, default `8010`.
```bash
conda activate desheng
cd backend
python main.py          # starts uvicorn on http://0.0.0.0:8010 with --reload
```

**Frontend**
```bash
cd frontend
npm run dev             # starts Vite dev server on http://localhost:3000
```

Vite proxies `/api` to `http://localhost:8010` (override with `KM_API_TARGET`).
Keep the two ports in sync — the proxy target and `KM_BACKEND_PORT` must match, or every
API call 502s.

MongoDB must be running for TradeSim's history and detail pages; the portal's own
modules do not need it.

**Database** — must exist before first backend start:
```sql
CREATE DATABASE IF NOT EXISTS knowledgemap CHARACTER SET utf8mb4;
```
Connection: `mysql+pymysql://root:root@localhost:3306/knowledgemap`

`knowledgemap` is the **single** MySQL database for every module — `tags`, `bills`,
`calendar_events` and TradeSim's `simulation_records` all live here, on one shared
`Base` and one `engine`/`SessionLocal`/`get_db`. Do not introduce a second engine or
`declarative_base()`; a feature module's models import `Base` from `app.models.bill`.

Tables are auto-created on startup via `Base.metadata.create_all()`. Default tags are seeded on first run by `seed_default_tags()`.

A legacy standalone `tradesim` MySQL database still exists on this machine holding the
pre-migration copy of those 6 records. It is unused by the app and kept only as a
rollback source — do not point code at it.

## Design system

Dark theme throughout. Core palette defined in `frontend/src/styles/main.css` via `@theme`:

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#0f0f14` | Page background |
| `--color-surface` | `#16161e` | Card backgrounds |
| `--color-border` | `#2a2a3a` | Borders |
| `--color-primary` | `#7c3aed` | Accent / CTAs |
| `--color-accent` | `#06b6d4` | Secondary accent |
| `--color-text` | `#e2e8f0` | Body text |
| `--color-muted` | `#64748b` | Muted / secondary text |

Smooth scroll: Lenis initialized in `App.vue`, RAF loop in `onMounted`.
Scroll-reveal: `useScrollReveal` composable, `data-reveal` attribute on elements.

## Billing module

### Data model

**`tags`** — hierarchical label store, shared across all tag dimensions:
- `type`: `category | subcategory | payment_platform | payment_channel | fund_type`
- `parent_id`: self-referential FK (subcategory → category)
- Bills reference tags via `*_id` FK columns (all nullable, `ON DELETE SET NULL`)

**`bills`** — one row per transaction:
- `record_type`: `支出 | 收入`
- `expense_date`, `expense_time`, `amount`
- Tag FKs: `category_id`, `subcategory_id`, `payment_platform_id`, `payment_channel_id`, `fund_type_id`
- `reimbursement_status`: `无需报销 | 待报销 | 已报销`
- `transaction_id` (unique, nullable), `note`

### Default category structure

```
餐饮 → 早饭, 午饭, 晚饭, 夜宵, 饮料, 零食
娱乐 → 购物, 虚拟会员
旅行 → 住宿, 出行, 门票
日常 → 交通, 工作, 医疗
工资 / 奖金 / 退款 / 生活费  (no subcategories)

payment_platform: 微信小程序, 抖音, 美团, 京东, 线下, 花呗, 淘宝, 拼多多
payment_channel:  微信, 支付宝, 银行卡
fund_type:        微信余额, 零钱通, 银行卡余额, 支付宝余额
```

To **re-seed categories** in a live DB (payment/channel/fund tags untouched):
```bash
conda activate desheng
cd backend
python -c "
from app.database import SessionLocal
from app.crud.tag import reseed_categories
with SessionLocal() as db:
    reseed_categories(db)
print('done')
"
```

### API endpoints

```
GET    /api/bills/              ?record_type, category_id, date_from, date_to, skip, limit
POST   /api/bills/
GET    /api/bills/summary/monthly  ?year, month
GET    /api/bills/{id}
PATCH  /api/bills/{id}
DELETE /api/bills/{id}

GET    /api/tags/               root tags with children (tree)
GET    /api/tags/all            flat list  ?tag_type=...
POST   /api/tags/
PATCH  /api/tags/{id}
DELETE /api/tags/{id}

GET    /api/health
```

### Frontend Bills.vue

- Month navigator (prev/next arrows, current month label)
- Day-grouped cards with expand/collapse, per-day income/expense totals
- Monthly summary bar (income / expense / net)
- Add / Edit modal via `<Teleport to="body">`, full form
- Subcategory dropdown auto-filters to children of selected category
- Payment fields hidden for 收入 records
- Delete confirmation dialog via Teleport

## TradeSim module

Stock backtesting project, migrated into the portal as a self-contained feature module.
Full migration record: `docs/3_KnowledgeMap集成TradeSim正式迁移计划.txt`.

### Backend

```
backend/app/tradesim/
├── router.py             # aggregates the three v1 routers
├── api/v1/
│   ├── ai.py             # SSE streaming LLM analysis
│   ├── records.py        # favorites: save / list / detail
│   └── simulate.py       # backtest execution
├── core/config.py        # Mongo + LLM settings only (no MySQL URL)
├── db/
│   ├── models.py         # SimulationRecord, inherits app.models.bill.Base
│   └── session.py        # Mongo client + close_tradesim_connections()
├── schemas/              # record.py, simulate.py
├── services/data_fetcher.py   # akshare wrapper, proxy env guarded by a Lock
└── strategy/
    ├── base.py
    └── specific/grid_trade.py
```

Imports inside the module must be fully qualified as `app.tradesim.*`. The only two
outward imports are `app.database.get_db` and `app.models.bill.Base`.

### Storage split

`simulation_records` (MySQL) holds the queryable index — symbol, dates, metrics,
`strategy_params` JSON — so list queries stay fast. The bulky arrays (equity curves of
240–2700 points, hundreds of execution records) go to MongoDB `tradesim.simulation_logs`,
linked by `mongo_log_id`. The Mongo database name `tradesim` is historical and unrelated
to the retired MySQL database of the same name.

`save-favorite` writes Mongo first, then MySQL; if the SQL write fails it rolls back and
deletes the orphaned Mongo document. Keep that compensation path intact when editing.

### API endpoints

```
POST   /api/tradesim/v1/simulate/run
POST   /api/tradesim/v1/records/save-favorite
GET    /api/tradesim/v1/records/list
GET    /api/tradesim/v1/records/detail/{record_id}
POST   /api/tradesim/v1/ai/analyze-stream        (SSE)
```

### Frontend

`features/tradesim/` holds `layouts/TradeSimLayout.vue` plus four views
(Simulator / Dashboard / Detail / YearLine), registered as children of `/tradesim` in
`main.ts`; `/tradesim` redirects to `/tradesim/simulate`. `/tradesim/yearline` is an
intentional placeholder — the year-line strategy is not implemented.

TradeSim keeps its original **light** Element Plus look while the portal is dark. The
isolation is container-level: everything sits inside `.tradesim-shell` with
`isolation: isolate`, and every component uses `<style scoped>`. TradeSim's global
`style.css` was deliberately not imported. Preserve this boundary — an unscoped style
block or a global Element Plus theme override will leak into the portal.

All requests go through `api/tradesim.ts` at the relative base `/api/tradesim/v1`.
Never hardcode a backend host; the Vite proxy handles it.

### Tests

```bash
conda activate desheng
cd backend
python tests/tradesim_grid_strategy_cases.py    # plain runner, expects 8 PASS
```

Not pytest — it is a standalone script covering grid cycles, multi-grid crossings,
insufficient cash, commission/slippage, base position and invalid params.

## Development notes

- IDE "Cannot find module" errors in backend files are **false positives** — the IDE interpreter is not set to the `desheng` conda env. Code runs fine from the terminal. Fix: set interpreter to `C:\Users\afrangry\anaconda3\envs\desheng\python.exe` in VS Code or PyCharm.
- `conda` is not on PATH in a plain PowerShell session. Either `conda activate desheng` in a
  conda-initialized shell, or call the interpreter by absolute path (above) for one-off commands.
- Do **not** run `npm install` or other heavy frontend commands — they trigger semgrep-core-proprietary.exe and slow the IDE. Hand these to the user to run manually. `npm run build` has
  therefore never been verified in this environment.
- Frontend dev server runs on `:3000`; CORS is whitelisted for `http://localhost:3000` in `main.py`.
- `main.ts` uses `createWebHistory()`. Local `npm run dev` has Vite's SPA fallback built in, but a
  production deploy would need the static server configured for it. No production deploy exists yet.
- Root-level `tp.md` is an unrelated scratch dump left in the working tree, untracked on purpose.
  Not part of the project.
