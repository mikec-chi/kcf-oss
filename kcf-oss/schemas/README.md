# KCF Machine Contracts

Versioned JSON Schemas governing the open-source stack's public artifacts.
kcf-oss stops at the semantic IR, so these contracts cover authoring the IR and
measuring/reporting its completeness — not code generation (LLM-based, in
`../codegen/`) or runtime.

- `model-ir-v1.schema.json` — normalized semantic IR (the central contract). Also
  governs the organizational-knowledge collections: organizations, information,
  rules, policies, reasoning, assertions, identity resolutions, knowledge queries.
- `profile-preset-v1.schema.json` — composable module/capability presets.
- `semantic-delta-v1.schema.json` — compatibility/delta reports.
- Coverage & readiness: `coverage-model-v1`, `coverage-report-v1`,
  `assess-report-v1`, `scaffold-v1`, `review-queue-v1`.
- Patterns & packaging: `pattern-contract-v1`, `pattern-report-v1`,
  `role-report-v1`, `package-manifest-v1`.
- Natural-language / document front doors: `source-document-v1`,
  `source-trace-v1`, `source-coverage-report-v1`, `ingest-report-v1`,
  `document-profile-v1`.

Schema validation runs before deeper semantic analysis. Contextual invariants —
reference resolution, graph reachability, authorization, idempotency, and
coverage — remain semantic rules rather than JSON Schema constraints.
