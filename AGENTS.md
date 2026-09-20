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

Install the backend dependencies **from `backend/requirements.txt`**, not by hand.

⚠ **That file lists minimums, not a lockfile — it contains no `==` pins at all** (only bare
names and `>=`). So the env can drift silently, and it did: on 2026-09-20 `akshare` and
`pyarrow` were both missing from `desheng`, which made `POST /api/tradesim/v1/simulate/run`
fail (`503`, then an `ImportError` from `polars.from_pandas`) even though the application code
was correct. **Verified resolved later the same day** — all 16 entries are now installed and
every constraint is satisfied (`akshare` 1.18.96, `pyarrow` 25.0.1, `polars` 1.44.0,
`pandas` 2.3.3, `fastapi` 0.127.0, `pymysql` 1.1.2, `motor` 3.7.1, `openai` 2.16.0,
`sqlalchemy` 2.0.45, `pydantic` 2.12.5, `uvicorn` 0.40.0, `alembic` 1.18.4). Method and raw
output: docs/7 §2.30.

**Seven entries are never imported by our own code — none of them may be pruned as "unused".**
They are runtime-indirect requirements, each with a specific consumer:

| Entry | Why it must stay |
|---|---|
| `pymysql` | SQLAlchemy loads it from the URL `mysql+pymysql://…` — never imported by name |
| `cryptography` | `pymysql/_auth.py` imports it inside a `try/except` and **raises at runtime without it** for MySQL 8's `caching_sha2_password` |
| `pymongo` | motor requires `pymongo<5.0,>=4.9`; it also provides the `bson` that `records.py` imports |
| `curl-cffi` | akshare requires `curl_cffi>=0.13.0` |
| `pandas` | akshare requires `pandas>=2.0.0` |
| `pyarrow` | polars declares it **only as an extra** (`polars[pyarrow]`), so it does *not* arrive for free — this is precisely the entry that went missing |
| `alembic` | deliberately unused (see the Alembic note above) |

Two direct imports of transitive packages, recorded rather than changed: `from bson import
ObjectId` (`tradesim/api/v1/records.py`) resolves inside pymongo's own bundled `bson` (there
is no standalone `bson` distribution installed), and `from starlette.concurrency import
run_in_threadpool` (`tradesim/api/v1/simulate.py`) relies on starlette arriving with fastapi —
starlette **is** a real distribution, but it is *not* listed in `requirements.txt`.

**Frontend side: verified clean and reproducible (2026-09-20).** Unlike Python, the frontend
*does* have a committed lockfile — `frontend/package-lock.json` (lockfileVersion 3, 166
package nodes) is tracked by git and not ignored (`.gitignore:33` only ignores
`frontend/node_modules/`). Measured: all **15 declared packages are installed and match the
lockfile exactly** (0 mismatches: vue 3.5.38, vite 8.0.16, element-plus 2.14.4, echarts 6.1.0,
tailwindcss 4.3.1, typescript 6.0.3, …), there are **no ghost top-level packages** and **no
undeclared imports** — scanning the `<script>` blocks of all 26 frontend source files yields 13
bare third-party specifiers, every one of them declared. (Vite 8 bundles with **rolldown**:
`@rolldown/binding-*` platform packages, not `@rollup/*`.)

⚠ **One stale entry survives in the lockfile** (checked 2026-09-20, later the same night):
removing `github-markdown-css` from `package.json` (the H1 fix) never regenerated
`package-lock.json`, so the lock's **root `dependencies` still declares
`github-markdown-css: ^5.9.0`** and still carries its `packages` entry, and
`node_modules/github-markdown-css` is still on disk. Everything else matches exactly (9/9
dependencies, 6/6 devDependencies, all ranges identical). This is **hygiene, not breakage** —
measured, with a control group: `npm ci --dry-run` in an isolated directory containing only
those two files **succeeds** (it does not fail a sync check), and it behaves identically once
the stale entry is removed. Fix it by running `npm install` once (only the owner may — see the
`npm install` note below); any install will silently drop the entry.

