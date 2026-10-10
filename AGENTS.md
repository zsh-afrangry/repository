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
├── dev-start.ps1     # DEV startup, Win11 (backend + Vite); Ctrl+C stops both
├── dev-stop.ps1      # DEV stop/status, Win11 — kills by PORT, not PID files
├── dev-start.sh      # DEV startup, Ubuntu 22.04 — syntax-checked only, NOT run on Linux yet
├── dev-stop.sh       # DEV stop/status, Ubuntu 22.04 — same caveat; see docs/15 §8
├── Start-KnowledgeMap.sh   # PRODUCTION/mobile mode (Tailscale + auth + built snapshot)
├── Stop-KnowledgeMap.sh    #   — a separate concern, see docs/11. Do NOT merge with dev-*
├── backend/          # FastAPI app (Python)
│   ├── main.py       # Sole entry point — `python main.py` starts uvicorn on :8010
│   ├── requirements.txt
│   ├── sql/          # exported table schema (versioned); see "Documentation"
│   │   └── knowledgemap.sql                  # snapshot of all 6 tables, --no-data
│   ├── scripts/      # dev/test helper scripts (NOT deployment tooling)
│   │   ├── ensure_database.py                # creates the DB if missing; reports tables/seeds/Mongo
│   │   ├── export_schema.py                  # dump schema → backend/sql/, with --check
│   │   ├── rebuild_calendar_events.py        # one-off: narrow tone + add completed_at
│   │   ├── code_volume_probe.py              # measure the 5 candidate code-volume metrics
│   │   ├── seed_week_demo.py                 # seed/clear [演示] rows ONLY (never the whole table)
│   │   └── check_doc_refs.py                 # validate every 对应文档： reference resolves
│   ├── tests/
│   │   ├── tradesim_grid_strategy_cases.py   # plain-python runner, 8 cases
│   │   ├── portal_crud_cases.py              # plain-python runner, 13 cases, in-memory SQLite
│   │   ├── calendar_crud_cases.py            # 114 cases: week bounds, overdue, completion asymmetry,
│   │   │                                     #            pending order/buckets, archive bin, completed list
│   │   ├── dashboard_overview_cases.py       # 24 cases: overview endpoint, null-vs-zero, NaN
│   │   ├── weather_cases.py                  # 24 cases, QWeather HTTP stubbed
│   │   ├── notes_cases.py                    # Notes HTTP/transaction, SQLite only
│   │   ├── notes_browser_server.py           # disposable SQLite API for browser checks
│   │   ├── notes_mysql_smoke.py              # opt-in live MySQL temporary topic
│   │   └── web_host_cases.py                 # authenticated launcher / SPA fallback
│   └── app/
│       ├── database.py       # MySQL engine + SessionLocal + get_db (single source)
│       ├── git_stats.py      # local-git read-only metrics (code lines, commit counts)
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
    ├── tests/          # browser regression, plain node + Playwright
    │   ├── portal-browser.cjs      # home/bills regression
    │   ├── dashboard-browser.cjs   # dashboard: card, ＋, modal, 待做 drawer, toast position
    │   ├── notes-browser.cjs       # Notes main flow
    │   └── notes-layout.cjs        # Notes 1/3/4/6-column layout
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
        │   ├── useScrollReveal.ts  # Intersection Observer scroll-reveal
        │   ├── useDialogFocus.ts   # Escape + Tab trap + scroll lock for dialogs/drawers
        │   ├── usePendingTasks.ts  # singleton state for the 待做 list (card + drawer share it)
        │   └── useToast.ts        # shared toast state: timer + countdown bar + hover pause
        ├── components/       # reusable UI
        │   ├── KnowledgeMapBackground.vue
        │   ├── StarfieldBackground.vue
        │   ├── PendingDrawer.vue   # global 待做 drawer, mounted in App.vue (Ctrl/Cmd+K)
        │   ├── AppToast.vue        # shared toast + countdown bar (archive undo, theme notice)
        │   └── ui/           # UiSurface/UiButton/AmbientGlow/GridDecoration + controls.css
        │       └── WeatherLocationPicker.vue  # Dashboard weather city switcher
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
PATCH  /api/calendar-events/{event_id}/completion   {done: bool} — tick/untick an item;
                                    the **server** stamps `completed_at`, never the client
PATCH  /api/calendar-events/{event_id}/archive      {archived: bool} — archive/restore;
                                    server stamps `archived_at`. Archiving means "I decided not
                                    to do it" and is **reversible** — unlike DELETE, which really
                                    removes the row
DELETE /api/calendar-events/{event_id}

GET    /api/dashboard/overview/     aggregate for the Dashboard's four cards (week progress +
                                    code lines + notes units + commit counters + pending + archived)
GET    /api/dashboard/pending/      pending-item list **and** the archive bin: every unfinished
                                    calendar event, no date window. The "待做事项" card reads the
                                    first part; it must not be derived from the calendar's
                                    currently-visible month
GET    /api/dashboard/git-stats/    commit counters (older endpoint, kept for compatibility)
GET    /api/weather/                ?location=<Location ID>  QWeather proxy (real network
                                    call, needs the API key); omitted → default city
