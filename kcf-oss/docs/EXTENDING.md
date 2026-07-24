# Extending KCF: changing and adding grammars

This is the contributor guide for changing an existing grammar module, adding a
new semantic dimension, or adding a whole new grammar family. It explains what to
touch, in what order, how to version it, and how the change ripples through the
rest of the stack.

> **Propose before you build.** A grammar change is a *semantic commitment*, not
> just code. For anything beyond a small tweak, open a **Grammar RFC** issue
> first (see `.github/ISSUE_TEMPLATE/grammar_rfc.md`) so the shape of the change
> is agreed before implementation. New dimensions and any breaking IR change
> require an accepted RFC.

## The mental model: four independent contracts

KCF versions four things separately (`docs/VERSIONING.md`), and a change ripples
only as far up this chain as it actually reaches:

1. **grammar-stack version** — the module set and their productions
2. **semantic IR version** (`model-ir-v1`) — the normalized model shape
3. **semantic-rule catalogue version** — the analyzer's rules
4. **emitter version** — a given emitter's output contract

The IR is the load-bearing interface. Everything downstream (analyzer, emitters,
presets, the playground, any external tool) targets `model-ir-v1`. As long as a
change still produces valid IR and emitters honor the trace-or-flag rule (D-005,
below), the stack degrades gracefully instead of breaking.

## How a change flows through the stack

```
grammar-stack.json (manifest) ──▶ module-lock.json (hashes)
        │                                    │
   .ebnf modules ──▶ reference compiler ─▶ model-ir-v1 (IR contract)
        │            (AUTHORING surface)      │
 SEMANTIC_VALIDATION.md ─▶ semantic-rules.json ─▶ analyzer ─▶ coverage.json
        │                                        │
    presets (closure) ◀─────────────────────────┘
        │
    emitters (D-005 trace) ─▶ goldens ─▶ conformance gate ─▶ compatibility-matrix.json
```

Much of this is **mechanical**: the manifest (`config/grammar-stack.json`) is
normative, and closure, catalogues, and hashes are *generated* — you edit the
smallest source and regenerate. The human-judgment surfaces are the IR schema,
the compiler's authoring surface, analyzer handlers, emitters, and versioning.

## Three kinds of change, and their blast radius

| Kind | Example | Blast radius |
|---|---|---|
| **A. Modify an existing module** | add an optional production to `ENTITY` | small, mostly mechanical |
| **B. Add a new dimension module** | a new `NEGOTIATION` grammar | large — IR, compiler, analyzer, emitters, presets |
| **C. Add a new grammar family** | an add-on language on the ANTLR track | architectural — a new compiler front-end |

---

## A. Modify an existing module

1. Edit the owning `.ebnf` under `kcf-oss/grammars/`. **Reference** shared
   productions from other modules; never copy them. Ownership is defined in
   `config/grammar-stack.json` and `AGENTS.md`.
2. If the module's *contract* changed (not just an internal refactor), bump the
   grammar-stack version and the module contract version.
3. Regenerate and gate, from the repository root:

   ```bash
   python kcf-oss/tools/normalize_stack.py --write   # canonical whitespace/line endings
   python kcf-oss/tools/validate_stack.py            # structural validity
   python kcf-oss/tools/lint_stack.py                # cycles, unreachable/nullable, unused imports
   python kcf-oss/tools/lock_modules.py              # regenerate module-lock.json hashes
   python kcf-oss/tools/kcf.py check                 # full conformance gate
   ```

   Only run `lock_modules.py` for an intentional, reviewed change — never to
   silence an unexplained hash mismatch.
4. If a separate commercial platform composes this stack downstream, its
   maintainers re-run their own gate after an OSS grammar change. As an
   open-source contributor you don't need it — the open stack never depends on
   any downstream platform, and `kcf check` is the gate for this repository.

If the edit is purely additive/optional you are usually done after regenerating
locks and any affected goldens.

## B. Add a new dimension module (the expensive one)

Do these in order — each step assumes the previous.

1. **Manifest + grammar.** Add the new `.ebnf`, then register it in
   `config/grammar-stack.json` (filename, start production, `imports` for EBNF
   symbol imports, `semanticImports` for dependency-without-copying). Regenerate
   `config/module-lock.json`. The module and production counts change and become
   new verified numbers in the handoff.
2. **Compiler (the step most people miss).** The reference compiler is a
   hand-written lexer/parser/normalizer that parses only the **AUTHORING textual
   surface**. If users will author the dimension in `.kcf`, extend the
   `AUTHORING` EBNF, lexer, parser, AST, normalizer, and compiler trials
   *together*. If the dimension is specification-only (not authored textually),
   the compiler is untouched — but it will not appear in IR compiled from `.kcf`.
