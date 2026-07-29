# Changelog

All notable changes to KCF are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/).

KCF versions **three contracts independently** (see `kcf-oss/docs/VERSIONING.md`).
Tag every contract-affecting entry with which one moved:

- **`grammar-stack`** — the module set and their productions
- **`ir`** — the normalized semantic IR shape (`model-ir-v1`)
- **`rules`** — the semantic-rule catalogue

(KCF stops at the IR; code generation is the LLM codegen pack.)

The distribution version (`pyproject.toml`) **tracks the grammar-stack release line**
(currently `1.11.0`); the three semantic contracts version independently inside the
manifest (grammar-stack `1.11.0`, IR `1.0.0`, rule catalogue `3.0.0`). `check_handoff.py`
asserts the distribution version equals the grammar-stack version. Breaking changes to
any contract require a major bump of THAT contract and, for `ir`, a migration path
(`tools/migrate_ir.py`).

## [Unreleased]

First public release of the open standard. Cut this section to a dated version
(e.g. `## [1.3.0] - YYYY-MM-DD`) when publishing to GitHub/PyPI.

### Changed

- **`[rules]` 2.2.0 → 3.0.0 (breaking).** The semantic-rule catalogue grew **270 → 322
  rules** and automated **14 new structural diagnostics** — ORDERING relationships must
  declare their dimension; `upsert` must declare a conflict key; destructive actions must
  cite a real authorization policy (not a bare exemption); bulk mutations must declare
  concurrency; `query`/`count` must be pure; transform lineage/classification/identity;
  `create` must return the created identity; a record CRUD action must target a
  record-shaped concept. These are **stricter validation, so some formerly-accepted
  models can now emit errors** — hence a major bump ("narrowing a required contract" is
  breaking per `docs/VERSIONING.md`). Separately, **52 rules the analyzer already
  enforced were catalogued** (documentation of pre-existing behavior, no change) and the
  automation triage was corrected with per-rule reasons in
  `semantics/automation-triage-overrides.json`. Automated enforcement rose 86 → **152**
  (47% of the catalogue). Downstream systems that pin the catalogue version — including
  the proprietary Taliden vendored engine — must re-ingest via their one-way flow and
  re-compare the contract fingerprint.
- **docs** — README/QUICKSTART/CONCEPTS/WALKTHROUGH/codegen/MCP claims de-overclaimed:
  KCF reports required-obligation readiness, closed-world completeness against a declared
  scope, source-confirmation, and an accounted realization handoff at an explicit
  evidence level — it does not claim domain completeness, "any stack", or behavioral
  proof.
- **codegen pack — 2026-07-28 field-report batch (UI fidelity), guidance-only.** Three
  advisory conventions landed in the codegen pack (no grammar/IR/analyzer contract change):
  `system-prompt.md` **rule 12** humanizes identifiers into Title-Case UI labels
  (`firstName`→"First Name"; report `20260728-11`); **rule 13** applies standard data-grid
  conventions to list views — drop identity/free-text columns, sortable headers, faceted
  filter bar + search, pagination (report `20260728-13`); and a new **design-system preset
  registry** `codegen/design-systems/` (`README.md` contract + `default` + `dense-enterprise`)
  lets an org standardize one look across every generated app via a generation setting, skin
  only (report `20260728-09`). Reflected in `design-system-default.md`,
  `codegen/CONSTRUCT_COVERAGE.md`, `codegen/generate-frontend.md`, and `codegen/README.md`.
- **`docs/IR-ROADMAP.md`** — two field reports that touch the grammar/IR contract were
  routed to Grammar RFCs rather than changed silently: **RFC-10** (additive advisory
  `label`/`description` on concepts + attributes, and reconciling the compiler with the
  metagrammar's `metadata` block; report `20260728-12`) and **RFC-11** (design page
  `section`s that optionally bind fields for model-driven record layout; report
  `20260728-10`); and **RFC-12** (attribute value domains / allowed-value sets, so a source
  enumeration is machine-checkable rather than prose; report `20260729-07`). No `grammar-stack`
  / `ir` change lands until an RFC is accepted.

### Fixed

