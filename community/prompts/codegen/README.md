# Codegen packs

House conventions for the *generation* half — how the app is built from a model.
Point `KCF_CODEGEN_OVERRIDES` (or `codegen_prompt(..., instructions=…)`) at a pack's
`overrides.md`. They're injected as a **highest-priority** section that overrides the
single-shot example where they conflict.

One folder per pack:

```
<pack-name>/
  overrides.md   # the conventions (point the env var here)
  README.md      # title, author, target stack, when to use
```

Copy [`TEMPLATE.md`](TEMPLATE.md) → `<pack-name>/overrides.md`, and add a short
`README.md` (say which **stack** it targets). Reference:
[`kcf-oss/codegen/overrides.example.md`](../../../kcf-oss/codegen/overrides.example.md).

**Rule:** overrides change *how* code is built, never the model's meaning — the
action contracts, "drop nothing," and the coverage self-audit still hold.
