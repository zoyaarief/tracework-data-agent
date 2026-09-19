# Tracework: AI Data Investigation Agent

**Ask a business question in plain English. Tracework inspects the schema, runs read-only
SQL, and answers with the evidence rows and an execution trace behind it.**

[![CI](https://github.com/zoyaarief/tracework-data-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/zoyaarief/tracework-data-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-Responses%20API-412991?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue)

![Tracework: ask the data, follow the evidence](public/og.png)

Tracework is a full-stack agent for questions such as "Which region has the highest average
order value?" An LLM calls three tools in a bounded loop: inspect the schema, execute SQL, and
profile the result. Every query passes an SQL AST guard and runs inside a read-only
transaction. The response includes the answer, the rows that support it, and a trace of each
step with its row count and timing.

It runs immediately with no API key: a deterministic demo investigator answers against a
generated SQLite commerce dataset. Adding an OpenAI key switches to the live Responses API
agent, which also works against PostgreSQL.

## Highlights

- **Tool-calling agent loop** on the OpenAI Responses API: strict function schemas,
  `parallel_tool_calls=False`, a step limit, `store=False`, and a stateless loop that carries
  prior output items and `function_call_output`s between calls.
- **Answers must rest on evidence.** The agent is rejected if it answers without running a
  query, and the UI shows the exact rows the answer rests on.
- **Defense-in-depth SQL safety**: `sqlglot` AST validation (one `SELECT` only, no
  writes/DDL/transactions), a denylist of dangerous functions, literal-only `LIMIT`s capped
  at a configured maximum, and read-only execution (`PRAGMA query_only` on SQLite,
  `SET TRANSACTION READ ONLY` plus a statement timeout on PostgreSQL).
- **Transparent traces, not hidden reasoning.** The trace records tool names, row counts,
  timings, and safe observations, not the model's chain of thought.
- **Regression tests from a review pass**: a round of review fixes (connection-pool poisoning
  by read-only mode, decimal and boolean profiling, reporting the effective row limit, and a
  UI that never shows sample figures as evidence after a failed run) each shipped with tests.
- **CI on every push**: pytest (including a real PostgreSQL 16 service), Ruff, Vitest, Oxlint,
  and a production build.

## How it works

```mermaid
flowchart LR
    UI["React investigation console"] -->|"POST /api/investigations"| API["FastAPI service"]
    API --> SEL{"OpenAI key<br/>configured?"}
    SEL -->|no| DEMO["Deterministic demo investigator"]
    SEL -->|yes| AGENT["OpenAI Responses agent<br/>(bounded tool loop)"]
    DEMO --> TOOLS
    AGENT --> TOOLS["Tools<br/>inspect_schema · execute_sql · analyze_results"]
    TOOLS --> GUARD["SQL AST guard<br/>+ read-only transaction"]
    GUARD --> DB[("SQLite / PostgreSQL")]
    API -->|"answer · evidence rows · trace"| UI
```

The demo dataset is generated on first start: 400 customers across regions and segments,
about six months of orders and order items, products, and refunds. In demo mode the
investigator recognizes four kinds of question (regional average order value, churn by
month, refund outliers by product, and quarter-over-quarter category growth) and runs the
same tools and guard as the live agent.

## Tech stack

| Layer | Technology |
|---|---|
| Agent and API | Python 3.11+, FastAPI, Pydantic Settings, OpenAI Responses API |
| Data | SQLAlchemy 2, `sqlglot`, SQLite, PostgreSQL (`psycopg`) |
| Frontend | React 19, TypeScript, Vite ([vinext](https://www.npmjs.com/package/vinext)), Tailwind CSS 4, shadcn/ui |
| Quality | pytest, Ruff, Vitest, Testing Library, Oxlint, GitHub Actions |
| Packaging | Dockerfiles for the API and web app |

## Quick start

Requirements: Python 3.11+, Node.js 22+, and npm.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm ci
```

Start the API, then the web app in a second terminal:

```bash
uvicorn backend.app.main:app --reload --port 8000
npm run dev
```

Open `http://localhost:3000`. FastAPI's interactive docs are at `http://localhost:8000/docs`.
The first API start creates `backend/data/commerce.db`.

### Enable the OpenAI agent

Set the key on the server only:

```bash
TRACEWORK_OPENAI_API_KEY=your_key_here
TRACEWORK_OPENAI_MODEL=gpt-5-mini
```

Never prefix the key with `NEXT_PUBLIC_`, which would expose it to browser code. The loop
follows the Responses API pattern of custom function tools, feeding each
`function_call_output` into the next request. See the
[OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).

### Connect PostgreSQL

Create a least-privilege login with `SELECT` access only, then set:

```bash
TRACEWORK_DATABASE_URL=postgresql+psycopg://tracework_reader:password@localhost/analytics
```

The demo seed is SQLite-only, and without an API key the deterministic questions are written
for the demo schema. Use live agent mode for your own PostgreSQL schema.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Database and agent-mode status |
| `GET` | `/api/schema` | Visible tables, columns, and relationships |
| `POST` | `/api/investigations` | Run a question through the agent |

```bash
curl -X POST http://localhost:8000/api/investigations \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which region has the highest average order value?"}'
```

The response includes `answer`, `columns`, `evidence` (the result rows), `trace` (one entry
per step), `mode` (`demo` or `openai`), and the effective `row_limit`.

## Testing

```bash
pytest               # API, SQL guard, agent loop, regressions, PostgreSQL dialect
ruff check backend
npm test             # Vitest + Testing Library UI tests
npm run lint
npm run build
```

CI runs all of these on every push and pull request. The PostgreSQL tests run when
`TRACEWORK_TEST_POSTGRES_URL` is set, as it is in CI.

## Security model

The application rejects anything other than a single `SELECT`, multiple statements, known
dangerous functions, dynamic or non-positive `LIMIT`s, and queries above the row cap.
SQLite runs with `PRAGMA query_only`, and PostgreSQL runs inside a read-only transaction with
a statement timeout.

This is defense in depth, not a SQL sandbox. A production deployment would also need a
database role limited to approved schemas and tables, network restrictions, authentication
and tenant authorization, request auditing, and infrastructure timeouts. A function denylist
cannot prove that arbitrary user-defined functions are side-effect free.

## Limitations

- No authentication, tenant isolation, schema allowlist, or saved investigation history.
- No browser-supplied database URLs, by design.
- The data may not be able to answer every question. Demo mode recognizes only the four
  included question types and falls back to quarterly category growth.
- SQLite has no true execution interrupt for pathological read queries.

## Repository layout

```text
app/                 React investigation console (+ UI tests)
components/ui/       shadcn/ui primitives
backend/app/         FastAPI app, agent loop, tools, SQL guard, database, demo seed
backend/tests/       API, SQL safety, PostgreSQL, concurrency, and agent-loop tests
.github/workflows/   CI
```

## License

[MIT](LICENSE)
