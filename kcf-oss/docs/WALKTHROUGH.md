# Walkthrough: from requirements to a code-generator-ready model

This is a runnable, end-to-end tutorial for someone learning KCF. It shows how to
turn application requirements into a normalized semantic model (the IR), reach
**sufficient modeling coverage**, and hand that IR to an LLM code generator.

Every command below runs against fixtures committed in this repository, so you can
reproduce the whole flow exactly. The draft-vs-ready outcome is also asserted in
the release gate (`tools/run_conformance.py`), so this example cannot silently rot.

- Sample models: `kcf-oss/tests/fixtures/walkthrough/support-ticket-draft.json`
  (deliberately incomplete) and `support-ticket-ready.json` (complete).
- Run everything from the repository root. Prerequisite: Python 3 with
  `jsonschema` installed.

---

## 0. The mental model

KCF separates three questions that are usually conflated:

| Question | Answered by | Example failure |
|---|---|---|
| Is it **well-formed**? | the grammar / compiler | a syntax error in `.kcf` |
| Is it **valid**? | the semantic analyzer | a relationship pointing at a missing concept |
| Is it **complete**? | knowledge coverage | an entity with no identity or lifecycle |

A model can be valid yet incomplete. "Sufficient coverage" is the third axis, and
it is a single measured verdict: **`kcf.py assess` reports `ready: true`** when the
model is valid, has **zero required coverage gaps**, has every claimed/required
pattern structurally proven, and has every trait resolving to a declared role.
Recommended gaps (lifecycle, full CRUD, set/bulk, transformation) may remain —
you decide whether they matter.

**You can hand a *valid* model to a code generator** — it needn't be fully
`ready`. The remaining coverage gaps travel with the IR as *enrichment guidance*:
the LLM realizes the sensible ones (or you fill them as synthetic knowledge first)
and notes the rest. `ready: true` is the completeness goal, not a hard gate on
generation.

---

## 1. Get requirements into a model (the "front doors")

You do not hand-write IR from scratch. Pick the entry path that matches your input;
all of them produce a `model-ir.json`:

| Your input | Front door | Start with |
|---|---|---|
| A named process ("procure-to-pay") | pattern-seeded synthesis | workflow `02b-pattern-seeded-synthesis.md`, `kcf.py scaffold` |
| Validated natural-language notes | NL extraction | workflow `01b-natural-language-extraction.md`, `kcf.py ingest` |
| A diagram / org chart / form | document extraction | workflow `01c-document-extraction.md`, `kcf.py import-mermaid`, `kcf.py document-check` |
| You want to author directly | textual `.kcf` or IR | `kcf.py compile` |

All are LLM-assisted except the deterministic importers. Whatever the door, the
result is a first-draft IR — which is where this walkthrough begins.

---

## 2. Assess the draft — is it sufficient yet?

```bash
python kcf-oss/tools/kcf.py assess kcf-oss/tests/fixtures/walkthrough/support-ticket-draft.json
```

Expected (abridged):

```json
{ "valid": true, "ready": false,
  "checks": { "coverage": { "requiredGaps": 1, "recommendedGaps": 5,
                            "requiredGapIds": ["coverage.entity.identity"] } } }
```

Exit code `1` (not ready). The model is **valid but incomplete**: something that
must have an identity does not (a *required* gap). The *recommended* gaps — full
CRUD, a set/bulk op, a lifecycle, a transformation — are enrichment you (or the
LLM) can add later; they don't block generation from a valid model. `assess`
composes four checks — validity, coverage, pattern proof, and role resolution —
into one `ready` verdict.

## 3. Locate the gaps, concept by concept

```bash
python kcf-oss/tools/kcf.py coverage-report \
  kcf-oss/tests/fixtures/walkthrough/support-ticket-draft.json --by-concept
```

Expected (abridged):

```
support.Customer -> [ (crud, recommended), (set-operation, recommended), (lifecycle, recommended) ]
support.Ticket   -> [ (identity, required), (crud, recommended), (set-operation, recommended), (lifecycle, recommended) ]
(model)          -> [ (transformation, recommended) ]
```

This is the dimension-by-dimension review view: the one *required* gap is that
**Ticket** lacks an identity. The rest — CRUD, a set/bulk op, a lifecycle, a
model-level transformation — are *recommended* enrichment you can add now or let
the generator fill. You know exactly what's essential vs. nice-to-have.

## 4. Close the gaps

Fix the one **required** gap, then enrich as far as you like (by hand, or have
the LLM fill and an SME confirm — see `review-queue`/`confirm`). Compared with the
draft, the ready model:

