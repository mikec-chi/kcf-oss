# KCF LLM Application Workflow

This folder contains an ordered prompt sequence for using a coding LLM to turn
domain requirements into a validated KCF semantic model and then into an
application.

## Important boundary

KCF now provides a textual domain-authoring compiler, versioned semantic IR
schema, reference analyzer, profile resolver, and an LLM code-generation pack
(`../../codegen/`). KCF stops at the semantic IR; the coding LLM generates code
for the target stack from that IR.
The coding LLM remains responsible for domain discovery, ambiguity resolution,
review, and production implementation choices; it no longer needs to invent or
manually normalize the IR structure.

Do not generate application code directly from prose requirements. First create
`domain/model.kcf`, compile and validate `domain/model-ir.json`, and treat the
validated IR as the machine source of truth for generated code and tests. The
`.kcf` file remains the editable source: repair it and recompile rather than
hand-editing generated IR.

## How to use the prompts

1. Copy `variables.example.json` to a project-specific configuration and fill
   in its values.
2. Give the LLM `00-shared-system-prompt.md` as its system or persistent project
   instruction.
3. Run prompts `01` through `16` in order.
4. Review and approve the output gate after every phase.
5. Re-run a phase whenever an earlier artifact changes materially.
6. Never proceed past prompt `10` while semantic validation contains errors or
   required manual reviews are unresolved.

The prompts assume the LLM can read the KCF repository and run local Python
commands. Replace bracketed variables such as `[DOMAIN]` before use, or provide
`variables.example.json` as context and instruct the LLM to substitute it.

## Prompt sequence

| Step | Prompt | Primary output |
| --- | --- | --- |
| 00 | Shared system prompt | Persistent KCF rules |
| 01 | Domain discovery | `domain/00-domain-brief.md` |
| 02 | Module and profile selection | `domain/01-model-profile.md` |
| 03 | Controlled vocabulary | `domain/02-vocabulary.md` |
| 04 | Concept classification | `domain/03-concepts.json` |
| 05 | Relationship model | `domain/04-relationships.json` |
| 06 | Behavior and actions | `domain/05-behavior.json` |
| 07 | Supporting dimensions | `domain/06-supporting-semantics.json` |
| 08 | Operational profiles | `domain/07-operational-profiles.json` |
| 09 | Author and compile the model | `domain/model.kcf`, generated `domain/model-ir.json` |
| 10 | Validation and repair | `domain/validation-report.json` |
| 11 | Runtime and emitter contracts | `domain/08-runtime-contract.json` |
| 12 | Application architecture | `app/generation-plan.md` |
| 13 | Experience and emitter models | Profile-specific model files and traceability review |
| 14 | Vertical-slice code generation | Reference-emitter baseline, application code, and tests |
| 15 | Semantic test generation | Rule-traceable test suite |
| 16 | Release governance | `release/semantic-release-report.md` |

## Approval gates

- **Discovery gate:** Domain scope, evidence, assumptions, and open questions
  have been reviewed.
- **Model gate:** Concepts, relationships, behavior, and profiles have stable
  semantic identities and no unresolved material ambiguity.
- **Validation gate:** `kcf.py validate` reports no errors and manual
  catalogue review has been recorded.
- **Generation gate:** Runtime requirements and emitter support are explicit;
  reference trace manifests are reviewed and unsupported semantics are not
  silently discarded.
- **Release gate:** Semantic delta, runtime drift, generated tests, and migration
  requirements have been reviewed; stack/IR/catalogue/emitter versions are
  compatible; registry integrity passes.

## Expected project layout

```text
project/
  domain/
    model.kcf
    00-domain-brief.md
    01-model-profile.md
    02-vocabulary.md
    02-open-questions.md
    03-concepts.json
    03-concepts.md
    04-relationships.json
    04-relationship-review.md
    05-behavior.json
    05-behavior-review.md
    06-supporting-semantics.json
    07-operational-profiles.json
    08-runtime-contract.json
    08-emitter-support.md
    model-ir.json
    previous-model-ir.json
    validation-report.json
    model-repair-log.md
    manual-rule-review.md
  app/
    generation-plan.md
    models/
    semantic-tests/
  generated/
    dbml/
      trace-manifest.json
    application/
      trace-manifest.json
    knowledge-graph/
      model.jsonld
      model.ttl
      shapes.ttl
      trace-manifest.json
  runtime/
    runtime-manifest.json
  release/
    semantic-release-report.md
```

## Validation commands

From `kcf-oss`:

```powershell
python tools\kcf.py compile <project>\domain\model.kcf `
  --output <project>\domain\model-ir.json --validate

python tools\kcf.py validate <project>\domain\model-ir.json `
  --output <project>\domain\validation-report.json

python tools\semantic_delta.py `
  <project>\domain\previous-model-ir.json `
  <project>\domain\model-ir.json

python tools\check_compatibility.py
```

Once the IR is `ready`, generate code with an LLM using the pack in
[`../../codegen/`](../../codegen/) — a stack-agnostic system prompt plus a
single-shot example per stack (backend + frontend). KCF stops at the IR.

Deterministic emitters (dbml, vertical-slice, knowledge-graph), runtime-drift
analysis, and the business-pattern presets are provided by a separate commercial
overlay that composes this open-source stack. They are not part of this
repository; this open-source stack neither ships nor depends on them.

The generated code must carry a coverage self-audit; an unsupported required
semantic is a generation blocker. After release approval, register the immutable
IR and
verify the registry index:

```powershell
python tools\registry.py register <package> <version> <project>\domain\model-ir.json
python tools\registry.py verify
```

The complete KCF stack itself can be verified with:

```powershell
python tools\kcf.py check
```
