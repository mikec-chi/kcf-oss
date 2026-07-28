# Knowledge Coding — the new vibe coding

**Knowledge Coding is the new Vibe Coding: semantic modeling + vibe coding.**

Vibe coding is magic until the app gets real — then the LLM starts guessing at your
domain: inventing fields, dropping half a lifecycle, hallucinating relationships,
quietly disagreeing with itself across files. The fix isn't a cleverer prompt; it's
a better *input*. You spend the first few minutes turning your domain into a
**validated, coverage-assessed, traceable model** — one that reports which obligations
passed rather than pretending your domain is complete — and the LLM builds from *that*
— same speed and vibe, but from a checked spec instead of a guess.

```
        vibe coding:   prose ─────────────────▶ LLM ─▶ app   (guesses the gaps)
   knowledge coding:   prose ─▶ checked model ─▶ LLM ─▶ app   (builds from a spec)
                                    ▲
                                    KCF checks it: valid? complete? nothing dropped?
```

## Two ways in

Same tools, different depth — pick your path and graduate when you're ready:

| | 🌱 **Path A — knowledge code in your chat LLM** | 🛠️ **Path B — build a real project** |
|---|---|---|
| **For** | trying it, prototyping, newcomers | shipping and maintaining an app |
| **Install** | **none** — connect to the hosted server | `pip install`, then `kcf init` |
| **You get** | a modeled + generated app, in chat | a repo where the model stays the source of truth |

**Start with A.** Move to B when you're building something you'll keep.

---

## 🌱 Path A — knowledge-code in your chat LLM (no install)

Point the LLM you already use at KCF's **hosted** connector and just talk — nothing
to install, nothing to run.

- **ChatGPT** — Settings → Connectors (developer mode) → *Add* an MCP server:
  ```
  https://kcf-mcp.onrender.com/mcp
  ```
- **Claude Code** — one line:
  ```bash
  claude mcp add --transport http kcf https://kcf-mcp.onrender.com/mcp
  ```
- **Claude Desktop / Cursor / other host** — add a *remote / custom MCP connector*
  with that same URL. (Or run it locally — see Path B.)

Then just say what you want:

> *"Use KCF to model a support-ticket system, then generate a FastAPI backend."*

The assistant models your domain, checks it, lets you **approve** anything it
inferred, and generates the app — from a checked spec, not a guess. More to try:

- *"Assess this model and tell me what's missing."*
- *"Fill the gaps, but let me approve them — bulk-accept the confident ones."*
- *"Which stacks can you generate?"*

> The hosted demo is **read-only** and on a free tier — the first request after it's
> been idle wakes it in ~30–60s (just retry once). It never stores your data.

That's knowledge coding. Ready to build something you'll keep? → **Path B**.

---

## 🛠️ Path B — build a real project (developer)

Here the model becomes your project's **source of truth**, and your coding agent
keeps the code in sync with it.

**1. Install & seed a project**
```bash
pip install "kcf-oss[mcp]"     # the `kcf` CLI + the `kcf-mcp` server
kcf init my-app                # scaffolds a knowledge application
```
`kcf init` creates `model/` (your model + compiled IR — the source of truth), an
**`AGENTS.md`** that tells your coding agent the rules, `.kcf/` (bundled grammar
reference + protocols), and `kcf.project.json`.

**2. Connect KCF to your LLM locally** (full tools, offline):
```bash
claude mcp add kcf -- kcf-mcp        # Claude Code
```
Claude Desktop / VS Code / Cursor: add `{ "command": "kcf-mcp" }` to the MCP config —
see the [MCP reference](../mcp/README.md#configure-your-host) for each host.

**3. Model → check → generate** — run [the flow](#the-flow) below, via the CLI
(`kcf compile` / `kcf assess`) or the MCP tools.

**4. Keep the model true (no drift)** — point your agent at the generated `AGENTS.md`.
The model is the source of truth: any change to *meaning* goes into the `.kcf`
**first**, and if you vibe-code straight into the code, the agent **reconciles** the
model back to match (asking you when intent is ambiguous). Full protocol:
[`MODEL_SYNC.md`](../codegen/MODEL_SYNC.md).

**5. Go further** — [self-host the connector](../mcp/README.md#host-it-yourself-free) ·
[tune elicitation & codegen](../mcp/README.md#tune-it-to-your-house-standards-optional) ·
target [your stack](../codegen/) · [contribute](../../community/).

---

## The flow

Five steps, whichever path — you watch the model and the verdict the whole way, so
the code is always built from a spec you approved:

1. **Describe** your domain in plain language.
2. **Model** — a checked `.kcf`: entities, actors, events, lifecycles, actions. It
   never invents facts you didn't state — it asks.
3. **Check** — `assess`: *valid? what's missing?* It fixes the required gaps.
4. **Approve** — inferred gap-fills arrive as a **bulk** chunk (accept fast) or a
   **review** list (decide one by one). Nothing inferred becomes fact without you.
5. **Generate** — pick a stack; the **backend** (with a Swagger API), then a
   **frontend** wired to it. Each ends with a self-audit proving nothing was dropped.

> One-command variants (guided prompts): **`model_domain`** runs all five;
> **`build_model`** models only; **`generate_app`** generates only.

---

## Under the hood

- **The model is the spec.** Your `.kcf` compiles to a normalized semantic IR — every
  entity, attribute, typed relationship, lifecycle state machine, and action contract
  (idempotency / atomicity / concurrency / authorization) made explicit.
- **KCF checks it.** `assess` gives one verdict: *valid* (analyzer-clean — enough to
  generate) and *ready* (also complete). Coverage gaps travel to the generator as
  guidance you approve.
- **Nothing is silently dropped.** Generated code ends with a *coverage self-audit*
  that accounts for every construct in the model (decision D-005).

You keep the speed and feel of vibe coding — on a foundation you can see, check, and
trust.

## Go deeper

- **[QUICKSTART](../QUICKSTART.md)** — the CLI loop (compile → assess → codegen) in 60 seconds.
- **[WALKTHROUGH](WALKTHROUGH.md)** — requirements → a ready model → a generated app.
- **[CONCEPTS](CONCEPTS.md)** — the mental model (well-formed vs. valid vs. complete).
- **[MODEL_SYNC](../codegen/MODEL_SYNC.md)** — the living-model / drift-prevention protocol.
- **[codegen/](../codegen/)** — the code-generation pack (system prompt + per-stack examples).
- **[mcp/](../mcp/)** — the MCP server reference (all tools, every host, self-hosting, tuning).
- **[community/](../../community/)** — contribute models, prompt packs, techniques, showcase.
- **[EXTENDING](EXTENDING.md)** — change or add a grammar.
