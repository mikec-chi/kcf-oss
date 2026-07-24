# KCF Community

This is where the community builds *on top of* the KCF standard. The core
(`kcf-oss/`) is the grammar, compiler, analyzer, IR, and codegen pack. This folder
is the shared library of **content and know-how** that grows around it — the part
that gets better the more people use KCF.

Everything here is **[Apache-2.0](../LICENSE)** (same as the repo) unless a
contribution's own README says otherwise. See **[CONTRIBUTING](../CONTRIBUTING.md)**
for the ground rules and PR process.

## What you can contribute

| Area | Contribute | Where |
|---|---|---|
| 🧩 **[Models](models/)** | `.kcf` domain models you've built, for others to learn from and reuse | `community/models/` |
| ✍️ **[Prompt packs](prompts/)** | House **elicitation guides** and **codegen overrides** that made the MCP better for you | `community/prompts/` |
| 💡 **[Techniques](techniques/)** | Write-ups of *how* to elicit and generate well — patterns, playbooks, lessons | `community/techniques/` |
| 🔤 **[Grammars](grammars/)** | New grammar modules or revisions (via RFC), and experimental grammar profiles | `community/grammars/` |
| 🏆 **[Showcase](showcase/)** | Apps you built with KCF — "Built with KCF" gallery | `community/showcase/` |

And these live in the core tree (contribution paths documented in
[CONTRIBUTING](../CONTRIBUTING.md)):

| Area | Contribute | Where |
|---|---|---|
| 🛠️ **Codegen stacks** | New backend/frontend targets (a worked `EXAMPLE.md`) | `kcf-oss/codegen/stacks/` |
| 📦 **Presets** | New domain profile presets | `kcf-oss/profiles/presets/` |
| 🔌 **Integrations** | MCP host configs, editor plugins, connectors | `kcf-oss/integrations/` |

## How it works

1. **Pick an area** above and read its `README.md` — each explains the format, the
   metadata, and the quality bar.
2. **Copy the `TEMPLATE`** in that area, fill it in, and put it in a folder named
   after your contribution (`kebab-case`).
3. **Check it.** Models must be **valid** (`python community/models/validate.py`);
   prose contributions just need to follow the template.
4. **Open a PR** — one contribution per PR, and say *why* it's useful. See
   [CONTRIBUTING](../CONTRIBUTING.md).

## The bar

Contributions are curated, not just collected — the goal is a library people
trust:

- **Real and usable** — something you actually used or built, not a placeholder.
- **Self-describing** — a short README with author, purpose, and how to use it.
- **Honest** — say what it's good for and what it isn't; don't oversell.
- **Attributed & licensed** — you keep credit; it ships under Apache-2.0 so anyone
  can build on it.

New here? A great first contribution is a **model** of a domain you know, or a
**technique** write-up of something that worked for you.
