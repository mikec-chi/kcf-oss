# KCF code-generation — frontend prompt template

*Send this as the user turn, after installing `system-prompt.md` as the system
prompt. Fill the `[BRACKETED]` placeholders and paste the matching **frontend**
stack's `EXAMPLE.md` (`stacks/<stack>/`, `tier: frontend`). You provide two
inputs: the KCF IR (meaning + UX intent) and the **backend's OpenAPI document**
(the actual API surface to bind to).*

---

**Tier:** frontend
**Target stack:** `[STACK ID — e.g. react-typescript-openapi]`

*(Generate from a **valid** model — it need not be fully `ready`. Optionally paste
`kcf coverage-report <model> --by-concept` output as enrichment guidance:
`required` gaps matter; `recommended` ones you realize or note.)*

Generate the frontend for **[CAPABILITY — e.g. the whole model, or the Customer
screens]** from the KCF IR below, bound to the backend OpenAPI that follows.
Follow the single-shot example's structure, data-fetching, and component idioms
exactly.

## The model (meaning + UX intent)

```json
[PASTE THE CONTENTS OF model-ir.json HERE]
```

## The backend OpenAPI document (the API you must call)

```json
[PASTE THE BACKEND'S OpenAPI JSON HERE — from the backend's /docs or /api/schema.
 Generate the typed client from THIS document.]
```

## The single-shot example to imitate

```
[PASTE THE CONTENTS OF stacks/<stack>/EXAMPLE.md HERE]
```

## House conventions (HIGHEST PRIORITY — optional)

*Paste your team's `codegen/overrides.md` here (see `overrides.example.md`), or
delete this section. These override the single-shot example and the defaults
below where they conflict — but never what the backend OpenAPI owns, and the
coverage self-audit still must hold.*

```
[PASTE YOUR HOUSE CONVENTIONS HERE, OR DELETE THIS SECTION]
```

## Instructions

- **Generate a typed API client from the OpenAPI document** and call it for all
  data and actions. Do not hand-roll requests that bypass the contract, and do
  not invent endpoints the OpenAPI does not contain.
- Realize the frontend-owned constructs per `CONSTRUCT_COVERAGE.md`: entity
  lists/detail/forms; **each action by its operation** — create→form, read/query→
  detail/list, update/patch→edit form (mutate-set fields only), delete→control,
  `bulk-*`→multi-select action, count/aggregate/transform→summary/filtered views —
  each calling the matching API operation and passing the concurrency token;
  **lifecycle controls that offer only the transitions legal from the current
  state**; events as feeds/timelines; MEASURE/analytics as dashboards; role-gated
  UI from ACTOR/policies.
- **Delegate everything the server owns** — persistence, the action contract,
  policy authority. Mirror validation/permission only for UX feedback; the server
  remains the source of truth.
- Add a charting lib only if the model uses `MEASURE`/`analytics`, and a map lib
  only for `SPATIAL`.
- If the model uses **tail** constructs (measures, temporal/spatial, logic/math,
  information/resource/organization/reasoning, rich events, profile blocks), also
  paste `COOKBOOK.md` and realize each per its frontend column.
- Output files as labelled code blocks (one per file, with its path).
- Finish with the **Coverage self-audit** (`tier: frontend`; every construct →
  realized / delegated / out-of-tier / unsupported; `dropped: []`).