⚠ **When scanning `.vue` files for imports or code patterns, scan the `<script>` blocks only —
never the whole file.** `Notes.vue` renders full-length markdown *articles*, and their fenced
code samples contain real-looking code: a naive full-text grep for `from '…'` finds
`import lodash from 'lodash'` / `import { cloneDeep } from 'lodash-es'` inside a Vite
bundle-optimisation tutorial on line 31, and reports two undeclared dependencies that do not
exist. The same trap applies to `.vue` comments and template text.

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
python main.py          # starts uvicorn on http://127.0.0.1:8010 with --reload
```

⚠ **There is no authentication of any kind — and the default binding is now `127.0.0.1`**
(owner's decision, 2026-09-20; it used to be `0.0.0.0`). The cost is real and deliberate:
**`http://<lan-ip>:8010` no longer answers, so a phone or any other device on the same network
cannot use the portal.** If it is ever exposed beyond this machine, **add an API-key dependency
first — do not simply put `0.0.0.0` back.**

Why it was restricted: with no auth at all, `0.0.0.0` made every `/api/...` route — bill data
included, and the **paid** LLM analysis endpoints — reachable by any device on the same network.
The CORS whitelist for `http://localhost:3000` is a browser-side rule and provides no protection
whatsoever against `curl`, a script, or any non-browser client. Note that only the **port** is
still configurable by env var; the **host is hard-coded on purpose**, so that re-exposing the
port can never be a one-character accident.

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

⚠ **`create_all()` never ALTERs an existing table — and this machine's `simulation_records` did not come
from it.** Measured 2026-09-20 by building all four tables into a throwaway database and diffing
`SHOW CREATE TABLE` against the live one (docs/7 §2.38). `bills` / `tags` / `calendar_events` come out
structurally identical (the only differences are `COMMENT`, `CHARACTER SET/COLLATE` and `AUTO_INCREMENT`
— decoration). But `simulation_records` differs in **four columns**: the model declares them nullable
while the live table has them `NOT NULL`.

| Column | Model ⇒ a fresh `create_all()` | This machine's live DB |
|---|---|---|
| `user_id` | `bigint DEFAULT '0'` (nullable) | `bigint NOT NULL DEFAULT '0'` |
| `data_frequency` | `varchar(20) DEFAULT 'daily'` (nullable) | `varchar(20) NOT NULL DEFAULT 'daily'` |
| `annualized_return` | `decimal(10,4) DEFAULT (0.0000)` (nullable) | `decimal(10,4) NOT NULL DEFAULT '0.0000'` |
| `created_at` | `timestamp NULL DEFAULT CURRENT_TIMESTAMP` | `timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP` |

The live table was created from **`表结构/tradesim.sql`** — its column definitions match the live table
word for word (including the `idx_simulation_records_*` index names and its own Chinese comments, none of
which appear in the model), so the model and that DDL are **two independent descriptions that disagree**.
The file itself is well-behaved (`CREATE TABLE IF NOT EXISTS`, `USE knowledgemap;`, **no `DROP`** — unlike
the footgun in H5), but for that same reason it **cannot repair drift either**: it does nothing once the
table exists.

This is harmless today — all four columns have defaults and the ORM never writes `NULL` into them — but
the practical consequence is: **a machine that builds the database from scratch gets a *looser* table, so
those four `NOT NULL` constraints exist only on this machine.** To align them, add `nullable=False` to
those four columns in `app/tradesim/db/models.py`; that is a model-only change and does **not** ALTER the
live DB (nor is there any reason to — live is already the strict one).

Note also that the `Enum` columns store the **member names**, not the Chinese values: the DB holds
`expense` / `income`, `na` / `pending` / `done`, `category` / `subcategory` / … while the API and the rest
of this file speak `支出` / `收入` and `无需报销` / `待报销` / `已报销`. That is SQLAlchemy's default
`Enum` behaviour (it stores names unless you pass `values_callable`), **not a bug** — do not "fix" the
database to hold Chinese strings.

`bills` has **no index on `expense_date` / `expense_time`**, even though `list_bills` filters by the date
range and orders by exactly those columns (`crud/bill.py:46-67`, `ORDER BY … :63`). With 29 rows this is
irrelevant; recorded as a scalability note, **not a bug**. (`tags.parent_id`, `calendar_events.event_date`
and all four `simulation_records` indexes exist ✓.)

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
any page it was reused on. That is gone (docs/7 §2.21): page-level surface styles live in the
page (`Bills.vue`), and the component styles only its own canvas. `KnowledgeMapBackground.vue`
is the model to copy.

**There are now zero real `:global()` selectors in the frontend** (measured docs/7 §2.44 — the
three remaining `:global(` hits in the tree are all inside explanatory comments, and the earlier
"the only remaining one is worth a second look" is obsolete). Keep it at zero.

