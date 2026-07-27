# KCF code-generation — platform prompt template

*Send this as the user turn, after installing `system-prompt.md` as the system
prompt. Fill the `[BRACKETED]` placeholders and paste the matching **platform**
stack's `EXAMPLE.md` (`stacks/<stack>/`, `tier: platform`). The `model-ir.json` is
the one `kcf assess` reported `ready: true`.*

---

**Tier:** platform
**Target stack:** `[STACK ID — e.g. netsuite-suitecloud-sdf]`

*(Generate from a **valid** model — it need not be fully `ready`. Optionally paste
`kcf coverage-report <model> --by-concept` output as enrichment guidance:
`required` gaps matter; `recommended` ones you realize or note.)*

Generate the platform customization project for **[CAPABILITY — e.g. the whole
model]** from the KCF IR below. Follow the single-shot example's object layout,
field-type mapping, script structure, naming, and deployment packaging exactly.

## The model (authoritative specification)

```json
[PASTE THE CONTENTS OF model-ir.json HERE]
```

## The single-shot example to imitate

```
[PASTE THE CONTENTS OF stacks/<stack>/EXAMPLE.md HERE]
```

## House conventions (HIGHEST PRIORITY — optional)

*Paste your team's `codegen/overrides.md` here (script-id prefixes, role naming,
which field types to prefer, sandbox vs. production deploy target…), or delete
this section. These override the single-shot example and defaults where they
conflict — but never the action contracts, and the coverage self-audit still
must hold.*

```
[PASTE YOUR HOUSE CONVENTIONS HERE, OR DELETE THIS SECTION]
```

## Instructions

- Realize **only** what the IR declares; add nothing, drop nothing.
- **No OpenAPI/Swagger** — the platform owns integration. Emit the platform's
  native objects + scripts and **package them for its deployment framework**
  (e.g. an SDF project + `deploy.xml`, deployable with the platform's CLI).
- Map each ENTITY → a custom data object; each attribute → a custom field with
  the platform's matching **field type** (see the stack's conventions).
- Realize **each action by its `operation` + `scope`** on the platform's script
  surface (e.g. a RESTlet) — record CRUD, set/bulk, and every
  `collectionTransforms` entry — honoring idempotency / atomicity / concurrency /
  the `mutate` set / authorization literally. Don't collapse them to "update".
- Realize the **lifecycle** two ways that agree: the platform's native
  workflow/state mechanism (UI transitions) **and** a script-level guard that
  rejects undeclared transitions (so programmatic/import changes are guarded too).
- rules → platform validations (server-side authoritative; mirror simple ones in
  a client script for instant feedback). policy → the platform's roles/permissions
  **plus** an in-script deny/permit gate.
- Immutable EVENTs → an append-only object written from an after-save hook (grant
  create-only on it). data-transformations → the platform's saved search/query.
- `experience`/`design` are delegated to native forms unless declared — note them
  delegated, not dropped.
- If the model uses **tail** constructs (measures, temporal/spatial, logic/math,
  information/resource/organization/reasoning, rich events, profile blocks), also
  paste `COOKBOOK.md` and realize each per its platform column.
- Output files as labelled code blocks (one per file, with its project path).
- Finish with the **Coverage self-audit** (`tier: platform`; every construct →
  realized / delegated / unsupported; `dropped: []`).
