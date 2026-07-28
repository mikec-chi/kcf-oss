# resolved/ — triaged & closed field reports

Reports that have been triaged and closed. Each file keeps its original
`kcf-field-report:v1` envelope plus a **Triage result** section (ACCEPTED+fixed or
REJECTED with reasoning). Archived here — out of [`incoming/`](../incoming/) — once the
disposition is recorded and any code change has landed and is green under `kcf check`.

Kept (not deleted) so the loop is auditable: accepted reports show what changed and why,
and rejected ones serve as calibration examples of reports corrected in triage.

## 2026-07-27 batch (kcfVersion 1.11.0)

| # | Report | Area | Sev | Disposition |
|---|--------|------|-----|-------------|
| 01 | `import-dbml` silent no-op on an unrecognized DBML dialect | tooling | high | **ACCEPTED** — `tools/import_dbml.py` + `tools/kcf.py` warn to stderr + exit 2 (no empty model) when 0 tables parse |
| 02 | `import-dbml` drops relationship cardinality / on_delete | source-fidelity | medium | **REJECTED** — already captured under `relationship.qualifiers` (`cardinality`, roles, `on-delete`); the report read the wrong IR field |
| 03 | status attribute unreconciled with lifecycle | codegen | high | **ACCEPTED** — codegen system-prompt **rule 9**: drive the attribute from the guarded `state`, keep it out of the Create schema, point measures at the guarded state |
| 04 | default principal = RBAC superuser (auth bypass) | codegen | high | **ACCEPTED** — codegen system-prompt **rule 8 (fail closed)**: an absent/blank principal is unprivileged (or 401), never the authority |
| 05 | COMPOSITION on-delete / required-parent not realized | codegen | high | **ACCEPTED** — codegen system-prompt **rule 10**: child parent-FK NOT NULL + required in Create; realize `on-delete` from qualifiers |
| 06 | only one event per command (drops CAUSATION targets) | codegen | medium | **ACCEPTED** — codegen system-prompt **rule 11**: emit ALL events a work `CAUSATION`-causes |
| 07 | `assess` silent on producer-less EVENTs | analyzer | low | **ACCEPTED** — advisory obligation `coverage.event.producer` (recommended, non-blocking) via the `concept-kind-targeted-by` evaluator |
| 08 | nav flattens transactional entities (no process grouping) | codegen | medium | **ACCEPTED** — `COOKBOOK.md` §F + system-prompt rule 5: sub-group transactional entities by the `process` whose works transform them (purely structural) |

Seven accepted (all landed and green under `kcf check`), one rejected. None changed the
grammar / `model-ir-v1` / analyzer *contract*: the accepted codegen changes are
prompt/guidance, #07 is an advisory (non-`required`) coverage obligation, and #01 is a
CLI safety guard.