**The one unscoped `<style>` block in the whole frontend is `App.vue`'s.** There are 12 `<style>`
blocks across the 12 `.vue` files: 11 are `scoped` (including all four TradeSim views and the
TradeSim layout, which is what keeps TradeSim's light theme from leaking) and the exception is the
root component, whose block sets `html { scroll-behavior: auto }` (to hand scrolling to Lenis) and
the root `<Transition>`'s `.fade-*` classes. Neither can be scoped to a component, so this is
deliberate — but a *second* unscoped block anywhere else would be a boundary violation.

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
  `?tag_type=` filtering (verified by ID set, docs/7 §2.18) — which is why `loadTags()` makes
  two requests rather than four.
- `monthly_summary`'s amounts really are `number`s (the endpoint has a `response_model`, see
  docs/7 §2.14), so do not `parseFloat` them. `BillItem.amount` is a `string` by contrast.
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
off the FastAPI `app` object and matching them against `frontend/src/api/` — see docs/7 §2.24;
**re-counted verb by verb in §2.40**). The backend exposes 23 application routes; the frontend
calls 17 of them and never calls **six**:

- `GET /api/bills/{bill_id}` — unused, and **redundant** for the current UI: the list response
  already carries every field the edit modal needs.
- `PATCH /api/calendar-events/{event_id}` — **implemented but unreachable from the UI.** Events
  can be created and deleted, not edited, so fixing a typo means delete-and-re-add. This is the
  one backend-ready gap a future UI could close.
- `POST /api/tags/`, `PATCH /api/tags/{tag_id}`, `DELETE /api/tags/{tag_id}` — **there is no tag
  management screen at all.** `api/tags.ts` exposes exactly two methods (`GET /tags/`,
  `GET /tags/all`) and has **no write-request wrapper whatsoever** — so this is not merely a
  missing screen, the whole REST surface has no client. Tags change only via the
  `reseed_categories` script or SQL.
- `GET /api/health` — ops-facing, never called by the frontend by design. It always returns
  `{"status":"ok"}` **without touching MySQL or Mongo**, so it is a liveness signal only and must
  not be used as a readiness probe — it answers 200 with the database down.

⚠ This section previously said "all but **five**" and listed health only in the prose below,
which left the headline number one short. Both counts are now verb-level: every one of the other
17 routes has a matching call in `api/*.ts` (the five TradeSim ones are axios calls in
`api/tradesim.ts:19`/`:23`/`:27`/`:31`/`:35`, using `baseURL` or a raw `fetch` for SSE — which is
why a path-level matcher reports them as uncalled).

None of this is dead code and none of it was removed — a complete REST surface is defensible.
But do not assume "the endpoint exists, so the UI must use it".

### Frontend Bills.vue

- Month navigator (prev/next arrows, current month label)
- Day-grouped cards with expand/collapse, per-day income/expense totals
- Monthly summary bar (income / expense / net)
- Add / Edit modal via `<Teleport to="body">`, full form
- Subcategory dropdown auto-filters to children of selected category
- Payment fields hidden for 收入 records
- Delete confirmation dialog via Teleport

### Dashboard is not wired to the database — its numbers are placeholders

⚠ **Do not "fix" the Dashboard's numbers: they are static, by design** (owner's explanation,
2026-09-20). The home page renders a hard-coded `projects` array and hard-coded statistics —
`8` cards while the card face may read `18`, "本月记录 236 条", and so on. **None of that is
fetched from the backend**, so a mismatch against the real row counts is **not** a data bug,
not a stale cache, and not a display defect: the page has simply never been connected.

The consequences worth knowing before touching it:

- `GET /api/dashboard/git-stats/` **is** real (it shells out to git), and it is the one
  Dashboard number backed by live data.
- Everything else on that page is presentation. If you wire it up later, that is a **new
  feature**, and the placeholder values should be replaced in the same change rather than
  left as a fallback — a silent fallback to fake numbers is exactly how this kind of page
  becomes untrustworthy.
- Card status text is also presentation, but it must at least not contradict itself: card
  `06`「文档资料库」used to say `可进入` ("you can enter") while carrying `route: null`
  (nothing to enter). It now reads `等待接入`. Keep the two fields consistent.

### Theme toast position

The nav theme button's "功能待开发" toast is **horizontally centred at `top: 20%`** (viewport
upper-middle), not a corner — owner's request, 2026-09-20. Narrow screens (`≤720px`) use
`top: 14%`, and the width is capped at `min(21rem, calc(100vw - 2rem))`.

