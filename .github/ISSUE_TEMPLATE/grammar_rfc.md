---
name: Grammar RFC
about: Propose changing a grammar, adding a new dimension, or adding a grammar family
title: "[RFC] "
labels: rfc, grammar
---

<!--
A grammar change is a semantic commitment, not just code. Open this RFC and reach
agreement BEFORE implementing. New dimensions, breaking IR changes, and new
grammar families REQUIRE an accepted RFC. See kcf-oss/docs/EXTENDING.md.
-->

## Summary

<!-- One paragraph: what you want to model or change, and why it belongs in the
     grammar rather than in an author's model. -->

## Change kind

- [ ] **A** — modify an existing module (which: ______)
- [ ] **B** — add a new semantic dimension module (name: ______)
- [ ] **C** — add a new grammar family (new compiler front-end)

## Motivation

<!-- What can't be expressed today? Show a concrete domain that the current 29
     dimensions can't capture cleanly. Why references/relationships/traits on
     existing dimensions are insufficient. -->

## Contracts affected

<!-- KCF versions four contracts independently; check every one this touches. -->

- [ ] `grammar-stack` — module set / productions
- [ ] `ir` — the `model-ir-v1` shape
- [ ] `rules` — the semantic-rule catalogue
- [ ] `emitter` — an emitter's output contract

Expected impact: <!-- compatible (optional additions) / breaking (removes,
narrows, newly-requires) --> ______

## Proposed grammar sketch

```ebnf
(* EBNF for the new/changed productions. Reference shared productions from other
   modules; do not copy them. State the start production and its imports. *)
```

## IR impact

<!-- New collections/objects/fields in model-ir-v1. Are they optional (compatible)
     or required (breaking)? If breaking, describe the irVersion bump + migration. -->

## Semantic rules & coverage

<!-- New validation rules (stable IDs) and their coverage obligations
     (required / recommended) in coverage-model.json. Note which are automated
     (need a negative regression fixture) vs manual-review. -->

## Emitter impact

<!-- Do existing emitters need to realize this, or is flagging it `unsupported`
     via D-005 acceptable for now? Any new emitter target proposed? -->

## Authoring surface

<!-- Will this be authored in textual .kcf? If yes, note the AUTHORING/lexer/parser/
     normalizer work. If spec-only, say so (it won't appear in compiled IR). -->

## Backward compatibility & migration

<!-- Effect on existing models/IR. Deprecations (aliases kept ≥1 major release).
     Migration steps for persisted IR. -->

## Alternatives considered

<!-- Other modeling approaches you weighed and why you rejected them. -->

## Downstream checklist (for the eventual PR)

- [ ] manifest + module-lock
- [ ] compiler (if authored textually)
- [ ] IR schema + normalizer (+ migration if breaking)
- [ ] analyzer rules + negative fixtures + catalogue
- [ ] coverage obligations
- [ ] emitters (support or D-005 unsupported) + goldens
- [ ] presets, versions, compatibility matrix
- [ ] docs + CHANGELOG; `kcf check` and overlay gate green
