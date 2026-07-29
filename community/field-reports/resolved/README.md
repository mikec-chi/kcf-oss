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

## 2026-07-28 batch (kcfVersion 1.11.0)

Five observations from making a generated app match an enterprise (dense, data-first) look
(arrived as PRs #9/#10). Triaged by area: three are advisory codegen conventions (landed);
two touch the grammar/IR contract and were routed to Grammar RFCs rather than changed
silently.

| # | Report | Area | Sev | Disposition |
|---|--------|------|-----|-------------|
| 09 | ship named, selectable design-system presets (one look across every app) | codegen | low | **ACCEPTED** — preset registry `codegen/design-systems/` (contract `README.md` + `default` + `dense-enterprise`); active preset is a generation setting; docs-only, skin-only (structure stays IR-derived) |
| 10 | design page `section`s can't bind fields (no model-driven record layout) | grammar-gap | low | **ACCEPTED → Grammar RFC** — **RFC-11** in `docs/IR-ROADMAP.md`: additive opt-in `section { fields… }` → `sections[]` objects; by-role heuristic stays the fallback. No silent contract change |
| 11 | UIs render raw identifiers; humanize into Title-Case labels | codegen | medium | **ACCEPTED** — codegen system-prompt **rule 12**: a `humanize()` label helper applied to all field/column/entity/nav/enum/state labels |
| 12 | human `label`/`description` not authorable + metagrammar↔parser drift | grammar-gap | medium | **ACCEPTED → Grammar RFC** — **RFC-10** in `docs/IR-ROADMAP.md`: additive advisory `label`/`description` on concepts+attributes + reconcile compiler with the metagrammar. Default UX already covered by rule 12 |
| 13 | list view needs data-grid conventions (drop UUID cols, sort, facets) | codegen | medium | **ACCEPTED** — codegen system-prompt **rule 13**: exclude identity/free-text columns, sortable headers, faceted filter bar + search, pagination — all registry-derived |

Five accepted — three landed as codegen guidance (rules 12–13 + the `design-systems/` preset
registry; green under `kcf check`), two routed to **Grammar RFCs** (RFC-10, RFC-11 in
`docs/IR-ROADMAP.md`) because they change the grammar / `model-ir-v1` contract and, per the
field-report routing and the one rule for core changes, must land through a Grammar RFC +
VERSIONING decision, never a silent change. No grammar/IR/analyzer *contract* changed in this
batch.

## 2026-07-29 batch (kcfVersion 1.11.0)

One observation from ingesting a model family as source documents (arrived as PR #12).

| # | Report | Area | Sev | Disposition |
|---|--------|------|-----|-------------|
| 01 | no `prose`/`image` document profile ships → declaring the default modality fails document-check while omitting it passes | source-fidelity | medium | **ACCEPTED** — shipped `config/document-profiles/prose.json` + `image.json` (pure data, schema-valid); and fixed the incentive in `tools/document_profile.py` so only segmentation *drift* fails — a missing/unprofiled/omitted modality now `warns`, so declaring is never worse than omitting |

One accepted. No grammar / `model-ir-v1` / analyzer *contract* change: two new shipped profiles
(pure data on the existing `document-profile-v1` schema) plus a CLI-conformance safety change
(warn-not-fail) in the same spirit as `import-dbml-silent-noop-20260727-01`.
