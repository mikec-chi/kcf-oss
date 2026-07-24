# Community Prompt Packs

Share the house conventions that made KCF work better *for you*. These are plain
Markdown files you inject into the MCP server (or the codegen pack) to tune **how
the domain is elicited** and **how code is generated** — without forking anything.
The best packs become starting points for everyone else.

Two kinds:

| Pack | Tunes | Plugs into |
|---|---|---|
| **[elicitation/](elicitation/)** | the questions asked & defaults proposed while modelling (tenancy, audit, standard actors/entities, naming) | `KCF_ELICITATION_GUIDE`, or the `model_domain` prompt's `conventions` arg |
| **[codegen/](codegen/)** | how code is generated (ORM, auth, naming, tests, observability) | `KCF_CODEGEN_OVERRIDES`, or `codegen_prompt(..., instructions=…)` |

Both are a **layer on top of** the checked model: they change *how* things are asked
and built, never *what* the model means — the required gaps, the action contracts,
and the coverage self-audit always still hold.

## Layout

One folder per pack, `kebab-case`:

```
community/prompts/elicitation/saas-multitenant/
  guide.md      # the elicitation conventions (this is the file you point the env var at)
  README.md     # what it's for, who made it, when to use it

community/prompts/codegen/fastapi-async-strict/
  overrides.md  # the codegen conventions
  README.md
```

Copy the `TEMPLATE.md` in each subfolder to start. See the shipped examples for the
full shape: [`kcf-oss/mcp/elicitation.example.md`](../../kcf-oss/mcp/elicitation.example.md)
and [`kcf-oss/codegen/overrides.example.md`](../../kcf-oss/codegen/overrides.example.md).

## The bar

- **Short and imperative** — a page of clear rules beats an essay.
- **Portable** — no secrets, no company-specific names a stranger can't reuse.
- **Scoped** — say which stack/domain it targets and when *not* to use it.
- **Honest** — it should be something you actually ran, with the effect you claim.

## Try a pack

```jsonc
// MCP host config — point the env var at a pack's file:
{ "mcpServers": { "kcf": { "command": "kcf-mcp", "env": {
    "KCF_ELICITATION_GUIDE": "/abs/path/community/prompts/elicitation/<pack>/guide.md",
    "KCF_CODEGEN_OVERRIDES": "/abs/path/community/prompts/codegen/<pack>/overrides.md"
} } } }
```
