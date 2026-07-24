# Quickstart — your first KCF model in 60 seconds

> **Want the conversational path instead?** [**Knowledge Coding — get
> started**](docs/KNOWLEDGE_CODING.md) connects KCF to your chat LLM (Claude /
> ChatGPT / VS Code / Cursor) so you build apps by describing them. This page is
> the CLI version of the same loop.

This is the shortest path from "I cloned the repo" to "a code generator has a
complete, machine-checked model of my domain." Every command runs against a
model committed in this repo, so you can reproduce it exactly.

**Prerequisites:** Python 3.10+ and `jsonschema` (`pip install jsonschema`, or
`pip install -e .` from the repo root which installs the `kcf` command).

Two ways to invoke the toolchain — pick one and use it throughout:

| If you did… | run the CLI as |
| --- | --- |
| `pip install -e .` (from the public repo root) | `kcf …` |
| nothing (running from a checkout) | `python kcf-oss/tools/kcf.py …` |

Below uses the installed `kcf` form.

---

## The model

We'll use [`tests/domains/business-application.kcf`](tests/domains/business-application.kcf) —
a tiny customer-service domain: one `Customer` entity, a `ServiceAgent` actor, an
`UpdateCustomerWork`, a `CustomerUpdated` event, a `CustomerLifecycle`, and an
`UpdateCustomer` command with full action semantics (idempotency, atomicity,
concurrency, authorization).

## 1. Compile → semantic IR

```bash
kcf compile kcf-oss/tests/domains/business-application.kcf --output model-ir.json --validate
```

`.kcf` text becomes a normalized `model-ir.json` (conforming to
`schemas/model-ir-v1.schema.json`), with source spans. `--validate` runs the
semantic analyzer as it compiles.

## 2. Assess — is it complete enough to build from?

```bash
kcf assess model-ir.json
```

```json
{
  "valid": true,
  "ready": true,
  "checks": { "coverage": { "requiredGaps": 0, "recommendedGaps": 0, "requiredGapIds": [] } }
}
```

`ready: true` is the gate. It means **all** of: valid (no analyzer errors), zero
required coverage gaps, every claimed/required pattern structurally proven, and
every trait resolved to a declared role. Exit code `0`.

> Try it on an *incomplete* model to see the other outcome —
> `kcf assess kcf-oss/tests/fixtures/walkthrough/support-ticket-draft.json`
> reports `ready: false` with a required identity gap (exit code `1`). Then
> `kcf coverage-report <model> --by-concept` tells you exactly what to add.

## 3. Generate an app — with your LLM, for any stack

KCF **stops at the IR**: a complete, machine-checked model is the deliverable.
Turning it into running code hands the IR to **your own LLM**, guided by a
tech-stack-agnostic system prompt and a single-shot example. Code generation is
split into two tiers that meet at the backend's OpenAPI:

1. Install [`codegen/system-prompt.md`](codegen/system-prompt.md) as the system prompt.
2. **Backend** — send [`codegen/generate-backend.md`](codegen/generate-backend.md)
   with your `model-ir.json` + a backend stack's `EXAMPLE.md`
   (`fastapi-sqlmodel-postgres`, `typescript-express-prisma`, `django-drf-postgres`).
   Each exposes a **Swagger/OpenAPI interface by default**.
3. **Frontend** — send [`codegen/generate-frontend.md`](codegen/generate-frontend.md)
   with your `model-ir.json` + the backend's `/openapi.json` + the frontend
   stack's `EXAMPLE.md` (`react-typescript-openapi`). The UI is generated against
   that contract.

Every generation returns the code **plus a coverage self-audit** giving each IR
construct a disposition (realized / delegated / out-of-tier / unsupported) with
`dropped: []`. What each tier realizes for every construct is in
[`codegen/CONSTRUCT_COVERAGE.md`](codegen/CONSTRUCT_COVERAGE.md); the overview is
[`codegen/README.md`](codegen/README.md).

## Where to go next

- **[codegen/](codegen/)** — generate an app from the IR with any LLM, for any stack.

- **[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md)** — the full requirements → ready
  IR → generated app loop, including how to close coverage gaps.
- **[docs/CONCEPTS.md](docs/CONCEPTS.md)** — the mental model (well-formed vs.
  valid vs. complete) and the four semantic layers.
- **[workflows/application-generation/](workflows/application-generation/)** — an
  ordered 16-step prompt package for turning real requirements into a validated
  IR with a coding LLM.
- **[README.md](README.md)** — full architecture, IR contract, and every CLI
  command.