- adds an identity attribute on `Ticket` (`ticketId: UUID identity`) — closes the
  only *required* gap, so `assess` reports `ready: true`;
- as recommended enrichment, gives `Ticket` full **CRUD**, a **set** operation
  (`BulkAssignTickets`), a **data-transformation** (`TicketProjection`), and a
  lifecycle `Open -> InProgress -> Resolved -> Closed` wired to `ResolveTicket`.

`Customer` is **reference data** synced from elsewhere, so it's marked read-only
(`metadata.mutability = "read-only"`) — the escape hatch that exempts an entity
from the CRUD/set/transformation recommendations.

For large or synthesized models you loop steps 2–4, and add the source-relative
checks (`kcf.py ingest`, `kcf.py source-coverage`) plus the by-segment SME review
(`kcf.py review-queue --by-segment`, `kcf.py confirm`) before re-assessing.

## 5. Re-assess — sufficient coverage reached

```bash
python kcf-oss/tools/kcf.py assess kcf-oss/tests/fixtures/walkthrough/support-ticket-ready.json
```

Expected (abridged):

```json
{ "valid": true, "ready": true,
  "checks": { "coverage": { "requiredGaps": 0, "recommendedGaps": 1 } } }
```

Exit code `0`. `ready: true` is the gate: valid, **zero required gaps**, patterns
proven, roles resolved. The one remaining recommended gap (Customer lifecycle) is
tolerated by design — you stay in control of "complete enough."

## 6. Hand the IR to the code generator

The `ready` `model-ir.json` **is** the comprehensive, machine-checked context the
LLM code generator builds from: every entity, attribute, typed relationship,
lifecycle state machine, and action contract (idempotency / atomicity /
concurrency / authorization) is explicit.

You do this with the **[codegen pack](../codegen/)**: install its system prompt,
pick your stack (or define one), paste the `ready` `model-ir.json` and the stack's
single-shot example, and your own LLM realizes the IR in that stack — for any
technology — returning a **coverage self-audit** that lists every IR construct as
realized / delegated / out-of-tier / unsupported, with `dropped: []`.

`dropped: []` is the guarantee that **nothing in the model was silently lost** in
the handoff (decision D-005). The LLM builds against a specification that is
complete, consistent, and traceable — not against prose it must guess at. (KCF
stops at the IR; deterministic emitters that consume the same IR are part of the
separate commercial platform.)

---

## The loop, on one screen

```
requirements ──(01b NL / 01c document / 02b pattern / author)──▶ model-ir.json
      ▲                                                              │
      │                    kcf.py assess ◀───────────────────────────┘
      │                          │ ready:false → coverage-report --by-concept → fix
      └──────────────────────────┘ (loop until required gaps = 0)
                                 │ ready:true   (= sufficient coverage)
                                 ▼
                    hand model-ir.json to your LLM (codegen/) for any stack
                    (coverage self-audit = proof of a lossless handoff)
```

## Command reference

| Command | Purpose |
|---|---|
| `kcf.py compile <src.kcf> -o model-ir.json` | author textually → IR |
| `kcf.py ingest <model> <source-doc> <trace>` | NL/document front door: one readiness+source report |
| `kcf.py scaffold --profile <pattern>` | pattern-seeding brief (roles + obligations) |
| `kcf.py assess <model>` | the readiness gate (`ready: true`?) |
| `kcf.py coverage-report <model> --by-concept` | locate gaps, per concept |
| `kcf.py pattern-check <model>` | prove claimed/required patterns structurally |
| `kcf.py roles-check <model>` | traits resolve to declared pattern roles? |
| `kcf.py review-queue <model> [--by-segment <trace>]` | tier synthetic knowledge for SME review |
| `kcf.py confirm <model> --reviewer X --as-of T --decisions d.json` | promote confirmed synthetic → fact |
| (then) hand the `ready` IR to your LLM via `codegen/` | generate code for any stack, with a coverage self-audit |

## What "sufficient coverage" means, precisely

`assess` reports `ready: true` iff **all** of:

1. `valid` — the semantic analyzer reports no error diagnostics;
2. `coverage.requiredGaps == 0` — every required knowledge obligation is met;
3. `patterns` — no `requiredButAbsent`, `claimedButUnproven`, or
   `requiredWithoutContract`;
4. `roles.unknownTraits == []` — every concept trait resolves to a declared role.

Recommended and info gaps never block `ready`; they are advisories you resolve at
your discretion. This walkthrough is asserted end-to-end in the release gate: the
draft must be *not ready* (with the identity gap) and the fixed model must be
*ready* with a lossless emitter handoff.
