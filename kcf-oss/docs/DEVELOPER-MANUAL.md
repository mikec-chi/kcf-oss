# KCF-OSS developer manual

> **Current contract:** grammar stack 1.11.0, semantic IR 1.0.0, and semantic
> catalogue 3.0.0. KCF produces a normalized, validated, coverage-assessed,
> source-traceable semantic IR. KCF stops at the IR; an LLM using `codegen/`
> generates application code and returns a realization manifest.

## 1. Development model

```text
requirements and sources
        ↓
KCF semantic model
        ↓
normalized semantic IR
        ↓
validity, coverage, source, pattern, and role checks
        ↓
reviewed organizational knowledge
        ↓
LLM code generation for a selected stack
        ↓
realization manifest and native application tests
```

The model is the durable source of domain meaning. Generated code is one
technology-specific realization.

Keep four layers separate:

1. grammar definitions;
2. domain concept assertions;
3. runtime instances;
4. generated artifacts.

Do not embed implementation code in grammar definitions, treat assertions as runtime
records, or reverse-engineer the semantic source of truth from generated code.

## 2. What KCF verdicts mean

| Verdict | Meaning |
|---|---|
| Schema-valid | The artifact has the required shape. |
| Semantically valid | Automated analyzer rules found no error-level violation. |
| Ready | Valid, zero required coverage gaps, required/claimed patterns proven, and traits resolve to roles. |
| Source-complete | The supplied trace accounts for the declared source and model constructs. |
| Source-confirmed | Source mappings contain governed review evidence. |
| Closed-world complete | Complete only against a declared scope whose evidence was evaluated. |
| Realization accounted | Every semantic identity has a manifest disposition. |
| Test-present | Referenced artifacts, symbols, and tests are present in a repository. |

KCF does not prove that the real-world domain is complete or correct, that a present
test passes, that generated behavior works, or that an application is secure and
production-ready. `ready: true` is a model handoff verdict.

## 3. Repository map

| Path | Responsibility |
|---|---|
| `grammars/` | KCF, relationship, action, dimensions, profiles, compilation, and AUTHORING EBNF. |
| `config/grammar-stack.json` | Module inventory, dependencies, start symbols, and stack version. |
| `schemas/model-ir-v1.schema.json` | Public normalized IR contract. |
| `compiler/` | AUTHORING lexer, parser, AST, normalization, and compilation. |
| `tools/kcf.py` | Unified CLI. |
| `semantics/` | Semantic rules and generated rule/coverage catalogues. |
| `profiles/presets/` | Six foundational presets. |
| `config/pattern-contracts/` | Domain-neutral pattern contracts and role vocabulary declarations. |
| `config/document-profiles/` | Guided extraction profiles for structured source documents. |
| `tests/domains/` | Textual reference models and compiler goldens. |
| `tests/fixtures/` | Validation, coverage, source, merge, and regression fixtures. |
| `workflows/application-generation/` | Ordered LLM-assisted modeling workflow. |
| `codegen/` | LLM generation contract, examples, cookbook, and coverage audit. |
| `mcp/` | Agent-accessible modeling and generation-prompt server. |

The commercial platform is downstream. KCF must not depend on it or contain its
proprietary code or branding.

## 4. Install and verify

From a source checkout:

```powershell
python -m pip install "jsonschema>=4"
python tools/kcf.py check
```

In the standalone public distribution:

```powershell
python -m pip install -e .
kcf --help
```

Optional MCP support:

```powershell
python -m pip install -e ".[mcp]"
kcf-mcp
```

Examples below use `python tools/kcf.py`. Installed users can substitute `kcf`.

## 5. Choose an authoring front door

| Input | Path |
|---|---|
| Direct semantic authoring | `.kcf` then `compile` |
| Relational schema | `import-dbml` |
| Mermaid flowchart | `import-mermaid` |
| Segmented prose | LLM extraction plus source document/trace, then `ingest` — guided by the `prose` document profile |
| Image / scan / screenshot | Vision transcription to segments, then extraction — guided by the `image` document profile |
| Form, org chart, flowchart, or structured document | Document profile (`form`/`org-chart`/`flowchart`) plus reviewed extraction |
| Reusable pattern | `scaffold` plus pattern-seeded authoring |
| Several domain models | Compile separately, then `merge` |
| Existing IR | `validate`, `assess`, and compatibility checks |