3. **IR contract.** Add the new collections/objects to
   `schemas/model-ir-v1.schema.json` and the normalizer. Adding *optional* shapes
   is compatible; removing, narrowing, or newly-requiring is breaking — bump
   `irVersion` and add `migrate_ir.py` logic for persisted IR.
4. **Analyzer + rules.** Put new validation rules in
   `semantics/SEMANTIC_VALIDATION.md`, regenerate the catalogue
   (`build_semantic_rules.py`). Every **automated** handler needs a **negative
   regression fixture** that emits its stable rule ID while all positive fixtures
   stay silent. The gate enforces this.
5. **Coverage.** Declare the dimension's required/recommended obligations in
   `config/coverage-model.json`. This is what `assess`'s `ready: true` verdict
   keys on.
6. **Emitters.** You do *not* have to support the new dimension in emitters
   immediately — D-005 (below) means they flag it unsupported rather than drop
   it. Real support is a separate emitter change (new goldens + a
   `compatibility-matrix.json` bump).
7. **Presets.** Add the module to any foundational preset that should include it;
   dependency closure recomputes automatically via `profile_resolver.py`.
8. **Goldens, fixtures, docs.** Regenerate compiler/emitter goldens, add domain
   fixtures, and update `README.md`, `docs/CONCEPTS.md`, and the whitepapers.

Then run the full gate (step A.3).

## C. Add a new grammar family

The planned path for future add-on grammars is a **separate ANTLR-based compiler
track** (not yet built), independent of the hand-written KCF compiler. The rule
that keeps this safe: a new front-end must normalize into the **same
`model-ir-v1` contract**. The IR is the stable seam that lets a new grammar
family plug in without destabilizing the existing modules. Everything downstream
of the IR (analyzer, emitters, presets, playground) is then reused unchanged.

---

## Versioning rules (what counts as breaking)

From `docs/VERSIONING.md`:

- **Breaking:** removing a concept, changing its primary kind, narrowing a
  required contract, or adding a runtime requirement. → major bump + migration.
- **Compatible:** adding an optional concept or attribute. → minor bump.
- **Patch:** documentation-only changes.
- Deprecated diagnostic IDs remain **aliases for at least one major release**.

Because the project ships as a package, move `pyproject.toml`'s version in
lockstep with the contract change, and record it in `CHANGELOG.md` under the
contract(s) affected. Once the repo is public and people target `model-ir-v1`
from their own tools, **the IR version is your public API version.**

Use `tools/semantic_delta.py` before release to classify a change, and
`tools/migrate_ir.py` to bring persisted older IR to the current schema
(recompile from `.kcf` source whenever possible; migration is for persisted IR
without a current source).

## The D-005 safety net

Whatever consumes the IR must account for every construct and mark any meaning it
cannot realize as `unsupported` — it may **never silently drop it**. This is why
adding a dimension does not immediately break consumers: unsupported meaning
surfaces as `complete: false` with an explicit `unsupported` list, not as lost
data. Preserve this discipline in every change.

## Interaction with a commercial platform

KCF is developed open-core (see `OPEN_CORE.md`). A separate commercial platform
builds on this stack. The dependency arrow points one way: the platform imports
`kcf-oss`, never the reverse, so new open modules can only *add* capability
downstream, never break it by direction. Keeping that arrow one-directional is a
hard rule — a PR that makes the open stack depend on any downstream platform will
not be merged. Re-verifying downstream after an OSS change is that platform's
maintainers' responsibility, done separately and outside this repository.

## Governance

- **Grammar RFC first** for new dimensions, breaking IR changes, or new grammar
  families — open the issue, reach agreement, then implement.
- **Record every contract-affecting change** in `CHANGELOG.md`, tagged with which
  of the four contracts moved.
- **Honor the deprecation policy** — aliases for ≥1 major release; announce
  removals a release ahead.

## Per-change PR checklist

- [ ] Change kind identified (A / B / C) and, for B/C, an accepted Grammar RFC linked
- [ ] `normalize_stack --write`, `validate_stack`, `lint_stack` clean
- [ ] `lock_modules.py` regenerated (intentional grammar change only)
- [ ] IR schema + normalizer updated; `irVersion` decided; migration added if breaking
- [ ] New analyzer rules have negative regression fixtures; catalogue regenerated
- [ ] Coverage obligations updated in `config/coverage-model.json`
- [ ] Emitters updated or unsupported-flagging verified (D-005); goldens regenerated
- [ ] `compatibility-matrix.json` and versions bumped as required
- [ ] `python kcf-oss/tools/kcf.py check` green
- [ ] `CHANGELOG.md` and docs updated
