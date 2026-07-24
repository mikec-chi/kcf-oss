"""KCF playground — a thin web wrapper around the open-source toolchain.

Paste a ``.kcf`` model and get back, in one round trip:
  1. compile        → normalized semantic IR (or a syntax error with line:col)
  2. assess         → the readiness verdict (valid / ready / coverage gaps)
  3. generate code  → the ready-to-paste LLM prompt for a chosen stack (system
                      prompt + this model's IR + the stack's single-shot example)

kcf-oss stops at the IR; code generation is the LLM ``codegen/`` pack. The
playground reuses the exact reference functions the CLI uses; it adds no
semantics of its own. It runs entirely against the open-source stack — no
proprietary overlay, no network calls, no persistence.

Run locally:
    pip install -r kcf-oss/playground/requirements.txt
    uvicorn app:app --app-dir kcf-oss/playground --reload
Then open http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Resolve the OSS toolchain: kcf-oss/tools (siblings import each other flat) and
# kcf-oss/ (for the `compiler` package). semantic-core is found by the tools
# themselves as a sibling of kcf-oss.
PLAYGROUND_DIR = Path(__file__).resolve().parent
OSS_ROOT = PLAYGROUND_DIR.parent
for entry in (OSS_ROOT, OSS_ROOT / "tools"):
    text = str(entry)
    if text not in sys.path:
        sys.path.insert(0, text)

from compiler import compile_text  # noqa: E402
from semantic_analyzer import Analyzer  # noqa: E402
from assess import assess as assess_model  # noqa: E402
from coverage_report import report as coverage_report, load_coverage_model  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

STATIC_DIR = PLAYGROUND_DIR / "static"
EXAMPLE = (OSS_ROOT / "tests" / "domains" / "business-application.kcf").read_text(encoding="utf-8")

# Code-generation pack (lead-with-prompts path): a tech-stack-agnostic system
# prompt + per-stack single-shot examples the user's own LLM consumes.
CODEGEN_DIR = OSS_ROOT / "codegen"
STACKS_DIR = CODEGEN_DIR / "stacks"

# The compiled parser is not a sandbox; cap input size so the endpoint can't be
# used to feed the toolchain an unbounded document.
MAX_SOURCE_BYTES = 64 * 1024

app = FastAPI(title="KCF Playground", version="1.0.0")


class RunRequest(BaseModel):
    source: str = Field(..., description="KCF model text (.kcf)")


@app.get("/api/example")
def example() -> dict:
    """The prefilled sample model (a golden fixture, so it can't rot)."""
    return {"source": EXAMPLE}


def _load_stacks() -> list[dict]:
    stacks = []
    if STACKS_DIR.exists():
        for stack_json in sorted(STACKS_DIR.glob("*/stack.json")):
            meta = json.loads(stack_json.read_text(encoding="utf-8"))
            stacks.append({"id": meta["id"], "title": meta.get("title", meta["id"]),
                           "tier": meta.get("tier", "backend")})
    return stacks


@app.get("/api/stacks")
def stacks() -> dict:
    """The tech stacks that ship a single-shot codegen example."""
    return {"stacks": _load_stacks()}


class CodegenRequest(BaseModel):
    source: str = Field(..., description="KCF model text (.kcf)")
    stack: str = Field(..., description="stack id, e.g. fastapi-sqlmodel-postgres")
    instructions: str = Field("", description="house conventions to inject (highest priority)")


@app.post("/api/codegen")
def codegen(request: CodegenRequest) -> dict:
    """Assemble the ready-to-paste LLM code-generation prompt for a chosen stack:
    the durable system prompt + this model's IR + the stack's single-shot example.
    OSS stops at the IR; the user's own LLM does the generation."""
    stack_dir = STACKS_DIR / request.stack
    if not (stack_dir / "stack.json").exists() or ".." in request.stack or "/" in request.stack:
        return {"ok": False, "error": f"unknown stack: {request.stack}"}
    if len(request.source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {"ok": False, "error": "model exceeds playground size limit"}
    try:
        model = compile_text(request.source, source="<playground>")
    except ValueError as exc:
        return {"ok": False, "error": f"compile: {exc}"}

    # A VALID model (no analyzer errors) is the gate for code generation — not a
    # fully `ready` one. Coverage gaps are passed to the LLM as guidance, not a
    # blocker: the model is the spec; missing recommended pieces get realized or
    # noted, and the LLM may enrich them.
    diagnostics = Analyzer(model).run()
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    if errors:
        return {"ok": False, "valid": False,
                "error": "model is not valid (fix analyzer errors before generating)",
                "diagnostics": errors}

    gap_report = coverage_report(model, load_coverage_model())
    guidance_lines = [f"- [{g['level']}] {g['subject']}: {g['message']}" for g in gap_report["gaps"]]
    guidance = ("\n".join(guidance_lines)
                if guidance_lines else "- none — the model is complete (ready).")

    meta = json.loads((stack_dir / "stack.json").read_text(encoding="utf-8"))
    tier = meta.get("tier", "backend")
    system_prompt = (CODEGEN_DIR / "system-prompt.md").read_text(encoding="utf-8")
    example = (stack_dir / "EXAMPLE.md").read_text(encoding="utf-8")
    ir_json = json.dumps(model, indent=2)
    guidance_block = (
        f"\n\n## Coverage guidance (enrichment — not blocking)\n\nThe model is "
        f"valid. These are the coverage gaps `kcf assess` reports; realize the ones "
        f"that make sense for the domain and note any you intentionally skip "
        f"(required gaps are the important ones):\n\n{guidance}\n"
    )

    # Tuning: inject house conventions (request param + KCF_CODEGEN_OVERRIDES file)
    # as a highest-priority section appended after the example.
    house_parts = [request.instructions.strip()] if request.instructions.strip() else []
    _ov = os.environ.get("KCF_CODEGEN_OVERRIDES")
    if _ov:
        try:
            house_parts.append(Path(_ov).read_text(encoding="utf-8").strip())
        except OSError:
            pass
    house = "\n\n".join(p for p in house_parts if p)
    house_block = (
        "\n\n## House conventions (HIGHEST PRIORITY)\n\nApply these; they override "
        "the example and defaults where they conflict. Still honor the action "
        "contracts, drop nothing, and finish with the coverage self-audit:\n\n"
        + house + "\n"
    ) if house else ""

    if tier == "frontend":
        user_prompt = (
            f"Tier: frontend. Generate the frontend for the whole model, targeting "
            f"the `{request.stack}` stack. Generate a typed API client from your "
            f"backend's OpenAPI document (paste it where marked) and call it for all "
            f"data and actions; delegate everything the server owns; realize views, "
            f"forms, lifecycle controls, and role-gated UI per the example. Finish "
            f"with the coverage self-audit."
            f"\n\n## The model (meaning + UX intent)\n\n```json\n{ir_json}\n```\n\n"
            f"## The backend OpenAPI (bind to this)\n\n"
            f"```json\n<PASTE YOUR BACKEND'S /openapi.json HERE>\n```\n"
            f"{guidance_block}\n"
            f"## The single-shot example to imitate\n\n{example}{house_block}"
        )
    else:
        user_prompt = (
            f"Tier: backend. Generate the implementation for the whole model from "
            f"the KCF IR below, targeting the `{request.stack}` stack. Follow the "
            f"single-shot example exactly; realize only what the IR declares, drop "
            f"nothing, expose an OpenAPI/Swagger interface by default, and finish "
            f"with the coverage self-audit.\n\n## The model (authoritative "
            f"specification)\n\n```json\n{ir_json}\n```\n"
            f"{guidance_block}\n"
            f"## The single-shot example to imitate\n\n{example}{house_block}"
        )
    return {"ok": True, "stack": request.stack, "tier": tier,
            "systemPrompt": system_prompt, "userPrompt": user_prompt}


@app.post("/api/run")
def run(request: RunRequest) -> dict:
    source = request.source or ""
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return {"stage": "input", "ok": False,
                "error": f"model exceeds {MAX_SOURCE_BYTES // 1024} KB playground limit"}

    # 1. compile ----------------------------------------------------------
    try:
        model = compile_text(source, source="<playground>")
    except ValueError as exc:  # LexError / ParseError carry "source:line:col: …"
        return {"stage": "compile", "ok": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"stage": "compile", "ok": False, "error": f"unexpected: {exc}"}

    response: dict = {"stage": "compile", "ok": True, "ir": model}

    # 2. assess (OSS stops at the IR; code generation is the LLM codegen pack) --
    diagnostics = Analyzer(model).run()
    response["diagnostics"] = diagnostics
    response["assess"] = assess_model(model)
    response["stage"] = "assess"
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
