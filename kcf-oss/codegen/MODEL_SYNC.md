# Keep the model and the code in sync — the living-model protocol

Knowledge coding only pays off if the model **stays** the source of truth. The
moment code carries meaning the model doesn't — a new field, a status, a rule, an
endpoint the model never declared — you've drifted back to vibe coding, and the
model becomes a lie. This is the protocol a code-generation LLM follows to prevent
that, in both directions.

> **One rule underneath all of it:** the model (`*.kcf` → compiled `model-ir.json`)
> is the specification. Code is a *projection* of the model. If the meaning isn't
> in the model, it isn't real yet — put it in the model first.

## The loop

```
        ┌─────────────────────────────────────────────┐
        │   model  (*.kcf → model-ir.json)  ← truth    │
        └───────────────┬──────────────▲───────────────┘
             generate    │              │  capture (model-first)
            from model    ▼              │  when intent changes
        ┌─────────────────────────────────────────────┐
        │   code  (each artifact traces to a construct) │
        └─────────────────────────────────────────────┘
```

Two directions, both mandatory:

1. **Generate from the model** — every artifact you write traces to an IR
   construct (or is a flagged *enriched* standard piece). Consult the model before
   you write.
2. **Capture back into the model (model-first)** — when the developer's intent
   changes the *meaning* of the app, update the model **before** the code.

## Before you write or change code

1. **Read the relevant model first.** Find the concept / action / rule / lifecycle
   the change concerns in `model-ir.json` (or ask the KCF tools: `assess`,
   `coverage`, `authoring_reference`). Generate against *that*, not a guess.
2. **Trace every artifact.** A table, field, endpoint, screen, state, or guard must
   map to an IR element. Annotate it with the construct it realizes (e.g.
   `# realizes customer.UpdateCustomer` / `// realizes customer.CustomerLifecycle`)
   so the mapping stays visible and reviewable.
3. **Never introduce un-modeled meaning silently.** No entity, attribute, status,
   relationship, business rule, or authorization that isn't in the model. Standard
   scaffolding you add for a *recommended* gap (e.g. missing CRUD) is allowed but
   must be flagged **enriched** in the coverage self-audit — never as declared.

## When the change alters meaning → model-first

If the developer asks for something that changes what the app *means* — a new
entity or field, a new command/query, a changed lifecycle, a new or altered rule /
policy / contract, a new relationship — **stop and update the model first**:

1. Edit the `.kcf` (use `authoring-brief.md` for syntax; add only what was stated —
   ask if unsure).
2. `kcf compile <model>.kcf -o model-ir.json --validate` — fix any errors.
3. `kcf assess model-ir.json` — the model must stay **valid**; note any new gaps.
4. *Then* generate/modify the code from the updated IR, tracing to the new
   constructs.

Doing it in this order is what prevents drift: the model never lags the code.

## Reconcile the model after direct code edits (vibe coding)

Developers *will* vibe-code straight into the code — that's the point. When code has
been changed directly (by the developer or another agent) without going through the
model, the model now lags reality, and your **first job before doing anything else
is to make the model true again**. Reconcile, don't build on drift:

1. **Detect what changed.** Diff the code against the last known state (e.g.
   `git diff`), or scan the touched files. Look specifically for changes to
   *meaning*: new/renamed entities or fields, new columns/migrations, new or changed
   endpoints/handlers, new statuses or transitions, new validation/authorization
   rules, new roles.
2. **Classify each change:**
   - **Meaning change** (a new field, action, rule, status, relationship, etc.) →
     it belongs in the model. Update the `.kcf` to describe it, `compile --validate`,
     `assess`. The model now reflects what the code does.
   - **Pure implementation** (refactor, styling, perf, library swap — no change to
     what the app *means*) → leave the model alone; it's correctly silent on this.
   - **Accidental drift** (meaning the developer did *not* intend — a stray field, a
     bypassed rule) → flag it to the developer; remove it or model it, their call.
3. **Confirm with the developer when intent is ambiguous.** Don't silently promote a
   vibe-coded guess into the canonical model — surface *"the code now does X; should
   the model say so?"* and let them decide. Never fabricate model meaning.
4. **Re-baseline.** Once reconciled, the model is authoritative again; continue
   model-first from here.

Reconciliation is the safety valve that lets vibe coding and a trustworthy model
coexist: code may lead momentarily, but the model is always brought back into
agreement before the next feature is built.

## Drift check (run before committing, and when in doubt)

Confirm the model and code still agree:

- **Recompile + reassess:** `kcf compile … --validate` then `kcf assess` — still valid?
- **Model → code:** is every construct in the model realized (or intentionally
  deferred/enriched, and recorded)? Regenerate the **coverage self-audit** and make
  sure `dropped: []`.
- **Code → model:** scan the diff for meaning the model doesn't have — a new column,
  status, endpoint, role, or rule. Each hit is either a bug (remove it) or a real
  intent change (add it to the model, model-first, then keep the code).
- **Contracts intact:** lifecycle transitions, `idempotency`/`atomicity`/
  `concurrency`/`authorization`, `mutate` sets, immutability — still honored?

Anything that fails is drift. Fix it by moving the meaning into the model, not by
patching the code around it.

## Why this matters

The model is what makes the app inspectable, regenerable, and safe to change with an
LLM. Keep it authoritative and every future generation — new stack, new feature,
new teammate's LLM — builds from the same trustworthy spec. Let it drift and you're
back to guessing from prose.
