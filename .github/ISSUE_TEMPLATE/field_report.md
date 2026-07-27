---
name: Field report
about: A sanitized, reproducible observation from using KCF (friction, bug, gap, doc drift)
title: "[field-report] "
labels: field-report
---

<!--
A field report is one sanitized, reproducible observation about the TOOLCHAIN — never
about your domain data. It is advisory: it helps maintainers triage friction. Fill the
envelope below (keep the fenced block), attach a minimal reproducer, and set
domainSanitized: true. See community/field-reports/README.md and TEMPLATE.md.
Anything that would touch the grammar / IR / analyzer contract will be routed into a
Grammar RFC + a VERSIONING decision.
-->

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