Prefer deterministic imports for machine-readable input. Preserve provenance whenever
interpretation is required.

## 6. Author textual KCF

```kcf
kcf model SupportDesk profile business-application {
  namespace support;

  entity Ticket {
    identity ticketId: UUID;
    required title: String;
    required status: String;
  }

  actor Agent { }
  work ManageTicketWork { }

  rule TicketAccess {
    kind CONSTRAINT;
    condition "the agent is assigned to the ticket";
    effect ManageTicketWork;
    applies-to Ticket;
    authority Agent;
  }

  policy TicketPolicy {
    authority Agent;
    rule TicketAccess;
    default-conflict deny-overrides;
  }

  command CreateTicket {
    operation create;
    scope record;
    target Ticket;
    input one;
    output one;
    idempotency conditional;
    idempotency-key requestId;
    atomicity atomic;
    authorization support.TicketPolicy;
  }

  query GetTicket {
    operation read;
    scope record;
    target Ticket;
    selection identity;
    input one;
    output one;
  }

  lifecycle TicketLifecycle for Ticket {
    initial Open;
    terminal Resolved;
    transition Open -> Resolved;
  }
}
```

Compile:

```powershell
python tools/kcf.py compile .\support-desk.kcf `
  --output .\support-desk-ir.json `
  --validate
```

Use [AUTHORING.md](AUTHORING.md) for the complete syntax. AUTHORING is ergonomic
syntax compiled into canonical IR; it is not a second semantic model.

Authoring principles:

- use a stable namespace and qualified names;
- give managed entities explicit identities;
- keep lifecycle state separate from work/process flow;
- model events as immutable facts;
- express behavior through ACTION contracts;
- use relationships instead of duplicating semantics;
- resolve traits through a declared role vocabulary;
- keep `implements` assertions separate from structural pattern proof;
- mark uncertain generated content as inferred.

## 7. Understand the IR

Core collections include `concepts`, `relationships`, `lifecycles`, `actions`,
`collectionTransforms`, `processes`, `events`, `resources`, `allocations`, `plans`,
`emitters`, `runtimeRequirements`, and `runtimeBindings`.

Organizational-knowledge collections include `organizations`, `information`, `rules`,
`policies`, `reasoning`, `assertions`, `identityResolutions`, and `knowledgeQueries`.

Cross-cutting sections are `integration`, `security`, `lineage`, `architecture`,
`experience`, `design`, `analytics`, and `ai`.

Prefer changing authoritative `.kcf` or extraction inputs over editing compiled IR.
Direct IR authoring is appropriate for tools, integrations, and controlled fixtures.

## 8. Validate, assess, and diagnose

```powershell
python tools/kcf.py validate .\support-desk-ir.json
python tools/kcf.py assess .\support-desk-ir.json `
  --output .\assessment.json
python tools/kcf.py coverage-report .\support-desk-ir.json `
  --by-concept `
  --output .\coverage.json
```

`assess` combines:

1. schema and semantic validity;
2. required coverage;
3. structural pattern proof;
4. role-vocabulary resolution.

Coverage levels:

- **required** gaps block readiness;
- **recommended** gaps need developer judgment;
- **informational** gaps are review guidance.

Do not fabricate CRUD, lifecycle, or policy merely to make a report green. Model the
actual domain and document intentional exceptions.

## 9. Profiles and scaffolds

Foundational presets:

- `business-application`;
- `operational-system`;
- `organizational-knowledge`;
- `event-driven-system`;
- `ai-application`;
- `analytics-platform`.

Resolve:

```powershell
python tools/kcf.py profile operational-system `
  --output .\resolved-profile.json
```

Create an authoring brief:

```powershell
python tools/kcf.py scaffold `
  --profile business-application `
  --patterns core.auditable-entity `
  --output .\scaffold.json
