# KCF — the open knowledge-coding standard

**The new vibe coding is _knowledge coding_ = semantic modeling + vibe coding.**
KCF compiles your domain into a normalized *semantic IR* — structurally validated,
coverage-assessed against explicit obligations, and traceable to its source — then
the LLM vibe-codes from that spec instead of guessing from prose. KCF does not claim
your domain is *complete*; it reports exactly which obligations passed, which declared
scope was covered, which source encodings were confirmed, and what realization
evidence exists (see [docs/CONCEPTS.md](docs/CONCEPTS.md#what-kcf-does-and-does-not-claim)).

**👉 New here? Start with [docs/KNOWLEDGE_CODING.md](docs/KNOWLEDGE_CODING.md)** —
connect KCF to your chat LLM (Claude / ChatGPT / VS Code / Cursor) and build your
first app in ~3 minutes.

Prefer the CLI? Start with **[QUICKSTART.md](QUICKSTART.md)** (a 60-second hello
world), then **[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md)** (requirements → ready
IR → generated app) and **[docs/CONCEPTS.md](docs/CONCEPTS.md)** (the mental
model). To turn a valid IR into an app with the LLM you choose, for your target
stack (the pack is stack-extensible), see
**[codegen/](codegen/)** — or plug KCF into your chat LLM with the
**[MCP server](mcp/)** (`kcf-mcp`). Contributing a grammar change? See
**[docs/EXTENDING.md](docs/EXTENDING.md)**. The rest of this file is the full
architecture and toolchain reference.

```bash
kcf compile tests/domains/business-application.kcf --output model-ir.json --validate
kcf assess model-ir.json            # → { "valid": true, "ready": true, "domainComplete": "not-proven" }
# then hand the ready IR to the LLM you choose, for your target stack (see codegen/)
```

## The six-stage journey (evidence → verified app)

`kcf init --guided` scaffolds an **evidence-first** project and one canonical journey a
person — or a coding agent (Claude Code, Codex) — follows without knowing which
low-level tool to run. `kcf status` always reports the current stage and the **single
recommended next action**, so you never have to discover the workflow from the docs.

| # | Stage | Command | What happens |
|---|-------|---------|--------------|
| 1 | Add evidence | `kcf sources add inputs/` | Drop prose, PDFs, screenshots, diagrams, schemas, transcripts, sample data under `inputs/`; register them (no manual source-JSON). |
| 2 | Elicit | `kcf elicit [--agent claude\|codex]` | Assembles the coding-agent prompt for the registered evidence; the agent authors `model/*.kcf`, asking only the highest-value questions, and does **not** write app code until you approve. |
| 3 | Review | `kcf review --open` | Generates a human-readable `review/model-summary.md` (actors, records, relationships, workflows, lifecycle diagrams, commands, rules, permissions, implied screens, source coverage, inferred knowledge, open questions) — read this before the `.kcf` or the IR. |
| 4 | Approve | `kcf approve --reviewer you [--confirm … --reject … \| --all]` | Sorts constructs into **stated / inferred / unresolved**; your decisions produce a governed IR + a machine-readable review envelope. |
| 5 | Choose a stack | `kcf generate-plan --backend fastapi-sqlmodel-postgres --frontend react-typescript-openapi` | Assembles deterministic backend/frontend prompt packages under `plans/` and explains what each realizes and what remains. KCF packages the prompts; it does not emit the code. |
| 6 | Generate + verify | `kcf verify-project` | After the agent runs the plans, one report card: model validity, required gaps, source coverage, unresolved decisions, realization accounting, and **model/code drift**. |

```bash
kcf init --guided ./order-desk --name OrderDesk
cd order-desk                       # drop files into inputs/, then:
kcf sources add inputs/ && kcf status   # status tells you the next step at every stage
```

Everything above is orchestration over the same engines documented below (compile,
assess, coverage, review-queue, confirm, source-coverage, codegen prompt assembly,
realization verification) — it adds no grammar, IR, or analyzer semantics. The MCP server
(`mcp/`) and the guided project's `START_HERE.md` + `AGENTS.md` present the **same six
stages**, so the CLI, the agent instructions, and the docs never disagree.

> **Maintainers & coding LLMs** should first read the repository
> `LLM_HANDOFF.md`, repository `AGENTS.md`, and this package's `AGENTS.md`. The
> authoritative/generated artifact index and current limitations are in
> `../.llm/`. Contribution guidance is in `CONTRIBUTING.md`.

This package implements the grammar-native semantic architecture described in
the three source whitepapers under `../docs/whitepapers/source/`:

- `Grammar-Native_Semantic_Architecture_Part_I.pdf`
- `Grammar-Native_Semantic_Architecture_Part_II.pdf`
- `Grammar-Native_Semantic_Architecture_Part_III.pdf`

The stack uses ISO/IEC 14977-style EBNF. `KCF` is the semantic metagrammar
and root module. Shared identifiers, references, conditions, expressions,
cardinality, temporal validity, provenance, versions, profiles, capability
contracts, assertions, and runtime instances are defined there once.

The current manifest is grammar-stack `1.11.0`: 29 modules and 580 productions,
with semantic IR `1.0.0`, 6 foundational profile presets, and the `3.0.0` KCF plus
semantic-core semantic-rule catalogue (322 rules; see `semantics/coverage.json` for
the live count and automation breakdown). The authoring surface is comprehensive across all 16
dimension grammars plus the ACTION/RELATIONSHIP algebra (see `docs/AUTHORING.md`). The
manifest, schemas, generated catalogue, and compatibility matrix remain
authoritative when these contracts change.

## Architecture

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Metagrammar | `KCF` | Shared semantic language and universal concept machinery |
| Relationship algebra | `RELATIONSHIP` | Classification, composition, association, identity, participation, dependency, transformation, causation, ordering, governance |
| Action contracts | `ACTION` | Record commands/queries, collection mutations and transformations, effects, scope, selection, transactions, concurrency, retries, authorization, and audit |
| Dimension grammars | `ENTITY`, `ACTOR`, `WORK`, `EVENT`, `LIFECYCLE`, `RULE`, `INFORMATION`, `RESOURCE`, `TEMPORAL`, `SPATIAL`, `ORGANIZATION`, `INTENT`, `REASONING`, `MEASURE`, `LOGIC`, `MATH` | One primary semantic dimension per grammar |
| Compilation | `COMPILATION` | Semantic IR, validation/reasoning/execution plans, emitters, packages, registry entries |
| Operational profiles | `INTEGRATION`, `SECURITY`, `LINEAGE` | Cross-dimensional integration contracts, security/risk/control semantics, lineage, bindings, and cost |
| Emitter profiles | `ARCHITECTURE`, `EXPERIENCE`, `DESIGN`, `ANALYTICS`, `AI` | Technology-facing views that preserve and bind KCF semantics without redefining the root constructs |
| Authoring | `AUTHORING` | Ergonomic textual domain syntax compiled into normalized semantic IR |

The architecture keeps four distinct semantic layers:

1. Grammar definitions define reusable meaning.
2. Domain concept assertions specialize and connect grammar constructs.
3. Runtime instances record actual concepts and relationships.
4. Emitted artifacts realize semantics in implementation technologies.

Do not collapse these layers. In particular, a relationship definition is not a
domain assertion, and a domain assertion is not a runtime relationship instance.

`config/grammar-stack.json` distinguishes `imports`, which are EBNF symbol imports,
from `semanticImports`, which declare cross-module semantic dependencies without
copying productions. The only permitted dependency cycle is the declared
type-only `KCF`/`RELATIONSHIP` cycle.

## Validation and tooling

The unified CLI compiles textual models, validates IR, resolves profiles,
migrates versions, and reports rule coverage. **KCF stops at the semantic IR** —
turning a `ready` IR into code is done with an LLM via the prompt pack in
[`codegen/`](codegen/), for any tech stack:

```powershell
python tools/kcf.py compile tests/domains/business-application.kcf --output model-ir.json --validate
python tools/kcf.py assess model-ir.json
python tools/kcf.py check
```

Run the complete conformance suite:

```powershell
python tools/run_conformance.py
```

Validate the complete stack:

```powershell
python tools/validate_stack.py
```

Check dependency cycles, unreachable productions, nullable repetitions, and
unused grammar imports:

```powershell
python tools/lint_stack.py
```

Check canonical whitespace/line endings, or repair them:

```powershell
python tools/normalize_stack.py
python tools/normalize_stack.py --write
```

Resolve any module into a self-contained, namespace-qualified EBNF grammar:

```powershell
python tools/resolve_stack.py WORK resolved-work.ebnf
```

Generate the machine-readable semantic rule catalogue and validate a normalized
semantic IR model. The catalogue is composed from the standalone shared semantic
core and KCF-local rules; it has no DBML build dependency:

```powershell
python tools/build_semantic_rules.py
python tools/semantic_analyzer.py tests\fixtures\valid\transportation-ir.json
```

Classify semantic compatibility between two model versions:

```powershell
python tools/semantic_delta.py tests\fixtures\valid\transportation-ir.json tests\fixtures\delta\transportation-v2-ir.json
```

Module filenames, start productions, syntactic dependencies, semantic
dependencies, and allowed type-only cycles are normative in
`config/grammar-stack.json`. `semantics/SEMANTIC_VALIDATION.md` is the human/LLM-readable
specification. `semantics/semantic-rules.json`, governed by
`semantics/semantic-rules.schema.json`, is the machine-readable catalogue. Stable rule
IDs connect both representations to analyzer diagnostics.

## Semantic IR contract

The reference analyzer consumes JSON semantic IR governed by
`schemas/model-ir-v1.schema.json`. Textual `.kcf` models compile into this IR
with source spans. Core collections are
`concepts`, `relationships`, `lifecycles`, `actions`, `collectionTransforms`,
`processes`, `events`, `resources`, `allocations`, `plans`, `emitters`,
`runtimeRequirements`, and `runtimeBindings`. Organizational-knowledge
collections are `organizations`, `information`, `rules`, `policies`,
`reasoning`, `assertions`, `identityResolutions`, and `knowledgeQueries`.
Extension objects are
`integration`, `security`, `lineage`, `architecture`, `experience`, `design`,
`analytics`, and `ai`. The fixtures are normative examples of a conforming
shape and a deliberately invalid shape under `tests/fixtures/`.

Profile presets under `profiles/presets/` calculate syntactic and semantic
dependency closure automatically. The IR is the stopping point: code generation
(the LLM codegen pack in `codegen/`) consumes the IR and must diagnose unsupported
meaning instead of silently
dropping it (decision D-005).

For governed organizational knowledge, use the `organizational-knowledge`
preset and read `docs/ORGANIZATIONAL_KNOWLEDGE.md`.

## Coding-LLM application workflow

`workflows/application-generation/` contains a reusable, ordered prompt package for
turning domain requirements into a validated semantic IR and then generating an
application with the LLM codegen pack. Start with its `README.md`, configure
`variables.example.json`, install `00-shared-system-prompt.md` as persistent
context, and run prompts `01` through `16` in order.

## Design decisions

- Concepts normally have one primary kind; cross-dimensional meaning is modeled
  with references, relationships, and traits.
- Entity CRUD is treated as an emitted implementation of declarative identity,
  mutation, composition, membership, archival, provenance, and validation.
- Lifecycle state evolution and Work process flow remain separate.
- Events are immutable facts; corrections are new events or provenance updates.
- Capability, skill, tool, actor, and work remain distinct.
- Information represents encoded meaning; Entity represents a managed subject.
- Output produced by work is distinct from Intent/outcome achieved.
- Relationship inverses are derived from one canonical storage orientation.
- Runtime execution binds semantic capability contracts to implementations;
  implementation code is not embedded in grammar definitions.
- Code generation (the LLM codegen pack) must report unsupported semantics rather
  than silently dropping them (D-005).

## License

Apache-2.0. © 2026 Composable Holdings Inc. KCF is created and maintained by
Composable Holdings Inc. See `../LICENSE` (or the repository-root `LICENSE` in
the public distribution) and `NOTICE`.
