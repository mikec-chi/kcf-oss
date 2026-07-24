# House conventions (code generation) — example

Copy this to `codegen/overrides.md`, edit it to your team's standards, and inject
it as the highest-priority layer of code generation. It **tunes how** the code is
generated; it never changes **what** the model means.

**Where it plugs in — same content, three surfaces:**

- **MCP** — set once in your host config, then every generation uses it:
  ```jsonc
  { "mcpServers": { "kcf": { "command": "kcf-mcp",
      "env": { "KCF_CODEGEN_OVERRIDES": "/abs/path/codegen/overrides.md" } } } }
  ```
  or per call: `codegen_prompt(source, stack, instructions="…")`.
- **Playground** — paste it into the *House conventions* box before "Build prompt".
- **Manual templates** — paste it into the *House conventions* section of
  `generate-backend.md` / `generate-frontend.md`.

Contract (all three surfaces enforce it): house conventions override the
single-shot example and the defaults **where they conflict** — but they never
override the action contracts or the backend's OpenAPI, never drop declared
meaning, and the **coverage self-audit still must hold**.

Keep it short and imperative. Everything below is an example — replace it.

---

## Language & framework

- Python 3.12+, FastAPI, **async SQLAlchemy 2.0** (not SQLModel), Pydantic v2.
- Package layout: `app/api`, `app/domain`, `app/repositories`, `app/services`.
- Type-hint everything; `from __future__ import annotations` in every module.

## Persistence

- Postgres; **snake_case** tables and columns; plural table names.
- UUID v7 primary keys named `id`; every table has `created_at` / `updated_at`.
- All writes go through a repository; no ORM objects above the service layer.

## API

- Version the API under `/api/v1`; keep Swagger UI at `/docs`.
- Errors use RFC 9457 `application/problem+json`.
- Cursor pagination on every collection query (`?limit=&cursor=`).

## Auth

- JWT bearer; enforce each action's `authorization` as a FastAPI dependency.
- Deny by default; never trust a client-supplied actor/role.

## Observability & tests

- OpenTelemetry spans around every command handler; structured JSON logs.
- pytest + httpx; one happy-path and one authorization-denied test per action.

## House rules

- No business logic in routers; routers call services only.
- Every enum/status in the IR becomes a real enum type, not a bare string.
