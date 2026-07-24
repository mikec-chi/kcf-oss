# The open-core promise

KCF is developed open-core. This page states plainly what that means, so you can
adopt the standard without worrying about a rug-pull.

## What is always open (this repository, Apache-2.0)

These are the **standard**, and they are free to use, fork, and build on —
forever, under [Apache-2.0](LICENSE):

- **The grammars** — all 29 EBNF modules and the `KCF` metagrammar.
- **The semantic IR contract** — `model-ir-v1` and the preset/delta schemas.
- **The reference compiler** — `.kcf` text → normalized IR.
- **The semantic analyzer** — validity, coverage, pattern-proof, role checks
  (`kcf assess`).
- **The code-generation pack** — `codegen/`: the tech-stack-agnostic system
  prompt, the per-run templates, the per-construct coverage audit, and the
  single-shot examples across **backend** tiers (each exposing a Swagger/OpenAPI
  interface) and **frontend** tiers (bound to that OpenAPI) that turn a KCF IR
  into an application with any LLM, for any stack. Open, and extensible with your
  own stack descriptors.
- **The application-generation workflow** — the ordered prompt package.

**OSS stops at the IR.** The open standard produces the machine-checked semantic
IR; turning that IR into running code is done by the LLM **codegen pack** (open,
above) or by deterministic **emitters**, which are part of the commercial overlay
(below). The IR schema is the contract: anyone can write their own compiler,
analyzer, or emitter against it without permission.

## What is commercial (a separate product)

A commercial platform from **Composable Holdings Inc.** composes this standard
and adds operational capabilities
on top — for example the deterministic **emitters** (vertical-slice, and
the tech-stack target/agentic emitters), a persisted semantic knowledge graph,
additional industry-specific pattern presets, runtime/drift tooling, and an
execution engine. That product **imports** the open standard; it never copies it
and never replaces it.

## The invariants we hold ourselves to

1. **The open standard never depends on proprietary code.** The dependency
   arrows point one way only: commercial → open, never open → commercial. A PR
   that inverts this will not be merged.
2. **The open gate stands alone.** `kcf check` passes using only this
   repository. It has no proprietary dependency.
3. **What is open stays open.** Everything in the open list above — the
   grammars, IR, compiler, analyzer, foundational presets, and the LLM codegen
   pack — stays open; new commercial features are additive on top of the IR.
   (Before the first public release the boundary was set deliberately at the IR:
   deterministic emitters are a commercial concern, since the open standard's job
   is to produce a complete, machine-checked IR, not to ship code generators.)
4. **The IR is a public contract.** Breaking changes to `model-ir-v1` are
   versioned and migrated in the open.

## Why open-core at all

Standards win by adoption, not by lock-in. Keeping the grammar, analyzer, and IR
fully open — with a permissive license and a patent grant — is what lets you
target KCF from your own tools with zero risk. The commercial layer exists to
fund the standard's development, not to gate it.

Questions about the boundary? Open a
[discussion](https://github.com/OWNER/kcf/discussions).