GET    /api/weather/locations       ?q= city search, returns QWeather Location IDs

GET    /api/health
```

(2026-10-07: the "待做事项" card was rewritten. `GET /api/dashboard/pending/` was added and
returns **every unfinished event regardless of date**, ordered with *unscheduled* items first.
The card used to filter to the current calendar week **and** read its data from `calendarEvents`
(the calendar's currently-visible month) — two independent windows, which meant a "due next
Monday" item was invisible, and clicking the calendar's next-month arrow silently emptied the
card while the progress number stayed put. See the "待做事项 card" section below and docs/14 §12.)

(2026-10-06, later: `/api/dashboard/overview/` was added, `/api/calendar-events/{event_id}/completion`
was added, and `calendar_events.tone` was **narrowed from four values to two** (`todo`/`meeting`)
with a new `completed_at` column. Table schemas are now exported to `backend/sql/`. See the
"Dashboard cards read real data" section below and docs/14.)

(2026-10-06: `/api/weather/` gained an optional `location` parameter and `/api/weather/locations`
was added, so the Dashboard weather widget's city is switchable instead of hard-coded. See the
weather note below the Dashboard section for the three things that were hard-coded and why the
air-quality call forced a GeoAPI lookup.)

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

### Dashboard cards read real data (2026-10-06)

Until 2026-10-06 the Dashboard's four hero cards plus the two lower widgets were **all static**:
hard-coded `focusTasks`, a hard-coded `weeklyProgress` object (`ratio: 72`, `tasks: 18/25`,
`docs: 6/10`), hard-coded `18` / `236` statistics, and a hard-coded three-item "今日安排" list.
They are now wired to `GET /api/dashboard/overview/` and to the calendar events API.

What changed, and the rules that matter when touching it:

- **One aggregate endpoint, not several.** `GET /api/dashboard/overview/` returns all four cards'
  data in one request, so the first paint doesn't have four cards each loading independently.
  The week-boundary, divide-by-zero and git logic lives in the backend, not in the component.
- **`null` means "could not fetch"; `0` means "genuinely zero".** The endpoint returns **200 with
  `null` fields** when git is unavailable rather than an error code, so one broken metric never
  blanks the whole page. The frontend renders `null` as `--`. **Never collapse `null` to `0`** —
  that would make "the backend is down" indistinguishable from "I wrote no code this month".
- **`ratio` is `null` when the denominator is 0** (e.g. Monday morning). `(0/0)*100` is `NaN`,
  and `NaN` in `stroke-dasharray` breaks the whole donut plus renders `NaN%`. Do not "default it
  to 0" as a fallback — the frontend keeps `--` and draws a zero-length arc.
- **`todo` and `meeting` have *opposite* completion semantics.** This is the subtle one:
  a `meeting` whose time has passed counts as **done** (the meeting happened), while a `todo`
  whose deadline has passed counts as **NOT done** (an overdue assignment is a failure).
  `crud/calendar.counts_as_progress()` owns this rule, and `is_overdue()` deliberately answers a
  different question ("has the time passed?"). Getting this backwards makes procrastinating
  *raise* your progress score — the regression is pinned by
  `tests/calendar_crud_cases.py::test_todo_overdue_does_not_count_as_progress`.
- **`completed_at` is stamped server-side.** `PATCH /api/calendar-events/{id}/completion` takes a
  boolean; the client never sends a timestamp (client clock skew would write wrong times).
- **The "今日安排" list is data-driven now.** It was the last hard-coded block on the page; it now
  reads the same `calendarEvents` the modal uses, so the two can no longer disagree.

### 待做事项 card: no fixed date window (2026-10-07)

The card was renamed from 「本周待做」 to 「待做事项」 and its data source changed. Two separate
defects made things disappear from it — **neither produced any error**:

1. **It filtered to the current calendar week** (Mon–Sun). So an item recorded on Friday as
   "due next Monday" was invisible all weekend, and became visible only once it was already due.
   Any fixed window has this problem at its boundary; "this month" fails the same way on the 31st.
2. **It read from `calendarEvents`**, which only holds the *calendar's currently-visible month*
   (`getVisibleCalendarRange()`). Clicking the calendar's next-month arrow therefore **emptied the
   card** while the weekly-progress number — which comes from an independent backend query —
   stayed put. The card and the progress figure were using two different windows.

Current rules:

- **Source**: `GET /api/dashboard/pending/` (also embedded as `overview.pending`). The card must
  **not** derive its contents from `calendarEvents`. If you find yourself filtering
  `calendarEvents` by a date range to feed this card, you are re-introducing defect 2.
- **Scope**: *every* unfinished event, **no date window** — past-due items included. The whole
  point is that nothing you still owe can scroll out of view.
- **Order** (`crud/calendar.pending_events()`, the single source): items with **no `event_time`
  come first**, then the rest by `(event_date, event_time)`. This is deliberate — an unscheduled
  item ("I jotted it down, haven't decided when") needs to be seen and scheduled, so it outranks
  a dated one. Overdue items still sort first *within* the dated group.
- **Display**: the summary shows only the first 3 items, so it **must** also show the category
  counts (`overdue` / `today` / `unscheduled`) and the unfinished total. A truncated list with no
  counts is just a new way to lose items.
- **Category counts are priority-ordered and do not overlap**: `overdue` > `unscheduled` > `today`.
  Future dated items fall into none of them, so **the three numbers sum to ≤ `total`, not `==`**.
- **`PENDING_LIMIT` is 200**; over that, `truncated: true` and the UI says "showing first N" —
  never a silent cut.

`is_overdue()` (which drives both the 「已过期」 badge and the `overdue` count) is *not* the same
question as `counts_as_progress()` — see the bullet above and docs/14 §2.2.

### 待做 drawer: global, non-modal navigation (2026-10-07)

`components/PendingDrawer.vue` is mounted **in `App.vue`**, so it is reachable from every route
(`Ctrl/Cmd + K`, or the card's 「查看全部 →」). Rules that matter:

- **It is a drawer, not a route.** The requirement was "reachable at any time **without
  interrupting what I'm doing**". A route change unmounts the current page (you'd lose scroll
  position and drafts mid-note), which defeats that. A drawer overlays instead. Do not "simplify"
  it into a `/tasks` page — that page is planned *separately* for bulk management (docs/14 §11.1).
- **Mount it permanently; control visibility with `v-if` inside the component.** `useDialogFocus`
  works via `watch(open)`, so wrapping the component itself in `v-if` breaks Escape and the focus
  trap.
- **State lives in `composables/usePendingTasks.ts`** — module-level refs, i.e. a singleton without
  a store library. The card and the drawer **must** share it; if the card keeps its own copy, a
  tick in one won't show in the other. Never feed this list from `calendarEvents` (that is
  defect 2 above).
- **Quick entry deliberately does not require a time.** One field, Enter to save; the item lands in
  the 「未安排」 group at the top of the list. This is the whole point — see docs/14 §11.2:
  if recording takes six steps, you won't record anything while busy, and the rest of the feature
  is moot. When adding a date default, use `todayKey()` from `utils/date.ts`, never
  `toISOString().slice(0,10)` (UTC → yesterday during UTC+8 early hours).
- **No Element Plus here.** That library is used only inside the TradeSim module; the portal pages
  are a custom dark design system. Reuse `components/ui/UiButton.vue` and the existing modal
  overlay styling instead.

### Toasts: one component, a countdown bar, and hover-pause (2026-10-07)

`components/AppToast.vue` (mounted in `App.vue`) renders **both** toasts: the archive undo prompt
(5s) and the theme button's "not implemented yet" notice (3s). State lives in
`composables/useToast.ts` — one place for the timer, the countdown bar, and pause/resume.

- **The bar and the timer must share one `durationMs`.** The bar is a CSS animation and dismissal
  is a JS timer — two clocks. Deriving both from the same number is the only reason they cannot
  drift when someone changes a duration. `:key` bumps re-create the element so the animation
  restarts per toast.
- **Pause on hover and on keyboard focus.** The prompt may carry an action button (「撤销」). If the
  countdown keeps running, a user about to click watches it vanish — and for keyboard users, tabbing
  to the button makes the toast disappear, i.e. the button is unreachable. Resume uses the
  *remaining* time, not a fresh start.
- **`prefers-reduced-motion` keeps the bar.** It conveys information (how long is left), unlike the
  page-scroll animation which is pure decoration; only the enter/leave transitions are dropped.
- **Verify the bar by measuring it, not by reading CSS.** Asserting `animationName`/`animationDuration`
  passes even when the element is invisible or the animation is overridden. Measure
  `getBoundingClientRect().width` at several moments and require it to strictly decrease.
- **Why not a toast library?** vue-toastification / react-toastify both ship this bar
  (`hideProgressBar` defaults to `false`). Rejected because the portal is a custom dark design
  system (library styling would need full overriding — the same reason Element Plus is confined to
  TradeSim), the needed feature set is under 100 lines, and keeping the bar and timer on one shared
  duration constant is easier by hand. If you do adopt one, replace `AppToast.vue` **and**
  `useToast.ts` together, and update the `.app-toast` selectors in `frontend/tests/*.cjs`.

⚠ **The theme toast used to be inlined in `Dashboard.vue`**, so it only appeared on the home page
while the archive toast worked everywhere. Both now go through `useToast()`. Don't re-inline a
toast in a page component — mount it via the shared layer so it works on every route.

⚠ **Sorting keys must be total.** The 「未安排」 group originally sorted by `(0, time)` only, so two
unscheduled items compared equal and `sorted()`'s stability left them in query order — newly
recorded items sank to the bottom and it looked like the save had failed. The key now includes
`-id` (newest first, owner's decision). If you add a sort here, make sure no two distinct items can
compare equal unless you *want* an arbitrary order.

### Archiving: "I decided not to do it" (2026-10-07)

`calendar_events.archived_at` (NULL = not archived) is a **third state**, independent of
`completed_at`:

| | meaning | counts toward week progress | shown in calendar |
|---|---|---|---|
| `completed_at` set | I did it | yes (as achieved) | yes |
| `archived_at` set | **I decided not to do it** | **no — neither numerator nor denominator** | **yes** |
| neither | still to do | yes | yes |

Rules, in the owner's words: archiving is a **bin you can browse and restore**, not a delete.
`DELETE` really removes the row; archiving keeps it and is reversible.

- **Two independent filters, two places to remember.** `pending_events()` excludes archived items
  (`completed_at IS NULL AND archived_at IS NULL`). `week_progress()` is a **separate query** (it
  filters by `event_date` range, not by "unfinished") and therefore needs its **own**
  `archived_at IS NULL`. Centralising the first did *not* cover the second — it was missed on the
  first attempt and only a test caught it (docs/14 §12.3). If you add another query over
  `calendar_events`, ask whether archived rows belong in it.
- **Calendar queries deliberately do NOT filter archived.** An archived item did occupy that day;
  hiding it would make the calendar disagree with what you remember. Do not "clean it up".
- **Archiving does not clear `completed_at`**, and vice versa. An item can be both.
- **No confirmation dialog, by design.** The action is reversible and immediately offers an undo
  toast (5s). A confirm prompt on a frequent action costs more than it saves. Keep the undo —
  it is what makes the no-confirm choice safe.
- **The toast lives in the shared store**, not in the drawer: it renders at the top of the page
  while the trigger is inside the drawer. Consecutive archives use an incrementing `key` so an
  older timer cannot dismiss a newer toast.

⚠ **Adding a column: run `scripts/rebuild_calendar_events.py`, don't write a new script.** It now
derives the expected columns **from the model** (it previously hard-coded `completed_at`, so it
reported "already up to date" when `archived_at` was added). It refuses to run on a non-empty
table and prints the exact `ALTER TABLE` statements instead.

### Drawer tabs: the three buckets are NOT a partition (2026-10-07)

The drawer has five tabs: **全部 / 今天 / 已过期 / 未安排 / 已完成**.
`crud/calendar.pending_bucket()` returns `'overdue' | 'unscheduled' | 'today'` — **or `None`**.

`None` is not an oversight. An item like "next Monday 14:00, hand in homework" is not overdue, not
today, and *does* have a time — it belongs to no bucket. Measured: of 5 pending items, only 3 fell
into a bucket. **「全部」exists to catch these.**

- **Never remove the 「全部」 tab**, and keep it the default. Without it, future-dated items would
  be invisible in *every* tab — exactly the class of bug the pending list was rewritten to fix
  (see the two-windows note above). The same applies to any future `/tasks` filter UI.
- **Bucket membership is decided in the backend, in one function.** `pending_summary().counts` and
  each item's `bucket` field both come from `pending_bucket()`, so a tab's badge number and its row
  count **cannot** disagree. The frontend filters with `item.bucket === activeTab` and must not
  re-derive the rule — that is how the two would drift apart.
  The invariant is pinned by
  `tests/calendar_crud_cases.py::test_bucket_counts_are_complete_partition_of_bucketed_items`.
- Priority is `overdue` > `unscheduled` > `today`, and an item lands in exactly one.
  `unscheduled` beats `today` deliberately: an item with no time recorded today is *unscheduled*,
  not "due today".
- **Empty-state text differs by tab.** An empty 「全部」 means nothing is pending; an empty
  category tab only means nothing is in *that* category; an empty 「已完成」 means nothing has been
  ticked yet. The category case must point the user at 「全部」, or it reads as "I'm done".

### Completed items: three mutually exclusive lists (2026-10-07)

Every event appears in **exactly one** of three lists:

| List | Predicate | Endpoint key |
|---|---|---|
| Pending | `completed_at IS NULL AND archived_at IS NULL` | `pending.items` |
| Completed | `completed_at IS NOT NULL AND archived_at IS NULL` | `completed.items` |
| Archive bin | `archived_at IS NOT NULL` | `archived.items` |

- **Archiving wins.** An item that is *both* completed and archived appears **only** in the bin —
  showing it in two places would leave the user unsure which is authoritative. Pinned by
  `tests/calendar_crud_cases.py::test_three_lists_are_mutually_exclusive_and_complete`.
- **「全部」 does NOT include completed items** (owner's decision). So the 全部 badge is *not* the
  sum of the other tabs — do not "fix" that arithmetic; summing it would mix done work into the
  main view until it drowns. Completed lives on its own tab.
- **The completed tab exists to undo a mis-tick.** Before it, ticking an item made it leave the
  drawer with no way back. Its rows differ on purpose: **no clickable checkbox** (they are done;
  a checkbox implies you could un-tick it there) and the right-hand button is 「恢复」.
- ⚠ **「恢复」 means two different functions**: `uncompleteItem()` on the completed tab (clears
  `completed_at`) vs `unarchiveItem()` in the bin (clears `archived_at`). Same user-facing word,
  two different code paths — don't collapse them.
- Both lists sort by **their own timestamp descending** (completed → `completed_at`, bin →
  `archived_at`), unlike the pending list's "unscheduled first" rule. They are for looking back.
- ⚠ `dashboard_overview_cases.py::build_client` mounts **only the dashboard router**. Don't call
  calendar endpoints from that file (they 404); flip columns directly on the session instead.

### Editing an item: the `exclude_unset` trap (2026-10-08)

The drawer's 「修改」 button (docs/14 §11.3) wires up `PATCH /calendar-events/{id}`, which had existed
unused for a long time. Frontend-only change — no backend or schema work was needed.

- ⚠ **To CLEAR a field you must send an explicit `null`; omitting it leaves the field alone.**
  The backend does `model_dump(exclude_unset=True)`, so `{}` and `{"event_time": null}` take
  *different* branches. "Change the time back to 未安排" is a core scenario of this feature, and if
  the form serialises an empty time by omitting the key, the user sees "I can change it but I can't
  clear it" — with no error to explain it. Pinned by
  `calendar_crud_cases.py::test_update_can_clear_event_time_to_null` and its counterpart
  `test_update_omitted_fields_are_untouched`.
- **The time input needs `step="1"`.** Without it browsers only offer minutes and silently truncate
  seconds, so editing an item once turns `22:48:39` into `22:48:00`. Pinned by
  `test_update_seconds_survive_round_trip`.
- **The edit form replaces the row in place; it is NOT a second modal.** The drawer is already a
  `role="dialog"` with a focus trap and a body-scroll lock. A nested modal would give you **two
  `useDialogFocus` instances** fighting over the same document keydown handler and
  `document.body.style.overflow` — Escape closes both and the scroll lock gets restored by whichever
  unmounts second.
- **Refresh after saving; never patch the local object.** Ordering (§2.4) and bucketing (§11.1) are
  derived by the backend, so a local-only update desynchronises the tab badges from the row counts.
  Changing an item's date legitimately moves it between tabs (and possibly between weeks for
  「本周进度」) — that is correct, not a bug.
- **Button order is deliberate: 修改 before 作废/恢复.** Editing does not change whether the item
  stays in the list; archiving does. Lower-impact action first.
- ⚠ **A row now has more than one `.drawer-item-action`.** Browser tests must locate buttons **by
  label** (`actionButton(scope, '作废')`), not by `first()` — `first()` is now 「修改」.
  When matching label text, **allow surrounding whitespace**: the buttons render as `" 恢复 "`, so
  `^恢复$` fails to match (hit in practice).

### Time gets the visual weight, date does not (2026-10-08)

In the drawer's row meta, the **date and the time are two separate elements on purpose** — do not
merge them back into one string (they were merged until 2026-10-08, rendering `10/13 21:06` at
9.92px/400 in `--text-secondary`, i.e. exactly as faint as a 「未安排」 status tag).

- The date answers "which day"; the time answers "**what time, do I need to prepare now**". The time
  is the hard constraint — it is the thing you can be late for — so it carries the weight:
  `--text-title` (near-white), 12px, weight 800, monospace. Measured contrast 9.87 vs the date's
  6.43 (WCAG AA needs ≥ 4.5). The date is dimmed to 0.8 opacity to push it back.
- **An overdue time turns amber** (`#fbbf24`, same family as the 「已过期」 tag): once it has passed,
  "what time" means "what time I already missed".
- **No background block or border on the time.** The row already carries several tags
  (未安排 / 待做 / 已过期); adding a filled chip makes four boxes in one line and the emphasis
  cancels out. Weight and brightness do the work — same approach as
  `Dashboard.vue .calendar-event-item time`.
- Keep the same rendering in the archive bin, but the row's `.is-archived` opacity dims it — an
  archived item genuinely doesn't need reminding.
- **Seconds stay hidden.** `event_time` stores them, but they are recording precision, not a
  decision input; `09:30:00` adds three characters per row that carry no information. Seconds remain
  in the DB and stay editable via `<input type="time" step="1">`.

⚠ **Do not assert "brighter" by summing RGB channels.** Amber `rgb(251,191,36)` sums to 478, *below*
the grey date's 495 — yet amber has the higher WCAG contrast (9.87 vs 6.43). Sum-of-channels is a
plausible-looking proxy that gives the **opposite** answer and fails silently. Use the relative
luminance formula; the browser test does exactly that.

### ⚠ NEVER clear `calendar_events` wholesale (2026-10-07 data loss)

**This table holds real user data alongside any test rows.** On 2026-10-07 a wholesale clear
deleted the owner's actual items (`智能计算VIT`, `组会`, `算法学习和网站开发`, …). The rounds
afterwards even reported "database clean: `calendar_events` rows = 0" as if that were good news —
it was the evidence of the loss.

- **"Clean up test data" and "empty the table" are different operations.** Every delete must be
  able to state *which rows* it removes: a title prefix or an explicit id list. Never rely on the
  assumption "this table should only contain test data".
- `scripts/seed_week_demo.py --clear` now deletes **only `[演示]`-prefixed rows**. It seeds with
  that prefix, so cleanup is still complete. Keep it that way.
- Browser tests are fine: they track the ids they created and sweep by their own `MARK` prefix.
- `rebuild_calendar_events.py` refuses to run on a non-empty table and prints `ALTER TABLE`
  statements instead — that guard is deliberate; don't add a `--force`.
- **Recovery, if it ever happens again**: `log_bin=ON` and `binlog_row_image=FULL` mean every
  DELETE carries a full column image of the removed row, and rows lost to `DROP TABLE` can be
  recovered from a pre-DROP liveness snapshot. `mysqlbinlog -v --base64-output=DECODE-ROWS` then
  replay. Note `DROP TABLE` leaves **no** row data, so snapshot before it — and **don't key
  recovery by `id`**, since ids get reused; key by `(title, detail)`.

### Dev startup scripts: two rules that must not be broken (2026-10-08)

`dev-start.{ps1,sh}` + `dev-stop.{ps1,sh}` run the **development** stack (uvicorn + Vite dev
server). They are deliberately separate from `Start-KnowledgeMap.sh` (production/mobile mode:
Tailscale + auth + built snapshot) — don't merge them.

- **The port is decided in ONE place, then injected into both processes.** The launcher sets
  `KM_BACKEND_PORT` (read by `main.py`) and `KM_API_TARGET` (read by `vite.config.ts` as the proxy
  target). This is not a style preference: the Vite proxy runs **inside the Node process**, not the
  browser, so the frontend can only learn the backend port at Vite startup. If the two ever decide
  independently, you get "the page loads but every API 404s" — a genuinely hard bug to localise.
  **Never add frontend-side backend-port discovery.**
- **`ensure_database.py` must stay non-destructive.** It exists to fill the one real gap: nothing
  creates the *database* (only `Base.metadata.create_all()` runs, and `create_all` builds tables,
  never the schema/database itself — a missing DB throws inside lifespan and the server won't
  start at all). It must never gain `--recreate`/`--force`, never run `backend/sql/knowledgemap.sql`
  (that file has `DROP TABLE IF EXISTS`), and never gain `subprocess`/`os.system` (no ability to
  run external commands ⇒ cannot delete files or stop services by accident). All of this is pinned
  by `tests/ensure_database_cases.py`.
- **Tables and seed data are `main.py`'s job, not the script's.** `seed_default_tags()` seeds when
  the table is empty; `seed_notes()` uses a `NotesSeed` marker row. The startup script only reports
  their state — overlapping would leave nobody able to say who is responsible.
- **Stop by PORT, never by PID file** (owner's requirement): PIDs change on every restart, so a
  recorded PID goes stale and may point at an unrelated process. `dev-stop` resolves the listener
  per port and refuses to kill anything whose command line doesn't look like this project unless
  `--force` is given.
- **Don't judge "ours" by the project path alone.** `dev-start` launches Vite with a *relative*
  entry (`node_modules/vite/bin/vite.js`), so the command line contains no project path — matching
  only on that made the stop script call its own frontend "not ours". Match on entry signatures
  (`main.py`, `vite`) too.
- **Kill the whole tree.** Windows needs `taskkill /T`; Unix needs `setsid` + `kill -TERM -<pgid>`.
  Vite and `uvicorn --reload` both spawn children; killing only the parent leaves orphans holding
  the ports, and the symptom looks like "nothing is running but the port is busy".

**Verifying `.sh` changes on Windows**: use Git Bash (`C:\Program Files\Git\bin\bash.exe`) for
`bash -n`. Do **not** trust `shutil.which("bash")` alone — on Windows it may return the WSL relay
(`C:\Windows\system32\bash.exe`), which fails with `execvpe(/bin/bash) failed` when no distro is
installed, looking like a script error. `tests/shell_script_cases.py` probes the candidate by
actually running it. And **do not hand-write a shell structure checker** — a first attempt had 7 of
8 assertions false-positive (Python parens inside heredocs, `{0,1}` inside a sed expression, `do`
at end of line). False alarms train people to ignore warnings; use the real parser.

⚠ **The Ubuntu path is NOT end-to-end verified (as of 2026-10-08).** `dev-start.sh` / `dev-stop.sh`
pass `bash -n` and the convention checks, but they have **never actually been run on Ubuntu** —
development happens on Windows. This does not block current work, but before relying on them on
the Linux host, walk through `docs/15_开发启动脚本方案.md` §8 (6 steps). The step that matters most
is `curl -s http://127.0.0.1:3000/api/health` — it proves `KM_API_TARGET` reaches the backend
rather than the hard-coded 8010, which is the failure mode that looks like "backend is down".

⚠ **Still static, deliberately**: the `projects` card array and the project-index pill counts
(`项目总数 18` etc.), and the card status text. Those remain presentation. If you wire them up,
replace the placeholder values in the same change rather than leaving them as a fallback — a
silent fallback to fake numbers is exactly how this kind of page becomes untrustworthy. Card
status text must at least not contradict itself: card `06`「文档资料库」used to say `可进入`
while carrying `route: null`; it now reads `等待接入`.

### Weather location is user-switchable (2026-10-06)

The Dashboard weather widget's city used to be hard-coded in **three** places, all in
`routers/weather.py`: the QWeather Location ID, the latitude/longitude, and the display label
`广东省 · 广州市 · 天河区`. The label also existed a fourth time as the placeholder object in
`Dashboard.vue`. Clicking the 📍 now opens a picker (`components/ui/WeatherLocationPicker.vue`).

The non-obvious part — **why the backend needs a GeoAPI lookup at all**: `/v7/weather/*` takes a
Location ID, but `/airquality/v1/current/` is called with **latitude/longitude**. So switching
city cannot just swap the ID; the backend resolves it through `/geo/v2/city/lookup` to get
`id` + `lat` + `lon` together. Consequences worth keeping:

- **The single-slot cache was a real bug, not just a limitation.** The old
  `_cache = {"expires_at", "value"}` held one entry, so switching city and switching back would
  have served the previous city's data within the TTL. `_weather_cache` is now keyed by Location
  ID; search results get their own 24 h `_geo_cache` so repeated searches don't burn quota
  (`/weather/locations` costs one GeoAPI call per uncached keyword).
- **The label is built from `adm1 · adm2 · name` with suffix-aware de-duplication.** Without it a
  city-level hit renders as `四川省 · 成都市 · 成都`; `_skeleton()` drops 省/市/区/县… before
  comparing, so the same place at two levels collapses to one.
- **GeoAPI failure must not fail the weather.** `_resolve_place()` returns `None` on error and
  the weather still loads, falling back to a Location-ID-based air-quality call. The display name
  then degrades to the raw ID — the frontend deliberately does **not** persist that value.
- The picker has a **preset list** (real Location IDs, no search call) plus keyword search, so the
  common case costs no extra quota. Selection persists in `localStorage` (`km.weather.locationId`)
  — a local UI preference, not backend state; a failed write only means the next visit starts from
  the default city.

### Theme toast position

The nav theme button's "功能待开发" toast is **horizontally centred at `top: 10%`** (viewport
upper-middle), not a corner — owner's request, 2026-09-20, moved up from `20%` on 2026-10-06.
Narrow screens (`≤720px`) use `top: 8%` (was `14%`), and the width is capped at
`min(21rem, calc(100vw - 2rem))`. The toast's *styling* is unchanged; only the position moved.

⚠ **The enter/leave transitions must use `translate(-50%, -14px)`** — the base rule already
uses `transform: translateX(-50%)` for centring, so an animation that only moves `translateY`
would drop the centring on its first frame and slide the toast in from the left edge. The
comment in `Dashboard.vue` says so.

Verified 2026-10-06 in headless Chrome: `rect.top = 90px / 902px =` **10.0%**, with the
horizontal centre offset at **0.0px** (i.e. centring intact). See docs/14 §F1–F8.

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
python tests/calendar_crud_cases.py             # plain runner, expects 114 PASS
python tests/dashboard_overview_cases.py        # plain runner, expects 55 PASS
```

Not pytest — these are standalone scripts that print `PASS`/`FAIL` and exit non-zero on failure.

- `tradesim_grid_strategy_cases.py` covers grid cycles, multi-grid crossings, insufficient
  cash, commission/slippage, base position and invalid params.
- `portal_crud_cases.py` contains thirteen **bill CRUD, monthly-summary, PATCH validation and pagination** cases using in-memory SQLite. Tags are fixture data; tag/calendar CRUD and HTTP-level behavior are not covered by these cases. Passing both runners does not close the audit's storage, chart or strategy-boundary findings; track missing coverage in root `todolist.txt`.
- `calendar_crud_cases.py` (added 2026-10-06, extended 2026-10-07) covers the
  **calendar / week-progress / pending-list** semantics: week boundaries (Mon–Sun, incl. Sunday
  and cross-month), `event_time`→23:59:59 fallback, cross-day overdue comparisons,
  `todo`-vs-`meeting` completion asymmetry, `ratio is None` on an empty week, `tone` narrowing,
  `completed_at` set/clear, **archiving** (pending/bin exclusivity, restore, week-progress exclusion, 
  calendar still shows them), **bucket membership** (incl. the `None` case for future-dated items),
  and the pending list's **ordering** (unscheduled first, newest-first
  within that group), **category counts** (priority-ordered, non-overlapping), **limit +
  `truncated`**, and that far-future items are included. In-memory SQLite only.
- `dashboard_overview_cases.py` (added 2026-10-06, extended 2026-10-07) covers
  `GET /api/dashboard/overview/` and `/pending/`: shape (incl. the `pending` section),
  notes aggregation (including rows missing `sections`/`units`), and — most importantly — that
  **`null` (unavailable) and `0` (genuinely zero) stay distinguishable**, that the response body
  never contains a `NaN` literal, and that a git failure still leaves the week and notes data
  intact. It also asserts `/pending/` and `overview.pending` are **identical** (the two must not
  drift). Git is stubbed, so results don't depend on this machine's repository state.
- `weather_cases.py` covers the weather location picker's backend: label de-duplication, city
  search, per-location caching (the old single-slot cache was a real bug), air-quality
  coordinates and GeoAPI-failure fallback. It stubs `_request_qweather`, so it exercises real
  logic **without** network calls, API keys or a database — and therefore does **not** prove
  the live weather service works.
- `notes_cases.py`, `notes_browser_server.py`, `notes_mysql_smoke.py` and `web_host_cases.py`
  are the other standalone runners; `notes_mysql_smoke.py` is the only one that writes to the
  live database and requires an explicit `--allow-write`.
- `frontend/tests/dashboard-browser.cjs` (added 2026-10-07) covers the dashboard's browser side:
  card rename, the ＋ button, the modal's option contract (`todo`/`meeting` only, `datetime-local`
  with `step="1"`), the overdue marker and the theme-toast position at both breakpoints. Since
  2026-10-07 it also covers **the 待做 drawer**: that `Ctrl+K` opens it from `/bills` without
  changing the route, and that quick entry saves with a title alone and lands at the top.
  It **seeds and cleans up its own `calendar_events` rows** (unique title marker, cleaned in a
  `finally`), so it needs no fixture step. Run it from the repo root, not from `frontend/`.

  ⚠ **Its cleanup must sweep by title prefix, not just by recorded ids.** The test creates rows
  through *two* paths — the API (ids collected) and the drawer's quick-entry UI (**the page issues
  that request, so the id is never collected**). Cleaning only the recorded ids left a row behind;
  the sweep now deletes by marker prefix as well. Any test that drives the UI to create data has
  this same gap.

⚠ **A path check must normalise the separator before comparing — this cost a real, long-lived
bug** (fixed 2026-10-07). `SPAFiles.get_response` in `app/web_host.py` guards against serving the
SPA shell for missing API/assets paths by testing `path.startswith("api/")`. But Starlette hands
that callback a **platform-dependent** path: on Windows it is `api\missing` (backslash), so the
guard never matched. Consequence on Windows only: `GET /api/missing` and `GET /assets/missing`
returned **200 + index.html** instead of 404, which makes the frontend's `apiFetch` report a
JSON-parse error for a mistyped endpoint instead of a clean 404. Linux uses forward slashes, so
the recorded Ubuntu pass was genuine — the defect sat in Windows-only territory, and
`web_host_cases.py` failed there for a **different, earlier** reason (`PermissionError` from the
sandbox creating its temp dir) that **masked** the real assertion failure. Fix: compare against
`path.replace("\\", "/")` while still passing the original `path` to `super()`.
**Lesson: an environment-class failure can hide a real assertion failure behind it — re-run after
the environment is unblocked instead of carrying the old "not our bug" conclusion forward.**

⚠ **Writing in-memory-SQLite tests against FastAPI**: `create_engine("sqlite://")` alone is not
enough — you need **both** `poolclass=StaticPool` (otherwise each new connection gets its own
empty in-memory database and you get `no such table`) **and**
`connect_args={"check_same_thread": False}` (FastAPI runs sync endpoints in a threadpool, and
sqlite3 refuses cross-thread use by default). Both were hit and fixed on 2026-10-06; see
`dashboard_overview_cases.py::build_client`.

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

**Every test and script file must be referenced from a document** (owner's requirement, 2026-10-06). The reading order is document first, code second, so a script that no document mentions looks like an orphan and is at risk of being deleted as one. Two halves, both required:

1. The script's header carries `对应文档：docs/<file>.md「<section>」` — see `backend/tests/weather_cases.py` for the shape. Add it as a comment for `.cjs` / `.sh` too.
2. The document names the script and what it covers. `docs/12_首页与账单收尾验收.md` keeps a 「相关测试与脚本」 table for the portal scripts; this file's "Tests" section covers the runners.

When you add a script, add both halves in the same change. If a script genuinely has no suitable document, say so rather than inventing a section.

**Run `python backend/scripts/check_doc_refs.py` to verify the half-1 references still resolve.** It scans every script under `backend/`, `frontend/tests/` and `scripts/`, parses the `对应文档：` line, and checks that the named document exists *and* that the named section heading is really in it. Renaming a section silently breaks these references, so re-run it whenever you rename a heading. Exit code 1 on any unresolved reference.

⚠ When writing a checker for this convention, the reference pattern must only match a line that **starts** with the marker (allowing a leading comment character). A loose substring match will also match prose that merely *describes* the format — the first version of `check_doc_refs.py` flagged its own example comment as a broken reference. Same class of mistake as docs/14 §V3.

**Script placement** (2026-10-06): development/test helper scripts live in **`backend/scripts/`**, tests in **`backend/tests/`**. Do not create a new root-level `scripts/` directory. The existing root `scripts/knowledgemap_launcher.py` is **deliberately left where it is** — moving it would touch both `.sh` wrappers, `docs/11` and this file, and it is deployment tooling rather than a dev helper.

**Table schemas are versioned in `backend/sql/`** (2026-10-06). `create_all()` only creates *missing* tables and never `ALTER`s an existing one, so schema changes used to survive only as long as someone remembered to run a manual SQL statement. Now:

- `backend/scripts/export_schema.py` dumps the live schema to `backend/sql/knowledgemap.sql` (`--no-data`; `AUTO_INCREMENT` counters and dump timestamps are stripped so `git diff` shows only real structural change).
- `--check` mode diffs the live database against that file and exits 1 on drift — use it when a schema change is suspected.
- The **SQLAlchemy models remain the authority**; the `.sql` file is their snapshot. After changing a model, re-export in the same change.
- The older `表结构/*.sql` at the repo root are **historical snapshots containing `DROP TABLE`** and must not be run against a live database. `backend/sql/` supersedes them.

⚠ **`backend/sql/knowledgemap.sql` drops all six tables** if executed as-is. For a single-table change use a targeted script instead — `backend/scripts/rebuild_calendar_events.py` is the worked example (it touches only `calendar_events`, refuses to run when the table is non-empty, detects column-comment drift, and is idempotent).

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
