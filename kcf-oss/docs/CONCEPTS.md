# Concepts — the KCF mental model

This is the web-readable orientation to KCF. It replaces "go read three PDFs"
with the ideas you actually need to be productive. The formal treatment is in
the source whitepapers (`../../docs/whitepapers/source/`); this page is the map.

## The one idea

An LLM (or any code generator) is only as good as the **model of your domain**
it is given. KCF makes that model a first-class, machine-checked artifact — the
*semantic IR* — instead of leaving it implicit in prose. You reach a model that
is *complete enough to build from*, then hand it off with a proof that nothing
was lost.

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

## The loop you'll actually run

```
requirements ──(author / NL / document / pattern front door)──▶ model-ir.json
      ▲                                                              │
      │                    kcf assess ◀───────────────────────────────┘
      │                          │ ready:false → coverage-report --by-concept → fix
      └──────────────────────────┘  (loop until required gaps = 0)
                                 │ ready:true  (= sufficient coverage)
                                 ▼
                    hand model-ir.json to your LLM (codegen/) for any stack
                    (coverage self-audit = proof of a lossless handoff)
```

## Why "lossless handoff" is the whole point

Whatever consumes the IR — the LLM codegen pack, or a separate commercial platform —
must account for every construct and either realize it or explicitly mark it
*unsupported*; it may **never silently drop it** (decision D-005). `dropped: []`
is the machine-checkable promise that what you generate reflects the entire
model. That is the difference between generating from a specification and
generating from a guess.

## Where code generation fits

KCF deliberately **stops at the IR**. The IR is the durable, machine-checked
specification; generating code is a separate, swappable step. The open path is
the **[codegen pack](../codegen/)** — a stack-agnostic system prompt plus a
single-shot example per stack that your own LLM uses to realize the IR in any
technology, returning a coverage self-audit that proves nothing was dropped.
(A separate commercial platform builds on the same IR; the IR is the
contract either target consumes.)

## Next

- **[QUICKSTART](../QUICKSTART.md)** — run the loop in 60 seconds.
- **[codegen/](../codegen/)** — generate an app from the IR with any LLM, for any stack.
- **[WALKTHROUGH](WALKTHROUGH.md)** — the full requirements → ready IR tutorial.
- **[README](../README.md)** — the complete IR contract and CLI reference.
