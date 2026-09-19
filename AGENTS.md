# KnowledgeMap — AGENTS.md

Personal portal aggregating all side-projects under one unified dashboard. Each project gets a card on the dashboard; clicking it navigates to that project's dedicated page.

## Repository layout

Two layout conventions coexist by design. The portal's own code is grouped **by layer**
(`models/`, `schemas/`, `crud/`, `routers/`); each integrated project is a self-contained
**feature module** (`app/tradesim/`, `features/tradesim/`). Add new projects as feature
modules, not as new files in the by-layer directories.

```
KnowledgeMap/
├── docs/             # design, audit and migration docs — see "Documentation" below
├── backend/          # FastAPI app (Python)
│   ├── main.py       # Sole entry point — `python main.py` starts uvicorn on :8010
│   ├── requirements.txt
│   ├── tests/
│   │   ├── tradesim_grid_strategy_cases.py   # plain-python runner, 8 cases
│   │   └── portal_crud_cases.py              # plain-python runner, 9 cases, in-memory SQLite
│   └── app/
│       ├── database.py       # MySQL engine + SessionLocal + get_db (single source)
│       ├── models/           # SQLAlchemy ORM models
│       │   ├── __init__.py   # re-export façade (Base, Bill, Tag, CalendarEvent, *Tone, enums)
│       │   └── bill.py       # the actual definitions — the only place `Base` is created
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
│       │   ├── calendar.py   # /api/calendar-events
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
        ├── api/              # request layer, one file per backend router
        │   ├── client.ts     # shared apiFetch (prefixes /api, unwraps `detail`)
        │   ├── bills.ts      # + tags.ts, calendar.ts, dashboard.ts, weather.ts
        │   └── tradesim.ts   # TradeSim uses axios; its SSE call uses raw fetch
        ├── types/            # shared TS interfaces per module
        │   ├── portal.ts     # portal modules (bills / tags / calendar / weather)
        │   └── tradesim.ts
        ├── utils/            # pure helpers — no reactive state, so not composables
        │   └── date.ts       # local-timezone date keys; read the UTC trap in its header
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
            ├── Vault.vue     # /vault — storage room for retired static UI drafts
            └── Notes.vue     # Notes pages (shared by 4 routes)
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend (portal) | Vue 3 `<script setup>`, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Vue Router 4, Lenis |
| Frontend (TradeSim) | Element Plus + icons, ECharts 6, axios, marked, DOMPurify, plus a vendored namespaced copy of `github-markdown-css` in `features/tradesim/styles/` |
| Backend | FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2 |
| Database | MySQL 8 via `pymysql`; MongoDB via `motor` (TradeSim large objects only) |
| Data / quant | polars, pandas, pyarrow, akshare, openai |
| Runtime | Python: conda env `desheng`; Node: system npm |

Install the backend dependencies **from `backend/requirements.txt`**, not by hand — that file
is accurate, but the `desheng` env has drifted from it before. On 2026-09-20 both `akshare`
and `pyarrow` turned out to be missing, which made
`POST /api/tradesim/v1/simulate/run` fail (`503`, then an `ImportError` from
`polars.from_pandas`) even though the application code was correct.

⚠ The env pins `HTTP_PROXY`/`HTTPS_PROXY` to a local proxy that cannot reach PyPI, so a plain
`pip install` hangs with no output. Install with the Tsinghua mirror and clear those two
variables for that command:
`python -m pip install <pkg> -i https://pypi.tuna.tsinghua.edu.cn/simple`

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

⚠ **There is no authentication of any kind.** Binding `0.0.0.0` means every `/api/...` route
— bill data included, and the **paid** LLM analysis endpoints — is reachable by any device on
the same network. The CORS whitelist for `http://localhost:3000` is a browser-side rule and
provides no protection whatsoever against `curl`, a script, or any non-browser client. For
local-only use bind `127.0.0.1`; if this is ever exposed beyond the machine, add an API-key
dependency first.

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
| `--color-primary` | `#7c3aed` | Accent / CTAs |
| `--color-accent` | `#06b6d4` | Secondary accent |
| `--color-text` | `#e2e8f0` | Body text |
| `--color-surface` | `#0f0f14` | Page background |
| `--color-border` | `#2e2e3a` | Borders |
| `--color-text-muted` | `#94a3b8` | Muted / secondary text |

