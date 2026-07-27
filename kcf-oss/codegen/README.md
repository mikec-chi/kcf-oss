# KCF code generation — generate an app from the IR, with any LLM, for any stack

KCF stops at the **semantic IR**: a complete, machine-checked model of your
domain (`kcf assess` said `ready: true`). This pack turns that IR into working
code using an LLM you already have — for whatever tech stack you choose — instead
of a fixed, per-framework code generator that rots.

**Why prompts + examples?**
The IR is the durable contract, and **OSS stops there**. A tech-stack-agnostic
**system prompt** plus a **single-shot example** per stack lets any capable LLM
target any stack and keep up with framework changes, while the IR guarantees the
model it builds from is complete and lossless.

## Two tiers that connect via OpenAPI

- **backend** stacks generate persistence, the full action contract,
  rules/policies, events, and an **OpenAPI/Swagger interface by default**.
- **frontend** stacks generate the UI **against that OpenAPI** — a typed client,
  entity views/forms, lifecycle controls, and role-gated components — delegating
  everything the server owns to the API.

The backend's Swagger document is the seam: generate the backend first, point the
frontend generation at its `/openapi.json`, and the two halves line up because
both derive from the same IR. What each tier realizes for **every** IR construct
(and the completeness verdict for these stacks) is in
[`CONSTRUCT_COVERAGE.md`](CONSTRUCT_COVERAGE.md).

### A third tier: platform

Some targets aren't a backend or a frontend you *build* — they're a SaaS/low-code
**platform** you *customize*, one that already owns the datastore, runtime, and UI
(NetSuite, Salesforce, …). A **platform** stack (`tier: platform`) maps the same IR
onto the platform's native objects + scripts and packages them for its deployment
framework — **no OpenAPI mandate**. It's a standalone target: realize the same
`ready` model as, say, a NetSuite SDF project *instead of* (or alongside) the
backend/frontend pair. See `CONSTRUCT_COVERAGE.md` → "Platform target — NetSuite".

## What's here

| File | Purpose |
|---|---|
| `system-prompt.md` | The durable, tier-aware contract. Install as the LLM's system prompt. Defines how to read `model-ir-v1`, the non-negotiable rules (generate only what's declared, cover every construct, honor action contracts/lifecycles), the Swagger/OpenAPI mandate, and the required **coverage self-audit**. |
| `CONSTRUCT_COVERAGE.md` | The audit: every IR construct → its backend and frontend representation, plus the completeness verdict. |
| `COOKBOOK.md` | Worked realization of every **tail** construct (quantitative/knowledge/cross-cutting) per tier — the target the stack examples don't show. Rides along automatically when a model uses one. |
| `design-system-default.md` | Brand-neutral, accessible baseline theme (tokens + component conventions) the generator applies when a model declares no `design` block. |
| `generate-backend.md` / `generate-frontend.md` | The per-run user prompts. Backend: paste the IR + example. Frontend: paste the IR + the **backend's OpenAPI** + example. |
| `stacks/<id>/` | A shipped stack: `stack.json` (`stack-target-v1`, incl. `tier`) + `EXAMPLE.md` (the same reference model realized in that stack). |
| `stack-target.schema.json` | The `stack-target-v1` schema. Author your own `stack.json` to target a stack we don't ship. |
| `overrides.example.md` | A starter set of **house conventions** (language, ORM, auth, naming…) you copy to `overrides.md` and inject to tune *how* code is generated. See "Tune the generated code" below. |

## Tune the generated code (house conventions)

The single-shot example fixes the *shape* of the output, but your team has its own
standards — a different ORM, an auth pattern, naming rules, required
observability. Inject them as a **highest-priority "House conventions" layer**
that overrides the example and defaults **where they conflict** — while the action
contracts, the "drop nothing" rule, and the coverage self-audit still hold.

Same content, three surfaces:

- **MCP** — set `KCF_CODEGEN_OVERRIDES` to your `overrides.md` in the host config
  (applies to every generation), or pass `codegen_prompt(source, stack,
  instructions="…")` per call. Both are merged.
- **Playground** — paste them into the *House conventions* box before building.
- **Manual templates** — paste them into the *House conventions* section of
  `generate-backend.md` / `generate-frontend.md`.

Start from [`overrides.example.md`](overrides.example.md): copy it to
`overrides.md`, trim it to your standards, keep it short and imperative. (To tune
*elicitation* — the questions asked while modeling — see
[`../mcp/elicitation.example.md`](../mcp/elicitation.example.md).)

## Shipped stacks

