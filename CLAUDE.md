# KnowledgeMap — CLAUDE.md

Personal portal aggregating all side-projects under one unified dashboard. Each project gets a card on the dashboard; clicking it navigates to that project's dedicated page.

## Repository layout

```
KnowledgeMap/
├── backend/          # FastAPI app (Python)
│   ├── main.py       # Entry point — `python main.py` starts uvicorn on :8000
│   ├── requirements.txt
│   └── app/
│       ├── database.py       # MySQL engine + SessionLocal + get_db
│       ├── models/           # SQLAlchemy ORM models (per-module files)
│       │   └── bill.py       # Tag, Bill, enums
│       ├── schemas/          # Pydantic v2 schemas (per-module files)
│       │   ├── bill.py
│       │   └── tag.py
│       ├── crud/             # DB operations (per-module files)
│       │   ├── bill.py
│       │   └── tag.py
│       └── routers/          # FastAPI routers (per-module files)
│           ├── bill.py       # /api/bills
│           └── tag.py        # /api/tags
└── frontend/         # Vite + Vue 3 app
    ├── package.json
    └── src/
        ├── main.ts           # App + Vue Router bootstrap
        ├── App.vue           # Root component with Lenis smooth scroll
        ├── styles/main.css   # Tailwind v4 @theme directives + globals
        ├── composables/
        │   └── useScrollReveal.ts  # Intersection Observer scroll-reveal
        └── views/
            ├── Dashboard.vue # Home — project cards grid
            └── Bills.vue     # Billing tracker page
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Vue 3 `<script setup>`, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Vue Router 4, Lenis |
| Backend | FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, Alembic |
| Database | MySQL 8 via `pymysql` driver |
| Runtime | Python: conda env `desheng`; Node: system npm |

## Running the project

**Backend**
```bash
conda activate desheng
cd backend
python main.py          # starts uvicorn on http://0.0.0.0:8000 with --reload
```

**Frontend**
```bash
cd frontend
npm run dev             # starts Vite dev server on http://localhost:3000
```

**Database** — must exist before first backend start:
```sql
CREATE DATABASE IF NOT EXISTS knowledgemap CHARACTER SET utf8mb4;
```
Connection: `mysql+pymysql://root:root@localhost:3306/knowledgemap`

Tables are auto-created on startup via `Base.metadata.create_all()`. Default tags are seeded on first run by `seed_default_tags()`.

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

## Planned structure evolution

Current layout (by layer) works fine for one module. When a second module (e.g. `tradesim`, `notes`) is added, migrate to **feature-based layout**:

```
backend/app/
├── billing/   models.py  schemas.py  crud.py  router.py
├── tradesim/  ...
└── database.py

frontend/src/
├── api/        billing.ts  tradesim.ts   (fetch wrappers per module)
├── types/      billing.ts  tradesim.ts   (shared TS interfaces)
├── components/ (reusable UI, split out from views)
├── composables/
└── views/
```

## Development notes

- IDE "Cannot find module" errors in backend files are **false positives** — the IDE interpreter is not set to the `desheng` conda env. Code runs fine from the terminal. Fix: set interpreter to `~/miniconda3/envs/desheng/python.exe` in VS Code or PyCharm.
- Do **not** run `npm install` or other heavy frontend commands — they trigger semgrep-core-proprietary.exe and slow the IDE. Hand these to the user to run manually.
- Frontend dev server runs on `:3000`; CORS is whitelisted for `http://localhost:3000` in `main.py`.
