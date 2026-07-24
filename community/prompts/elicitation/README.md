# Elicitation packs

House conventions for the *modelling* half — the questions the assistant asks and
the defaults it proposes while turning a domain into a `.kcf` model. Point
`KCF_ELICITATION_GUIDE` (or the `model_domain` prompt's `conventions` arg) at a
pack's `guide.md`.

One folder per pack:

```
<pack-name>/
  guide.md    # the conventions (point the env var here)
  README.md   # title, author, when to use, what it assumes
```

Copy [`TEMPLATE.md`](TEMPLATE.md) → `<pack-name>/guide.md`, and add a short
`README.md`. Keep it imperative and portable. Reference:
[`kcf-oss/mcp/elicitation.example.md`](../../../kcf-oss/mcp/elicitation.example.md).

**Rule:** these guide the *questions and defaults* only — the assistant must still
ask before inventing facts, and the model must reach `valid` before generation.
