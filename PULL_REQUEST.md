## Summary

Adds Tracework, a full-stack AI data investigation agent with a FastAPI backend, OpenAI Responses API tool loop, SQLite/PostgreSQL integration, a generated commerce demo dataset, and a responsive React evidence console.

## What changed

- Added schema inspection, read-only SQL execution, structured result analysis, and trace capture.
- Added a stateless Responses API loop that carries prior output items and function results between calls.
- Added a deterministic no-key demo path for revenue, region, churn, and refund questions.
- Added SQL AST validation, statement/row caps, known dangerous-function rejection, and database read-only transactions.
- Made SQLite demo seeding safe across concurrent workers with an immediate transaction.
- Added API/UI tests, CI, containers, environment examples, and project documentation.

## Assumptions

- Python 3.11+, Node 22+, and a server-side OpenAI key for live mode.
- Production PostgreSQL uses a least-privilege, read-only database role.
- The configured database contains business-safe tables that the agent is allowed to inspect.
- The frontend and API origins are explicitly configured for CORS.

## Out of scope by design

- Authentication, multi-tenancy, row-level authorization, and investigation persistence.
- Browser-provided connection strings or database writes.
- A semantic business-metrics layer or guarantees that every question is answerable.
- A complete allowlist of side-effect-free PostgreSQL/user-defined functions.
- Hard cancellation of pathological SQLite queries.

## Human review requested

- Verify the production database role cannot write or access sensitive schemas.
- Confirm the chosen model, retention posture (`store=False`), and data-governance policy are acceptable.
- Review which tables/columns should be allowlisted before connecting company data.
- Exercise representative production questions and validate metric definitions with a domain owner.
- Confirm deployment origins, secrets, rate limiting, logging, and alerting.

## Validation

- `pytest`
- `ruff check backend`
- `npm run lint`
- `npm run build`
- Manual API smoke request in demo mode
