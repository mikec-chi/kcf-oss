# KCF MCP server — model your domain, then vibe-code from the model

> New to this? Read **[Knowledge Coding — get started](../docs/KNOWLEDGE_CODING.md)**
> first (the 3-minute, per-LLM setup). This page is the detailed server reference.

Plug KCF into the chat LLM you already use. Instead of vibe-coding against prose,
you talk to Claude / ChatGPT / VS Code, and it uses KCF to build a **validated,
coverage-assessed, traceable semantic model** of your domain — reporting what passed
rather than asserting the domain is complete — then generates code from that model,
for your target stack. This is **knowledge coding = semantic modeling + vibe coding**.

**The flow:** describe your domain → the assistant **models** it (`.kcf`) →
**checks** it (`assess`) → you **approve** anything it inferred (bulk or one by one)
→ it **generates** the backend, then a matching frontend. Every step is a tool below;
the assistant drives them in that order (see [Built to be agent-driven](#built-to-be-agent-driven)).

### Try the hosted demo (no install)

Just want to point ChatGPT (or any remote MCP host) at a live server? Use the
project's hosted demo endpoint:

```
https://kcf-mcp.onrender.com/mcp
```

It's **read-only** (no data stored) and runs on a free tier that sleeps when idle, so
the first request after a lull cold-starts in ~30–60s (just retry once). To run your
own always-on instance, see [Host it yourself (free)](#host-it-yourself-free).

### One-invocation start (guided prompts)

The server ships **guided prompts** — surfaced by the host (e.g. `/kcf…` in Claude,
"Prompts" in the connector UI):

- **`model_domain`** — runs the whole loop end to end: draft a `.kcf` → `compile` →
  `assess` → fix required gaps + enrich → pick a stack → `codegen_prompt` → app.
- **`build_model`** — the modelling half only (prose → a valid model). Delegate to a
  model-building sub-agent.
- **`generate_app`** — the generation half only (valid model → backend, then frontend
  against its OpenAPI). Delegate to a generation sub-agent.

### Built to be agent-driven

The pipeline is a self-navigating loop: an agent calls **`next_action(source)`**
after every edit and does exactly what it returns (`recommendedTool` + why), until
`readyToGenerate` is true — then follows the returned `generationPlan` (backend, then
frontend). The whole toolset is annotated (titles, read-only/idempotent hints,
per-parameter descriptions) and `capabilities()` returns the phase map, so an
autonomous agent can maximize the tools without hard-coding the order. Start any agent
with `capabilities()`.

### Tools

| Tool | What it does |
|---|---|
| `capabilities` | a self-describing map of the whole pipeline + tools + provenance vocabulary (**call first**) |
| `next_action` | the **agent driver**: the single best next step + whether the model is ready to generate (call after every edit) |
| `authoring_reference` | a compact `.kcf` syntax + vocabulary reference (read before drafting) |
| `elicitation_guide` | the process for interviewing a user and drafting a model, dimension by dimension |
| `example_model` | a small, ready sample `.kcf` to learn the syntax |
| `scaffold` | a pattern-seeding brief for a profile to author against |
| `compile` | `.kcf` text → semantic IR + diagnostics + `valid` flag |
| `assess` | readiness verdict: `valid`, `ready`, coverage gap counts/ids |
| `coverage` | the gap list (enrichment to-do); `by_concept` for a per-concept view |
| `coverage_model` | the reference for **how** gaps are derived from constructs |
| `review_queue` | tier synthetic (LLM-proposed) fills into a **bulk** (mass-approve) and **review** (individual) chunk |
| `confirm_synthetic` | apply approve/reject decisions → the governed IR (the one write tool) |
| `list_stacks` | the tech stacks with a single-shot codegen example |
| `codegen_prompt` | assemble the ready-to-run code-gen prompt for a stack (from `.kcf` or a governed IR) |

Four **resources** expose the same reference material as attachable context:
`kcf://capabilities`, `kcf://guide/elicitation`, `kcf://reference/authoring`,
`kcf://reference/coverage-model`.

**kcf-oss stops at the IR** — there is no emitter; `codegen_prompt` returns the
LLM prompt pack, and the host LLM writes the code (finishing with a realization
manifest that accounts for every construct — verifiable at an explicit evidence
level with `verify-realization`).

### Synthetic gap-filling — approve fast, or review rigorously

`assess`/`coverage` report **gaps** (knowledge the grammar's checklist expects but
the model doesn't yet capture, per construct). The assistant can propose
smallest-plausible fills from general domain knowledge — each **tagged with
provenance** (`extraction-method llm; confidence …; status inferred;`) so it stays
distinguishable from what the user actually stated. Then you choose your pace:

- **Fast** — `review_queue` puts high-confidence fills in a **bulk** chunk you
  approve in one click; `confirm_synthetic` with all their ids governs them at once.
- **Rigorous** — the **review** chunk holds the rest for individual approve/reject.

`confirm_synthetic` stamps who approved and when, flips inferred assertions to
`asserted`, and drops rejects — then `codegen_prompt(model_ir=…)` generates from the
reviewed, approved model. Nothing synthetic is ever silently promoted to fact.

## Install

```bash
pip install "kcf-oss[mcp]"     # provides the `kcf-mcp` command
# or from a checkout:
pip install mcp && python kcf-oss/mcp/server.py
```

The server speaks **stdio** by default (what Claude/VS Code expect for a local
server). For a **remote** host (a hosted ChatGPT connector, or sharing one server
with a team) run it over HTTP by setting the transport via env vars:

```bash
KCF_MCP_TRANSPORT=streamable-http KCF_MCP_HOST=0.0.0.0 KCF_MCP_PORT=8000 kcf-mcp
# or containerized:
docker build -f kcf-oss/mcp/Dockerfile -t kcf-mcp . && docker run -p 8000:8000 kcf-mcp
```

`KCF_MCP_TRANSPORT` accepts `stdio` (default), `streamable-http`, or `sse`.

## Configure your host

**Claude Code (CLI):**
```bash
claude mcp add kcf -- kcf-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json` (Settings → Developer →
Edit Config):
```jsonc
{
  "mcpServers": {
    "kcf": { "command": "kcf-mcp" }
    // from a checkout instead:
    // "kcf": { "command": "python", "args": ["/abs/path/kcf-oss/mcp/server.py"] }
  }
}
```

**VS Code** (built-in MCP, or via an MCP-capable extension) — add to your MCP
config / `.vscode/mcp.json`:
```jsonc
{ "servers": { "kcf": { "command": "kcf-mcp" } } }
```

**ChatGPT** — Developer mode → Connectors support MCP over HTTP. Deploy the
server with `KCF_MCP_TRANSPORT=streamable-http` (the Dockerfile above does this),
put it behind a reachable HTTPS URL, and add that URL as a connector. See OpenAI's
connector docs for the current setup.

After adding it, restart the host so it discovers the `kcf` tools.

## Host it yourself (free)

Want your own always-on (or private) endpoint? Deploy the server to any host that
runs a container. The free, no-card path is **Render**:

1. Assemble a deploy repo and push it to GitHub:
   ```bash
   bash kcf-oss/packaging/make-render-repo.sh ../kcf-mcp-render
   # then create a GitHub repo and push ../kcf-mcp-render to it
   ```
   It contains a `Dockerfile` (binds Render's `$PORT`) and a `render.yaml` blueprint.
2. On <https://render.com>: **New → Web Service → Public Git Repository**, paste your
   repo URL, pick the **Free** instance, **Create**. Render builds the Dockerfile and
   serves it at `https://<name>.onrender.com`; the MCP endpoint is that URL + `/mcp`.

Render's free tier sleeps after ~15 min idle (cold start on the next hit). For an
always-on host, the same repo deploys to Google Cloud Run (always-free usage) or any
container platform — set `KCF_MCP_TRANSPORT=streamable-http`, `KCF_MCP_HOST=0.0.0.0`,
and bind the platform's port.

> **Hugging Face note:** HF Spaces can host it too, but **Docker Spaces now require an
> HF PRO subscription** (only static Spaces are free). `packaging/make-hf-space.sh`
> and `packaging/deploy-hf-space.py` still work if you have PRO.

The server is **read-only** (no data, no persistence), so a public URL is low-risk;
gate it behind a token if you prefer.

## Tune it to your house standards (optional)

Inject your team's conventions so both halves of the loop follow them — without
forking anything. Point two env vars at Markdown files in your host config:

```jsonc
{ "mcpServers": { "kcf": { "command": "kcf-mcp", "env": {
    "KCF_ELICITATION_GUIDE": "/abs/path/mcp/elicitation.md",
    "KCF_CODEGEN_OVERRIDES": "/abs/path/codegen/overrides.md"
} } } }
```

- **`KCF_ELICITATION_GUIDE`** tunes *how the domain is elicited* — the questions
  asked and defaults proposed while drafting the model (tenancy, audit, standard
  actors/entities…). It rides into the `model_domain` prompt as *House elicitation
  conventions*. Start from [`elicitation.example.md`](elicitation.example.md). You
  can also pass it per invocation via the prompt's `conventions` argument.
- **`KCF_CODEGEN_OVERRIDES`** tunes *how code is generated* — ORM, auth, naming,
  observability. It rides into `codegen_prompt` as a highest-priority *House
  conventions* section. Start from [`../codegen/overrides.example.md`](../codegen/overrides.example.md).
  You can also pass it per call via `codegen_prompt(source, stack, instructions="…")`.

Both are guidance layered *on top of* the checked model: they change how things
are asked and built, never what the model means — required gaps, the action
contracts, and the coverage self-audit still hold.

## What you can say once it's connected

- *"Model a support-ticket system with KCF, then generate a FastAPI backend."*
  The assistant drafts a `.kcf`, calls `assess`, fixes required gaps, enriches the
  recommended ones, then `codegen_prompt` → the app.
- *"Assess this model and tell me what's missing."* → `compile` / `assess` /
  `coverage`.
- *"Fill the gaps but let me approve them — bulk-accept the confident ones, walk me
  through the rest."* → tagged fills → `review_queue` → `confirm_synthetic`.
- *"Which stacks can you generate?"* → `list_stacks`.
- *"Give me a starting brief for an analytics platform."* → `scaffold`.

The point: the model is built and checked **before** code generation, so the LLM
builds against a specification, not a guess — and you can see (and confirm) exactly
what was inferred versus stated.