```

Extension libraries can use `KCF_PRESET_PATH` and `KCF_PATTERN_CONTRACT_PATH`.
KCF-OSS itself owns only foundational, domain-neutral content.

## 10. Import structured sources

Mermaid:

```powershell
python tools/kcf.py import-mermaid .\order-flow.mmd `
  --id OrderFlow `
  --namespace orders `
  --output .\order-flow-ir.json `
  --source-doc .\order-flow-source.json `
  --trace .\order-flow-trace.json
```

DBML:

```powershell
python tools/kcf.py import-dbml .\crm.dbml `
  --id CRM `
  --namespace crm `
  --profile business-application `
  --output .\crm-ir.json `
  --source-doc .\crm-source.json `
  --trace .\crm-trace.json
```

Validate another segmented document:

```powershell
python tools/kcf.py document-check .\source-document.json
```

A schema or diagram rarely establishes intent, actors, governance, lifecycle, and
policy completely. Treat the import as a starting model and inspect coverage.

## 11. Govern prose extraction and sources

KCF has no general natural-language parser. An LLM/person creates KCF or IR plus:

- a segmented source document;
- a trace from source segments to semantic identities.

Combined check:

```powershell
python tools/kcf.py ingest `
  .\model-ir.json `
  .\source-document.json `
  .\source-trace.json `
  --output .\ingest-report.json
```

Source-only check:

```powershell
python tools/kcf.py source-coverage `
  .\source-document.json `
  .\model-ir.json `
  .\source-trace.json
```

Review uncovered segments, unsourced constructs, dangling links, source version,
excerpt hashes, reviewer, review time, and disposition. `sourceComplete` and
`sourceConfirmed` are separate.

## 12. Review inferred knowledge

LLM-proposed constructs retain `extractionMethod: llm`, `status: inferred`,
confidence, and source provenance.

```powershell
python tools/kcf.py review-queue .\draft-ir.json `
  --by-segment .\source-trace.json `
  --output .\review-queue.json

python tools/kcf.py confirm .\draft-ir.json `
  --reviewer "domain.owner" `
  --as-of "2026-07-27T18:00:00Z" `
  --decisions .\decisions.json `
  --output .\governed-ir.json
```

`confirm` promotes accepted knowledge while retaining its origin and removes rejected
constructs. Never erase provenance to make generated knowledge look human-stated.

## 13. Patterns and roles

```powershell
python tools/kcf.py pattern-check .\model-ir.json `
  --output .\pattern-report.json
python tools/kcf.py roles-check .\model-ir.json `
  --output .\role-report.json
```

An `implements` statement is an assertion. A pattern contract independently proves
structure. Pattern contracts declare roles, and concept traits must resolve to those
roles. Patterns are optional accelerators, not a requirement for every domain.

## 14. Merge domain models

```powershell
python tools/kcf.py merge `
  .\sales-ir.json .\support-ir.json `
  --id CustomerOperations `
  --namespace operations `
  --identity-map .\identity-map.json `
  --output .\unified-ir.json
```

Concepts normally unify by qualified name, behavioral constructs by ID, and additive
lists by union. Scalar disagreements become diagnostics. Treat identity maps as
governed decisions and reassess the merged model.

## 15. Declared-scope completeness

```powershell
python tools/kcf.py completeness `
  .\model-ir.json `
  .\declared-scope.json `
  --document .\source-document.json `
  --trace .\source-trace.json `
  --output .\completeness-report.json
```

A scope may bound sources, profiles, patterns, subdomains, reviewers, effective date,
and acceptance criteria. Declared sources must be evaluated. A true result says
complete against this contract—not universally complete.

## 16. Plan runtime realization

```powershell
python tools/kcf.py execution-plan .\model-ir.json `
  --output .\execution-plan.json
```

The plan distinguishes deterministic, one-time codegen, runtime-LLM, symbolic, and
human-review paths. Use it to decide implementation and verification controls.

## 17. Generate an application

KCF-OSS has no deterministic application emitter. A capable LLM reads the IR and
the prompt pack.

Shipped codegen examples:

