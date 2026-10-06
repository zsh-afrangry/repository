# KnowledgeMap — AGENTS.md

> **Current Linux checkout (2026-10-03):** See `docs/11_Linux本机启动.md`. This host uses Miniconda `desheng` Python 3.12.14, system MySQL and user-service MongoDB. Windows paths and old local runtime observations below are historical, not this host configuration.

Personal portal aggregating all side-projects under one unified dashboard. Each project gets a card on the dashboard; clicking it navigates to that project's dedicated page.

**Current scope (2026-10-04):** TradeSim is frozen pending full requirements and domain decisions. Portal home/bills close-out is complete within the verified scope. Notes agreed scope is implemented and ready for owner acceptance: overview, topic/section management, same-topic DAG dependencies, deep links, shared-MySQL persistence and composable visuals. Contract and verification: `docs/13_Notes学习模块功能与视觉开发方案.md` §11–13. Portal verification: `docs/12_首页与账单收尾验收.md`.

**Current documentation entry:** `docs/0_README.md`. Root `todolist.txt` is the sole execution-status source, using stable D/E/V/P IDs. `docs/9_文档核查与交接遗留清单.md` records the code-backed audit and corrects older claims; historical measurements below are dated evidence, not proof that all current behavior is correct. Follow current task status and audit evidence when they supersede an archived conclusion.

## Repository layout

Two layout conventions coexist by design. The portal's own code is grouped **by layer**
(`models/`, `schemas/`, `crud/`, `routers/`); each integrated project is a self-contained
**feature module** (`app/tradesim/`, `features/tradesim/`). Add new projects as feature
modules, not as new files in the by-layer directories.

```
KnowledgeMap/
├── docs/             # active docs + 历史设计原稿/20260625/; see "Documentation"
├── 已归档/           # historical docs 2/3/4/5/7 + 整理前快照/
├── todolist.txt      # sole execution-status ledger, stable D/E/V/P IDs
├── backend/          # FastAPI app (Python)
│   ├── main.py       # Sole entry point — `python main.py` starts uvicorn on :8010
│   ├── requirements.txt
│   ├── tests/
│   │   ├── tradesim_grid_strategy_cases.py   # plain-python runner, 8 cases
│   │   └── portal_crud_cases.py              # plain-python runner, 13 cases, in-memory SQLite
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
            └── Notes.vue     # Notes overview/workspace/reader entry (legacy routes redirect)
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
output: 已归档/7 §2.30.

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

**Frontend dependency state (verified 2026-09-20).** `frontend/package.json` and
`frontend/package-lock.json` agree on the declared dependency set; `github-markdown-css` is
not a runtime dependency. TradeSim markdown styling is provided by the vendored,
namespaced `features/tradesim/styles/tradesim-markdown.css`. Do not reintroduce the upstream
global stylesheet or treat the old lockfile observation as a current defect.

⚠ **When scanning `.vue` files for imports or code patterns, scan the `<script>` blocks only —
never the whole file.** `Notes.vue` renders full-length markdown *articles*, and their fenced
code samples contain real-looking code: a naive full-text grep for `from '…'` finds
`import lodash from 'lodash'` / `import { cloneDeep } from 'lodash-es'` inside a Vite
bundle-optimisation tutorial on line 31, and reports two undeclared dependencies that do not
exist. The same trap applies to `.vue` comments and template text.

⚠ Historical Windows installation issue: `HTTP_PROXY`/`HTTPS_PROXY` pointed to a proxy that could not reach PyPI, so a plain
`pip install` hangs with no output. If that issue recurs, use the Tsinghua mirror and clear those two
variables for that command:
`python -m pip install <pkg> -i https://pypi.tuna.tsinghua.edu.cn/simple`

Alembic is listed in `requirements.txt` but **deliberately not used** — schema comes from
`Base.metadata.create_all()`. Decision recorded in
`已归档/3_KnowledgeMap集成TradeSim正式迁移计划.txt` §13; revisit only if schema churn increases.

## Running the project

**Backend** — `KM_BACKEND_PORT` overrides the port, default `8010`.
```bash
conda activate desheng
cd backend
python main.py          # starts uvicorn on http://127.0.0.1:8010 with --reload
```

