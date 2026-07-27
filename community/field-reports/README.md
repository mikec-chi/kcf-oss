# Field reports — the "I noticed something" loop

A **field report** is one sanitized, reproducible observation from *using* kcf-oss —
building a model, compiling/assessing an IR, or generating an app — captured so
maintainers can triage and act on it. Friction, a bug, a coverage/authoring gap,
doc↔parser drift, a migration break, a source-fidelity loss, a skeleton-quality
generation, or a rough CLI/MCP edge.

It is deliberately shaped like the rest of KCF:

- **Advisory** — capturing a report must never block modeling or generation.
- **Machine-ingestable** — each report is a fenced `kcf-field-report:v1` YAML envelope,
  so maintainers can auto-triage by `area`/`severity`/`phase`.
- **Sanitized** — reports are about the *toolchain*, never anyone's domain data
  (`domainSanitized: true` is required).
- **Governed** — anything that would touch the **grammar / IR / analyzer contract**
  routes into the existing [Grammar RFC](../../kcf-oss/docs/EXTENDING.md) +
  [VERSIONING](../../kcf-oss/docs/VERSIONING.md) decision, not a silent change.

This is the lightweight front door. It is *not* a substitute for a Grammar RFC or a PR —
it's how an observation reliably reaches the people who can decide what to do with it.

## The envelope (`kcf-field-report:v1`)

One report = one observation = one file. Put exactly one fenced block per report:

````markdown
```yaml
<!-- kcf-field-report:v1 -->
id: <short-slug-YYYYMMDD-nn>        # e.g. coverage-over-modeling-20260727-01
kcfVersion: <grammar-stack version> # e.g. 1.11.0  (from config/grammar-stack.json)
commit: <git short sha or "unknown">
phase: model | compile | assess | codegen | runtime
area: doc-drift | migration | coverage-model | source-fidelity | grammar-gap | analyzer | codegen | tooling | dx
construct: <IR construct / tool / doc touched, or "-">   # e.g. lifecycle, kcf assess, AUTHORING.md
severity: low | medium | high
title: <one line, imperative or descriptive>
observation: >
  What happened, in a sentence or two. What you expected vs what you got.
evidence:
  commands:                        # exact commands, copy-pasteable
    - <command>
  diagnostics:                     # analyzer/compiler messages, verbatim (optional)
    - <message>
  snippet: |                       # a MINIMAL reproducer — sanitized .kcf / IR fragment
    <the smallest input that shows it>
impact: >
  Who it affects and how (e.g. "every model that marks reference data ends up with a
  spurious lifecycle recommendation").
suggestedChange: >                 # optional — your proposed fix or direction
  ...
workaround: >                      # optional — what you did instead
  ...
domainSanitized: true              # REQUIRED — no real domain data, names, or values
```
````

**Requirements (a report is only useful if it's actionable):**

- A **minimal reproducer** — `evidence.commands` and a `snippet` that reproduce it. Strip
  it to the smallest thing that still shows the behavior.
- **`domainSanitized: true`** — replace real entity/field names and values with neutral
  placeholders (`Order`, `Customer`, `amount`). Never paste a customer's schema or data.
- One observation per envelope. Split unrelated findings into separate reports.

See [`TEMPLATE.md`](TEMPLATE.md) for a filled-in worked example.

## How to submit

**Humans**
- Open a labeled issue: `gh issue create --repo <owner>/kcf-oss --label field-report --title "…" --body-file <report>.md`
  (or use the **Field report** issue template), **or**
- Open a PR adding your file under [`incoming/`](incoming/).

**Agents (sandboxed LLMs)**
1. Write the file(s) to `community/field-reports/incoming/<id>.md` — one report per file.
2. If you have `gh`/repo access, open the labeled PR/issue and **return the URL**.
3. Otherwise, **print the raw envelope(s) in your final message with the exact submit
   commands above**, and hand off to the human.
4. **Never claim a submission you did not make.** No fabricated issue/PR URLs.

## Triage & routing (what maintainers do with it)

- **`area` in {doc-drift, coverage-model, source-fidelity, codegen, tooling, dx, analyzer}**
  → a normal issue/PR against kcf-oss (docs, a coverage rule, a codegen-guidance change,
  an advisory analyzer check — none of which touch the contract).
- **`area` in {grammar-gap, migration}** or anything that would change the grammar, the
  `model-ir-v1` shape, or analyzer *severity*/semantics → a
  **[Grammar RFC](../../kcf-oss/docs/EXTENDING.md)** plus a
  **[VERSIONING](../../kcf-oss/docs/VERSIONING.md)** decision (with a deprecation window
  for breaking changes). Field reports feed these; they don't replace them.

Reports under `incoming/` are periodically triaged; accepted ones become issues/Page
entries and the file is removed or archived. Nothing here changes the grammar/IR/analyzer
contract on its own.
