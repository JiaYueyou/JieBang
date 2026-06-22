# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

"智联职引" — Multi-source heterogeneous data-driven job & capability graph construction platform. Competition entry for enterprise命题赛 (科大讯飞 sponsor). Full-stack: FastAPI + Vue 3 + MySQL + Neo4j + DeepSeek Agent.

## Common Commands

```bash
# Backend
cd fyz-src/backend
conda activate jiebang                                     # Python 3.10 env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pytest test/ -v                                            # Full backend suite
pytest test/api/test_auth.py -v                            # Single test file
pytest test/ -v --html=report.html                         # HTML report

# Frontend
cd fyz-src/frontend
npm run dev                                                # Vite dev server (port 5173)
npm run build                                              # Type-check + build
npx vue-tsc --noEmit                                       # Type-check only

# Candidate frontend
cd jtt-src/frontend
npm run dev
npm run build                                              # Type-check + build

# Data analysis pipeline (requires DEEPSEEK_API_KEY in .env)
cd data_analysis
python scripts/01_merge_clean.py                           # Step 1: merge data sources
python scripts/02_normalize_titles.py                      # Step 2: job title standardization
python scripts/03_extract_skills.py                        # Step 3: skill extraction
python scripts/04_build_reference.py                       # Step 4: reference dataset
```

## Architecture

```
docs/                    # Competition requirements, dev plan, dev spec
data/                    # Crawled job data: jd_crawl_ifly.json (iflytek 50), jd_crawl_zl.json (zhaopin 50)
data_analysis/           # Skill extraction pipeline (4-step), uses DeepSeek API
fyz-src/
├── backend/             # FastAPI (port 8000), Python 3.10
│   ├── app/
│   │   ├── main.py      # App entry and lifespan
│   │   ├── core/        # config, security (JWT+bcrypt), database (MySQL+SQLAlchemy async), neo4j
│   │   ├── models/      # SQLAlchemy business and audit models
│   │   ├── schemas/     # Pydantic: ApiResponse(code,message,data,meta), auth, PageMeta
│   │   └── api/v1/      # auth, jobs, skills, graph, imports, and module routes
│   └── test/            # pytest + SQLite in-memory + pytest-asyncio
├── frontend/            # Vue 3 + TS + Vite (port 5173), Element Plus, Plus Jakarta Sans font
│   └── src/
│       ├── views/       # Login, Register, Dashboard, 7 placeholder pages
│       ├── components/layout/  # AppLayout (sidebar + topbar + content)
│       ├── api/         # axios wrapper (request.ts) + auth.ts
│       ├── router/      # Vue Router with auth guard (noAuth meta flag)
│       └── stores/      # Pinia: user store (token, username, login, logout, restore)
├── FULLSTACK_PLAN.md    # 11-module plan: 5 phases, MySQL schema, Neo4j extensions
└── GRAPH_ARCHITECTURE.md # 5-layer skill forest model, data pipeline, API design
jtt-src/
└── frontend/            # Candidate-facing Vue 3 app with MSW-backed development data
```

## Key Design Decisions

- **Testing**: All backend tests use `TESTING=true` env var to switch to `sqlite+aiosqlite:///:memory:` (no MySQL needed). Test DB reset before each test via `_setup_db` fixture. Defined in `pytest.ini` with `asyncio_mode=auto`.
- **Auth**: JWT via `python-jose`, bcrypt hashing directly (NOT passlib — incompatible with `bcrypt>=4.0`). Placeholder routes use `dependencies=[Depends(get_current_user)]` on the router. `noAuth` meta flag on frontend routes skips the guard.
- **API response format**: All endpoints return `{"code": 200, "message": "success", "data": {...}, "meta": null}`. Error codes: 40001 (auth fail), 40002 (duplicate), 40100 (bad token).
- **Neo4j**: Singleton driver in `core/neo4j.py` via `graphdatabasedriver`. Connection tested by `test_neo4j.py` (7 tests, skip gracefully if Neo4j unavailable). `.env` must have correct `NEO4J_PASSWORD`.
- **Conda env**: Located at `E:\Computer_tools\Anaconda\dld\envs\jiebang`. All Python commands must use this env.
- **No passlib**: Direct `bcrypt.hashpw()` / `bcrypt.checkpw()` due to passlib incompatibility with newer bcrypt.

## Frontend Design System

- Font: Plus Jakarta Sans (headings) + JetBrains Mono (code/time displays), loaded from Google Fonts
- Color: `--color-brand: #4f6ef6` (indigo), success `#34b37e`, warning `#f59e4b`, danger `#e85d5d`
- CSS variables defined in `src/assets/styles/global.css` — all custom classes use these variables
- Layout: 232px fixed sidebar + flex content area. Mobile: sidebar hidden below 768px
- Animations: `.anim-fade-up`, `.anim-fade-in`, `.anim-scale-in` with `.anim-delay-1` through `.anim-delay-4`

## Documentation Files

| File | Purpose |
|------|---------|
| `docs/requirements.md` | Competition requirements, 4 core modules, scoring criteria |
| `docs/dev-plan.md` | 5-person team, 12-week timeline, AI-assisted dev guide |
| `docs/dev-spec.md` | API conventions, DB design, code standards, Git workflow |
| `fyz-src/GRAPH_ARCHITECTURE.md` | Neo4j 5-layer forest model, Agent pipeline, 3 engine APIs |
| `fyz-src/FULLSTACK_PLAN.md` | 11-module plan with MySQL schemas, 5 phases, dependencies |
| `fyz-src/DEVELOPMENT_PLAN.md` | Original MVP dev plan (login, layout, placeholder pages) |

## Contributor Workspaces

- `fyz-src/backend`: shared FastAPI service and data/graph APIs.
- `fyz-src/frontend`: management and decision-support frontend.
- `jtt-src/frontend`: candidate-facing Vue 3 frontend. Run its commands from
  that directory; do not commit its `node_modules`, `dist`, `.npm-cache`, or
  local tool configuration.