**Remote launcher (2026-10-04):** Root `Start-KnowledgeMap.sh` / `Stop-KnowledgeMap.sh`
manage an independent authenticated web service on port 8020 via the same `backend/main.py`
entry point. Default mode binds `127.0.0.1` and uses Tailscale Serve HTTPS 8443; `--lan`
explicitly binds `0.0.0.0:8020`. `KM_WEB_CONFIG` enables access-key authentication through
one-click fragment links (`/_km/login#key=…`) that establish an HttpOnly/SameSite session
cookie (Secure on HTTPS); HTTP Basic (username `km`) remains supported. Authentication
covers the SPA, static assets, API and docs; only the login bootstrap is public. The
launcher builds a private frontend snapshot with SPA fallback; credentials stay outside Git.
LAN HTTP has no TLS and is for trusted networks only. See `docs/11_Linux本机启动.md` for
commands, sudo requirements and verification limits. DSH's HTTPS 443 mapping is reserved;
never use `tailscale serve reset` or Funnel in these scripts.

**Manual development remains loopback-only and unauthenticated** on 8010/3000. Never expose
those development listeners directly; CORS is not authentication. The remote launcher has
its own service and must not kill existing development processes or databases when stopped.

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

⚠ **`create_all()` never ALTERs an existing table.** The live `simulation_records` table was
originally created from `表结构/tradesim.sql`; its four formerly divergent nullability
constraints are now also declared in `app/tradesim/db/models.py` (`nullable=False`). A fresh
schema therefore uses the same nullability contract. Existing tables still require explicit
migration for any future structural change; `create_all()` does not perform that migration.

Note also that the `Enum` columns store the **member names**, not the Chinese values: the DB holds
`expense` / `income`, `na` / `pending` / `done`, `category` / `subcategory` / … while the API and the rest
of this file speak `支出` / `收入` and `无需报销` / `待报销` / `已报销`. That is SQLAlchemy's default
`Enum` behaviour (it stores names unless you pass `values_callable`), **not a bug** — do not "fix" the
database to hold Chinese strings.

`bills` has **no index on `expense_date` / `expense_time`**, even though `list_bills` filters by the date
range and orders by exactly those columns (`crud/bill.py:46-67`, `ORDER BY … :63`). With 29 rows this is
irrelevant; recorded as a scalability note, **not a bug**. (`tags.parent_id`, `calendar_events.event_date`
and all four `simulation_records` indexes exist ✓.)

On the original Windows machine, a legacy standalone `tradesim` MySQL database held the
pre-migration copy of those 6 records. It was unused by the app and retained as a
rollback source on that machine — do not point code at it.

## Design system

Notes module tokens now live in `frontend/src/features/notes/styles/theme.css` (scoped page import; docs/13 §10). The old `--reference-*` names have been replaced by semantic `--notes-*` names; historical inventory below does not describe their current names. Shared defaults remain in `styles/main.css`, with local `--ui-*` hooks for common controls.

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
any page it was reused on. That is gone (已归档/7 §2.21): page-level surface styles live in the
page (`Bills.vue`), and the component styles only its own canvas. `KnowledgeMapBackground.vue`
is the model to copy.

**There are now zero real `:global()` selectors in the frontend** (measured 已归档/7 §2.44 — the
three remaining `:global(` hits in the tree are all inside explanatory comments, and the earlier
"the only remaining one is worth a second look" is obsolete). Keep it at zero.

**The one unscoped `<style>` block in the whole frontend is `App.vue`'s.** There are 12 `<style>`
blocks across the 12 `.vue` files: 11 are `scoped` (including all four TradeSim views and the
TradeSim layout, which is what keeps TradeSim's light theme from leaking) and the exception is the
root component, whose block sets `html { scroll-behavior: auto }` (to hand scrolling to Lenis) and
the root `<Transition>`'s `.fade-*` classes. Neither can be scoped to a component, so this is
deliberate — but a *second* unscoped block anywhere else would be a boundary violation.

## Notes module

`frontend/src/features/notes/` owns graph, reader dialog, prose, navigation/draft state and theme; `api/notes.ts` uses apiFetch. `backend/app/notes/` uses the shared Base and database session. Topic JSON aggregates in `notes_topics` commit all content/sections/edges atomically using an optimistic version; stale writes return 409. Edges are scoped to their enclosing topic, validate membership and a DAG, and are never inferred from adjacent directories. Nonempty containers cannot be cascade-deleted. Seed marker `notes_seed_versions` prevents restarts overwriting edited/deleted seed content; preserve both Notes tables in backups. Initial 31 units include four otherwise orphaned legacy articles in a separate retained topic. Details/limits: docs/13 §11.

Markdown now uses existing marked + DOMPurify, then scoped NotesProse. No math renderer was added. Historical Notes parser/line-number statements elsewhere in this file describe the previous implementation. Test scripts: backend/tests/notes_cases.py (isolated), notes_browser_server.py (disposable SQLite API), notes_mysql_smoke.py (explicit opt-in live temporary topic); frontend/tests/notes-browser.cjs and notes-layout.cjs.

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
  `?tag_type=` filtering (verified by ID set, 已归档/7 §2.18) — which is why `loadTags()` makes
  two requests rather than four.
- `monthly_summary`'s amounts really are `number`s (the endpoint has a `response_model`, see
  已归档/7 §2.14), so do not `parseFloat` them. `BillItem.amount` is a `string` by contrast.
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
off the FastAPI `app` object and matching them against `frontend/src/api/` — see 已归档/7 §2.24;
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

