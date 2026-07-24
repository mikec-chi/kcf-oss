# Experimental grammars

A staging area for grammar ideas that aren't part of the shipped stack yet — share,
try, and critique them here before proposing them for core via a
[Grammar RFC](../README.md#lane-1--a-change-to-the-core-grammar-via-rfc).

**These are not loaded by the compiler** and carry **no compatibility promise**.
They exist so grammar work can be discussed against something concrete.

## Layout

One folder per experiment, `kebab-case`:

```
experimental/<name>/
  <NAME>.ebnf     # the grammar module(s), ISO/IEC 14977 EBNF like the core stack
  README.md       # what it adds, why, an example, and open questions
```

## Your README should answer

- **What meaning does this add** that models can't express today?
- **How does it compose** with the existing dimensions/relationships?
- **Example** — a snippet of model text using it, and the IR you'd expect.
- **Open questions** — what still needs deciding before it could be core.

When it's ready, open a Grammar RFC and follow
[`kcf-oss/docs/EXTENDING.md`](../../../kcf-oss/docs/EXTENDING.md) to graduate it.