⚠ **The enter/leave transitions must use `translate(-50%, -14px)`** — the base rule already
uses `transform: translateX(-50%)` for centring, so an animation that only moves `translateY`
would drop the centring on its first frame and slide the toast in from the left edge. The
comment in `Dashboard.vue` says so.

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

**`strategy_params.grid_step_pct` is a PERCENT — `5` means 5%.** The engine converts it in
`grid_trade.py`'s `_percent_to_ratio()` and both of its error messages say so ("例如 5 表示
5%"). Established by a control experiment on one dataset (`000400`, 2024, 242 bars,
`lower_bound=20 / upper_bound=30`) holding everything else fixed — and **re-measured
2026-09-20 with an independent instrument, the live HTTP API** (docs/7 §2.39), which is why
the numbers below differ from the first version of this paragraph:

| `grid_step_pct` | grid nodes | completed cycles | `win_rate` | `total_trades` |
|---|---|---|---|---|
| `5` (percent, correct) | 9 | 27 (all profitable) | **1.0** | 57 |
| `0.05` (ratio, mistyped) | 812 | 75 (all losing) | **0.0** | 155 |

So a `win_rate` of 0 is not an engine bug — it is the correct answer to a mistyped unit. The
loss mechanism was re-confirmed from the response's own `execution_records`:
`slippage_cost = volume × 0.01`, so one completed cycle (one buy + one sell) loses exactly
`volume × 0.02` (8.00 for 400 shares); the measured total grid slippage was 509.00 over 75
cycles = 6.79 per cycle, matching the 300–400 share range.

⚠ **Record the parameters with any control experiment.** The first version of this paragraph
cited 11 / 103 / 1023 nodes and 13 cycles without stating the bounds; those numbers are not
reproducible (they imply `lower_bound ≈ 18`), and a re-measurement at 20/30 gives 9 / 82 / 812.
Also note `metrics.total_trades` counts **grid trades only** — `BASE_OPEN` is excluded
(`docs/2:137`), so 30 buys + 27 sells = 57, which is *not* the cycle count.

⚠ **All six saved records carry the OLD unit (`0.05`, i.e. a ratio)** — they were created
2026-02-21…04-28, before `grid_trade.py` entered this repository (`d7d90eb`, 2026-08-13), so
their metrics are snapshots from the pre-migration engine and are **not reproducible by
today's engine** without converting that parameter. `TradeSimDetail.vue:182` still uses the
old semantics (`currentGrid *= (1 + value)`, no `/100`), and that array **is** consumed by the
price chart's `markLine` (`:239`) — so the overlay is correct for the old records by accident
and draws a **single line** for any newly saved record. The simulator's two previews do divide
by 100 (`TradeSimSimulator.vue:55`, `:123`).

**The numbers that decision actually turns on** (rebuilt 2026-09-20 from each record's own
`strategy_params`, docs/7 §2.39 — measured, not estimated):

| id | symbol | range | `grid_type` | markLines today | if `/100` were applied blindly |
|---|---|---|---|---|---|
| 1 / 3 | 000400 / 600585 | 15–25 | geometric | 11 each | 1023 each |
| 2 | 000400 | 15–35 | geometric | 18 | 1696 |
| 4 / 5 | 600585 | 10–50 | **arithmetic** | 21 each | **21 each — unaffected** |
| 6 | 600585 | 10–50 | geometric | 33 | 3220 |
| | | | **total** | **115** | **7004** |

Two things that are easy to get wrong here: **records 4 and 5 use `grid_type: "arithmetic"`,
so their node count comes from `grid_count` and the unit question does not apply to them at
all** (only 4 of the 6 records are affected); and **none of the six uses a 20–30 range**, so a
synthetic 20/30 experiment does not describe them.

