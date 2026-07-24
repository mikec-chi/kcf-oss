# Techniques

Write-ups of *how* to do knowledge coding well — the craft that isn't in the
grammar. If you found a way to elicit a tricky domain, get better generated code,
review synthetic gaps efficiently, or structure an agent loop, teach it here.

Topics that fit:

- **Elicitation** — how to interview for a hard domain; turning messy requirements
  into clean concepts/lifecycles/contracts; when to split a model or merge models.
- **Code generation** — getting an LLM to honor contracts; wiring backend↔frontend
  via OpenAPI; taming a stubborn stack; useful `overrides.md` patterns.
- **Gap review** — approving synthetic fills fast vs. rigorously; what to confirm
  vs. reject; catching over-eager inference.
- **Agent orchestration** — driving `next_action`, splitting `build_model` /
  `generate_app` across agents, verification loops.

## Layout

One Markdown file per technique, `kebab-case.md`:

```
community/techniques/eliciting-lifecycles-from-prose.md
```

Copy [`TEMPLATE.md`](TEMPLATE.md) to start.

## The bar

- **Concrete** — a real example (a snippet of `.kcf`, a prompt, a before/after)
  beats abstract advice.
- **Reproducible** — a reader can follow it and get a similar result.
- **Honest about limits** — say when it *doesn't* apply.