**Backend** (each exposes Swagger by default):
- **`fastapi-sqlmodel-postgres`** — Python · FastAPI · SQLModel · PostgreSQL · `/docs`
- **`typescript-express-prisma`** — TypeScript · Express · Prisma · swagger-ui at `/docs`
- **`django-drf-postgres`** — Python · Django + DRF · drf-spectacular at `/api/docs`

**Frontend** (binds to a backend's OpenAPI):
- **`react-typescript-openapi`** — React · TypeScript · TanStack Query · openapi-typescript client

**Platform** (customizations inside a SaaS/low-code platform — no OpenAPI; the
platform owns datastore/runtime/UI):
- **`netsuite-suitecloud-sdf`** — NetSuite · SuiteCloud SDF · SuiteScript 2.1 ·
  custom records/fields, a SuiteFlow workflow, a role, a saved search, and a
  RESTlet, packaged as an SDF project (`suitecloud project:deploy`)

Every stack example realizes the **same** reference model
(`../tests/domains/business-application.kcf`) so backend and frontend line up and
you can compare stacks apples-to-apples; the model is a committed golden fixture,
so it can't rot. It deliberately exercises the mainstream constructs — full CRUD +
`upsert` + `bulk-update`, a data-transformation, a rule, and a policy — so each
example demonstrates all of them (see [`CONSTRUCT_COVERAGE.md`](CONSTRUCT_COVERAGE.md)).

### Reference models — mainstream vs. the full grammar

The stack examples cover the **mainstream**. The rest of the grammar (the
quantitative, knowledge, and cross-cutting dimensions) is exercised by a set of
committed, golden-locked **tail reference models**, and realized construct-by-construct
in [`COOKBOOK.md`](COOKBOOK.md) so a codegen LLM has a worked target for every one:

| Reference model | Exercises |
|---|---|
| `business-application.kcf` | **mainstream** — ENTITY/ACTOR/WORK/EVENT, lifecycle, relationships, the action contract (CRUD/upsert/bulk), a data-transformation, a rule, a policy (the stack examples) |
| `entity-rich.kcf` | rich ENTITY — references/compositions/embedded collections, an inline lifecycle, an entity-embedded **`mutation`** |
| `quantitative.kcf` | **INTENT**, **TEMPORAL**+`calendar`, **SPATIAL**+`geometry`/`route`, **LOGIC** (`proposition`/`predicate`), **MATH** (`formula`/`function`/`optimize`/`distribution`/`simulation`), **RESOURCE** |
| `analytics-ai.kcf` | **MEASURE**+`unit`, **REASONING**, **INFORMATION** |
| `capability-skill.kcf` | **capability**/**skill**, **ORGANIZATION**, standalone **authority** |
| `profiles.kcf` | all 8 cross-cutting **profile blocks** (`integration`/`security`/`lineage`/`architecture`/`experience`/`design`/`analytics`/`ai`) → `ir[section]` |

Each is analyzer-valid and compiles to IR (verified). `COOKBOOK.md` shows, per
construct, the backend / frontend / platform realization — pull it in for whatever
tail constructs a real model uses.

## Use it in four steps

```bash
# 1. get a ready IR (see ../QUICKSTART.md)
kcf compile ../tests/domains/business-application.kcf -o model-ir.json --validate
kcf assess model-ir.json          # → ready: true

# 2. install codegen/system-prompt.md as your LLM's system prompt
# 3. BACKEND: send generate-backend.md with model-ir.json + a backend stack's
#    EXAMPLE.md. You get a service that exposes /openapi.json (Swagger).
# 4. FRONTEND: send generate-frontend.md with model-ir.json + the backend's
#    /openapi.json + a frontend stack's EXAMPLE.md. You get a UI bound to it.
```

Each generation returns the implementation **plus a coverage self-audit** that
gives every IR construct a disposition (realized / delegated / out-of-tier /
unsupported) with `dropped: []` — a lossless-handoff discipline mirroring the
IR's own guarantee.

## Add your own stack

1. Copy a `stacks/<id>/` folder of the same **tier**.
2. Edit `stack.json` (validate against `stack-target.schema.json`): set `tier`
   (`backend`/`frontend`), your language/framework/orm/db, `apiDocs` (how the
   OpenAPI is exposed or consumed), and a short list of conventions.
3. Rewrite `EXAMPLE.md` — realize the reference `business-application` model in
   your stack, faithfully honoring its lifecycle and the `UpdateCustomer` action
   contract (backend) or binding to the backend OpenAPI (frontend). That worked
   example *is* the teaching signal for the LLM.
4. Check it against [`CONSTRUCT_COVERAGE.md`](CONSTRUCT_COVERAGE.md): your example
   should show how the tier handles each relevant construct.
5. PRs adding high-quality stacks are welcome (see `../../CONTRIBUTING.md`).
