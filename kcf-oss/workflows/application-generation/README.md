# KCF LLM Application Workflow

This folder contains an ordered prompt sequence for using a coding LLM to turn
domain requirements into a validated KCF semantic model (the IR). Once the IR is
validated, generate the application from it with the code-generation pack in
[`../../codegen/`](../../codegen/).

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
3. Run prompts `01` through `10` in order — they produce the validated IR. Then
   generate code from that IR with the pack in [`../../codegen/`](../../codegen/).
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

Once step 10 produces a validated IR, hand it to the code-generation pack in
[`../../codegen/`](../../codegen/) to build the application.

## Approval gates

- **Discovery gate:** Domain scope, evidence, assumptions, and open questions
  have been reviewed.
- **Model gate:** Concepts, relationships, behavior, and profiles have stable
  semantic identities and no unresolved material ambiguity.
- **Validation gate:** `kcf.py validate` reports no errors and manual
  catalogue review has been recorded. The validated IR is the handoff to code
  generation ([`../../codegen/`](../../codegen/)).

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
    model.kcf
    model-ir.json
    previous-model-ir.json
    validation-report.json
    model-repair-log.md
    manual-rule-review.md
```

The validated `domain/model-ir.json` is the handoff to code generation — see
[`../../codegen/`](../../codegen/) for turning it into an application.

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

Capabilities beyond the IR are provided by a separate commercial platform that
builds on this open-source stack. They are not part of this repository; this
open-source stack neither ships nor depends on them.

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