**Corrected 2026-09-20 — this table previously listed three tokens that do not exist or do
not hold the stated value** (verified against `main.css`):

- `--color-bg` **does not exist**. The page background is `--color-surface`, i.e. Tailwind's
  `--color-surface: var(--surface)` with `--surface: #0f0f14`.
- `--color-surface` was documented as `#16161e` "card backgrounds" — wrong on both counts:
  it is `#0f0f14`. Card backgrounds use `--card-bg: #16161e`, which is **not** exposed as a
  Tailwind colour and must be consumed as `var(--card-bg)`.
- `--color-border` is `#2e2e3a`, not `#2a2a3a`.
- `--color-muted` should read `--color-text-muted` (`#94a3b8`).

Re-check `main.css` before quoting a token here — this table has drifted once already.

`--accent` / `--accent-light` and the `--color-accent*` aliases exist only for the retained
light theme; nothing consumes them at runtime today. See "Theme" below.

Smooth scroll: Lenis initialized in `App.vue`, RAF loop in `onMounted`.
Scroll-reveal: `useScrollReveal` composable, `data-reveal` attribute on elements.

**A background component must not style its consumer.** `StarfieldBackground.vue` used to carry
a `:global(.starry-workspace)` block that reached out of its `scoped` styles to define layout
and the whole dark palette for whichever page mounted it — so it would have silently repainted
any page it was reused on. That is gone (docs/5 §2.21): page-level surface styles live in the
page (`Bills.vue`), and the component styles only its own canvas. `KnowledgeMapBackground.vue`
is the model to copy. The same rule applies to `:global()` in any `.vue` file — the only
remaining one is worth a second look before you add another.

## Portal request layer

Portal modules reach the backend through `frontend/src/api/`, one file per backend router
(`bills.ts`, `tags.ts`, `calendar.ts`, `dashboard.ts`, `weather.ts`), all sharing
`api/client.ts`'s `apiFetch` — which prefixes `/api`, defaults `Content-Type`, unwraps the
backend's Chinese `detail` on failure, and returns `null` for 204. **Do not call `fetch` from
a view**; add a function to the matching module instead. Response types live in
`types/portal.ts` (portal) and `types/tradesim.ts` (TradeSim), so views and the request layer
share one declaration instead of each view redeclaring its own.

(Before 2026-09-20 each view carried its own private `apiFetch` — `Bills.vue` and
`Dashboard.vue` had two byte-identical copies — and declared its own response interfaces.)

Three things look like redundancy but are not; read the notes in `types/portal.ts` before
"simplifying" them:

- `GET /tags/` returns **25 root tags that are not all categories** — payment platform,
  payment channel and fund type are roots too. Callers must filter by `type`.
- `GET /tags/all` returns **39 entries** (25 roots + 14 subcategories), and its category
  entries **do** carry `children`. Grouping it client-side by `type` is equivalent to
  `?tag_type=` filtering (verified by ID set, docs/5 §2.18) — which is why `loadTags()` makes
  two requests rather than four.
- `monthly_summary`'s amounts really are `number`s (the endpoint has a `response_model`, see
  docs/5 §2.14), so do not `parseFloat` them. `BillItem.amount` is a `string` by contrast.
  That asymmetry is intentional — writes send a number, reads return a string.

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

