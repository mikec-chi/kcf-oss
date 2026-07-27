# KCF Tools

| Tool | Purpose |
| --- | --- |
| `kcf.py` | Unified compile, validate, profile, migrate, coverage/assess, and conformance CLI (stops at the IR) |
| `profile_resolver.py` | Resolve profile presets and complete module dependency closure |
| `migrate_ir.py` | Migrate legacy/unversioned semantic IR |
| `lock_modules.py` | Regenerate version and SHA-256 module locks |
| `check_compatibility.py` | Validate locks, supported versions, and catalogue compatibility |
| `property_tests.py` | Deterministic graph, action-safety, knowledge-evolution, and semantic-version property tests |
| `validate_stack.py` | Validate EBNF productions, imports, and start symbols |
| `lint_stack.py` | Check cycles, reachability, unused imports, and nullable repetitions |
| `normalize_stack.py` | Enforce canonical whitespace and line endings |
| `resolve_stack.py` | Emit a namespace-qualified, closed grammar for one module |
| `build_semantic_rules.py` | Generate the combined machine-readable semantic catalogue |
| `semantic_analyzer.py` | Validate normalized KCF semantic IR |
| `semantic_delta.py` | Classify compatibility between two semantic IR versions |
| `run_conformance.py` | Run fixtures, resolution, validation, lint, delta, and emitter checks |
| `check_codegen_coverage.py` | Cross-stage codegen gate: every construct is elicited (`mcp/`), IR-reachable (reference models), and shown in an example/`COOKBOOK.md` |
| `check_doc_examples.py` | Doc↔grammar drift gate: every complete ` ```kcf ` example in the docs compiles against the current parser (mark illustrative blocks `// doc-skip`) |
| `import_dbml.py` | Deterministic DBML→KCF importer: tables→entities, columns→attributes, refs→relationships (carrying cardinality + on_delete + category), plus a source document + trace for `source-coverage` |

Run tools from the `kcf-oss` directory or pass paths relative to the
current working directory. Each tool derives the package root from its own file
location.

The complete release gate is `python tools/kcf.py check`.

Some higher-level tooling is proprietary and lives in a separate commercial
platform that builds on this open-source stack. That tooling is not part of this
repository, and this open-source stack does not depend on it.