### Dashboard project statistics are placeholders; calendar, weather and Git use live requests

⚠ **Do not "fix" the Dashboard's numbers: they are static, by design** (owner's explanation,
2026-09-20). The home page renders a hard-coded `projects` array and hard-coded statistics —
`8` cards while the card face may read `18`, "本月记录 236 条", and so on. **None of that is
fetched from the backend**, so a mismatch against the real row counts is **not** a data bug,
not a stale cache, and not a display defect: the page has simply never been connected.

The consequences worth knowing before touching it:

- `GET /api/dashboard/git-stats/` **is** real (it shells out to git), and its commit counters are live. Calendar and weather also use backend requests; the project-card statistics remain static.
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
Full migration record: `已归档/3_KnowledgeMap集成TradeSim正式迁移计划.txt`.

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

**Data sources.** Daily bars use a 东财 → 新浪 → 腾讯 fallback chain. The backend also accepts `5min`/`1min` and provides a 东财 → 新浪 intraday fallback. **The UI currently exposes only daily bars:** the two minute-frequency options in `TradeSimSimulator.vue` are inside an HTML comment. Backend reachability does not mean the feature is available from the UI. Eastmoney connectivity failures recorded in the archive are historical network observations, not a permanent availability guarantee.

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
2026-09-20 with an independent instrument, the live HTTP API** (已归档/7 §2.39), which is why
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
(`已归档/2:137`), so 30 buys + 27 sells = 57, which is *not* the cycle count.

⚠ **The six records in the original Windows audit carry the OLD unit (`0.05`, i.e. a ratio)** — they were created
2026-02-21…04-28, before `grid_trade.py` entered this repository (`d7d90eb`, 2026-08-13), so
their metrics are snapshots from the pre-migration engine and are **not reproducible by
today's engine** without converting that parameter. `TradeSimDetail.vue:182` still uses the
old semantics (`currentGrid *= (1 + value)`, no `/100`), and that array **is** consumed by the
price chart's `markLine` (`:239`) — so the overlay is correct for the old records by accident
and draws a **single line** for any newly saved record. The simulator's two previews do divide
by 100 (`TradeSimSimulator.vue:55`, `:123`).

**The numbers that decision actually turns on** (rebuilt 2026-09-20 from each record's own
`strategy_params`, 已归档/7 §2.39 — measured, not estimated):

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

