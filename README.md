# AI Agent Generation & Maintenance System

A configurable platform for defining, building, versioning, deploying, and
monitoring AI agents — the "Agent Factory" described in the functional spec.
Built as a **Phase 1 foundation** with hooks for the later roadmap phases
(governance, KPI/cost dashboards, optimization).

Repository: [https://github.com/gdierksmeier/OC-Agent](https://github.com/gdierksmeier/OC-Agent)

## Stack

| Layer    | Technology                                    |
|----------|-----------------------------------------------|
| Backend  | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| Database | SQLite (file-based, no server)                |
| Frontend | Vue 3 + Vite, Vue Router, Pinia, Axios        |

## What's implemented

- **13 SQLite tables** covering users, agents, agent versions, workflows, tasks,
  endpoint registry, AI model registry, prompts, executions, execution steps,
  cost records, budgets, and environment settings
- **Full CRUD REST API** for every entity (`/docs` for interactive Swagger UI)
- **Workflow execution engine** with retries, fallbacks, escalation, and
  per-step cost / token / latency tracking. Endpoint and model calls are
  simulated so the platform runs end-to-end without real API keys — swap in
  real adapters when you're ready
- **Vue admin UI** with 11 views: dashboard, agents (list + detail with
  config/workflow/run/versions tabs), workflows, endpoints (with test
  console and environment/input-based test payloads), models, prompts,
  environment settings, executions (with full step-by-step trace), and
  cost dashboard with budgets
- **Seed data** so the platform is usable out of the box (sample
  "EWA Complaint Analysis Agent" + 5 OUC-style endpoints + 3 models
  (default local Llama) + 2 prompts + 8-task workflow)
- **Environment settings module** for DEV/QA/PROD variables like
  `OUC_API_HOST`, `OUC_API_PORT`, and bearer token values (masked when secret)

## Quickstart

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The first run creates `ai_agent_platform.db` and seeds it. API docs:
<http://localhost:8000/docs>.

### 2. Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api/*` to the backend.

## Mapping to the functional spec

| Spec section                          | Implementation                                       |
|---------------------------------------|------------------------------------------------------|
| §4.1 Agent Definition Management      | `Agent`, `AgentVersion` models · `routers/agents.py` |
| §4.2 Workflow & Task Management       | `Workflow`, `Task` models · `routers/workflows.py`   |
| §4.3 Endpoint Registry                | `Endpoint` model · `routers/endpoints.py` (+ test)   |
| §4.3 Runtime Env Config               | `EnvironmentSetting` model · `routers/environment_settings.py` |
| §4.4 Multi-Model Support              | `AIModel` model · `routers/ai_models.py`             |
| §4.5 Prompt & Context                 | `Prompt` model · `routers/prompts.py`                |
| §6 Agent Lifecycle                    | `transition` endpoint, snapshot/version history      |
| §7.1 Operational KPIs                 | `dashboard/kpis` endpoint + Dashboard view           |
| §7.2 Quality KPIs                     | Schema compliance, escalation rate                   |
| §7.3 Cost Validation                  | `CostRecord`, `Budget`, cost-summary endpoint        |
| §10 Example execution flow            | `execution_engine.py` (classify → endpoints → model → validate) |

## Domain parameterization (IndraAI / EWA profile)

The default seeded profile is now parameterized for the EWA complaint-analysis
domain:

- Agent: **EWA Complaint Analysis Agent**
- Workflow: **PreAnalysis → AccountTariffCheck → ConsumptionCheck →
  HierarchyCheck → BillingsChecks → PreviousComplaints → Reasoning → Validate**
- Endpoints: `/profileDetails`, `/consumptionDetails`, `/billDetails`,
  `/hierarchyDetails`, `/historicalRccs`
- Default model: **Llama 3 70B (local)**

## Going to production

The places to plug real implementations in:

1. **`execution_engine._simulate_endpoint_call`** — replace with `httpx`
   calls that resolve auth from a real secret manager
2. **`execution_engine._simulate_model_call`** — replace with provider SDKs
   (OpenAI / Anthropic / local model adapters)
3. **Auth** — the `User` table exists but no auth middleware is wired. Add
   OAuth/JWT via FastAPI dependencies
4. **Switch SQLite to Postgres** for concurrent writes — change
   `database.py:DATABASE_URL`, no model changes needed
5. **Workflow visual designer** (Phase 2 of the roadmap) — the data model
   already supports branching/parallel/conditional tasks via `depends_on`
   and `config` JSON fields

## Project structure

```
ai_agent_platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── database.py          # SQLite session
│   │   ├── models.py            # SQLAlchemy ORM (13 tables)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── execution_engine.py  # Workflow runner + simulators
│   │   ├── seed.py              # Sample data
│   │   └── routers/             # 8 FastAPI routers
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── main.js, App.vue, router.js, api.js
    │   ├── components/Sidebar.vue
    │   ├── views/               # 11 view components
    │   └── assets/styles.css
    ├── package.json
    └── vite.config.js
```