⚠ **That block describes the DEFAULTS `seed_default_tags()` writes — not the current database.**
Verified 2026-09-20 against both the seed code (`crud/tag.py:104`/`:112`) and the live DB: the
seed creates exactly the 8 platforms and 4 fund types listed above, but the live `knowledgemap`
DB holds **two more that the seed does not create** — `软件本体` (`payment_platform`, id=49) and
`亲情卡` (`fund_type`, id=48), both added by hand. `reseed_categories()` deliberately leaves the
payment/channel/fund tags untouched, so they survive a re-seed; but **a database rebuilt from
scratch will not have them**, and any bill pointing at them would silently lose that tag (the FK
is `ON DELETE SET NULL`). Re-add them by hand if you ever rebuild.

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
GET    /api/bills/{bill_id}
PATCH  /api/bills/{bill_id}
DELETE /api/bills/{bill_id}

GET    /api/tags/               roots + children (roots are NOT all categories — see below)
GET    /api/tags/all            all tags (25 roots + 14 subcategories)  ?tag_type=...
POST   /api/tags/
PATCH  /api/tags/{tag_id}
DELETE /api/tags/{tag_id}

GET    /api/calendar-events/    list calendar events
POST   /api/calendar-events/
PATCH  /api/calendar-events/{event_id}
DELETE /api/calendar-events/{event_id}

GET    /api/dashboard/git-stats/    commit counters for the Dashboard card
GET    /api/weather/                QWeather proxy (real network call, needs the API key)

GET    /api/health
```

(2026-09-20: the calendar prefix is `/api/calendar-events`, not `/api/calendar`, and the
dashboard and weather routers were missing from this list entirely.)

(2026-09-20, later: the path parameters are now spelled the way FastAPI names them —
`{bill_id}` / `{tag_id}` / `{event_id}` — instead of a generic `{id}`. This list was checked
against the **live route table** on the `app` object: **23 application routes, all of them
listed here**, so the only mismatch left was the parameter *names*, which made this list
disagree with `/openapi.json` for no reason. The URL shape is identical either way. Note that
`/docs`, `/redoc`, `/docs/oauth2-redirect` and `/openapi.json` are FastAPI's own and are not
part of the 23.)

**Which of these the UI actually calls** (measured 2026-09-20 by enumerating the live routes
off the FastAPI `app` object and matching them against `frontend/src/api/` — see docs/5 §2.24).
The backend exposes 23 application routes; the portal frontend calls all but five:

- `GET /api/bills/{bill_id}` — unused, and **redundant** for the current UI: the list response
  already carries every field the edit modal needs.
- `PATCH /api/calendar-events/{event_id}` — **implemented but unreachable from the UI.** Events
  can be created and deleted, not edited, so fixing a typo means delete-and-re-add. This is the
  one backend-ready gap a future UI could close.
- `POST /api/tags/`, `PATCH /api/tags/{tag_id}`, `DELETE /api/tags/{tag_id}` — **there is no tag
  management screen at all.** Tags change only via the `reseed_categories` script or SQL. The
  trio is a complete REST surface waiting for a UI that does not exist.

None of this is dead code and none of it was removed — a complete REST surface is defensible.
But do not assume "the endpoint exists, so the UI must use it". `GET /api/health` is likewise
never called by the frontend, by design (it is ops-facing); note that it always returns
`{"status":"ok"}` **without touching MySQL or Mongo**, so it is a liveness signal only and must
not be used as a readiness probe — it answers 200 with the database down.

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
├── services/data_fetcher.py   # akshare wrapper: daily EM -> Sina -> TX, intraday EM -> Sina; proxy env guarded by a Lock
└── strategy/
    ├── base.py
    └── specific/grid_trade.py
```

Imports inside the module must be fully qualified as `app.tradesim.*`. The only two
outward imports are `app.database.get_db` and `app.models.bill.Base`.

**Data sources.** Daily bars use a 东财 → 新浪 → 腾讯 fallback chain. Intraday
(`5min`/`1min`) uses its own 东财 → 新浪 chain — the Eastmoney kline host is unreachable
from this machine (`RemoteDisconnected`, independent of the proxy), and intraday is a
**reachable** code path, not dead code: `TradeSimSimulator.vue` exposes a `data_frequency`
dropdown and `schemas/simulate.py` accepts `daily | 5min | 1min`.

