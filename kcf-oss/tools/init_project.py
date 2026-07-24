"""`kcf init` — seed a KCF *knowledge application*.

Scaffolds a project where the **model is the source of truth** and a coding agent
keeps code and model in sync (the living-model / drift-prevention loop). The seeded
project bundles the grammar authoring reference, a starter model (compiled to IR),
the sync protocol, and `AGENTS.md` instructions a codegen LLM follows.

Layout produced::

    <project>/
      model/<Name>.kcf         the model — SOURCE OF TRUTH
      model/model-ir.json      compiled IR (regenerate from the .kcf)
      AGENTS.md                drift-prevention instructions for coding agents
      CLAUDE.md                one-liner pointing Claude Code at AGENTS.md
      kcf.project.json         project config (model/ir paths, profile, stack)
      README.md                human intro to the loop
      .kcf/authoring-brief.md  grammar authoring reference (navigate the grammar)
      .kcf/MODEL_SYNC.md       the full bidirectional sync protocol
      .kcf/system-prompt.md    the codegen system prompt (with drift rules)
"""
from __future__ import annotations

import json
from pathlib import Path

from compiler import compile_text

PACKAGE_ROOT = Path(__file__).resolve().parents[1]  # kcf-oss/
PROFILES = ("business-application", "operational-system", "organizational-knowledge",
            "event-driven-system", "ai-application", "analytics-platform")


def _starter_model(name: str, profile: str, ns: str) -> str:
    return f"""\
// {name} — your domain model. THIS FILE IS THE SOURCE OF TRUTH.
// Edit it first; generate/adjust code from it. See AGENTS.md and .kcf/MODEL_SYNC.md.
// Check it:  kcf compile model/{name}.kcf -o model/model-ir.json --validate

kcf model {name} profile {profile} {{
  namespace {ns};

  // Actors: who acts in your domain.
  actor Person {{ }}

  // Entities: the things you track. Every entity needs an `identity`.
  entity Item {{
    identity id: UUID;
    required title: String;
    optional notes: String;
  }}

  // Commands change state (declare `authorization`); queries read state.
  command CreateItem {{
    operation create;
    scope record;
    target Item;
    input one;
    output one;
    idempotency conditional;
    atomicity atomic;
    authorization {ns}.ManageItems;
  }}

  query ListItems {{
    operation query;
    scope set;
    target Item;
    input zero;
    output many;
  }}
}}
"""


def _agents_md(name: str, model_path: str, ir_path: str) -> str:
    return f"""\
# Working in this repo — read this first (coding agents)

This is a **KCF knowledge application**. The model is the **source of truth**, and
the code is a *projection* of it. Your job is to keep them in sync so the app never
drifts back into un-inspectable guesswork.

- **Model (truth):** `{model_path}`  →  compiled IR: `{ir_path}`
- **Grammar / syntax:** `.kcf/authoring-brief.md`
- **The full sync protocol:** `.kcf/MODEL_SYNC.md` (read it)
- **Codegen system prompt:** `.kcf/system-prompt.md`

## The drift rule (non-negotiable)

The meaning of this app lives in the model. If it isn't in the model, it isn't real
yet.

1. **Read the model before you code.** Find the concept / action / rule / lifecycle
   your change concerns in the IR and build against *that* — not memory or a guess.
2. **Model-first for meaning changes.** If a change adds or alters meaning — a new
   entity, field, command/query, rule, policy, lifecycle, relationship, or
   authorization — update `{model_path}` **first**, then:
   ```
   kcf compile {model_path} -o {ir_path} --validate
   kcf assess {ir_path}
   ```
   *then* write the code, tracing each artifact to its construct.
3. **Reconcile after direct (vibe-coded) edits.** If code was changed directly
   without going through the model, your FIRST task is to make the model true again:
   diff the code, find any changed *meaning*, and update the `.kcf` to match
   (compile + assess). Ask the developer when intent is ambiguous — never invent
   model meaning. Only then continue.
4. **Annotate realizations.** Every table, endpoint, screen, state, or guard names
   the construct it realizes (e.g. `# realizes {name.lower()}.CreateItem`).
5. **Don't invent.** No entity, field, status, rule, or role that isn't in the
   model. Standard scaffolding for a *recommended* gap is fine but flag it as
   *enriched* in the coverage self-audit — never as declared.

## Tools

Use the `kcf` CLI (`pip install "kcf-oss"`) or the KCF MCP server (`kcf-mcp`):

- `kcf compile {model_path} -o {ir_path} --validate` — model → IR, check validity.
- `kcf assess {ir_path}` — readiness verdict + coverage gaps.
- MCP: `capabilities`, `next_action`, `compile`, `assess`, `coverage`,
  `codegen_prompt` — the guided build→generate loop.

## Before you commit

Run the drift check from `.kcf/MODEL_SYNC.md`: recompile + reassess (still valid?),
confirm every model construct is realized (coverage self-audit, `dropped: []`), and
scan the diff for meaning the model doesn't have. Fix drift by moving meaning **into
the model**, not by patching around it.
"""