**Partial compatibility fix, 2026-09-20 (owner's decision); D2 remains open for new steps below 1%.** `TradeSimDetail.vue` now branches on the value
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
deliberately **not** deleted (see the Mongo decision in `已归档/5`), so the *read* schema is the
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
imports (已归档/7 §2.44): **no portal file imports anything from `features/tradesim/`**, and the
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
2026-09-20 (已归档/7 §2.40, after an earlier truncated scan under-counted it) — what that global
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

✅ **Resolved 2026-09-20 (was 已归档/4 finding H1).** TradeSim's markdown used to be styled by
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

`features/notes/components/NotesProse.vue` now owns Notes typography and scoped markdown
surface defenses (docs/13 §9). Its root and table rows have explicit transparent backgrounds;
links, quotes, code and table styles are local. `Notes.vue` supplies module palette variables.
Keep these styles scoped and do not reintroduce global markdown styles.

All requests go through `api/tradesim.ts` at the relative base `/api/tradesim/v1`.
Never hardcode a backend host; the Vite proxy handles it.

### Tests

```bash
conda activate desheng
cd backend
python tests/tradesim_grid_strategy_cases.py    # plain runner, expects 8 PASS
python tests/portal_crud_cases.py               # plain runner, expects 13 PASS
```

Not pytest — both are standalone scripts that print `PASS`/`FAIL` and exit non-zero on failure.

- `tradesim_grid_strategy_cases.py` covers grid cycles, multi-grid crossings, insufficient
  cash, commission/slippage, base position and invalid params.
- `portal_crud_cases.py` contains thirteen **bill CRUD, monthly-summary, PATCH validation and pagination** cases using in-memory SQLite. Tags are fixture data; tag/calendar CRUD and HTTP-level behavior are not covered by these cases. Passing both runners does not close the audit's storage, chart or strategy-boundary findings; track missing coverage in root `todolist.txt`.

⚠ `portal_crud_cases.py` runs against an **in-memory SQLite** database, never MySQL — the
original Windows machine's MySQL held real bill data, and these cases insert and delete rows. Two dialect
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

Start with `docs/0_README.md`. Technical conventions live in this file; `CLAUDE.md` is an entry pointer. **Root `todolist.txt` is the only execution-status ledger**, with stable D/E/V/P task IDs.

| Location | Role and update rule |
|---|---|
| `docs/0_README.md` | Current document navigation and reading order. |
| `docs/1_前端界面背景与特效整理.txt` | Current background/effect register; update implementation boundaries in place and reference task IDs for outstanding work. |
| `docs/6_当前状态与待决策.txt` | Concise current-state summary; rewrite in place, link to root TODO rather than duplicate task status. |
| `docs/8_交接说明.txt` | Current handover and running guide; update in place. |
| `docs/9_文档核查与交接遗留清单.md` | Code-backed audit evidence and verification limits; execution progress belongs in root TODO. |
| `docs/11_Linux本机启动.md` | Current Ubuntu runtime, startup and dated verification evidence. |
| `docs/10_早期界面设计整理.md` | Comparison of early design intentions with current implementation. |
| `docs/历史设计原稿/20260625/` | Four original design files moved from root `20260625/` with explicit user authorization; historical source material, not an active task list. |
| `已归档/0_README.md` | Archive navigation and historical path mapping. |
| `已归档/2_交易策略模块的完善.txt` | Historical strategy analysis; retained requirements are tracked by current TODO IDs. |
| `已归档/3_KnowledgeMap集成TradeSim正式迁移计划.txt` | Historical integration plan. |
| `已归档/4_项目整理审计与清理计划.txt` | Frozen audit baseline; preserve the original content. |
| `已归档/5_清理执行日志与工作汇报.txt` | Historical stage report and decisions. |
| `已归档/7_工作记录（时间线）.txt` | Archived timeline; **do not append new work here**. |
| `已归档/整理前快照/` | Pre-reorganization copies of documents 1/6/8 and the old root TODO. Read these when following old chapter references. |

Keep active documents concise: replace obsolete current-state text instead of adding contradictory corrections below it. Record task status and completion evidence against stable IDs in root `todolist.txt`; use the effect register or a focused evidence document for supporting detail. Do not restart the archived timeline or maintain a second execution checklist in documents 6/8/9/10.

Historical references use the same document number under `已归档/` for 2/3/4/5/7. Old chapter references to documents 1/6/8 map to their matching originals in `已归档/整理前快照/`, not to the rewritten active pages. Historical `§2.x` timeline entries belong to archive 7; archive 5 contains the stage conclusions. Archived text may retain old paths and erroneous claims as evidence: consult the archive index and current audit instead of rewriting the frozen originals. Prefer task IDs or section names to moving line numbers.

Secrets (`backend/.env`), MySQL row data and MongoDB documents are not carried by Git. Same-machine handover uses the existing local data; a new-machine move requires appropriate configuration and both databases. Missing credentials or an unreachable database can prevent startup because lifespan runs schema creation and tag seeding. Follow the current handover guide rather than treating historical row counts or a successful health probe as readiness guarantees.

## Dead code and "unused" things (measured — none of it is dead)

Audited 2026-09-20 with fresh instruments (已归档/7 §2.45). **That historical scan found no unintended dead code; it is not a permanent guarantee.**
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

Historical inventory: 2026-09-20 (已归档/7 §2.43). Retain unrelated archives and caches unless a current request authorizes a change. **The current user explicitly authorized moving root `20260625/` into `docs/历史设计原稿/20260625/`; that move supersedes the earlier keep-in-place rule for these four files.** Execution status belongs in root `todolist.txt`, not this inventory.

**Current Ubuntu checkout (2026-10-04):** tracked text uses LF; `core.autocrlf` is unset and no `.gitattributes` exists. The old CRLF measurements were Windows-only. Normalize line endings when comparing content across platforms.

**Tracked leftovers that are not part of the app:**

| Path | Size | What it is |
|---|---:|---|
| `frontend_example/` | 20 files, 2.25 MB | **Two prototypes from before the rewrite**: a Transformer learning-map at the top level and a static prototype under `看这个！/`. **5 files are byte-identical between the two** (`tex-mml-chtml.js` 997 KB, `app.js`, `marked.min.js`, `styles.css`, `index.html`) ⇒ **1.10 MB of the 2.25 MB is pure duplication**, and deduplicating would cost no content. Its `看这个！/README.md` tells you to serve on **port 8000, which on the original Windows machine ran a different project** (`yb_reconcile_demo`) — that is why the backend lives on 8010. |
| `docs/历史设计原稿/20260625/` | 4 files | Original 2026-06-25 design plans, moved from root `20260625/` with the user's authorization during documentation reorganization. Preserve as historical originals; current comparison is `docs/10_早期界面设计整理.md`, execution status is root `todolist.txt`. |
| `tp2.txt` | 2,815 B | Prompt scratch, tracked but unrelated to this project. (`tp.md` is also tracked.) |
| `skills-lock.json` | 284 B | Lock for the agent skill pack. **Resolved:** its `computedHash` (`899b8438…`) is **not** a content sha256 of anything local *or* upstream — the installed `SKILL.md`'s LF content is byte-identical to `Leonxlnx/taste-skill@main` (`aa194351…`), so the lock must use a non-content scheme. No install needed to close this. |

The Windows cache sizes and loose-object inventory are historical (archive 7 §2.43), not properties of this clone. On Ubuntu, `frontend/node_modules/` and `frontend/dist/` are ignored; `UI预览图/`, `tmp_screenshots/`, `.pnpm-store/` and `.npm-cache/` are absent. Do not delete design assets or caches if later restored. `repository/` is an empty, untracked directory, not another application. `frontend_example/`, `tp.md` and `tp2.txt` are retained historical/reference files, not runtime entry points.

## Development notes

- **Never take "today" with `new Date().toISOString().slice(0, 10)`** — `toISOString()` is
  always UTC, and in UTC+8 that returns **yesterday** between local 00:00 and 07:59 (8 hours
  of every day). This was a real bug in `Bills.vue`'s default `expense_date`. Use `todayKey()`
  / `dateToKey()` from `src/utils/date.ts` instead.
- On Ubuntu Bash, use `TZ=Asia/Shanghai node path/to/helper.ts` for pure TypeScript helper checks. PowerShell syntax in historical records is Windows-only.
- Use conda `desheng`, or `/home/afrangry/miniconda3/envs/desheng/bin/python`. IDE import errors require checking both the selected interpreter and installed dependencies; they are not automatically false positives.
- Existing dependencies are installed. If a reinstall is needed, use `npm ci` for the committed frontend lock and `python -m pip install -r requirements.txt` for the backend. Do not change dependencies as part of an unrelated documentation check.
- Run `npm run build` from `frontend/`; it includes `vue-tsc`. Ubuntu verification and warnings are recorded in `docs/11_Linux本机启动.md`.
- Vite does not hard-code IPv6-only listening; use its printed URL. Ubuntu checks use `http://localhost:3000` and bypass local HTTP proxies.
- Frontend dev server runs on `:3000`; CORS is whitelisted for `http://localhost:3000` in `main.py`.
- `main.ts` uses `createWebHistory()`. **Measured 2026-09-20 against the real `frontend/dist/`
  (已归档/7 §2.39): a plain static server breaks every deep route.** Serving `dist/` with
  `python -m http.server` returns 200 for `/` but **404 for `/bills` and `/tradesim/simulate`**,
  while `vite preview` returns the SPA's `index.html` (200) for all three. Note the trap: in-app
  navigation still works without server support (`history.pushState`), so this only shows up on a
  **refresh, a bookmark or a shared direct link**. Any production deploy must configure the
  fallback (or switch to hash history). The historical IPv6-only preview observation was environment-specific; inspect current listeners rather than assuming it.
  The authenticated launcher now provides SPA fallback; see docs/11 for deployment verification limits.
- Root-level `tp.md` is a tracked historical scratch document.
  Not part of the project.