⚠ The Sina minute endpoint **ignores the requested date range** and always returns a fixed
window of ~1970 bars. `_clip_to_range()` therefore filters the result to
`[start_date, end_date]` locally, and a request whose range falls outside that window is
**refused with a 400** rather than silently backtesting a different period. Also note
`_normalize()` keeps only the first 10 characters of the timestamp, so intraday bars carry a
date-only label — unchanged from the original Eastmoney path.

### Storage split

`simulation_records` (MySQL) holds the queryable index — symbol, dates, metrics,
`strategy_params` JSON — so list queries stay fast. The bulky arrays (equity curves of
240–2700 points, hundreds of execution records) go to MongoDB `tradesim.simulation_logs`,
linked by `mongo_log_id`. The Mongo database name `tradesim` is historical and unrelated
to the retired MySQL database of the same name.

`save-favorite` writes Mongo first, then MySQL; if the SQL write fails it rolls back and
deletes the orphaned Mongo document. Keep that compensation path intact when editing.

**Two equity-point schemas, on purpose.** `simulate/run` returns the strict `EquitySnapshot`;
`records/detail` returns `StoredEquitySnapshot(EquitySnapshot)`, which relaxes only
`close_price`, `benchmark_value` and `position_utilization` to optional. Those three were added
to the engine later, and the two oldest saved records (`id=1`, `id=2`, symbol `000400`) lack
**all three** on **every** point — 242 and 2676 points respectively. A strict read path would
therefore turn their detail page into a `ResponseValidationError` 500. Those records are
deliberately **not** deleted (see the Mongo decision in `docs/5`), so the *read* schema is the
thing that gives way. The frontend mirrors the split with a `StoredEquitySnapshot` type.
Do **not** "fix" this by deleting the old data or by relaxing the write path — keeping the
write path strict is what still catches an engine that forgets to emit a field.
(`execution_records` needs no such split: all six saved records carry all seven `TradeRecord`
fields.)

### API endpoints

```
POST   /api/tradesim/v1/simulate/run
POST   /api/tradesim/v1/records/save-favorite
GET    /api/tradesim/v1/records/list
GET    /api/tradesim/v1/records/detail/{record_id}
POST   /api/tradesim/v1/ai/analyze-stream        (SSE)
```

`annualized_return` is stored in MySQL and returned by `simulate/run`, but it is **not**
exposed by `/records/list` or `/records/detail` (nor declared in `RecordBriefResponse`), so no
page can display 年化收益 today. That is a gap in the interface, not a defect — the AI prompt
does not reference it either. Adding it would be a new response field.

### Frontend

`features/tradesim/` holds `layouts/TradeSimLayout.vue` plus four views
(Simulator / Dashboard / Detail / YearLine), registered as children of `/tradesim` in
`main.ts`; `/tradesim` redirects to `/tradesim/simulate`. `/tradesim/yearline` is an
intentional placeholder — the year-line strategy is not implemented.

TradeSim keeps its original **light** Element Plus look while the portal is dark. The
isolation is container-level: everything sits inside `.tradesim-layout` with
`isolation: isolate`, and every component uses `<style scoped>`. TradeSim's global
`style.css` was deliberately not imported. Preserve this boundary — an unscoped style
block or a global Element Plus theme override will leak into the portal.

(2026-09-20 correction: the isolating class is `.tradesim-layout`, on the outer element in
`layouts/TradeSimLayout.vue`. This section previously named `.tradesim-shell`, which is only
the inner `el-container` and carries no `isolation` property.)

