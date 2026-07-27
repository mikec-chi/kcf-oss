# Field report — TEMPLATE

Copy this file, fill the envelope, keep exactly **one** report per file, and submit per
[`README.md`](README.md). Delete this heading and the notes; keep the fenced block.

Blank envelope to fill:

```yaml
<!-- kcf-field-report:v1 -->
id: <short-slug-YYYYMMDD-nn>
kcfVersion: <grammar-stack version>
commit: <git short sha or "unknown">
phase: model | compile | assess | codegen | runtime
area: doc-drift | migration | coverage-model | source-fidelity | grammar-gap | analyzer | codegen | tooling | dx
construct: <IR construct / tool / doc, or "->
severity: low | medium | high
title: <one line>
observation: >
  <what happened; expected vs actual>
evidence:
  commands:
    - <command>
  diagnostics:
    - <message, if any>
  snippet: |
    <minimal sanitized reproducer>
impact: >
  <who/what it affects>
suggestedChange: >
  <optional>
workaround: >
  <optional>
domainSanitized: true
```

---

## Worked example (a real observation from a build)

This is the format filled in — a genuine coverage-model finding, so maintainers have a
concrete, high-signal report to calibrate triage against.

```yaml
<!-- kcf-field-report:v1 -->
id: coverage-over-modeling-20260727-01
kcfVersion: 1.11.0
commit: unknown
phase: assess
area: coverage-model
construct: coverage.entity.lifecycle
severity: high
title: "Chasing recommendedGaps: 0 pushes a lifecycle onto every entity, degrading model signal"
observation: >
  `kcf assess` recommends a lifecycle for every entity regardless of its nature. Driving
  the recommended-gap count to zero therefore meant adding a lifecycle to reference and
  config entities that have no meaningful states. That was semantically wrong, and it
  destroyed the ability to infer record-nature from shape: with "has a lifecycle" now true
  for everything, a downstream classifier mislabeled 20 of 24 entities as transactional.
evidence:
  commands:
    - kcf compile model.kcf -o model-ir.json --validate
    - kcf assess model-ir.json
  diagnostics:
    - "[recommended] coverage.entity.lifecycle: ENTITY <ns>.ReferenceList has no lifecycle"
  snippet: |
    kcf model M profile business-application {
      namespace m;
      entity ReferenceList {          // a static lookup — no operational states
        identity id: UUID;
        required label: String;
      }
    }
    // assess recommends a lifecycle for ReferenceList; adding one to satisfy it is wrong.
impact: >
  Any model with reference/config/master data is nudged toward over-modeling; the added
  empty lifecycles pollute the structural signal other tooling (and code generators) rely
  on to tell master data from transactional data.
suggestedChange: >
  Make coverage obligations category-aware: expect a lifecycle only for `transactional`
  entities; don't recommend one for `reference`/`config`/`master`. Reward appropriate
  modeling, not maximal modeling.
workaround: >
  Left the recommended lifecycle gaps open (generation only needs a *valid* model, not a
  fully `ready` one) instead of adding meaningless lifecycles.
domainSanitized: true
```

> Note: this exact observation was triaged and addressed — `kcf assess` coverage is now
> category-aware. It's kept here as the calibration example precisely because it shows the
> loop working end to end: observe → sanitized envelope → triage → contract-safe fix.
