# Grammars — new modules & revisions

Grammar changes are the highest-leverage — and highest-responsibility —
contribution, because the grammar defines what every model *means*. A change to a
production or the IR is a **semantic commitment** that ripples through the compiler,
analyzer, coverage model, and every downstream generator. So this area has two
lanes.

## Lane 1 — a change to the core grammar (via RFC)

For anything that touches the shipped stack (`kcf-oss/grammars/**`) or the IR — a
new dimension, a new production, a breaking change — go through the process:

1. **Read** [`kcf-oss/docs/EXTENDING.md`](../../kcf-oss/docs/EXTENDING.md) — the full
   recipe (what to touch, in what order, how to version and lock it).
2. **Open a Grammar RFC** first (issue template: *Grammar RFC*) and reach agreement
   on the *meaning* before writing code. Contract-affecting changes are recorded in
   [`CHANGELOG.md`](../../CHANGELOG.md) and versioned per
   [`kcf-oss/docs/VERSIONING.md`](../../kcf-oss/docs/VERSIONING.md).
3. **Implement** against the RFC: update the module, normalize + lint + relock,
   add fixtures, keep `kcf check` green.

The bar is high on purpose — but small, well-scoped revisions (a missing enum value,
a clarified production, a fixed edge case) are very welcome and usually easy.

## Lane 2 — an experimental grammar (share before it's core)

Have a grammar idea that isn't ready to be core — a domain-specific profile, a
speculative dimension, a proof of concept? Put it in
[`experimental/`](experimental/) so others can try and critique it **without**
changing the shipped stack. Experimental grammars are not loaded by the compiler and
carry no compatibility promise; the good ones graduate to core via Lane 1.

## What a good grammar contribution looks like

- **Motivated by meaning** — it lets models express something they genuinely can't
  today, not just sugar.
- **Minimal & composable** — reuses the existing dimension/relationship vocabulary
  rather than duplicating it.
- **Versioned & tested** — normative metadata updated, fixtures added, gate green
  (for core); clearly labelled and self-explaining (for experimental).