✅ **Resolved 2026-09-20 (was docs/4 finding H1).** TradeSim's markdown used to be styled by
`github-markdown-css/github-markdown-light.css`, imported **globally** by
`TradeSimSimulator.vue` and `TradeSimDetail.vue`. That file keys everything off the single
class name `.markdown-body`, which the portal's notes reader also uses — so visiting any
TradeSim page injected `.markdown-body { background-color:#ffffff; color:#1f2328 }` into the
document and turned the portal's reader into a white box with near-invisible text.

The fix: the dependency is **no longer imported at all**. `features/tradesim/styles/tradesim-markdown.css`
is a namespaced copy of that stylesheet in which every one of its 191 rules has been renamed
from `.markdown-body` to `.tradesim-markdown` (values untouched, so rendering is identical).
It is imported **once**, from `layouts/TradeSimLayout.vue`, and the two AI panels now use
`class="tradesim-markdown"`. The upstream file has no bare `body`/`html`/`*`/`:root`
selectors, so a fully-prefixed copy cannot leak into the portal at all, and
`github-markdown-css` was removed from `package.json`.

`Notes.vue` additionally keeps a narrow defensive block (search for "防御全局 markdown 样式泄漏").
It pins only what the leak could actually hijack — the reader container's background, plus
links/blockquotes/hr/table rows, which the portal never styles. **Do not add descendant colour
rules to that block**: `Notes.vue` already defines the reader's dark palette at its own
`.markdown-body` rules, and the defensive selectors outrank them, so a `color` declaration
there silently overrides the portal's own styling (the first version of this fix did exactly
that and had to be narrowed).

All requests go through `api/tradesim.ts` at the relative base `/api/tradesim/v1`.
Never hardcode a backend host; the Vite proxy handles it.

### Tests

```bash
conda activate desheng
cd backend
python tests/tradesim_grid_strategy_cases.py    # plain runner, expects 8 PASS
python tests/portal_crud_cases.py               # plain runner, expects 9 PASS
```

Not pytest — both are standalone scripts that print `PASS`/`FAIL` and exit non-zero on failure.

- `tradesim_grid_strategy_cases.py` covers grid cycles, multi-grid crossings, insufficient
  cash, commission/slippage, base position and invalid params.
- `portal_crud_cases.py` covers the portal's three modules (`bills` / `tags` /
  `calendar_events`) end to end through the CRUD layer.

⚠ `portal_crud_cases.py` runs against an **in-memory SQLite** database, never MySQL — the
dev machine's MySQL holds real bill data, and these cases insert and delete rows. Two dialect
differences are handled explicitly and documented in the file: `monthly_summary` uses MySQL's
`YEAR()`/`MONTH()`, so the test registers equivalent SQLite functions; and SQLite stores
`Numeric` via float, which is why money assertions normalise through `float()` first. Because
of that first point, the SQLite shim is a **test double** — it is not evidence that the query
is portable, and production remains MySQL-only.

## Theme (retained on purpose, not wired up)

`frontend/src/styles/main.css` still carries a complete light palette under `.theme-light`,
and `Dashboard.vue` still has `updateThemeClass()`. **Neither is reachable at runtime**: the
day/night toggle was removed in an earlier iteration when the starfield background became the
only design, `isDark` is hard-coded to `true`, and `onMounted` pins the dark class — so the
`else` branch can never execute.

The owner decided (2026-09-20) to **keep both** rather than delete them, so do not "clean
them up" as dead code. Both sites carry comments saying so.

The nav theme button is a deliberate placeholder: it does **not** switch the theme, it only
shows a transient "功能待开发" toast that fades out after 3s (`notifyThemePending()` in
`Dashboard.vue`). To actually revive the theme, flip `isDark` and call `updateThemeClass()`
from that handler. The toast is portal-native CSS rather than Element Plus `ElMessage`, on
purpose — using Element Plus here would leak its light styling into the portal.

## Storage room (`/vault`)

`views/Vault.vue` is an **archive page, not a product feature**. It holds static UI drafts
retired from the Dashboard: the journal grid, the newsletter band and the author panel —
everything that remains of the first landing-page design. It takes no backend data; the
newsletter form's submit is prevented.

