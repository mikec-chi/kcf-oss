<!--
Codegen pack — copy to <pack-name>/overrides.md and edit.
Header (for the sibling README.md):
  Title:   e.g. "FastAPI async, strict"
  Author:  <you>
  Stack:   <the stack id this targets — e.g. fastapi-sqlmodel-postgres, or "any backend">
  Use when: <the situation this fits>
-->

# House conventions (code generation) — <pack name>

Apply these; they override the single-shot example and defaults where they
conflict. Still honor the action contracts, drop nothing, and finish with the
coverage self-audit.

## Language & framework

- <e.g. Python 3.12+, FastAPI, async SQLAlchemy 2.0, Pydantic v2.>

## Persistence

- <e.g. Postgres; snake_case tables; UUID v7 PKs; created_at/updated_at everywhere.>

## API

- <e.g. version under /api/v1; RFC 9457 problem+json errors; cursor pagination.>

## Auth

- <e.g. JWT bearer; enforce each action's `authorization` as a dependency; deny by default.>

## Observability & tests

- <e.g. OpenTelemetry spans per command; one happy-path + one authz-denied test per action.>

## House rules

- <e.g. no business logic in routers; every IR enum becomes a real enum type.>
