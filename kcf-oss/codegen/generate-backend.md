# KCF code-generation — backend prompt template

*Send this as the user turn, after installing `system-prompt.md` as the system
prompt. Fill the `[BRACKETED]` placeholders and paste the matching **backend**
stack's `EXAMPLE.md` (`stacks/<stack>/`, `tier: backend`). The `model-ir.json` is
the one `kcf assess` reported `ready: true`.*

---

**Tier:** backend
**Target stack:** `[STACK ID — e.g. fastapi-sqlmodel-postgres]`

*(Generate from a **valid** model — it need not be fully `ready`. Optionally paste
`kcf coverage-report <model> --by-concept` output as enrichment guidance:
`required` gaps matter; `recommended` ones you realize or note.)*

Generate the backend for **[CAPABILITY — e.g. the whole model, or the
`UpdateCustomer` command]** from the KCF IR below. Follow the single-shot
example's layering, naming, ORM style, validation, and test shape exactly.

## The model (authoritative specification)

```json
[PASTE THE CONTENTS OF model-ir.json HERE]
```

## The single-shot example to imitate

```
[PASTE THE CONTENTS OF stacks/<stack>/EXAMPLE.md HERE]
```

## House conventions (HIGHEST PRIORITY — optional)

*Paste your team's `codegen/overrides.md` here (see `overrides.example.md`), or
delete this section. These override the single-shot example and the defaults
below where they conflict — but never the action contracts, and the coverage
self-audit still must hold.*

```
[PASTE YOUR HOUSE CONVENTIONS HERE, OR DELETE THIS SECTION]
```

## Instructions

- Realize **only** what the IR declares; add nothing, drop nothing.
- Realize **each action by its `operation` + `scope`** — record CRUD
  (create/read/replace/update/patch/delete/upsert/exists/count), set/bulk
  (`bulk-*`, `synchronize`), and every `collectionTransforms` entry
  (filter/map/group/aggregate/join/…). Don't collapse them to "update".
- Honor every action contract (idempotency / atomicity / concurrency /
  authorization / retry / mutations) and every lifecycle transition literally.
- Cover every construct in the model per `CONSTRUCT_COVERAGE.md`; `experience`
  and `design` are out-of-tier.
- **Expose an OpenAPI 3 document + Swagger UI by default** (the stack's
  conventional path). Every command/query action and entity resource must appear
  in it — this is the contract the frontend will consume.
- Pull in a geo binding only if the model uses `SPATIAL`, and a task queue only
  for long-running `processes`/`plans`.
- Output files as labelled code blocks (one per file, with its path).
- Finish with the **Coverage self-audit** (`tier: backend`; every construct →
  realized / out-of-tier / unsupported; `dropped: []`).
