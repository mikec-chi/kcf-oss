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

The package version (`pyproject.toml`) moves in lockstep with the highest-impact
contract change in a release. Breaking changes to any contract require a major
bump and, for `ir`, a migration path (`tools/migrate_ir.py`).

## [Unreleased]

First public release of the open standard. Cut this section to a dated version
(e.g. `## [1.3.0] - YYYY-MM-DD`) when publishing to GitHub/PyPI.

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