It deliberately **drops the `.reveal-item` scroll-reveal classes** its source markup used.
On a standalone route there is no IntersectionObserver, so keeping those classes would leave
the content stuck at `opacity: 0` — invisible. Restoring the animation means calling
`useScrollReveal()` in Vault.vue and defining the reveal CSS there.

Its styles are self-contained by design: it carries copies of `.section-block`,
`.section-heading` and `.outline-button`, which the Dashboard also keeps for its own use
(hero buttons, the projects section). This duplication is intentional — the goal is
archiving, not reuse. Do not "de-duplicate" those copies into a shared sheet without
updating Dashboard's scoped styles at the same time.

Reachable from the nav (「储物间」) and from a project card (`idCode: '08'`). The nav item
used to be 「关于我」 pointing at the now-removed `#about` anchor.

## Documentation

| File | Role |
|---|---|
| `AGENTS.md` (this file) | **Single source of truth for AI/human contributors.** `CLAUDE.md` is only a pointer to it — edit this file, not that one. |
| `docs/1_前端界面背景与特效整理.txt` | Living register of background/animation effects. Log UI-effect changes here. |
| `docs/2_交易策略模块的完善.txt` | Historical archive (2026-08-14). Read the banner at its top for the falsified claims. |
| `docs/3_KnowledgeMap集成TradeSim正式迁移计划.txt` | Historical migration record. Read the banner at its top for superseded claims. |
| `docs/4_项目整理审计与清理计划.txt` | **Frozen audit baseline** — findings H1–H9 / M1–M17, batch plan, deletion-safety proofs. Do not edit. |
| `docs/5_清理执行日志与工作汇报.txt` | Live execution log. Append progress and measured results here. |

## Development notes

- **Never take "today" with `new Date().toISOString().slice(0, 10)`** — `toISOString()` is
  always UTC, and in UTC+8 that returns **yesterday** between local 00:00 and 07:59 (8 hours
  of every day). This was a real bug in `Bills.vue`'s default `expense_date`. Use `todayKey()`
  / `dateToKey()` from `src/utils/date.ts` instead.
- Pure frontend helpers can be tested with no test runner at all:
  `TZ=Asia/Shanghai node --experimental-strip-types path/to/helper.ts` executes the real file
  (Node 22.17). Used to verify `utils/date.ts` — see docs/5 §2.20.
- IDE "Cannot find module" errors in backend files are **false positives** — the IDE interpreter is not set to the `desheng` conda env. Code runs fine from the terminal. Fix: set interpreter to `C:\Users\afrangry\anaconda3\envs\desheng\python.exe` in VS Code or PyCharm.
- `conda` is not on PATH in a plain PowerShell session. Either `conda activate desheng` in a
  conda-initialized shell, or call the interpreter by absolute path (above) for one-off commands.
- Do **not** run `npm install` — it triggers semgrep-core-proprietary.exe and slows the IDE.
  Hand it to the user unless they have explicitly authorised it for the session.
- `npm run build` **has been verified** (2026-09-20): it passes and emits `frontend/dist/`.
  The previous note here claiming it "has never been verified in this environment" is
  obsolete. `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` is the cheap gate for type
  errors and needs no dev server.
- Vite's dev server binds **IPv6 `::1` only** — `127.0.0.1:3000` refuses connections; use
  `http://localhost:3000`. In PowerShell, `Invoke-WebRequest` against a local server needs
  `-NoProxy`, otherwise the request goes through the local proxy and returns 502.
- Frontend dev server runs on `:3000`; CORS is whitelisted for `http://localhost:3000` in `main.py`.
- `main.ts` uses `createWebHistory()`. Local `npm run dev` has Vite's SPA fallback built in, but a
  production deploy would need the static server configured for it. No production deploy exists yet.
- Root-level `tp.md` is an unrelated scratch dump left in the working tree, untracked on purpose.
  Not part of the project.
