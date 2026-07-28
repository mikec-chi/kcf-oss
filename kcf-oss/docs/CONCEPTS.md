# Concepts — the KCF mental model

This is the web-readable orientation to KCF. It replaces "go read three PDFs"
with the ideas you actually need to be productive. The formal treatment is in
the source whitepapers (`../../docs/whitepapers/source/`); this page is the map.

## The one idea

An LLM (or any code generator) is only as good as the **model of your domain**
it is given. KCF makes that model a first-class, validated and coverage-assessed
artifact — the *semantic IR* — instead of leaving it implicit in prose. You reach a
model that meets its **required-obligation readiness** (sufficient coverage for
handoff — not a claim that the domain is complete; see the claim section below), then
hand it off with an **accounted realization manifest** you can verify at an explicit
evidence level.

## Three questions KCF keeps separate

Most tools conflate these; KCF answers them with three different mechanisms:

| Question | Answered by | Example failure |
| --- | --- | --- |
| Is it **well-formed**? | the grammar / compiler | a syntax error in `.kcf` |
| Is it **valid**? | the semantic analyzer | a relationship pointing at a missing concept |
| Is it **complete**? | knowledge coverage (`kcf assess`) | an entity with no identity or lifecycle |

A model can be *valid* yet *incomplete*. "Sufficient coverage" is the third
axis, and `kcf assess` collapses it to one verdict: **`ready: true`** iff the
model is valid, has zero required coverage gaps, has every claimed/required
pattern structurally proven, and has every trait resolved to a declared role.
Recommended gaps (lifecycle, CRUD, set/bulk, transformation) are advisories. You
can hand a **valid** model to a code generator — it needn't be fully `ready`; the
coverage gaps travel with it as enrichment guidance (the LLM realizes the sensible
ones or you fill them as synthetic knowledge first). `ready: true` is the
completeness goal, not a hard gate.

## Four semantic layers (never collapse them)

KCF deliberately keeps four layers distinct:

1. **Grammar definitions** define reusable meaning (what an `entity`, a
   `relationship`, a `lifecycle` *is*).
2. **Domain concept assertions** specialize and connect those constructs (your
   `Customer`, your `CustomerLifecycle`).
3. **Runtime instances** record actual concepts and relationships that occurred.
4. **Emitted artifacts** realize the semantics in a target technology (SQL, an
   OpenAPI spec, tests).

A relationship *definition* is not a domain *assertion*, and a domain assertion
is not a runtime *instance*. Keeping these apart is what makes the model
reusable and the handoff lossless.

## The dimensions

Meaning is decomposed into one grammar per primary semantic **dimension**, all
rooted in the `KCF` metagrammar and the `RELATIONSHIP` algebra:

`ENTITY`, `ACTOR`, `WORK`, `EVENT`, `LIFECYCLE`, `RULE`, `INFORMATION`,
`RESOURCE`, `TEMPORAL`, `SPATIAL`, `ORGANIZATION`, `INTENT`, `REASONING`,
`MEASURE`, `LOGIC`, `MATH`.

A concept normally has **one primary kind**; cross-dimensional meaning is
modeled with references, typed relationships, and traits — not by making a
concept be two things at once. A few consequences worth internalizing:

- **Entity CRUD** is an *emitted implementation* of declarative identity,
  mutation, composition, membership, archival, provenance, and validation — not
  a modeling primitive you write by hand.
- **Lifecycle** (state evolution) and **Work** (process flow) stay separate.
- **Events** are immutable facts; a correction is a new event, not an edit.
- **Information** (encoded meaning) is distinct from **Entity** (a managed
  subject); **Output** of work is distinct from **Intent**/outcome.
