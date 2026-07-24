# Knowledge Coding — the new vibe coding

**The new vibe coding is _knowledge coding_: semantic modeling + vibe coding.**

Vibe coding is magic until the app gets real — then the LLM starts guessing at
your domain: inventing fields, dropping half a lifecycle, hallucinating
relationships, and quietly disagreeing with itself across files. The problem isn't
the LLM. It's that it's building from **prose**, which is ambiguous and incomplete.

Knowledge coding fixes the input. You spend the first few minutes turning your
domain into a **complete, machine-checked model** — a semantic IR — and then the
LLM vibe-codes from *that*. Same speed and vibe, but now the code is built from a
specification instead of a guess.

```
        vibe coding:   prose ─────────────────▶ LLM ─▶ app   (guesses the gaps)
   knowledge coding:   prose ─▶ checked model ─▶ LLM ─▶ app   (builds from a spec)
                                    ▲
                                    KCF checks it: valid? complete? nothing dropped?
```

And it's **conversational** — you do it inside the chat LLM you already use.

---

## Start here: 3 minutes to your first knowledge-coded app

1. **Install** the KCF connector (an [MCP](https://modelcontextprotocol.io) server):
   ```bash
   pip install "kcf-oss[mcp]"      # provides the `kcf-mcp` command
   ```
2. **Connect it to your LLM** — one line for Claude Code, one config block for
   Claude Desktop / VS Code / Cursor, or a hosted URL for ChatGPT. See
   [Deploy KCF for your LLM](#deploy-kcf-for-your-llm) below.
3. **Knowledge-code.** In the chat, say:
   > *"Model a support-ticket system with KCF, then generate a FastAPI backend."*

   The assistant drafts a `.kcf` model, checks it (`assess`), fixes what's missing,
   asks your stack, and hands you a working app — built from a spec, not a guess.

That's it. The rest of this page is the flow, the deploy details per LLM, and
what's happening under the hood.

---

## The flow, from your words to a running app

Five steps, all in the chat:

1. **Describe** your domain in plain language — *"a support desk: tickets, agents,
   and SLAs."*
2. **Model** — the assistant drafts a checked `.kcf`: your entities, who acts, what
   happens, the lifecycles, and the actions. It never invents facts you didn't
   state — it asks.
3. **Check** — it runs `assess`: *is the model valid? what's missing?* It fixes what's
   required and shows you the verdict as it goes.
4. **Approve** — for anything it *inferred* to fill a gap, you stay in control: accept
   the confident suggestions in one **bulk** click to move fast, or **review** them
   one by one to be rigorous. Nothing inferred becomes fact without your say-so.
5. **Generate** — pick a stack; it generates the **backend** (with a Swagger API),
   then a **frontend** wired to it. Each ends with a self-audit proving nothing in
   your model was dropped.

You watch the model and the verdict the whole way, so the code is always built from a
spec you approved — not a guess.

> **Prefer one command?** Invoke a guided prompt: **`model_domain`** runs all five
> steps; **`build_model`** does steps 1–4 (model only); **`generate_app`** does step 5
> (generate only). Handy for splitting the work across agents.

---

## Deploy KCF for your LLM

All of these expose the same KCF tools and the guided prompts (`model_domain`,
`build_model`, `generate_app`). Install once: `pip install "kcf-oss[mcp]"`. The full
tool list is in the [MCP server reference](../mcp/README.md).

### Claude Code (CLI) — one command
```bash
claude mcp add kcf -- kcf-mcp
```
Then restart Claude Code. The tools are available, and the guided prompt shows up
in the prompt menu. (Optional convenience: a `/kcf-model` slash command — see
[`../integrations/claude-code/`](../integrations/claude-code/).)

### Claude Desktop
Settings → Developer → Edit Config, then add to `claude_desktop_config.json`:
```jsonc
{
  "mcpServers": {
    "kcf": { "command": "kcf-mcp" }
  }
}
```
Restart Claude Desktop.

### VS Code
Add an MCP server (VS Code's built-in MCP, or an MCP-capable extension). In
`.vscode/mcp.json` (workspace) or your user MCP config:
```jsonc
{ "servers": { "kcf": { "command": "kcf-mcp" } } }
```

### Cursor
`~/.cursor/mcp.json` (or Settings → MCP):
```jsonc
{ "mcpServers": { "kcf": { "command": "kcf-mcp" } } }
```

### ChatGPT (and any remote/hosted host)
ChatGPT connectors speak MCP over HTTP, so they need a reachable HTTPS URL.

**Fastest — use the hosted demo** (nothing to install): add this as a connector
(Developer mode → Connectors):
```
https://kcf-mcp.onrender.com/mcp
```
It's read-only and on a free tier that sleeps when idle (first call after a lull
cold-starts in ~30–60s — retry once).

**Host your own** (always-on or private) — deploy the container to a free host like
Render in a couple of clicks, or run it anywhere with:
```bash
KCF_MCP_TRANSPORT=streamable-http KCF_MCP_HOST=0.0.0.0 KCF_MCP_PORT=8000 kcf-mcp
# or containerized:  docker build -f kcf-oss/mcp/Dockerfile -t kcf-mcp . && docker run -p 8000:8000 kcf-mcp
```
Then add your URL + `/mcp` as the connector. Full self-host guide (Render blueprint,
Cloud Run, notes): [`../mcp/README.md`](../mcp/README.md#host-it-yourself-free).

### Any other MCP host
Command: `kcf-mcp` (stdio). Or run `python kcf-oss/mcp/server.py` from a checkout.
Full reference: [`../mcp/README.md`](../mcp/README.md).

---

## What to say (once connected)

Drive [the five-step flow](#the-flow-from-your-words-to-a-running-app) in plain
language:

- **Model + build:** *"Knowledge-code a library: books, members, and loans; then
  generate a Django backend."*
- **One-shot start:** invoke the **`model_domain`** prompt (e.g. `/kcf` in Claude)
  with your domain description.
- **Check a model:** *"Assess this model and tell me what's missing."*
- **Approve inferred gaps:** *"Fill the gaps, but let me approve them — bulk-accept
  the confident ones and walk me through the rest."*
- **See your options:** *"Which stacks can you generate?"* (backend and frontend tiers).

---

## What's happening under the hood

- **The model is the spec.** Your `.kcf` compiles to a normalized semantic IR: every
  entity, attribute, typed relationship, lifecycle state machine, and action
  contract (idempotency / atomicity / concurrency / authorization) is explicit.
- **KCF checks it, so the LLM can't drift.** `assess` gives one verdict:
  - *valid* — analyzer-clean (identities present, references resolve). **This is
    all you need to generate.**
  - *ready* — also complete (zero required coverage gaps). A goal, not a gate.
    Recommended gaps (full CRUD, lifecycles, set/bulk, transformations) travel to
    the generator as **guidance**; the LLM fills the sensible ones (tagged, so you
    can see what was inferred vs. stated) or you leave them.
- **Gaps can be filled — with your approval.** `assess` reports *coverage gaps*
  (knowledge the checklist expects per construct). The assistant can propose fills
  from general domain knowledge, each **tagged** as inferred (never asserted as
  fact). Over MCP you approve at your pace: high-confidence fills come as a **bulk**
  chunk you accept in one click to move fast, the rest as a **review** list you
  decide one by one to be rigorous. Confirmed fills are stamped with who approved
  them; rejected ones are dropped. Nothing synthetic is silently promoted.
- **Nothing is silently dropped.** The generated code ends with a *coverage
  self-audit* mapping every construct in the model to how it was realized — the
  same lossless discipline the standard enforces (D-005).

The result: you keep the speed and feel of vibe coding, but the app is built on a
foundation you can see, check, and trust.

## Keep the model true (the living model, no drift)

Knowledge coding only pays off if the model *stays* the source of truth. The moment
code carries meaning the model doesn't — a stray field, a status, a rule you
hand-added — you've drifted back to vibe coding. So the loop runs **both ways**, and
your coding agent enforces it:

- **Generate from the model** — every artifact traces to a construct.
- **Model-first for meaning changes** — a new entity/field/action/rule/lifecycle
  goes into the `.kcf` *first* (`kcf compile --validate` → `assess`), then the code.
- **Reconcile after vibe coding** — if you edited the code directly, the agent's job
  is to bring the model back into agreement (add the new meaning to the model), so it
  never lags reality — asking you when intent is ambiguous.

Seed a project wired for this in one command:

```bash
pip install "kcf-oss"
kcf init my-app          # creates model/ (source of truth) + AGENTS.md + .kcf/ refs
```

The generated **`AGENTS.md`** tells your coding agent (Claude Code, Cursor, …) the
drift rules; the full protocol is [`codegen/MODEL_SYNC.md`](../codegen/MODEL_SYNC.md).
Point your agent at `AGENTS.md` and vibe-code freely — the model stays true.

## Make it yours (tune the prompts)

KCF is guidance-driven, so you tune both ends of the loop with plain Markdown —
no forking. Your conventions are a **layer on top of** the checked model: they
change *how* things are asked and built, never *what* the model means.

- **Tune elicitation** — the questions asked and defaults proposed while modeling
  (tenancy, audit, standard actors/entities, naming). Copy
  [`mcp/elicitation.example.md`](../mcp/elicitation.example.md) → `elicitation.md`
  and set `KCF_ELICITATION_GUIDE` in your MCP host config (or pass the
  `model_domain` prompt's `conventions` argument).
- **Tune code generation** — ORM, auth pattern, naming, observability, test shape.
  Copy [`codegen/overrides.example.md`](../codegen/overrides.example.md) →
  `overrides.md` and set `KCF_CODEGEN_OVERRIDES` (or pass `codegen_prompt(…,
  instructions="…")`, or paste it into the playground's *House conventions* box or
  the manual `generate-*.md` templates).

Example MCP config that turns both on:

```jsonc
{ "mcpServers": { "kcf": { "command": "kcf-mcp", "env": {
    "KCF_ELICITATION_GUIDE": "/abs/path/mcp/elicitation.md",
    "KCF_CODEGEN_OVERRIDES": "/abs/path/codegen/overrides.md"
} } } }
```

The required gaps, the action contracts, and the coverage self-audit still hold —
tuning can't override the parts that keep the app faithful to the model.

## Go deeper

- **[QUICKSTART](../QUICKSTART.md)** — the CLI loop (compile → assess → codegen) in 60 seconds.
- **[WALKTHROUGH](WALKTHROUGH.md)** — requirements → a ready model → a generated app.
- **[CONCEPTS](CONCEPTS.md)** — the mental model (well-formed vs. valid vs. complete; the four layers).
- **[codegen/](../codegen/)** — the code-generation pack (system prompt + per-stack examples, backend + frontend).
- **[mcp/](../mcp/)** — the MCP server reference (all tools + every host's config).
- **[EXTENDING](EXTENDING.md)** — change or add a grammar.
