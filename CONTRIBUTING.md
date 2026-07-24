# Contributing to KCF

Thanks for your interest — KCF is an open standard, and it gets better the more
people model with it, tune it, and extend it. There are two tracks: **build on
KCF** (share content — no core changes) and **improve the core** (grammar,
analyzer, tooling).

## Ground rules

- Be respectful; we follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- By contributing you agree your work is licensed under [Apache-2.0](LICENSE).
- KCF is open-core. This repository is the **open standard** — grammars, compiler,
  analyzer, IR schema, foundational presets, and the LLM codegen pack. It **stops at
  the semantic IR**; deterministic emitters and the runtime are a separate commercial
  platform that composes it. See [OPEN_CORE.md](OPEN_CORE.md) — we won't merge changes
  that make the open standard depend on proprietary code.
- One focused contribution per PR; describe the *why*, not just the *what*.

---

## Track A — build on KCF (the `community/` area)

No core changes, no gate to pass beyond the area's own check. Start at
**[`community/README.md`](community/README.md)**; each area has a `TEMPLATE` and a
short guide.

| Contribute | Where | Check |
|---|---|---|
| 🧩 **Models** — `.kcf` domains you built | [`community/models/`](community/models/) | `python community/models/validate.py` (must be `valid`) |
| ✍️ **Prompt packs** — elicitation guides & codegen overrides | [`community/prompts/`](community/prompts/) | follow the template |
| 💡 **Techniques** — how-to write-ups for elicitation & codegen | [`community/techniques/`](community/techniques/) | follow the template |
| 🏆 **Showcase** — apps you built with KCF | [`community/showcase/`](community/showcase/) | follow the template |
| 🔤 **Experimental grammars** — grammar ideas, pre-core | [`community/grammars/experimental/`](community/grammars/experimental/) | self-describing |

These are curated for quality, not just collected — real, self-describing, honest,
and reusable. A model of a domain you know, or a technique that worked for you, is a
great first PR.

---

## Track B — improve the core

### Adding a code-generation stack (easy, high-value)

New tech-stack examples for the codegen pack are the friendliest core contribution:
copy a folder under [`kcf-oss/codegen/stacks/`](kcf-oss/codegen/stacks/), write a
`stack.json` (validated against `stack-target.schema.json`), and author an
`EXAMPLE.md` that realizes the reference `business-application` model in your stack —
honoring its lifecycle and the `UpdateCustomer` action contract. See
[`kcf-oss/codegen/README.md`](kcf-oss/codegen/README.md).

### Adding a domain preset

New foundational profiles live in
[`kcf-oss/profiles/presets/`](kcf-oss/profiles/presets/) with automatic dependency
closure. Presets that capture a broad, reusable domain shape are welcome.

### Changing or adding a grammar

Grammar changes are semantic commitments, not just code. Read
**[`kcf-oss/docs/EXTENDING.md`](kcf-oss/docs/EXTENDING.md)** for the full recipe. For
anything beyond a small tweak — a new dimension, a breaking IR change, a new grammar
family — **open a [Grammar RFC](../../issues/new?template=grammar_rfc.md) first** and
agree on the meaning before implementing. Not sure it's ready for core? Share it in
[`community/grammars/experimental/`](community/grammars/experimental/) first. Record
every contract-affecting change in [CHANGELOG.md](CHANGELOG.md).

### Analyzer rules, integrations, docs

- **Analyzer rules**: a rule ID must exist in the catalogue, and every automated
  handler needs a negative regression fixture under `tests/fixtures/invalid/`.
- **Integrations**: MCP host configs and editor plugins live in
  [`kcf-oss/integrations/`](kcf-oss/integrations/).
- **Docs**: improvements to the guides and examples are always welcome.

### The one gate you must pass (core changes)

```bash
python semantic-core/tools/build_rules.py
python kcf-oss/tools/build_semantic_rules.py
kcf check                    # == python kcf-oss/tools/kcf.py check
```

CI runs exactly this on every pull request. Green locally ⇒ green in CI.

### What each core change needs

- **Grammar edits** (`kcf-oss/grammars/**`): intentional versioning, whitespace
  normalization (`tools/normalize_stack.py --write`), lint (`tools/lint_stack.py`),
  lock regeneration, updated docs, updated compatibility metadata. Module filenames,
  start productions, and dependencies are normative in `config/grammar-stack.json`.
- **Emitters** (in the commercial platform): must produce a `trace-manifest.json`
  and report unsupported meaning rather than silently dropping it (decision D-005).
- **Do not hand-edit generated files** (semantic catalogues, coverage, fixture
  indexes, module locks, `*.golden.json`) — change the source and regenerate.

See `kcf-oss/AGENTS.md` and `.llm/MAINTENANCE.md` for the full maintainer rules.

---

## Development setup

```bash
git clone https://github.com/mikec-chi/kcf-oss.git && cd kcf-oss
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .            # provides the `kcf` command + jsonschema
```

`kcf-oss/` and `semantic-core/` must stay **sibling directories** — the toolchain
resolves the shared semantic core by relative path.

## Pull request checklist

1. **Community content:** the area's check passes (e.g. `validate.py` for models),
   and your contribution has its short README/metadata filled in.
2. **Core changes:** `kcf check` is green; new behavior has a fixture/golden; new
   analyzer rules have negative fixtures.
3. Docs updated (README / QUICKSTART / docs) if user-facing.
4. One focused change per PR; explain the *why*.

## Good first contributions

- A **model** of a domain you know (`community/models/`).
- A **technique** write-up of something that worked (`community/techniques/`).
- A new **codegen stack** (`kcf-oss/codegen/stacks/`).
- Docs fixes and additional example domains.

Look for the [`good first issue`](../../labels/good%20first%20issue) label.
