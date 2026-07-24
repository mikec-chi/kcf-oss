# 10 - Semantic Validation and Repair

## Gate

No application generation is allowed until this gate passes.

## Prompt

```text
Validate [PROJECT_ROOT]/domain/model-ir.json with the KCF reference
analyzer:

python tools/kcf.py validate [PROJECT_ROOT]/domain/model-ir.json `
  --output [PROJECT_ROOT]/domain/validation-report.json

For every diagnostic:

- explain the semantic cause;
- identify the responsible source construct;
- identify related declarations;
- propose the smallest semantically correct repair;
- confirm that the repair does not violate another rule;
- update model.kcf and recompile model-ir.json; never hand-edit generated IR;
- record the repair in domain/model-repair-log.md.

Repeat analysis until there are no error diagnostics.

Then use kcf-oss/semantics/coverage.json and semantic-rules.json to review
every applicable rule whose enforcement is manual-review, partially-automated,
or profile-dependent. Use tests/fixtures/rules/fixture-index.json to understand
the automated evidence. Record:

- rule ID;
- applicability;
- evidence inspected;
- pass, fail, unavailable, or not-applicable status;
- corrective action;
- reviewer assumptions.

Write this review to domain/manual-rule-review.md.

Do not suppress, downgrade, or bypass a rule merely to pass validation.

Re-run the compile command with `--validate` after every repair. The gate passes
only when analyzer errors are zero, manual failures are zero, and unavailable
checks are visible and accepted by the appropriate reviewer.
```
