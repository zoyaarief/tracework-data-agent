# Tracework — Data Investigation AI Agent

Tracework is a portfolio-grade data investigation agent. It receives a natural-language business question, inspects a relational schema, executes model-selected read-only SQL, analyzes intermediate results, and returns a concise answer with evidence and a traceable execution log.

The app runs immediately in deterministic demo mode against a generated SQLite commerce dataset. Add an OpenAI API key to enable the iterative Responses API tool-calling loop. PostgreSQL is supported through SQLAlchemy for live agent mode.

![Tracework social preview](public/og.png)

## Architecture

```text
React investigation console
          │ POST /api/investigations
          ▼
FastAPI service ──► agent selector
                       ├── demo investigator (no key)
                       └── OpenAI Responses agent
                                  │
                      inspect_schema / execute_sql / analyze_results
                                  │
                                  ▼
                  SQL AST guard + read-only transaction
                                  │
                           SQLite / PostgreSQL
```

The trace exposes operational facts—tool names, row counts, timing, and safe observations—not hidden chain-of-thought.

## What is included

- Iterative OpenAI Responses API function-calling loop with bounded steps
- Deterministic offline agent for an instantly runnable demo
- Schema inspection, safe SQL execution, result profiling, and evidence-backed answers
- SQL AST validation, single-statement enforcement, automatic row limits, forbidden-function checks, and read-only transactions
- SQLite sample data generator with process-safe initialization
- PostgreSQL connection support
- FastAPI endpoints, Pydantic validation, CORS configuration, and generic error boundaries
- Responsive React console with answer, evidence table, and execution trace
- Docker, GitHub Actions, Ruff, Pytest, Oxlint, and production builds

## Quick start

Requirements: Python 3.11+, Node.js 22+, and npm.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm ci
```

Start the API:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

In another terminal, start the web app:

```bash
npm run dev
```

Open `http://localhost:3000`. FastAPI's interactive docs are at `http://localhost:8000/docs`.

The first API startup creates `backend/data/commerce.db` with 400 customers, six months of orders, order items, products, and refunds.

## Enable the OpenAI agent

Set the key only on the server:

```bash
TRACEWORK_OPENAI_API_KEY=your_key_here
TRACEWORK_OPENAI_MODEL=gpt-5-mini
```

Do not prefix the API key with `NEXT_PUBLIC_`; that would expose it to browser code. The implementation follows the official Responses API model of providing custom function tools and feeding each `function_call_output` into the next response. See the [official OpenAI Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).

## Use PostgreSQL

Create a least-privilege login with `SELECT` access only, then configure:

```bash
TRACEWORK_DATABASE_URL=postgresql+psycopg://tracework_reader:password@localhost/analytics
```

The demo seed is SQLite-only. Without an API key, the deterministic churn query is also SQLite-specific; use live agent mode for a PostgreSQL schema.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Database and agent-mode status |
| `GET` | `/api/schema` | Inspect visible tables and relationships |
| `POST` | `/api/investigations` | Run a question through the agent |

Example:

```bash
curl -X POST http://localhost:8000/api/investigations \
  -H 'Content-Type: application/json' \
  -d '{"question":"Which region has the highest average order value?"}'
```

## Checks

```bash
pytest
ruff check backend
npm run lint
npm run build
```

CI runs all four on every push and pull request.

## Security boundaries

The application rejects non-`SELECT` statements, multiple statements, dangerous known functions, dynamic or non-positive limits, and queries above the configured row cap. SQLite uses `PRAGMA query_only`; PostgreSQL uses a read-only transaction and statement timeout.

This is defense in depth, not a SQL sandbox. Production deployments must also use a database role limited to approved schemas/tables, restrict network access, add authentication and tenant authorization, audit requests, and enforce infrastructure timeouts. A function denylist cannot prove arbitrary user-defined functions are side-effect free.

## Deliberate limitations

- No user authentication, tenant isolation, schema allowlist, or persisted investigation history
- No arbitrary browser-supplied database URLs
- No guarantee that available data can answer every question
- Demo mode recognizes only the included portfolio questions; unsupported questions fall back to quarterly category growth
- SQLite does not yet have a true execution interrupt for pathological read queries
- The hosted frontend demonstrates the interface when no separately deployed API is reachable

## Repository layout

```text
app/                 React investigation console
components/ui/       shadcn interface primitives
backend/app/         FastAPI, agent loop, tools, guard, and data seed
backend/tests/       API, SQL safety, concurrency, and agent-loop tests
.github/workflows/   Continuous integration
```

## License

MIT