- **analyzer / assess / verifier — 2026-07-29 behavioural-gap batch (#10, #12, #13, #15).**
  Four fixes so the toolchain can no longer silently pass a model whose behavioural half won't
  generate, none changing the grammar / `model-ir-v1` / analyzer *contract*: (#10) the analyzer now
  resolves MATH expression `ref` operands against the result measure's subject attributes (+params/
  measures/units) and warns (`kcf.math.reference`) on an operand that resolves to nothing — a
  formula over phantom fields no longer assesses clean; (#12) `assess` gains a **`behaviourallyComplete`**
  axis, reported *separately* from `ready` (the mirror of `domainComplete: not-proven`), so a model
  that will only scaffold is visible on day one; (#13) `verify-realization` adds a per-construct-class
  **`byClass`** realized/total ratio (`action.invoke` split from CRUD) and a 0%-realized **`notices`**
  list — "accounted for" is no longer mistaken for "realized"; (#15) `ir_identity.model_semantic_ids`
  makes each **profile-section member** (view/control/threat/adapter/…) an accountable identity, so a
  manifest that builds none of the declared screens fails and an honest per-item `delegated` entry is
  accepted (fixing the same inverted incentive as `document-profile-missing-prose-image-20260729-01`).
  `assess-report-v1` and `realization-report-v1` schemas updated (additive); each fix regression-pinned
  in `run_conformance.py`.
- **`docs/IR-ROADMAP.md`** — two behavioural-grammar reports routed to Grammar RFCs rather than
  changed silently: **RFC-13** (parse rule `condition` into an AST like a formula expression; report
  `20260729-11`) and **RFC-14** (an ACTION `procedure` surface for `invoke` actions; report
  `20260729-14`). No `grammar-stack` / `ir` change until an RFC is accepted; the *visibility* of both
  gaps ships now via #10/#12/#13.
- **analyzer / tooling — 2026-07-29 field-report batch (#03–#06, #08), authoring & analysis fidelity.**
  Five fixes from transcoding a large external model family, none changing the grammar /
  `model-ir-v1` / analyzer *contract*: (#03 `ordering-dimension-qualifier-catch-22`) added the
  required `dimension` qualifier to `KNOWN_RELATIONSHIP_QUALIFIERS`, so a valid `ORDERING` edge no
  longer trips the spurious "not recognized" advisory; (#04 `source-coverage-blind-to-five-collections`)
  `source_coverage.construct_ids` now walks **every** id-bearing IR collection (incl. `math`,
  `propositions`, `authorities`, `processes`, and the profile sections) except an explicit
  infrastructure exclusion list, so faithfulness is reachable for models beyond entities/actions;
  (#05 `entity-immutable-declaration-dropped`) `immutable;` on a non-EVENT concept now projects to
  `metadata.mutability = "read-only"` instead of silently vanishing; (#06 `lifecycle-obligation-ignores-exempt`)
  `ev_concept_kind_has_lifecycle` now honours `_is_exempt`, so a read-only/immutable transactional
  entity (ledger, audit trail) is no longer left a permanently-unsatisfiable lifecycle gap; (#08
  `scope-capabilities-need-qualified-identifiers`) `completeness` matches a scope capability by both
  its bare local name and its namespace-qualified form, and the CLI now prints the nearest model
  term for an uncovered capability. Each is regression-pinned in `run_conformance.py`; the
  `scope-v1` schema now documents the matching rule.
- **tooling / source-fidelity — 2026-07-29 field report (`document-profile-missing-prose-image-20260729-01`).**
  Shipped two missing document profiles, `config/document-profiles/prose.json` and `image.json`
  (pure data on the existing `document-profile-v1` schema; the natural-language front door's two
  default modalities previously had none). And fixed a perverse incentive in
  `tools/document_profile.py`: `document-check` used to **fail** a document that honestly declared
  an unprofiled `documentKind` while **passing** one that omitted the field — rewarding stripping
  provenance. Conformance now fails only on genuine segmentation **drift** (a segment kind foreign
  to a resolved profile); a missing, unprofiled, or omitted modality is a non-fatal `warning` (new
  `warnings` field). Declaring a modality is never worse than omitting it. The warnings are
  surfaced to stderr on **every** entry point — a shared `emit_warnings()` helper is called by both
  `document_profile.py` and the `kcf document-check` CLI handler (the CLI path originally dropped
  them; report `document-check-warnings-not-surfaced-by-cli-20260729-02`), and the behavior is now
  pinned in `run_conformance.py`. No grammar / `model-ir-v1` / analyzer *contract* change.
- **tooling** — `kcf import-dbml` no longer silently emits an empty model. When a
  source parses to 0 tables (typically a non-dbml.org DBML dialect), it now warns to
  stderr naming the accepted `Table { ... }` subset and exits non-zero without writing
  output, instead of producing an empty model at exit 0. Domain-agnostic (inspects only
  the table count). From field report `import-dbml-silent-noop-20260727-01`.

### Added
- **Open standard** — `kcf-oss`: 29 ISO/IEC 14977 EBNF grammar modules (580
  productions) rooted in the `KCF` metagrammar, the ergonomic `AUTHORING` textual
  surface, the reference compiler, the semantic analyzer, and the reusable
  application-generation prompt workflow. `grammar-stack` 1.11.0.
- **Comprehensive authoring surface — `[grammar-stack]` 1.11.0.** The ergonomic
  `.kcf` surface now expresses **all 16 dimension grammars plus the ACTION /
  RELATIONSHIP algebra** first-class (it previously covered a structural subset):
  rich **events** (`kind`, `trigger`, `affect-lifecycle`, `severity`,
  `expectedness`, `correlation-key`, occurrence/detection time, `match`) — emitting
  an event can drive the named lifecycle transition; **measures**
  (`unit`/`aggregation`/`scale`/`period`/`threshold`/`target`); **temporal**
  (+`calendar`); **spatial** (`geometry`/`route`); **intent** goals; **LOGIC**
  (`proposition`/`predicate`); **MATH** (`formula`/`function`/`optimize`/
  `distribution`/`simulation` with real math-expression ASTs); richer **actor**
  (`role`/`authority`), **work** (BPMN `process`), **lifecycle** (state
  entry/exit/invariant, transition trigger/guard/effect), and **resource**
  (capacity/allocation); and the cross-cutting **profile blocks** (`integration`,
  `security`, `lineage`, `architecture`, `experience`, `design`, `analytics`, `ai`)
  authored as top-level sections that land in `ir[<section>]`. The compiler,
  normalizer, and IR carry these through end to end (verified live), with new
  reference domains (`entity-rich`, `quantitative`, `profiles`, `capability-skill`)
  + goldens. The pre-IR guidance (`mcp/authoring-brief.md`, the MCP elicitation
  flow), the codegen `system-prompt.md`, and `codegen/CONSTRUCT_COVERAGE.md` were
  updated so models both **express** and **realize** the richer semantics.
- **Semantic IR** — the `model-ir-v1` contract (`ir` 1.0.0) with source spans,
  plus the delta schema.
- **Semantic-rule catalogue** — combined KCF + stack-neutral `semantic-core`
  rules with stable diagnostic IDs and coverage tracking (`rules` catalogue).
- **Coverage: build-operation guidance.** `[rules]` `kcf assess` reports
  build-operation coverage grounded in the `ACTION` grammar's operation
  vocabulary — per-entity **CRUD** and **set/bulk** (`coverage.entity.crud`,
  `coverage.entity.set-operation`) and a model-level **data-transformation**
  (`coverage.model.transformation`) — at **recommended** level (enrichment, not a
  hard gate). Reference/immutable entities opt out via
  `metadata.mutability = "read-only"`. The gate for code generation is a **valid**
  model (analyzer-clean); `ready` is the completeness goal and its gaps travel to
  the codegen prompt as guidance. (Coverage-model contract + `coverage-model-v1`
  schema updated.)
- **Code-generation pack** — `codegen/`: a tier-aware, tech-stack-agnostic system
  prompt, per-tier prompt templates, and a per-construct coverage audit
  (`CONSTRUCT_COVERAGE.md`) mapping every `model-ir-v1` construct to a backend and
  frontend representation. Single-shot examples across two tiers:
  **backend** — FastAPI+SQLModel, TypeScript+Express+Prisma, Django+DRF (each
  exposing an OpenAPI/**Swagger** interface by default); **frontend** —
  React+TypeScript+TanStack Query bound to the backend's OpenAPI. The primary
  path from a `ready` IR to a full application with any LLM, for any stack; users
  add their own via the `stack-target-v1` descriptor (`tier`, `apiDocs`).
- **CLI** — `kcf` (compile / assess / coverage-report / …), installable via
  `pip install kcf-oss`.
- **"Knowledge coding" getting-started guide** — `docs/KNOWLEDGE_CODING.md`: the
  positioning (knowledge coding = semantic modeling + vibe coding) plus per-LLM
  MCP deploy procedures (Claude Desktop / Claude Code / VS Code / Cursor / ChatGPT)
  and a first-app walkthrough. Surfaced as "Start here" from the README, QUICKSTART,
  and the MCP reference.
- **MCP server** — `kcf-oss/mcp/` (`kcf-mcp`, `pip install "kcf-oss[mcp]"`) exposes
  the full toolchain over the Model Context Protocol so Claude / ChatGPT / VS Code can
  turn a prose domain description into a checked model and generate code from it —
  conversationally. **13 tools** across the pipeline: `capabilities` (a
  self-describing manifest), `authoring_reference`, `elicitation_guide`,
  `example_model`, `scaffold`, `compile`, `assess`, `coverage`, `coverage_model` (how
  gaps derive from constructs), `review_queue` + `confirm_synthetic` (synthetic
  gap-fill approval, below), `list_stacks`, and `codegen_prompt` (now also generates
  from a governed IR); a **`model_domain` guided prompt**; and **4 resources**
  (`kcf://capabilities`, `kcf://guide/elicitation`, `kcf://reference/authoring`,
  `kcf://reference/coverage-model`). Every tool carries a title, read-only/idempotent
  annotations, and per-parameter descriptions so the host LLM recognizes what each
  does.
- **Agent-driven orchestration (MCP).** A `next_action(source)` **driver** turns the
  pipeline into a self-navigating loop — after every edit it returns the single best
  next tool, the current verdict, whether the model is `readyToGenerate`, and (once
  valid) an ordered `generationPlan` (backend, then frontend against its OpenAPI) — so
  an autonomous agent maximizes the toolset without hard-coding the order. Two
  role-scoped guided prompts scope the halves for sub-agents: **`build_model`** (prose
  → valid model) and **`generate_app`** (valid model → generated app), alongside the
  end-to-end **`model_domain`**. `capabilities()` gained an `agentLoop` describing the
  pattern.
- **Synthetic gap-filling with tiered approval (MCP).** The LLM proposes fills for
  coverage gaps, tagged in the grammar's own provenance vocabulary (`extraction-method
  llm; confidence …; status inferred;`) so they stay distinguishable from stated fact.
  `review_queue` tiers them into a **bulk** chunk (mass-approve to move fast) and a
  **review** chunk (decide individually to be rigorous); `confirm_synthetic` records
  the decisions (stamps `reviewedBy`/`recordedAt`, flips inferred→asserted, drops
  rejects) and returns the governed IR to generate from. Surfaces the existing
  `review_queue`/`confirm_synthetic` tools over MCP; nothing synthetic is ever
  silently promoted.
- **Codegen gate is `valid`, not `ready`.** Code generation proceeds from a valid
  model; coverage gaps travel to the codegen prompt as enrichment guidance (the LLM
  realizes the sensible ones or you fill them as tagged synthetic knowledge). CRUD /
  set-operation coverage moved to `recommended` (see coverage entry).
- **Prompt tuning (house conventions)** — teams tune *how* the domain is elicited
  and *how* code is generated without forking. Code generation accepts
  `KCF_CODEGEN_OVERRIDES` (a Markdown file) and a `codegen_prompt` `instructions`
  arg / playground *House conventions* box; elicitation accepts
  `KCF_ELICITATION_GUIDE` and the `model_domain` `conventions` arg. Both inject a
  highest-priority layer that overrides examples/defaults where they conflict but
  never the action contracts or the coverage self-audit. Starter files:
  `codegen/overrides.example.md`, `mcp/elicitation.example.md`.
- **Hosted MCP demo + one-command self-host.** A public read-only demo endpoint is
  documented (`https://kcf-mcp.onrender.com/mcp`) for remote hosts like ChatGPT with
  zero install. `packaging/make-render-repo.sh` assembles a ready-to-deploy repo
  (Dockerfile binding the platform's `$PORT` + a `render.yaml` blueprint) for a free
  Render web service; `make-hf-space.sh`/`deploy-hf-space.py` still target Hugging
  Face (now that HF **Docker Spaces require PRO**).
- **Playground** — a zero-persistence web app (`kcf-oss/playground/`) that runs
  compile → assess → assemble the LLM codegen prompt, in the browser.
- **Living model — drift prevention.** The model is the source of truth and coding
  agents keep code in sync with it, both ways. New `codegen/MODEL_SYNC.md` defines the
  bidirectional protocol: generate-from-model, **model-first** for any meaning change,
  and **reconcile the model from code** when a developer vibe-codes directly (ask when
  intent is ambiguous; never invent model meaning). The codegen `system-prompt.md`
  gains a model-first non-negotiable rule + a "refer to the model as you code"
  section, and MCP `capabilities()` gains a `livingModel` entry. **`kcf init`** seeds a
  *knowledge application* — `model/` (source of truth) + compiled IR + `AGENTS.md`
  (drift rules for Claude Code / Cursor / …) + `.kcf/` (bundled authoring reference,
  sync protocol, codegen prompt) + `kcf.project.json` — so a project is wired for the
  loop out of the box.
- **Reference model + single-shot examples now construct-complete.** The reference
  `business-application` model gained a **rule** (CONSTRAINT), a **policy**
  (deny-overrides; the commands' `authorization` now resolves to it), a
  **data-transformation** (`ActiveCustomers` filter), and an **`upsert`** command —
  so it exercises the mainstream IR constructs end to end. All four single-shot
  codegen examples (FastAPI, Express/Prisma, Django/DRF, React) were extended to
  realize each construct with concrete code and an **exhaustive coverage self-audit**
  (every construct → realized / delegated / out-of-tier, `dropped: []`). Golden
  fixture regenerated; `kcf check` green.
- **Community contribution area** — a top-level `community/` where the ecosystem
  builds on the standard: **models** (shared `.kcf` domains, gated by
  `community/models/validate.py`), **prompt packs** (elicitation guides + codegen
  overrides for the MCP), **techniques** (elicitation/codegen how-tos), **showcase**
  ("Built with KCF"), and **experimental grammars** (pre-core staging). Each area has
  a README + `TEMPLATE`. `CONTRIBUTING.md` is reorganized into two tracks (build on
  KCF vs. improve the core), and `make-oss-repo.sh` ships `community/` in the public
  repo.
- **Project scaffolding** — Apache-2.0 license (© Composable Holdings Inc.),
  contributor/community docs, CI wired to the conformance gate, the `EXTENDING`
  guide, and the Grammar RFC process.

- **Platform codegen tier + NetSuite pack.** Code generation gained a third
  **`platform`** tier (`codegen/stack-target.schema.json`) for targets you
  *customize* rather than *build* — a SaaS/low-code platform that already owns the
  datastore, runtime, and UI, so there is **no OpenAPI/Swagger mandate**. The first
  platform stack, **`netsuite-suitecloud-sdf`**, realizes the reference
  `business-application` model as a SuiteCloud **SDF** Account Customization Project:
  ENTITY→`customrecordtype`+fields (KCF types → NetSuite field types), lifecycle→a
  `customlist` + SuiteFlow `workflow` **and** a `beforeSubmit` guard, the action
  contract→a SuiteScript 2.1 **RESTlet** (optimistic concurrency via a `version`
  field, `mutate`-set writes, conditional idempotency, best-effort bulk), the
  data-transformation→a `savedsearch`, the CONSTRAINT→a User Event validation (+ a
  Client Script mirror), the policy→a `role` + an in-script deny-overrides gate, and
  the immutable EVENT→an append-only log record — packaged for
  `suitecloud project:deploy`, with the same exhaustive coverage self-audit
  (`dropped: []`). `system-prompt.md`, `CONSTRUCT_COVERAGE.md` (a NetSuite
  construct-map), `generate-platform.md`, and the MCP `codegen_prompt`/`next_action`
  generation plan all learned the platform tier; `list_stacks` surfaces it
  automatically.

- **Full-grammar codegen coverage — elicit → IR → codegen, gated.** Closed the gap
  where the rich half of grammar-stack 1.11.0 was *authorable* but neither reliably
  *elicited* nor *demonstrated* for code generation. (1) The MCP elicitation process
  now probes the whole tail — a dedicated *Quantitative & analytical* step
  (measure/intent/temporal+calendar/spatial+route/logic/math) and an *Information &
  knowledge* step (information/resource+allocation/organization/reasoning/assertion/
  identity-resolution/knowledge-query/capability/skill) plus richer mainstream prompts
  (lifecycle entry/exit/guard, the full action-operation set + mutations, all rule
  kinds). (2) `codegen/COOKBOOK.md` gives a worked backend/frontend/platform
  realization of **every** tail construct; it rides along with `codegen_prompt`
  automatically whenever a model uses one. (3) `CONSTRUCT_COVERAGE.md` gained the
  previously-unmapped rows (`calendar`, `route`, `capability`/`skill`, standalone
  `authority`) and an honest note that `plans` is the one IR construct not yet in the
  authoring surface. (4) A new **cross-stage regression gate**
  (`tools/check_codegen_coverage.py`, wired into `kcf check`) asserts every
  concept-kind, profile block, and tail array is elicited **and** IR-reachable **and**
  shown in an example — so "documented but never realizable" can't come back. (5) A new
  `knowledge-ops` reference model exercises the constructs the other fixtures left out
  (allocation, BPMN `process`, assertion, identity-resolution, knowledge-query); all
  reference models are analyzer-valid and golden-locked.

- **Entity `category` — advisory data-management classification, reconciled.**
  Restores the record-nature ground truth (DBML-style master/transactional/reference/
  config) that semantic modeling otherwise drops — but as **advisory metadata, not a
  primitive**, honoring KCF's rule that record-nature is *emergent shape* (lifecycle/
  event/transformation/mutability), not a flat tag. Author `category <value>;` on an
  entity (same mechanism as `mutability`, lands in `concept.metadata.category`; no
  grammar change). A new analyzer check (`kcf.entity.category-shape` /
  `kcf.entity.category-vocab`, **warnings only**) reconciles the stated tag against the
  derived shape — flagging e.g. an entity marked `master` that is a TRANSFORMATION
  target and emits events (likely `transactional`), or a bad vocabulary value —
  without ever blocking a model, and conservatively (it never guesses master vs config
  vs reference, which shape can't separate). Elicitation now captures it (with a
  caution not to bolt on lifecycles/CRUD just to close coverage gaps, which distorts
  the signal); `system-prompt.md`/`CONSTRUCT_COVERAGE.md` use it as a UI/topology
  driver (master→pickers+stewardship, transactional→workflow lists, config→settings,
  reference→static). New `entity-category` reference domain + a conformance assertion
  lock the behavior. `CONCEPTS.md` documents the ontology decision.

- **Model-quality guardrails — three additions from real authoring friction.**
  - **Category-aware coverage.** `kcf assess` coverage now respects an entity's
    advisory `category`: `transactional` expects the full treatment (CRUD + set +
    lifecycle), `master` expects CRUD but not a lifecycle, and `reference`/`config`
    are exempt from write/lifecycle obligations. Coverage rewards *appropriate*
    modeling, not maximal — closing the anti-pattern where chasing `recommendedGaps: 0`
    added empty lifecycles to master/config entities and destroyed record-nature
    inference. Behavior is unchanged when no `category` is stated.
  - **Unknown-concept-field warning.** A new advisory analyzer check
    (`kcf.concept.unknown-field`, **warning only**) flags a concept field captured by
    the concept-body metadata catch-all that isn't a recognized advisory tag — so a
    typo or an unsupported field is caught at authoring time instead of surfacing as a
    hard error only after a later grammar version types that slot.
  - **Doc↔grammar drift gate.** `tools/check_doc_examples.py` (wired into `kcf check`)
    compiles every *complete* ` ```kcf ` example in the docs against the current parser;
    illustrative blocks opt out with a `// doc-skip` first line. Directly guards the
    "docs were ahead of the compiler" drift class. (It immediately caught one stale
    example.)

- **Source-fidelity + UI-generation upgrades (from real build friction).**
  - **DBML importer.** `kcf import-dbml` (`tools/import_dbml.py`) deterministically
    turns a DBML schema into a KCF model + source document + trace — tables→entities,
    columns→attributes, refs→relationships carrying **`cardinality`** and **`on-delete`**,
    and a DBML **`category`** (table setting or `Note`) → advisory `metadata.category`.
    Complete by construction, so hand-translation no longer silently drops columns,
    cardinality, or the category. Conformance-tested.
  - **Source-coverage surfaced.** A new `source_coverage` MCP tool + an elicitation
    prompt report *what fraction of a source document the model captures* ("covers 71%;
    5 segments dropped"), so fidelity loss is visible by default, not discovered later.
  - **Relationship qualifiers drive UI.** `cardinality`/`source-role`/`target-role`/
    `on-delete` (which ride the relationship catch-all — no grammar change) are now
    documented, advisory-checked (`kcf.relationship.unknown-qualifier` /
    `on-delete-vocab`), and mapped in codegen: `one-to-many`→master-detail grid/tab
    (labeled by `target-role`), `one-to-one`→panel, `on-delete`→the FK delete rule.
  - **Codegen floor raised.** `COOKBOOK.md` gained a *Frontend depth* section
    (master-detail, typed inputs, enum-from-rules, lifecycle controls) and the system
    prompt now mandates emitting **OpenAPI from the live server, never a static file**
    (which goes stale). A brand-neutral **`design-system-default.md`** is applied when a
    model declares no `design` block, so every generated app has a coherent baseline.

- **Aggregate structure → navigation (roots vs pure parts).** Code generation now
  derives UI navigation from the aggregate structure the `COMPOSITION` graph already
  encodes, so parts of an aggregate stop showing up as top-level nav. A **pure part** (a
  `COMPOSITION` target that is not itself a composition parent and has no independent
  inbound reference) renders as a **subtab on its parent's detail** (parent = the
  `COMPOSITION` source); every other entity is an **aggregate root** (top-level nav). The
  rule is fully **domain-agnostic** (pure graph structure) and documented in
  `COOKBOOK.md` §F, `CONSTRUCT_COVERAGE.md`, and the system prompt. An optional advisory
  `metadata.containment` (`root`/`part`) overrides the derivation for ambiguous cases and
  is analyzer-reconciled against the structure (`kcf.entity.containment-shape` /
  `containment-vocab`, **warnings only**) — the same reconciliation pattern as `category`.
  New `entity-containment` reference domain + a conformance assertion lock the derivation
  and the reconciliation; `CONCEPTS.md` documents the ontology decision (root/part is
  emergent from `COMPOSITION`, not a primitive).

- **Field-report feedback loop (`community/field-reports/`).** A lightweight, advisory
  "I noticed something" front door so downstream humans and LLM agents feed toolchain
  observations (friction, bugs, gaps, doc drift, over-modeling, source-fidelity loss,
  skeleton generations) back for triage. Each report is a fenced, machine-parseable
  `kcf-field-report:v1` YAML envelope (`phase`/`area`/`severity`/`evidence`/…) requiring a
  minimal reproducer and `domainSanitized: true` (toolchain feedback, never domain data).
  A capture directive is embedded in `mcp/authoring-brief.md`, `codegen/system-prompt.md`,
  and a new repo-root `CLAUDE.md` — advisory, never blocks modeling or generation; agents
  write to `community/field-reports/incoming/` and emit the envelope, never fabricating a
  submission. Wired into `CONTRIBUTING.md` and a `field-report` issue template; reports
  that would touch the grammar/IR/analyzer contract route into the existing Grammar RFC
  (`docs/EXTENDING.md`) + `VERSIONING.md` governance. Nothing here changes the contract.

### Notes
- Advanced pattern authoring is a proprietary capability and is **not**
  part of this open-source stack.

<!--
Template for future releases:

## [X.Y.Z] - YYYY-MM-DD
### Added        (compatible; minor)
### Changed      (note contract + breaking/compatible)
### Deprecated   (aliases retained ≥1 major release)
### Removed      (breaking; major)
### Fixed
### Security
Tag contract-affecting lines, e.g.: "[ir] add optional `evidence` to concepts".
-->
