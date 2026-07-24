# 16 - Semantic Release Governance

## Gate

Block release when the model and application no longer agree.

## Prompt

```text
Perform semantic release governance for [DOMAIN].

Run:

python tools/kcf.py compile [PROJECT_ROOT]/domain/model.kcf `
  --output [PROJECT_ROOT]/domain/model-ir.json --validate

python tools/semantic_delta.py `
  [PROJECT_ROOT]/domain/previous-model-ir.json `
  [PROJECT_ROOT]/domain/model-ir.json

python tools/check_compatibility.py

Re-run every selected emitter, inspect its trace manifest, and run all generated
application tests, semantic tests, contract tests, security tests, migration
tests, and project golden tests. Run `python tools/kcf.py check` when releasing a
changed KCF stack or toolchain, not as a substitute for domain-specific tests.

Produce [PROJECT_ROOT]/release/semantic-release-report.md containing:

- model validation result;
- manual rule-review result;
- semantic delta and recommended version change;
- breaking-change migration plan;
- runtime capability and binding drift;
- emitter support and semantic-loss assessment;
- generated artifact traceability status;
- grammar-stack, IR, catalogue, runtime-manifest, and emitter compatibility;
- module-lock and registry integrity status;
- semantic test coverage;
- security, lineage, and provenance status;
- unresolved unavailable checks;
- final release decision and evidence.

Block release when:

- semantic validation contains errors;
- a manual semantic rule fails;
- a breaking change lacks a major-version decision and migration;
- required runtime capabilities are missing;
- binding versions are incompatible;
- an emitter silently loses required semantics;
- trust-boundary controls or authorization are missing;
- generated tests no longer trace to the current model;
- application behavior differs from the validated Action or relationship
  contracts.

If release is approved, archive the released model-ir.json as the next
previous-model-ir.json baseline and record its checksum and semantic version.
Then register [REGISTRY_PACKAGE] [MODEL_VERSION] as an immutable artifact and
run `python tools/registry.py verify`. Never overwrite an existing registered
name/version.
```