✅ **Resolved 2026-09-20 (owner's decision).** `TradeSimDetail.vue` now branches on the value
instead of assuming a unit: `rawStep >= 1` is treated as a **percent** and divided by 100,
anything below 1 is already a ratio and used as-is. Measured effect: the six old records keep
exactly the same overlay — **115 markLines before and after, record by record** — while a
newly saved record (`grid_step_pct: 5`) now draws the same 11 lines as `0.05` instead of a
single line. Do **not** revert this to an unconditional `/100`: that is the 7004-line outcome
in the table above, and the branch is what makes both eras readable by one page.

**`max_drawdown` may legitimately exceed 1.0 — this is the intended 口径, not a bug.** The
formula is `(peak - net_value) / peak`, so once the net value is driven **negative** the result
is necessarily > 1. Measured across the six saved records: only one record, **11 points**,
maximum **1.0452**. Both the formula site (`strategy/base.py`) and the `max(...)` site
(`strategy/specific/grid_trade.py`) carry a comment saying so. **Do not add `min(x, 1.0)` or
clamp it in the UI** — a "drawdown above 100%" is exactly the information that a blown-up
account produces, and hiding it would defeat the metric.

**Base position: opened once, and never added to afterwards.** `grid_trade.py` keeps
`self.base_position_opened`; `execute()` builds the base position only while that flag is
`False`. The owner chose this 口径 explicitly over the alternative ("a break below
`lower_bound` should trigger a stop-loss"): **a break below the lower bound is not a stop
signal, it is simply outside the grid.** Measured with six bars all below `lower_bound`: the
old code *retried* on every bar (2 fills at `base_position_ratio=0.5` — it runs out of cash
after two — and 6 fills at 0.1, i.e. one per bar), the current code opens exactly **1**.
The comment at both sites says this in one line so it is not "fixed" back later.

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

**The portal↔TradeSim seam is exactly one file.** Measured with an AST/regex pass over the real
imports (docs/7 §2.44): **no portal file imports anything from `features/tradesim/`**, and the
only places *outside* the module that mention it are `main.ts`'s five route-registration sites
(`:54`, `:63`, `:68`, `:73`, `:78` — the lazy imports plus the route records). In the other
direction the module imports exactly nine external specifiers — `vue`, `vue-router`,
`element-plus`, `@element-plus/icons-vue`, `echarts`, `marked`, `dompurify`, its own
`@/api/tradesim`, and the shared `@/components/KnowledgeMapBackground.vue`. Nothing else crosses.
Backend side the same holds: AST-scanning every `app/tradesim/**/*.py` for `app.*` imports finds
**exactly two** — `app.database` (`api/v1/records.py:8`) and `app.models.bill` (`db/models.py:3`)
— and zero reverse imports from the portal. And the module graph has **no import cycles**
(39 modules, 34 edges, 0 cycles of length > 1). Treat any new crossing edge as an architecture
change, not a convenience.

⚠ **Element Plus is registered globally, and every TradeSim component silently depends on that.**
`main.ts:3-5` together with `:86-87` do `app.use(ElementPlus)`, register **all 293 icons** from
`@element-plus/icons-vue`, and import the full `element-plus/dist/index.css`. Measured
2026-09-20 (docs/7 §2.40, after an earlier truncated scan under-counted it) — what that global
registration is actually providing:

| Provided by the global registration | Count | Where |
|---|---|---|
| `el-*` components | **28 kinds / 150 usages** | all in the 5 TradeSim `.vue` files |
| icons, tag form (`<Cpu />`) | **9** | `ArrowLeft` `ArrowRight` `Cpu` `DataLine` `Loading` `Monitor` `Star` `TrendCharts` `Trophy` |
| icons, string form (`:icon="'Back'"`) | **2** | `TradeSimDetail.vue:283`, `TradeSimDashboard.vue:50` |
| the `v-loading` directive | **2 usages** | `TradeSimDetail.vue:279`, `TradeSimDashboard.vue:55` |

The portal's 7 `.vue` files use **zero** `el-*` tags and zero icons, so the entry bundle
(`index.css` 389.64 kB + `index.js` 1,163.78 kB, ≈**368 kB gzip on every page load**) is paid
entirely for TradeSim. (`QuestionFilled` is the one icon already imported locally, in
`TradeSimSimulator.vue:4`, so it does not depend on the global registration.)

Two traps if Element Plus is ever made on-demand: a **string** `:icon` is resolved *through the
global registration*, so importing `Back` locally is not enough — `:icon="'Back'"` must also
become `:icon="Back"`; and **`v-loading` is a directive, not a component**, so it simply
disappears. All three categories live in those same five files, which is what makes the
"a missed import renders as a blank spot, warned about in dev but **silent in a production
build**" risk **machine-checkable**: assert that every `el-*` and icon tag in each root template
is imported in that same file, that no `:icon="'…'"` string form remains, and that `v-loading` is
either absent or its directive registered. Do not verify this by eye alone.

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

| File | Role | Lines |
|---|---|---|
| `AGENTS.md` (this file) | **Single source of truth for AI/human contributors.** `CLAUDE.md` is only a pointer to it — edit this file, not that one. | 851+ |
| `docs/1_前端界面背景与特效整理.txt` | Living register of background/animation effects. Log UI-effect changes here. | 312 |
| `docs/2_交易策略模块的完善.txt` | Historical archive (2026-08-14). Read the banner at its top for the falsified claims. | 252 |
| `docs/3_KnowledgeMap集成TradeSim正式迁移计划.txt` | Historical migration record. Read the banner at its top for superseded claims. | 495 |
| `docs/4_项目整理审计与清理计划.txt` | **Frozen audit baseline** — findings H1–H9 / M1–M17, batch plan, deletion-safety proofs. **Do not edit.** | 756 |
| `docs/5_清理执行日志与工作汇报.txt` | **Conclusions and the decision sheet** — one-page index, measured-evidence summary, the A/B/C decision list. It used to be the chronological log too. | ~832 |
| `docs/6_当前状态与待决策.txt` | ⭐ **Read this first.** Short current-state page plus the open choices (group B). **Rewritten in place, never appended** — that is what keeps it short. | ~190 |
| `docs/7_工作记录（时间线）.txt` | The full chronological work log (was `docs/5` §2, ~2.6k lines = 78% of that file). Verbatim copy; read it by section number, not linearly. | ~2,600 |

**Why the docs were split (2026-09-20, owner's request).** Measured before the split:
`docs/5` had grown to **3,317 lines, of which §2 alone was 2,576 (78%)** — the log had buried
the conclusions it was supposed to support, while the parts a human actually reads (§0, §3–§9,
§13–§17) were only ~700 lines. So §2 was extracted verbatim to `docs/7`, `docs/5` kept the
conclusions, and `docs/6` was added as the short always-current page. Rule going forward:
**append to `docs/7`; rewrite `docs/6`; update the conclusions in place in `docs/5`.**

⚠ **`§2.x` citations now live in `docs/7`, not `docs/5`** — 53 references across
`AGENTS.md`, `todolist.txt`, `docs/1` and `docs/3` were rewritten accordingly and verified
(0 broken links of 199 cross-document references, checked mechanically). `docs/5` no longer has
a second section; bare `§N` mentions *inside* `docs/7` are original text and refer to `docs/5`
chapters — including deliberate quotations of citations that were wrong when written. Read the
banner at the top of `docs/7` before "fixing" any citation you find there.

⚠ **Line-number references into `docs/1`–`docs/3` are stale.** Those documents were edited in
2026-09 (a banner was prepended to `docs/2` / `docs/3`, and `docs/1` gained sections), which
pushed every line down by a *different* amount depending on where the insertion landed. So the
`docs/N:123` references inside the **frozen** `docs/4` — correct when written — now point at
blank lines or unrelated content, and no single offset fixes them (measured: `docs/2` shifted by
exactly +19; `docs/1` by +35 at line 11 but +80 by line 130; docs/7 §2.39 has the full old→new
mapping table). References into the frozen `docs/4` itself are still exact — that is the control
case. **When you edit a document that other documents cite by line number, fix the citations in
the same commit** — or cite sections (`§2.39`) instead of lines, which is what this file does.

## Dead code and "unused" things (measured — none of it is dead)

Audited 2026-09-20 with fresh instruments (docs/7 §2.45). **This project has no dead code.**
Everything below looks unused to a naive scan and is deliberate — read this before deleting.

- **Backend: 0 dead functions out of 81.** The one candidate — `_register_mysql_date_functions`
  (`tests/portal_crud_cases.py:45`) — is registered with `@event.listens_for(engine, "connect")`,
  so SQLAlchemy calls it and source code never mentions it again. ⚠ **A callback registered via a
  decorator or registry can never look "called"** — any zero-reference list must subtract route
  handlers, validators, `property`, event listeners and fixtures first, or it reports all of them.
- **Frontend: 0 symbols are entirely unused; 9 exports have no consumer in another file** —
  `API_BASE` (`api/client.ts:19`) and `TRADESIM_API_BASE` (`api/tradesim.ts:10`) (both used inside
  their own file; the owner decided to keep them exported), five types in `types/tradesim.ts`
  (`TradeSimStrategyParams`, `EquitySnapshot`, `StoredEquitySnapshot`, `TradeRecord`,
  `SimulationMetrics`), `WeatherForecast` (`types/portal.ts:149`, composed into `WeatherInfo`) and
  `padDatePart` (`utils/date.ts:25`, used by `dateToKey`). Exporting a module's public types is
  normal; deleting them buys nothing.
- **CSS: 88 custom properties, 82 consumed.** The 6 unread ones are all deliberate: `--card-title`
  and `--card-footer-text` live inside `.theme-light` (`main.css:81`), `--color-accent` /
  `--color-accent-light` are the light-theme-only `@theme` aliases described under "Theme", and
  `--reference-muted` (`Notes.vue:1618`) is one member of the coherent `--reference-*` token set
  (`:1617-1621`) whose siblings *are* used. ⚠ **Do not judge `@theme` tokens by `var()` usage** —
  Tailwind v4 consumes them by *generating utility classes* (`--color-surface` → `bg-surface`),
  so a `var()`-only scan wrongly reports most of the live palette as unused (it claimed 27; the
  real number is 6). Likewise `--el-menu-*` (`TradeSimLayout.vue:122-126`) is read by Element
  Plus's own stylesheet, not by our CSS.
- **`@keyframes`: 4 kinds / 5 definitions, all referenced** (`waterfall-fade` `main.css:178`;
  `fadeIn` defined twice — `Dashboard.vue:3500` and `TradeSimDashboard.vue:122` — which is fine
  because both are `scoped`; `cal-dot-pulse` `Dashboard.vue:1727`; `pulse` `Notes.vue:864`).
- **Assets: 6 files under `frontend/public/`, 0 unreferenced.** ⭐ All five images in
  `public/images/` are referenced **only by `/vault`**: `pic1-3.png` via `Vault.vue:54-56`'s data
  array, `pic4.gif` as the avatar (`:71`), and **`pic5.jpg` (906,859 B — the largest file in
  `public/`) as a CSS background at `Vault.vue:429`**. Because that rule sits in Vault's `scoped`
  style, the home page and every other route never request it. (The 443 KB `pic6.jpg` seen in the
  git history no longer exists on disk — see the `.git` note above.)

## Repository hygiene (leftovers, line endings, object store)

Measured 2026-09-20 (docs/7 §2.43). **The owner's ruling on these archives is: keep them where they
are, and record them** — so none of this is a to-do list, it is a map of what is deliberately there.

**Line endings: the working tree is CRLF, the blobs are LF.** `core.autocrlf=true` is set in the
**local** repo config and there is **no `.gitattributes`**. Consequence: for any text file the
working-tree bytes differ from the stored bytes (measured on
`.claude/skills/design-taste-frontend/SKILL.md`: 88,459 B on disk vs 87,253 B in the blob — the
difference is exactly its 1,206 CRLFs). ⚠ **Any content hash or byte comparison must normalise line
endings first** (use `git cat-file blob`, or convert `\r\n`→`\n`), or the same unchanged file yields
two different sha256 values. The LF→CRLF warnings that `git commit` prints are this, not corruption.

**Tracked leftovers that are not part of the app:**

| Path | Size | What it is |
|---|---:|---|
| `frontend_example/` | 20 files, 2.25 MB | **Two prototypes from before the rewrite**: a Transformer learning-map at the top level and a static prototype under `看这个！/`. **5 files are byte-identical between the two** (`tex-mml-chtml.js` 997 KB, `app.js`, `marked.min.js`, `styles.css`, `index.html`) ⇒ **1.10 MB of the 2.25 MB is pure duplication**, and deduplicating would cost no content. Its `看这个！/README.md` tells you to serve on **port 8000, which on this machine runs a different project** (`yb_reconcile_demo`) — that is why the backend lives on 8010. |
| `20260625/` | 4 files | Dated (2026-06-25) design plans, badly stale. |
| `tp2.txt` | 2,815 B | Prompt scratch, tracked but unrelated to this project. (`tp.md` is the untracked counterpart.) |
| `skills-lock.json` | 284 B | Lock for the agent skill pack. **Resolved:** its `computedHash` (`899b8438…`) is **not** a content sha256 of anything local *or* upstream — the installed `SKILL.md`'s LF content is byte-identical to `Leonxlnx/taste-skill@main` (`aa194351…`), so the lock must use a non-content scheme. No install needed to close this. |

**Ignored but on disk (311 MB)** — verified as correctly ignored (0 tracked files in
`frontend/dist/` and `frontend/node_modules/`): `node_modules/` 238 MB, `.pnpm-store/` 41.8 MB,
`.npm-cache/` 9.3 MB, `tmp_screenshots/` 8.7 MB, `UI预览图/` 5.75 MB, `frontend/dist/` 4.0 MB.
⚠ **Do not delete `.pnpm-store` / `.npm-cache`**: removing them breaks nothing but forces the next
install to re-download everything. `UI预览图/` is the owner's design baseline and is **not in git** —
it exists only on this machine.

**The object store has never been packed:** `.git` is 34.13 MiB with `packs: 0` — 2,892 loose
objects plus **2,144 dangling blobs** (from repeatedly staging and rewriting files). A `git gc`
would shrink it, but it also **irreversibly prunes those dangling objects**, so it is deliberately
left to the owner and is *not* on the decision sheet (the only benefit is disk space). Single branch
`master`, 0 tags, 0 stashes, 124 tracked files.

## Development notes

- **Never take "today" with `new Date().toISOString().slice(0, 10)`** — `toISOString()` is
  always UTC, and in UTC+8 that returns **yesterday** between local 00:00 and 07:59 (8 hours
  of every day). This was a real bug in `Bills.vue`'s default `expense_date`. Use `todayKey()`
  / `dateToKey()` from `src/utils/date.ts` instead.
- Pure frontend helpers can be tested with no test runner at all — **use the PowerShell form**:
  `$env:TZ='Asia/Shanghai'; node --experimental-strip-types path/to/helper.ts`
  executes the real file (Node 22.17). Used to verify `utils/date.ts` — see docs/7 §2.20.
  ⚠ The bash form `TZ=Asia/Shanghai node …` **does not work in this project's shell**:
  PowerShell tries to execute a program literally named `TZ=Asia/Shanghai` and dies with
  「术语 'TZ=Asia/Shanghai' 不会被识别为 cmdlet…」, running nothing at all (verified 2026-09-20).
  This was the only documented way to test a pure helper, so it failed for anyone who copied it
  verbatim.
- IDE "Cannot find module" errors in backend files are **false positives** — the IDE interpreter is not set to the `desheng` conda env. Code runs fine from the terminal. Fix: set interpreter to `C:\Users\afrangry\anaconda3\envs\desheng\python.exe` in VS Code or PyCharm.
- `conda` is not on PATH in a plain PowerShell session. Either `conda activate desheng` in a
  conda-initialized shell, or call the interpreter by absolute path (above) for one-off commands.
  ⚠ **Bare `python` is a trap on this machine** — it resolves to the Microsoft Store stub
  (`…\AppData\Local\Microsoft\WindowsApps\python.exe`), which runs nothing and exits **9009**
  with "Python was not found; run without arguments to install from the Microsoft Store…"
  (verified 2026-09-20). So every `python …` recipe in this file — `python main.py`, the two
  test runners, the re-seed snippet — is valid **only after** `conda activate desheng`. If you
  see that Store message, you skipped it; do not read it as a missing dependency.
- Do **not** run `npm install` — it triggers semgrep-core-proprietary.exe and slows the IDE.
  Hand it to the user unless they have explicitly authorised it for the session.
- `npm run build` **has been verified** (2026-09-20): it passes and emits `frontend/dist/`.
  The previous note here claiming it "has never been verified in this environment" is
  obsolete. `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit` — **run it from `frontend/`**;
  the path is relative, so from the repo root it exits 1 with a module-not-found (verified
  2026-09-20) — is the cheap gate for type errors and needs no dev server.
- Vite's dev server binds **IPv6 `::1` only** — `127.0.0.1:3000` refuses connections; use
  `http://localhost:3000`. In PowerShell, `Invoke-WebRequest` against a local server needs
  `-NoProxy`, otherwise the request goes through the local proxy and returns 502.
- Frontend dev server runs on `:3000`; CORS is whitelisted for `http://localhost:3000` in `main.py`.
- `main.ts` uses `createWebHistory()`. **Measured 2026-09-20 against the real `frontend/dist/`
  (docs/7 §2.39): a plain static server breaks every deep route.** Serving `dist/` with
  `python -m http.server` returns 200 for `/` but **404 for `/bills` and `/tradesim/simulate`**,
  while `vite preview` returns the SPA's `index.html` (200) for all three. Note the trap: in-app
  navigation still works without server support (`history.pushState`), so this only shows up on a
  **refresh, a bookmark or a shared direct link**. Any production deploy must configure the
  fallback (or switch to hash history). Vite's **preview** server binds IPv6 `::1` only, exactly
  like the dev server — `http://localhost:4173/…` works, `http://127.0.0.1:4173/…` is refused.
  No production deploy exists yet.
- Root-level `tp.md` is an unrelated scratch dump left in the working tree, untracked on purpose.
  Not part of the project.