- backends: FastAPI/SQLModel/Postgres, Express/Prisma, Django/DRF/Postgres;
- frontend: React/TypeScript/OpenAPI;
- platform: NetSuite SuiteCloud SDF.

Provide:

1. `codegen/system-prompt.md`;
2. governed model IR;
3. selected stack `EXAMPLE.md`;
4. relevant `COOKBOOK.md` sections;
5. house conventions;
6. backend, frontend, or platform generation prompt.

Generate the backend before the frontend; the frontend consumes its OpenAPI.

Require a realization manifest in which every identity is realized, delegated,
out-of-tier, or unsupported with a reason.

Verify:

```powershell
python tools/kcf.py verify-realization `
  .\model-ir.json `
  .\app\realization-manifest.json `
  --repo .\app `
  --output .\realization-report.json
```

This verifies accounting and, with `--repo`, cited files, symbols, and test presence.
It does not execute tests. Run the application's formatter, compiler/typechecker,
tests, security checks, and deployment validation separately.

## 18. Add a codegen stack

1. Copy a same-tier folder under `codegen/stacks/`.
2. assign a stable ID;
3. update `stack.json` and validate against `stack-target.schema.json`;
4. faithfully rewrite `EXAMPLE.md` using the reference business model;
5. demonstrate lifecycle, actions, policy, errors, and tier boundaries;
6. update construct coverage;
7. use the cookbook for tail dimensions;
8. generate and verify a realization manifest;
9. add documentation/conformance coverage.

An example is the LLM's teaching signal and must show the behavior you expect.

## 19. Develop through MCP

```powershell
python -m pip install "kcf-oss[mcp]"
kcf-mcp
```

For remote HTTP:

```powershell
$env:KCF_MCP_TRANSPORT = "streamable-http"
$env:KCF_MCP_HOST = "0.0.0.0"
$env:KCF_MCP_PORT = "8000"
kcf-mcp
```

Agent workflow:

1. `capabilities`;
2. `authoring_reference` and `elicitation_guide`;
3. draft and `compile`;
4. call `next_action` after each revision;
5. inspect coverage;
6. review and confirm synthetic content;
7. continue until ready;
8. list stacks and request `codegen_prompt`;
9. generate code and the realization manifest;
10. verify from the CLI.

MCP convenience does not change the trust model.

## 20. Migrate older IR

```powershell
python tools/kcf.py migrate `
  .\old-model-ir.json `
  .\current-model-ir.json `
  --report .\migration-report.json