- **Record nature** (master / transactional / reference / config) is **not** a
  primitive. Persistence languages (e.g. DBML's `category`) tag the table with a
  flat enum; KCF factors that role into orthogonal dimensions — *lifecycle* (moves
  through states?), *event* (emits immutable facts?), *work/transformation* (changed
  by processes?), *mutability* (read-only?) — so "transactional-ness" is *emergent
  shape*, not a stored label; at the pattern layer, `implements master-data` asserts
  it as a bundle of obligations. You *may* still carry the modeler's stated class as
  advisory `metadata.category` (ground truth from the source, a codegen driver), and
  the analyzer **reconciles** it against the shape — but promoting it to a first-class
  field would re-import the denormalized dual-source-of-truth KCF avoids.
- **Aggregate root vs part** (DDD) is likewise *emergent*, not a primitive. `COMPOSITION`
  already encodes whole-part ownership, so an entity's containment role is **derived**: a
  *pure part* (→ a subtab on its parent's detail) is a `COMPOSITION` target with no
  children and no independent inbound reference; everything else is an aggregate *root*
  (→ top-level nav). An advisory `metadata.containment` (`root`/`part`) may override the
  derivation for an ambiguous case and is analyzer-reconciled against the structure —
  the same pattern as `category`. Model the ownership with `COMPOSITION`; don't reach for
  a flat tag first.

## The loop you'll actually run

```
requirements ──(author / NL / document / pattern front door)──▶ model-ir.json
      ▲                                                              │
      │                    kcf assess ◀───────────────────────────────┘
      │                          │ ready:false → coverage-report --by-concept → fix
      └──────────────────────────┘  (loop until required gaps = 0)
                                 │ ready:true  (= sufficient coverage)
                                 ▼
                    hand model-ir.json to the LLM you choose (codegen/), for your stack
                    (realization manifest = accounted-for handoff, at an evidence level)
```

## What KCF does — and does not — claim

KCF is deliberately careful about what it asserts. It does **not** claim your domain
is complete. It reports, each on its own axis:

- **Structural validity** — the model is well-formed and passes the semantic analyzer.
- **Required-obligation readiness** (`kcf assess`) — the configured required coverage
  obligations for the declared profile(s) are met. `ready: true` means *sufficient
  coverage for handoff*, and the report also carries `domainComplete: "not-proven"` —
  coverage is a necessary, never a sufficient, condition for real completeness.
- **Closed-world completeness** (`kcf completeness`) — measured against an *explicitly
  declared scope*, never an open world; it names the blockers when it is not complete.
- **Source confirmation** (`kcf source-coverage`) — *source-complete* (linkage) is
  distinct from *source-confirmed* (a human reviewed the encoding, governed by
  reviewer/time/disposition and a verified excerpt hash).
- **Semantic enforcement** — which rules are *mechanically enforced* vs still manual
  (`kcf automation-report`, coverage by risk); most rules are not yet automated.
- **Realization evidence** (`kcf verify-realization`) — every IR identity is accounted
  for, at a reported *evidence level* (`accounted` without a repo → `test-present`).

The honest one-liner: *KCF tells you which structural obligations passed, which
declared scope was covered, which source encodings were confirmed, which rules were
mechanically enforced, and what realization evidence exists — not that your domain is
done.*

## Why an accounted handoff is the point

Whatever consumes the IR — the LLM codegen pack, or a separate commercial platform —
must account for every construct and either realize it or explicitly mark it
*unsupported*; it may **never silently drop it** (decision D-005). The realization
manifest (`kcf verify-realization`) makes that accounting machine-checkable: every IR
identity has a disposition, realized ones cite artifacts, and gaps carry a reason. Its
*evidence level* is honest about how far the check went — `accounted` (declared) is not
the same as `test-present` (files, symbols, and tests verified against the repo). That
is the difference between generating from a checked specification and from a guess.

## Where code generation fits

KCF deliberately **stops at the IR**. The IR is the durable, validated,
coverage-assessed specification; generating code is a separate, swappable step. The
open path is the **[codegen pack](../codegen/)** — a stack-agnostic system prompt plus
a single-shot example per stack that the LLM you choose uses to realize the IR, ships
several stacks and is extensible to others, and returns a realization manifest whose
handoff you verify (`kcf verify-realization`) at a reported evidence level. (A separate
commercial platform builds on the same IR; the IR is the contract either target
consumes.)

## Next

- **[QUICKSTART](../QUICKSTART.md)** — run the loop in 60 seconds.
- **[codegen/](../codegen/)** — generate an app from the IR with the LLM you choose, for your target stack (stack-extensible).
- **[WALKTHROUGH](WALKTHROUGH.md)** — the full requirements → ready IR tutorial.
- **[README](../README.md)** — the complete IR contract and CLI reference.
