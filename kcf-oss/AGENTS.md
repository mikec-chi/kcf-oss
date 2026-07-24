# KCF Stack Instructions

Read the repository `AGENTS.md`, `LLM_HANDOFF.md`, this stack's `README.md`,
and `../.llm/MAINTENANCE.md` before editing.

## Ownership

- `KCF` owns shared metagrammar machinery.
- `RELATIONSHIP` owns the ten-root relationship algebra.
- `ACTION` owns record commands/queries, set mutations, and collection
  transformations.
- Each dimension grammar owns one primary semantic dimension.
- Operational and emitter profiles compose dimensions; they do not redefine
  root constructs.
- AUTHORING is ergonomic syntax compiled to canonical IR; it is not a second
  semantic model.

## Generated files

Do not hand-edit semantic catalogues, coverage, fixture indexes, module locks,
compiler `.golden.json` files, or updated PDFs. Change their sources and
regenerate them using `.llm/MAINTENANCE.md`. (kcf-oss stops at the IR; a separate
commercial platform builds on top of it.)

## Required checks

Use `python tools/kcf.py check` as the final gate. Grammar edits also require
intentional versioning, normalization, lint, lock regeneration, documentation,
and updated compatibility metadata. Analyzer rule IDs must exist in the
catalogue and automated handlers require negative regression fixtures.

## Business profiles

Preset inheritance is resolved by `tools/profile_resolver.py` and validated by
`schemas/profile-preset-v1.schema.json`. Required/prohibited patterns must
remain disjoint after composition. `implements` and `excludes` claims are
explicit model assertions; do not represent them as automatic structural proof.

## Name

This open-source stack is `KCF` (`kcf-oss/`). A separate proprietary overlay
(maintained as its own product, not part of this repository) composes this stack.
Keep KCF grammar identifiers free of any commercial-platform branding, and never
copy proprietary platform code into `kcf-oss/`. The dependency
arrow points one way only: the platform imports `kcf-oss`, never the reverse.

## Preset scope

`kcf-oss/profiles/presets/` holds only the six foundational presets
(business-application, operational-system, organizational-knowledge,
event-driven-system, ai-application, analytics-platform). Additional
business-pattern presets are provided by the proprietary overlay and inherit
these foundations via the `KCF_PRESET_PATH` search path that
`profile_resolver.py` honors.