```

Read `VERSIONING.md` and `config/compatibility-matrix.json`. Grammar stack,
AUTHORING, IR, semantic catalogue, supporting schemas, and packaging versions have
related but distinct compatibility effects.

## 21. Application developer checklist

```text
author/import
→ compile and validate
→ assess
→ inspect required and recommended gaps
→ check patterns and roles
→ review sources and inferred knowledge
→ reassess
→ evaluate declared-scope completeness
→ classify execution
→ generate through codegen pack
→ verify realization
→ run native application tests
```

Keep `.kcf`, source documents/traces, governed IR, scope, realization manifest, and
test evidence versioned together where practical.

## 22. Contribute to KCF-OSS

Before editing, read:

- repository `AGENTS.md`;
- parent `LLM_HANDOFF.md`;
- `README.md`;
- `../.llm/MAINTENANCE.md`;
- relevant ownership docs.

Ownership:

- `KCF` owns universal machinery;
- `RELATIONSHIP` owns the ten-root relationship algebra;
- `ACTION` owns commands, queries, set mutation, and transformation;
- each dimension owns its primary semantics;
- profiles compose and do not redefine roots;
- AUTHORING compiles to canonical IR.

Change the smallest authoritative source.

Never hand-edit generated semantic catalogues, semantic coverage, fixture indexes,
module locks, compiler `.golden.json` files, or updated PDFs.

## 23. Change grammar safely

1. Find the owning module in `config/grammar-stack.json`.
2. Edit the owning EBNF.
3. Update imports/semantic imports deliberately.
4. If syntax changes, update AUTHORING EBNF, lexer, parser, AST, normalizer, schema,
   docs, and compiler fixtures together.
5. Decide version impact.
6. Normalize, validate, and lint.
7. review and regenerate locks;
8. update compatibility metadata and changelog;
9. run the gate.

```powershell
python tools/normalize_stack.py --write
python tools/validate_stack.py
python tools/lint_stack.py
python tools/lock_modules.py
python tools/kcf.py check
```

Never regenerate a lock only to hide an unexplained mismatch.

## 24. Change semantic validation safely

For each rule:

1. edit the authoritative semantic document;
2. preserve or introduce a stable rule ID;
3. classify automation honestly;
4. implement a handler only where mechanically enforceable;
5. add a focused negative fixture that emits that ID;
6. preserve positive fixtures;
7. regenerate catalogue/coverage;
8. run the full gate.

```powershell
python tools/kcf.py automation-report
python tools/kcf.py coverage-meta --strict
```

An automated handler without a negative regression fixture is incomplete.

## 25. Change the IR safely

Treat IR as a public API. Coordinate schema, normalizer, compiler, analyzer, delta,
identity enumeration, coverage, merge, realization verification, profiles,
migrations, fixtures, codegen docs, compatibility, and versioning.

Every new top-level property must be classified as identity-bearing or explicitly
excluded from realization accounting for a defensible reason. Prefer stable semantic
identities over array-position fallbacks.

## 26. Profiles, patterns, coverage, and importers

### Foundational profiles

KCF-OSS owns only the six foundational presets. Validate against
`profile-preset-v1.schema.json`, prefer `extends`, keep required/prohibited patterns
disjoint after composition, add fixtures, and run the gate.

### Pattern contracts

Keep OSS contracts domain-neutral, declare every role used by obligations, use traits
instead of literal concept names, add positive and negative fixtures, and keep author
assertions separate from proof.

### Coverage

For a new construct family, declare required/recommended/conditional/intentionally-none
policy with reasons, add critical positive/negative fixtures, regenerate derivatives,
and run `coverage-meta --strict`.

### Importers

A deterministic importer should produce IR, a source document, and a source trace.
Every meaningful source element and generated semantic identity should be traceable.
Surface uncertain mappings instead of presenting them as deterministic.

## 27. Versioning and release

Version deliberately:

- grammar stack;
- module contracts;
- AUTHORING surface;
- semantic IR;
- semantic catalogue;
- supporting report schemas;
- Python distribution.

Update compatibility matrix, changelog, migrations, package version where required,
handoff state, and downstream compatibility.

Final gate:

```powershell
python tools/kcf.py check
```

For grammar/release changes also confirm normalization, validation, lint, intentional
locks, reviewed goldens, expected delta, profile closure, fixture governance, coverage
policy, property tests, documentation examples, packaging metadata, and handoff state.

Downstream products ingest a new KCF release deliberately. Never edit their vendored
copies from KCF.

## 28. Common mistakes

- Treating `ready` as universal completeness.
- Authoring raw IR without understanding AUTHORING and normalization.
- Filling recommended gaps with invented domain behavior.
- Promoting LLM content without review.
- Omitting unsupported semantics during code generation.
- Treating realization accounting as behavioral proof.
- Adding business-specific presets to foundational OSS.
- Hand-editing generated catalogues or locks.
- Adding an analyzer handler without a negative fixture.
- Making KCF depend on a commercial platform.

## 29. Reference

- [Knowledge Coding](KNOWLEDGE_CODING.md)
- [Quickstart](../QUICKSTART.md)
- [Concepts](CONCEPTS.md)
- [Authoring](AUTHORING.md)
- [Walkthrough](WALKTHROUGH.md)
- [Extending](EXTENDING.md)
- [Versioning](VERSIONING.md)
- [Runtime-interpretable constructs](RUNTIME-INTERPRETABLE-CONSTRUCTS.md)
- [IR roadmap](IR-ROADMAP.md)
- [Codegen](../codegen/README.md)
- [MCP](../mcp/README.md)
- `../.llm/MAINTENANCE.md`
- `tools/kcf.py --help`