def _readme_md(name: str, model_path: str) -> str:
    return f"""\
# {name} — a KCF knowledge application

The new vibe coding is *knowledge coding*: this project keeps a **model** of the
domain as the source of truth, and generates/maintains the code from it so nothing
drifts.

- **`{model_path}`** — the model. Edit this to change what the app *means*.
- **`AGENTS.md`** — how a coding agent (Claude Code, Cursor, …) keeps code and model
  in sync. Point your agent at it.
- **`.kcf/`** — the grammar reference, the sync protocol, and the codegen prompt.

## The loop

1. **Model** your domain in `{model_path}` (see `.kcf/authoring-brief.md`).
2. **Check** it: `kcf compile {model_path} -o model/model-ir.json --validate` then
   `kcf assess model/model-ir.json`.
3. **Generate** code from the IR (KCF codegen pack or the MCP `codegen_prompt`).
4. **Vibe-code** freely — but whenever the *meaning* changes, update the model first
   (or reconcile it after), so the model stays true. That discipline is what keeps
   the app inspectable and regenerable.

Get KCF: `pip install "kcf-oss[mcp]"` — then `kcf --help` or connect `kcf-mcp` to
your LLM. Learn more: <https://github.com/mikec-chi/kcf-oss>.
"""


def init_project(target: Path, name: str, profile: str) -> list[str]:
    """Scaffold a knowledge application at ``target``. Returns created paths."""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile '{profile}'. Choose one of: {', '.join(PROFILES)}")
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"{target} already exists and is not empty")

    ns = "".join(ch for ch in name.lower() if ch.isalnum()) or "app"
    (target / "model").mkdir(parents=True, exist_ok=True)
    (target / ".kcf").mkdir(parents=True, exist_ok=True)

    model_rel = f"model/{name}.kcf"
    ir_rel = "model/model-ir.json"
    created: list[str] = []

    # 1. starter model + compiled IR
    model_text = _starter_model(name, profile, ns)
    (target / model_rel).write_text(model_text, encoding="utf-8")
    ir = compile_text(model_text, source=model_rel)
    (target / ir_rel).write_text(json.dumps(ir, indent=2) + "\n", encoding="utf-8")
    created += [model_rel, ir_rel]

    # 2. bundled references (so the project is self-describing / offline-capable)
    for src, dst in (
        (PACKAGE_ROOT / "mcp" / "authoring-brief.md", ".kcf/authoring-brief.md"),
        (PACKAGE_ROOT / "codegen" / "MODEL_SYNC.md", ".kcf/MODEL_SYNC.md"),
        (PACKAGE_ROOT / "codegen" / "system-prompt.md", ".kcf/system-prompt.md"),
    ):
        if src.exists():
            (target / dst).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            created.append(dst)

    # 3. agent instructions + project config + readme
    (target / "AGENTS.md").write_text(_agents_md(name, model_rel, ir_rel), encoding="utf-8")
    (target / "CLAUDE.md").write_text(
        "# Project instructions\n\nSee **[AGENTS.md](AGENTS.md)** — this is a KCF "
        "knowledge application; the model is the source of truth and must be kept in "
        "sync with the code (drift-prevention protocol in `.kcf/MODEL_SYNC.md`).\n",
        encoding="utf-8")
    (target / "kcf.project.json").write_text(json.dumps({
        "kcfProjectVersion": "1.0.0",
        "name": name,
        "profile": profile,
        "model": model_rel,
        "ir": ir_rel,
        "sourceOfTruth": "model",
        "stack": {"backend": None, "frontend": None},
        "conventions": {"elicitationGuide": None, "codegenOverrides": None},
    }, indent=2) + "\n", encoding="utf-8")
    (target / "README.md").write_text(_readme_md(name, model_rel), encoding="utf-8")
    created += ["AGENTS.md", "CLAUDE.md", "kcf.project.json", "README.md"]

    return created
