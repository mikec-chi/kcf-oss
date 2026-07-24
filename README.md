# KCF — The Semantic Framework for Making Knowledge Executable

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/mikec-chi/kcf-oss/actions/workflows/ci.yml/badge.svg)](https://github.com/mikec-chi/kcf-oss/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

*The open **Knowledge Coding Framework** from [Composable Holdings Inc.](#license)*

**KCF helps you encode and capture business knowledge — entities, relationships,
lifecycles, rules, and actions — so that it can be made executable.** Knowledge
Coding is the new Vibe Coding: you model your domain into a complete, machine-checked
semantic spec, then let an LLM build the application from that spec instead of
guessing from prose — **knowledge coding = semantic modeling + vibe coding**.

> ### 👉 Start here: [**Knowledge Coding — get running in 3 minutes**](kcf-oss/docs/KNOWLEDGE_CODING.md)
> Two ways in: 🌱 **no install** — point your chat LLM at the hosted connector and
> just describe your app; or 🛠️ **build for real** — `pip install` + `kcf init` a
> project where the model stays the source of truth.

KCF turns domain knowledge — entities, relationships, lifecycles, actions,
events — into a normalized **semantic IR**: a single JSON model that is *valid*
(no dangling references), *complete* (every entity has an identity, every
required obligation met), and *traceable* (nothing is silently dropped on the
way to code). The LLM builds against that spec, not a vibe.

```text
requirements ──▶ checked model (IR) ──▶ LLM ──▶ app     (built from a spec)
                     ▲            │ kcf assess: valid? gaps? → guidance
                     └────────────┘
```

---

## Why this exists

LLM code generators are only as good as the model of the domain they're given.
Feed them a paragraph and they hallucinate fields, invent relationships, and
drop half your lifecycle. KCF makes the *model* the artifact:

- **Well-formed?** the grammar / compiler answers that (syntax).
- **Valid?** the semantic analyzer answers that (no relationship points at a
  missing concept).
- **Complete enough to build from?** `kcf assess` answers that with a single
  verdict: **valid** (analyzer-clean — enough to generate) and **ready** (also
  complete: zero required coverage gaps, patterns proven, roles resolved).

You generate from a **valid** model; the coverage gaps travel to the LLM as
enrichment guidance (`ready` is the completeness goal, not a hard gate). The
generated code ends with a **coverage self-audit** proving nothing in the model
was dropped (`dropped: []`).

## 60-second quickstart

```bash
pip install kcf-oss        # provides the `kcf` command

# 1. compile a tiny domain model → semantic IR (grab the sample from the repo)
curl -O https://raw.githubusercontent.com/mikec-chi/kcf-oss/main/kcf-oss/tests/domains/business-application.kcf
kcf compile business-application.kcf --output model-ir.json --validate

# 2. is it complete enough to generate from?
kcf assess model-ir.json
#  → { "valid": true, "ready": true,
#      "checks": { "coverage": { "requiredGaps": 0 } } }
```

Once `ready: true`, generate the application. **KCF stops at the IR** — the IR is
the durable specification; your own LLM turns it into code for whatever stack you
choose, guided by a stack-agnostic system prompt and a single-shot example.

```text
# 3. generate — with any LLM, for any stack (codegen/). Two tiers meet at OpenAPI:
#    BACKEND  → generate-backend.md  + a backend stack  → a service with Swagger by default
#               (fastapi-sqlmodel-postgres · typescript-express-prisma · django-drf-postgres)
#    FRONTEND → generate-frontend.md + the backend's /openapi.json + a frontend stack
#               (react-typescript-openapi) → a UI bound to that contract
```

The LLM returns the implementation **plus a coverage self-audit** proving every
IR identity was realized and nothing dropped (`dropped: []`). See
[`kcf-oss/codegen/`](kcf-oss/codegen/) and, for the full requirements-to-code
tour, [`kcf-oss/docs/WALKTHROUGH.md`](kcf-oss/docs/WALKTHROUGH.md).

KCF **stops at the IR** — a complete, machine-checked model is the deliverable.
Turning it into running code is the LLM codegen pack's job (deterministic
emitters are part of the separate commercial platform).

> **From source instead:** `git clone https://github.com/mikec-chi/kcf-oss.git && cd kcf-oss && pip install -e .`
> A source checkout also gives you the contributor gate (`kcf check`) and the
> full-stack tooling, which need the bundled `semantic-core`.

## Use it in your chat LLM (MCP)

Plug KCF into the chat LLM you already use and it builds a complete, machine-checked
model of your domain, then generates the app from it — instead of vibe-coding
against prose.

**🌱 No install — connect to the hosted server.** Point your LLM at the hosted
connector `https://kcf-mcp.onrender.com/mcp`:

```bash
claude mcp add --transport http kcf https://kcf-mcp.onrender.com/mcp   # Claude Code
# ChatGPT: Settings → Connectors → add that URL. (Read-only demo; free tier, sleeps when idle.)
```

**🛠️ Building for real — install locally and seed a project:**

```bash
pip install "kcf-oss[mcp]"      # the `kcf` CLI + the `kcf-mcp` server
kcf init my-app                 # a project where the model is the source of truth
claude mcp add kcf -- kcf-mcp   # local Claude Code; see kcf-oss/mcp/README.md for other hosts
```

Either way, describe your domain — or invoke a guided prompt (**`model_domain`** end
to end, **`build_model`** to model only, **`generate_app`** to generate only). The
assistant drafts a `.kcf`, checks it, lets you **approve anything it inferred**
(bulk-accept the confident gaps, or review them one by one), then generates the
backend and a matching frontend — each proving nothing in your model was dropped.
See **[Knowledge Coding](kcf-oss/docs/KNOWLEDGE_CODING.md)** for both paths, step by
step.

## Try it in the browser

Prefer a UI? The **[playground](kcf-oss/playground/)** is a zero-persistence web
app: paste a `.kcf` model and see its IR, readiness verdict, and the ready-to-paste
LLM code-generation prompt for your chosen stack — the whole loop, live.

```bash
pip install "kcf-oss[playground]"
uvicorn app:app --app-dir kcf-oss/playground   # → http://127.0.0.1:8000
# or: docker build -f kcf-oss/playground/Dockerfile -t kcf-playground . && docker run -p 8000:8000 kcf-playground
```

## What's in the box

| Piece | What it is |
| --- | --- |
| **Grammars** | 29 ISO/IEC 14977 EBNF modules — one primary semantic dimension each (`ENTITY`, `ACTOR`, `WORK`, `EVENT`, `LIFECYCLE`, `RULE`, …) rooted in the `KCF` metagrammar |
| **Compiler** | `.kcf` text → normalized semantic IR with source spans |
| **Analyzer** | validity + coverage + pattern-proof + role-resolution checks |
| **IR schema** | versioned `model-ir-v1` JSON contract you can target from any tool |
| **Presets** | 6 composable foundational profiles (business-application, event-driven-system, analytics-platform, …) |
| **Codegen pack** | `codegen/` — a stack-agnostic system prompt + single-shot examples across **backend** (FastAPI, Express/Prisma, Django — each with Swagger) and **frontend** (React/TS bound to the backend's OpenAPI) tiers, plus a full per-construct coverage audit |
| **MCP server** | `mcp/` — plug the toolchain into Claude / ChatGPT / VS Code; model a domain and generate code conversationally (`kcf-mcp`) |
| **LLM workflow** | an ordered 16-step prompt package (`kcf-oss/workflows/`) for going from requirements to a validated IR |

## Learn more

- **[Knowledge Coding — get started](kcf-oss/docs/KNOWLEDGE_CODING.md)** — connect KCF to your LLM and build your first app (start here).
- **[QUICKSTART](kcf-oss/QUICKSTART.md)** — the hello-world above, annotated.
- **[codegen/](kcf-oss/codegen/)** — generate an app from the IR with your LLM, for any stack.
- **[WALKTHROUGH](kcf-oss/docs/WALKTHROUGH.md)** — requirements → ready IR → generated app.
- **[CONCEPTS](kcf-oss/docs/CONCEPTS.md)** — the mental model and the four semantic layers.
- **[kcf-oss/README](kcf-oss/README.md)** — full architecture, IR contract, and toolchain reference.
- **[EXTENDING](kcf-oss/docs/EXTENDING.md)** — how to change or add a grammar (and the Grammar RFC process).
- **[CHANGELOG](CHANGELOG.md)** — releases, tagged by which contract moved.

## Open core

KCF is open under **Apache-2.0** — the standard, compiler, analyzer, IR schema,
foundational presets, and the codegen pack are free to use and always will be.
A separate commercial platform builds *on top of* this standard; it never
subtracts from it. See **[OPEN_CORE.md](OPEN_CORE.md)** for the exact promise.

## Contributing

KCF gets better the more people model with it. Two tracks — start with
**[CONTRIBUTING.md](CONTRIBUTING.md)**:

- **Build on KCF** — share in the **[`community/`](community/)** area: `.kcf`
  **models** you built, **prompt packs** (elicitation guides + codegen overrides)
  that tuned the MCP for you, **techniques** for eliciting and generating well, a
  **showcase** of apps you shipped, and **experimental grammars**. Each area has a
  template and a quick check (models must be `valid` — `python
  community/models/validate.py`).
- **Improve the core** — new **codegen stacks** and **presets**, **analyzer rules**,
  **integrations**, or **grammar** changes (read **[EXTENDING](kcf-oss/docs/EXTENDING.md)**
  and open a **Grammar RFC** first). The core is gated by `kcf check` (runs in CI on
  every PR).

New here? A model of a domain you know, or a technique that worked for you, is a
great first PR. See the [good first issues](../../labels/good%20first%20issue).

## License

[Apache-2.0](LICENSE). © 2026 **Composable Holdings Inc.** KCF is created and
maintained by Composable Holdings Inc.
