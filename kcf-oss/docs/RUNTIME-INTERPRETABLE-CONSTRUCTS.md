# Runtime-interpretable constructs and how they are realized

KCF's grammars are built from meaning-bearing, sentence-like constructs. This
reference catalogues them, gives the natural-language sentence each forms, and
classifies **how each is realized** at build/run time into three modes:

- **`deterministic`** — the content is a structured, machine-evaluable expression;
  a **downstream generator compiles it** to a guard, query, or state machine. No
  LLM. (KCF-OSS stops at the IR + this classification; realization is done by the
  OSS `codegen/` pack or any generator built on the IR.)
- **`codegen`** — the content is a free-text but *checkable* predicate; a
  **code-generation LLM turns it into a runtime artifact once** (a validator/query
  function), which is reviewed and then runs deterministically.
- **`runtime-llm`** — the content is an open-ended directive (a goal, an argument,
  a judgement); it is **carried as-is and interpreted live by an LLM at runtime**.

The dividing line is *not the construct type* but whether a given `condition` /
`proposition` / `where` slot holds a **structured expression** (→ deterministic)
or **prose** (→ codegen or runtime-llm). `kcf.py execution-plan <model>` computes
this classification for a model (schema `execution-plan-v1`); an explicit
`executionMode` on a construct overrides the default.

Scope: KCF-OSS provides only the *classification* below — it names no proprietary
component and ships no runtime. How each disposition is realized (deterministic
generation, build-time code-gen, or a runtime interpreter) is downstream of the IR.

## The sentence-like constructs (grammar-level)

| Construct | Grammar | NL sentence it forms | Interpret / Execute |
|---|---|---|---|
| Relationship assertion `assert rel(a, b)` | KCF metagrammar | "*a rel b*" (SVO fact) | interpret |
| `forward` / `inverse` phrasing on a relationship | RELATIONSHIP | the English verb to read the triple each way ("manages" / "is managed by") | interpret |
| `term "…" maps-to ref` (lexical binding) | KCF metagrammar | grounds a natural-language term to a construct (locale + confidence) | interpret |
| Action contract (`effect` + `operation` + `target`) | ACTION | "*Update the ticket*" (imperative, full contract) | execute |
| `execute:` / `validate:` / `reason:` clause; `runtime-capability` + `bind … to …` | KCF metagrammar | "*at runtime, run this capability*" | execute |
| Rule (`condition` + `effect` + `mode`) | RULE | "*If ⟨condition⟩ then it is OBLIGATORY/PERMITTED/PROHIBITED that ⟨effect⟩*" | execute |
| Modal proposition / predicate | LOGIC | "*necessarily/possibly/permitted P*"; `predicate(x){ … }` | interpret/execute |
| Quantified expression (`all x in S : …`) with `is`/`contains`/`matches`/`before`/`after`/`within` | KCF metagrammar | "*every order has a positive total*" (controlled NL / FOL) | interpret/execute |
| Intent (`desired-state`, `success`, `tradeoff X against Y`) | INTENT | "*the goal is ⟨state⟩; trade cost against speed*" | interpret |
| Reasoning (`proposition`, `premise`, `conclusion`, `method`) | REASONING | "*Premises A, B; therefore C, deductively*" | interpret |
| Assertion (`subject`/`predicate`/`object`/`status`) | knowledge IR | "*Discount requiresApproval LegalOfficer*" | interpret |
| Knowledge query (`select`, `where`, `world`, `negation`) | AUTHORING/IR | "*select the rules where ⟨where⟩ under open-world*" | interpret/execute |

## How each is realized (the three modes)

### Deterministic (no LLM)
Everything that is fully **structural**, plus condition slots holding a
**structured expression**. KCF-OSS classifies these as deterministically
realizable and stops there; a downstream generator (the OSS `codegen/` pack, or
any generator built on the IR) produces the artifact:

- Concepts, attributes, typed relationships, lifecycles (state machines), action
  contracts, collection transforms, org reporting — a generator produces these
  mechanically from the IR.
- A `condition` / `where` / `predicate` written symbolically
  (`discount.rate <= 0.2`, `ruleKind == CONSTRAINT`, `all x in S : x.total > 0`)
  compiles to a guard or query. `execution-plan` marks these `deterministic`.
- Assertions (`subject predicate object`) are a graph triple by construction and
  project deterministically.

### Build-time code-gen artifact (LLM once, then deterministic)
Condition slots holding **free-text but checkable predicates** — statements that
*can* be frozen into a function but aren't symbolic yet:

- Rule conditions like *"a discount over the standard threshold requires
  management approval"*; transform predicates; NL knowledge-query `where` clauses.
- A code-generation LLM turns each into a runtime artifact (a validator/query
  function) **once**, which is reviewed (it flows through the same
  synthetic → SME-confirm governance) and then runs deterministically. This is the
  bridge between the two extremes: LLM effort at build time, determinism at runtime.
- `execution-plan` marks these `codegen`.

### Runtime LLM interpretation (carried as-is)
Constructs whose meaning is genuinely **open-ended** — goals, arguments,
judgements that cannot be frozen into a fixed function:

- Intent `desired-state`, reasoning `proposition`/`conclusion`, and any condition an
  author marks `executionMode: runtime-llm`.
- These are carried verbatim in the IR and interpreted live by an LLM at runtime
  (the agentic path). `execution-plan` marks these `runtime-llm`.

## Worked example

`kcf.py execution-plan kcf-oss/tests/fixtures/execution/discount-rules.json`:

```
deterministic | rule  DiscountCap        discount.rate <= 0.2                 (structured expression)
codegen       | rule  ApprovalPolicy     a discount over the standard ...     (free-text predicate)
runtime-llm   | rule  ManualReviewRule   amount > 1000            [override]   (executionMode: runtime-llm)
runtime-llm   | reasoning MarginRationale large discounts erode margin ...    (open-ended argument)
deterministic | query ActiveConstraints  ruleKind == CONSTRAINT               (structured expression)
summary: { deterministic: 2, codegen: 1, runtimeLlm: 2 }
```

Note `ManualReviewRule`: its condition *is* structured (`amount > 1000`) so the
default would be `deterministic`, but the author set `executionMode: runtime-llm`
to force live interpretation — the override wins.

## The design bias

The structured detector is **conservative on purpose**: only unambiguous symbolic
signals (`==`, `<=`, `>`, `implies`, quantifier-with-colon) mark content as
deterministic. English words like *is*, *and*, *in* occur in prose, so they never
by themselves promote a condition to deterministic. The safe default is that prose
needs an LLM (codegen or runtime) — KCF never silently assumes a sentence is
machine-evaluable. This keeps the static guarantees honest: the analyzer treats a
free-text condition as opaque, and `execution-plan` tells you exactly which
constructs escape deterministic emission and how they should be realized instead.

This classification is asserted in the release gate, so it cannot silently rot.
