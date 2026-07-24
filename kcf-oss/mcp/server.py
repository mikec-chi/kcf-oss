"""KCF MCP server — plug the open knowledge-coding toolchain into your chat LLM.

Exposes the kcf-oss tools over the Model Context Protocol so an LLM host (Claude
Desktop / Claude Code, ChatGPT, VS Code, …) can build a complete, machine-checked
**semantic model** of a domain and then generate code from it, for any stack —
instead of vibe-coding against prose.

The intended loop is conversational:
  1. draft a `.kcf` model (the LLM writes it),
  2. `assess` it → read the coverage gaps,
  3. fix the `required` gaps, optionally enrich the `recommended` ones,
  4. `codegen_prompt` for a target stack → run the returned prompt to generate code.

kcf-oss stops at the semantic IR; there is no emitter here — code generation is
the LLM prompt pack (`codegen/`), which `codegen_prompt` assembles.

Run it directly (from a checkout):  python kcf-oss/mcp/server.py
Or, once `pip install "kcf-oss[mcp]"`:  kcf-mcp
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

# Make the sibling helper module importable whether run as a script or launched.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _tools as t  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    from pydantic import Field
    from starlette.responses import HTMLResponse
except ModuleNotFoundError:  # pragma: no cover - helpful message if the extra is missing
    raise SystemExit(
        "The MCP SDK is not installed. Install it with:\n"
        "  pip install \"kcf-oss[mcp]\"   (or: pip install mcp)\n"
        "then run this server again."
    )

# Every tool here is a pure function of its inputs: it computes and returns, and
# never mutates a database, filesystem, or the outside world. Advertising that
# (read-only + idempotent, not open-world) lets hosts call them freely without
# side-effect confirmation prompts.
_READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

INSTRUCTIONS = """\
KCF turns a domain into a complete, machine-checked semantic model (an IR) that you
then generate code from — so the code is built from a spec, not guessed from prose.
This server is that toolchain. The user holds no state: YOU (the assistant) write
the `.kcf` model text and pass it into each tool, so the natural loop is
draft -> compile -> assess -> edit -> assess -> codegen_prompt.

Call `capabilities()` first for a self-describing map of the whole pipeline. The
tools, and when to reach for each:

Orient & elicit:
- `capabilities()` - the full pipeline, tools, coverage model, and provenance
  vocabulary in one call. Start here.
- `authoring_reference()` - the `.kcf` syntax + vocabulary cheat-sheet. READ before
  drafting, so the model you write compiles.
- `elicitation_guide()` - the process for interviewing the user and drafting a model
  dimension by dimension (plus any house conventions).
- `example_model()` - a small, ready sample `.kcf` to copy and adapt.
- `scaffold(profile)` - a starting brief for one of six domain presets.

Drive & check:
- `next_action(source)` - THE agent driver: the single best next step + whether the
  model is ready to generate. Call it after every edit to loop autonomously.
- `compile(source)` - `.kcf` -> semantic IR + diagnostics + a `valid` flag.
- `assess(source)` - the readiness verdict: `valid`, `ready`, coverage gap counts.
  Your primary "is the model good enough?" check.
- `coverage(source)` - the itemized gap to-do list (missing obligations per
  construct; add `by_concept=true` for a per-concept view).
- `coverage_model()` - HOW gaps are derived from constructs (the reference), and the
  provenance vocabulary for tagging synthetic fills.

Review & approve synthetic fills (the user approves what the LLM inferred):
- `review_queue(model_ir)` - tier the synthetic (LLM-proposed, tagged) fills into a
  `bulk` chunk (offer for one-click MASS approval - fast) and a `review` chunk
  (decide INDIVIDUALLY - rigorous).
- `confirm_synthetic(confirm, reject, model_ir)` - apply the decisions; returns the
  governed IR. Confirmed fills become fact; rejected are removed.

Generate:
- `list_stacks()` - the backend/frontend stacks you can generate for.
- `codegen_prompt(source|model_ir, stack)` - assembles the system + user prompt that
  generates the app. Run the returned prompts yourself.

Drive it as a loop (this is how an agent maximizes the tools): after every edit call
`next_action(source)` — it returns the single best next tool, why, and whether the
model is `readyToGenerate`. Act on it and repeat.

1. `capabilities()` + `authoring_reference()` (and `example_model()`/`scaffold`).
2. Following `elicitation_guide()`, draft a `.kcf` capturing the user's entities,
   actors, events, lifecycles, relationships, and action contracts. Invent nothing
   they did not state - ask when unsure.
3. `next_action(source)` → do what it says: fix syntax (`compile`), fix validity, fill
   every `required` gap. Repeat until the verdict is `valid`. (`assess`/`coverage`
   give the detail.)
4. (Optional, to reduce omission) Propose smallest-plausible fills for recommended
   gaps as `.kcf`, TAGGED with provenance (`extraction-method llm; confidence <0..1>;`
   and assertions `status inferred;`). `compile` -> `review_queue(model_ir)` -> show
   the user the `bulk` chunk for mass approval and the `review` chunk one by one ->
   `confirm_synthetic(confirm, reject, model_ir)` to govern the model.
5. When `next_action` reports `readyToGenerate`, follow its `generationPlan`:
   `list_stacks()` then `codegen_prompt(stack, model_ir=… or source)` for the backend,
   then again for a frontend stack against the backend's OpenAPI. Run the returned
   prompts; each ends with a coverage self-audit proving nothing was dropped.

Guided prompts run this for you: `build_model` (prose → valid model) and
`generate_app` (valid model → app) scope the two halves for sub-agents; `model_domain`
runs both end to end. House conventions tune elicitation and codegen (the
`conventions`/`instructions` params and the KCF_* env vars).
"""

# Transport is stdio by default (what Claude Desktop / Claude Code / VS Code
# expect for a local server). For a remote host (e.g. a hosted ChatGPT connector)
# set KCF_MCP_TRANSPORT=streamable-http (or sse) and bind a reachable host/port:
#   KCF_MCP_TRANSPORT=streamable-http KCF_MCP_HOST=0.0.0.0 KCF_MCP_PORT=8000 kcf-mcp
_TRANSPORT = os.environ.get("KCF_MCP_TRANSPORT", "stdio")

mcp = FastMCP(
    "kcf",
    instructions=INSTRUCTIONS,
    host=os.environ.get("KCF_MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("KCF_MCP_PORT", "8000")),
)


# This server is an MCP API (the endpoint is `/mcp`), not a website — so a browser
# hitting `/` would otherwise get a bare 404. Serve a friendly landing page there
# that names the endpoint and redirects to the project home. Point the redirect
# elsewhere with KCF_HOME_URL. (Only used under the HTTP transports; stdio ignores it.)
KCF_HOME_URL = os.environ.get("KCF_HOME_URL", "https://github.com/mikec-chi/kcf-oss")

_LANDING_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KCF MCP Server</title>
<meta http-equiv="refresh" content="5; url=__HOME__">
<style>
 :root{color-scheme:light dark}
 body{margin:0;min-height:100vh;display:grid;place-items:center;
      font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;
      background:#0b0b12;color:#e8e8f0}
 .card{max-width:34rem;padding:2.5rem;text-align:center}
 h1{font-size:1.5rem;margin:0 0 .75rem}
 code{background:rgba(127,127,160,.18);padding:.2em .5em;border-radius:.4em;
      word-break:break-all}
 a{color:#8ab4ff}
 .muted{opacity:.7;font-size:.9rem;margin-top:1.75rem}
</style></head>
<body><div class="card">
 <h1>🧩 KCF MCP Server</h1>
 <p>This is a live <b>Model Context Protocol</b> endpoint — an API for your LLM, not
    a web page. Point an MCP host (Claude, ChatGPT, VS&nbsp;Code…) at:</p>
 <p><code>__ENDPOINT__</code></p>
 <p>Model your domain, then generate the app — <i>knowledge coding</i>.</p>
 <p class="muted">Taking you to the open-source project… →
    <a href="__HOME__">__HOME__</a></p>
</div></body></html>"""


@mcp.custom_route("/", methods=["GET", "HEAD"])
async def _landing(request):  # noqa: ANN001 - Starlette Request
    host = request.headers.get("host") or (request.url.hostname or "localhost")
    scheme = "http" if host.startswith(("localhost", "127.")) else "https"
    endpoint = f"{scheme}://{host}/mcp"
    html = _LANDING_HTML.replace("__HOME__", KCF_HOME_URL).replace("__ENDPOINT__", endpoint)
    return HTMLResponse(html)


@mcp.tool(title="Get a sample .kcf model", annotations=_READ_ONLY)
def example_model() -> dict:
    """Return a small, ready-to-run sample `.kcf` model. Call it to learn the syntax
    by example and to copy a working skeleton before drafting the user's domain.
    No inputs. Returns `{ok, source}` where `source` is the `.kcf` text."""
    return t.example_model()


@mcp.tool(title="Read the .kcf authoring reference", annotations=_READ_ONLY)
def authoring_reference() -> dict:
    """Return a compact reference for writing `.kcf` model text — the model skeleton,
    the concept / relationship / action vocabulary, and what `valid` vs `ready` means.
    READ THIS FIRST, before drafting, so the model you write compiles. No inputs.
    Returns `{ok, reference}` (Markdown)."""
    return t.authoring_reference()


@mcp.tool(title="Describe this server's capabilities", annotations=_READ_ONLY)
def capabilities() -> dict:
    """A self-describing manifest of everything this server does: the end-to-end
    pipeline (orient → elicit & model → check → fill gaps → review & approve →
    generate), which tool serves each phase, the `valid`/`ready` verdicts, the
    coverage dimensions, and the provenance vocabulary that powers synthetic
    gap-filling. CALL THIS FIRST to recognize the whole flow. No inputs."""
    return t.capabilities()


@mcp.tool(title="Get the next best step (agent driver)", annotations=_READ_ONLY)
def next_action(
    source: Annotated[str, Field(description="The current `.kcf` model text (empty if "
        "you haven't drafted one yet).")] = "",
) -> dict:
    """The pipeline DRIVER — the tool an autonomous agent calls after every edit to
    know exactly what to do next, so it can drive the whole build→generate loop
    without guessing the order. Returns `{phase, verdict, readyToGenerate,
    recommendedTool, recommendedArgs, rationale, ...}` (plus the blocking errors or
    gaps for the current phase, and a `generationPlan` once valid). Loop: draft/fix →
    `next_action` → act on `recommendedTool`, until `readyToGenerate` is true; then
    follow `generationPlan`."""
    return t.next_action(source)


@mcp.tool(title="Get the elicitation process", annotations=_READ_ONLY)
def elicitation_guide() -> dict:
    """The process for turning a plain-language domain into a `.kcf` model: how to
    interview the user dimension by dimension (concepts → relationships → lifecycles →
    actions/contracts → rules), what to ask, and the discipline of never inventing
    fact. Returns `{ok, process, houseConventions}` — `houseConventions` carries any
    KCF_ELICITATION_GUIDE. Read this before eliciting a domain. No inputs."""
    return t.elicitation_process()


@mcp.tool(title="Explain how coverage gaps are found", annotations=_READ_ONLY)
def coverage_model() -> dict:
    """The reference for HOW coverage gaps are identified from grammar constructs
    (independent of any model): the obligations checked per profile, each one's
    dimension/construct and required/recommended level, how entities opt out
    (reference/read-only), and the provenance vocabulary for filling gaps. Use it to
    understand or explain the gap list that `coverage(source)` returns. No inputs."""
    return t.coverage_model_reference()


@mcp.tool(title="Compile .kcf to semantic IR", annotations=_READ_ONLY)
def compile(
    source: Annotated[str, Field(description="The full `.kcf` model text to compile.")],
) -> dict:
    """Compile `.kcf` model text into the normalized semantic IR. Returns
    `{ok, valid, ir, diagnostics}`: the IR, analyzer diagnostics, and whether the
    model is `valid` (analyzer-clean). Use it as a fast syntax/validity check while
    authoring; when `valid` is false, read `diagnostics` to see what to fix. A
    `compile` error (bad syntax) comes back as `{ok: false, stage: "compile", error}`
    with a `source:line:col` message."""
    return t.compile_model(source)


@mcp.tool(title="Assess a model's readiness", annotations=_READ_ONLY)
def assess(
    source: Annotated[str, Field(description="The full `.kcf` model text to assess.")],
) -> dict:
    """Compile and assess a `.kcf` model — your primary "is the model good enough?"
    check. Returns `{ok, valid, ready, requiredGaps, recommendedGaps, requiredGapIds,
    checks}`. Code generation only needs `valid` (analyzer-clean); `ready` (zero
    required gaps + patterns proven + roles resolved) is the completeness goal. Fix
    every `required` gap; treat `recommended` gaps as enrichment. Use `coverage` for
    the itemized to-do list."""
    return t.assess_model(source)


@mcp.tool(title="List a model's coverage gaps", annotations=_READ_ONLY)
def coverage(
    source: Annotated[str, Field(description="The full `.kcf` model text to analyze.")],
    by_concept: Annotated[bool, Field(description="If true, group gaps per concept, "
        "dimension by dimension, instead of a flat list.")] = False,
) -> dict:
    """The itemized coverage-gap to-do list for a model — use it to decide what to
    enrich next. Each gap has a `level`: `required` gaps are essential (fix them);
    `recommended` gaps (CRUD, set/bulk, lifecycle, transformation) are guidance you or
    the generator can fill (mark reference/immutable entities read-only via
    `mutability "read-only"`). Returns `{ok, summary, gaps}`, or `{ok, byConcept}`
    when `by_concept=true`."""
    return t.coverage_report(source, by_concept=by_concept)


@mcp.tool(title="Tier synthetic fills for approval", annotations=_READ_ONLY)
def review_queue(
    model_ir: Annotated[dict | None, Field(description="A compiled IR (from `compile`) "
        "whose model contains synthetic, provenance-tagged fills.")] = None,
    source: Annotated[str, Field(description="Alternatively, `.kcf` text to compile "
        "first.")] = "",
    high_confidence: Annotated[float, Field(description="Confidence threshold (0..1) "
        "for the bulk tier. Fills at or above go to bulk; below go to review.")] = 0.8,
) -> dict:
    """Tier the synthetic (LLM-proposed, provenance-tagged) knowledge in a model into
    an approval queue so the user can go FAST or be RIGOROUS:
    - a `bulk` tier — high-confidence fills — to offer for one-click MASS approval in
      chunks when they just want to get through it;
    - a `review` tier — low-confidence/unscored fills — to decide INDIVIDUALLY when
      they want rigor.
    Only records tagged synthetic (`extraction-method llm`, an assertion `status
    inferred`, or a seeded concept) appear — human-stated fact is never queued. Returns
    `{ok, counts, decisions}` with per-item ids to pass to `confirm_synthetic`."""
    return t.review_queue(model_ir=model_ir, source=source, high_confidence=high_confidence)


@mcp.tool(title="Apply approve/reject to synthetic fills",
          annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=False))
def confirm_synthetic(
    confirm: Annotated[list | None, Field(description="Ids (from `review_queue`) to "
        "approve. Bulk-approve a chunk by passing all its ids at once.")] = None,
    reject: Annotated[list | None, Field(description="Ids to drop from the model.")] = None,
    model_ir: Annotated[dict | None, Field(description="The compiled IR to govern "
        "(from `compile`).")] = None,
    source: Annotated[str, Field(description="Alternatively, `.kcf` text to compile "
        "first.")] = "",
    reviewer: Annotated[str, Field(description="Who approved — recorded as reviewedBy.")] = "sme",
    as_of: Annotated[str, Field(description="ISO timestamp to record; defaults to now "
        "(UTC).")] = "",
) -> dict:
    """Apply the user's approve/reject decisions to the synthetic knowledge in a model
    and return the GOVERNED IR (feed it to `codegen_prompt(model_ir=…)`). Confirmed
    fills are stamped `reviewedBy`/`recordedAt` and an assertion's `status` flips
    inferred→asserted (they become governed fact); rejected fills are removed; anything
    in neither list keeps its inferred provenance. Returns `{ok, model, report}` where
    `report` lists confirmed / rejected / notFound. This is the only tool that changes
    a model — but it never invents content, it only records human decisions."""
    return t.confirm_synthetic(confirm=confirm, reject=reject, model_ir=model_ir,
                               source=source, reviewer=reviewer, as_of=as_of)


@mcp.tool(title="Get a starting brief for a domain preset", annotations=_READ_ONLY)
def scaffold(
    profile: Annotated[str, Field(description="One of: business-application, "
        "operational-system, organizational-knowledge, event-driven-system, "
        "ai-application, analytics-platform.")],
    patterns: Annotated[list | None, Field(description="Optional extra pattern ids to "
        "seed into the brief.")] = None,
) -> dict:
    """A pattern-seeding brief (module closure + roles + obligations) for a domain
    preset, to author a model against when the user's domain fits a known shape. A
    STARTING POINT, not a finished model — you still write the entities and actions.
    Returns `{ok, scaffold}`."""
    return t.scaffold(profile, patterns)


@mcp.tool(title="List generatable tech stacks", annotations=_READ_ONLY)
def list_stacks() -> dict:
    """List the tech stacks that ship a single-shot code-generation example, each as
    `{id, title, tier}` where `tier` is `backend` or `frontend`. Call this before
    `codegen_prompt` so you pass a real `stack` id (and can offer the user the
    choices). No inputs. Returns `{ok, stacks}`."""
    return t.list_stacks()


@mcp.tool(title="Assemble the code-generation prompt", annotations=_READ_ONLY)
def codegen_prompt(
    stack: Annotated[str, Field(description="A stack id from `list_stacks()`, e.g. "
        "`fastapi-sqlmodel-postgres`.")],
    source: Annotated[str, Field(description="The `.kcf` model text to generate from "
        "(compiled here). Must be `valid`; need not be fully `ready`. Omit if passing "
        "`model_ir`.")] = "",
    instructions: Annotated[str, Field(description="Optional house conventions to "
        "inject as a highest-priority section, e.g. 'use async SQLAlchemy; JWT auth; "
        "snake_case tables; add OpenTelemetry'.")] = "",
    model_ir: Annotated[dict | None, Field(description="A pre-compiled IR to generate "
        "from — pass the GOVERNED IR returned by `confirm_synthetic` to build from the "
        "reviewed, approved model. Takes precedence over `source`.")] = None,
) -> dict:
    """The final step: assemble the ready-to-run LLM code-generation prompt for a
    valid model and a chosen stack. Generate from either `.kcf` `source` or a
    pre-compiled `model_ir` (use the governed IR from `confirm_synthetic`). Returns
    `{ok, stack, tier, systemPrompt, userPrompt}` — a system prompt + a user prompt
    containing the IR, coverage guidance, and the stack's single-shot example. RUN
    those two prompts yourself to generate the application; it finishes with a coverage
    self-audit proving nothing was dropped. If the model is not `valid`, returns
    `{ok: false, valid: false, diagnostics}` — fix those first.

    `instructions` injects house conventions as a highest-priority section that
    overrides the example where they conflict (contracts + self-audit still hold). A
    `KCF_CODEGEN_OVERRIDES` file (set in the MCP host config's env) is merged in too."""
    return t.codegen_prompt(source, stack, instructions, model_ir=model_ir)


@mcp.prompt(title="Model a domain with KCF, then generate code")
def model_domain(
    domain: Annotated[str, Field(description="Optional plain-language description of "
        "the domain to model (e.g. 'a support-ticket system'). Leave empty to have the "
        "assistant ask.")] = "",
    conventions: Annotated[str, Field(description="Optional house elicitation "
        "conventions — standard entities, required questions (audit/tenancy), naming "
        "rules — merged with any KCF_ELICITATION_GUIDE file.")] = "",
) -> str:
    """Guided end-to-end flow: turn a plain-language domain description into a
    complete, machine-checked KCF model, then generate an application from it.
    Optionally pass the domain description, and `conventions` (house elicitation
    rules — e.g. standard entities, required questions like audit/tenancy). A
    `KCF_ELICITATION_GUIDE` file (MCP host env) is merged in too."""
    brief = t.authoring_reference()["reference"]
    target = (f"The domain to model:\n\n{domain}\n" if domain.strip()
              else "First, ask the user to describe the domain (or point you at requirements).\n")
    house = "\n\n".join(x for x in (conventions.strip(), t.elicitation_guidance()) if x)
    house_block = (
        f"\n\n**House elicitation conventions (apply these):**\n\n{house}\n"
        if house else ""
    )
    return (
        "You are going to model the user's domain in KCF and then generate an "
        "application from that model — so the code is built from a checked "
        "specification, not guessed from prose.\n\n"
        f"{target}{house_block}\n"
        "Use the KCF tools on this server. Follow these steps, showing the user the "
        "model and the readiness verdict at each iteration:\n\n"
        "1. **Draft** a `.kcf` model capturing the entities, actors, events, "
        "lifecycles, relationships, and command/query action contracts the domain "
        "implies. Do not invent fields, statuses, or rules the user did not state — "
        "ask when unsure.\n"
        "2. **compile** the draft; fix any syntax/analyzer errors it reports.\n"
        "3. **assess** it. Fix every `required` gap (e.g. a missing identity). "
        "Realize the sensible `recommended` gaps (CRUD, lifecycle, set/bulk, "
        "transformation); mark reference/immutable entities read-only with "
        "`mutability \"read-only\";`. You only need the model to be **valid**, not "
        "fully `ready` — use `coverage` for a per-concept to-do list.\n"
        "4. Ask which **tech stack** to target (call **list_stacks** to show the "
        "options; backend and frontend tiers are available).\n"
        "5. Call **codegen_prompt(source, stack)** and run the returned system + "
        "user prompts to generate the application. It finishes with a coverage "
        "self-audit proving nothing in the model was dropped.\n\n"
        "To drive this without guessing the order, call **next_action(source)** after "
        "every edit — it names the next tool and tells you when you are ready to "
        "generate.\n\n"
        "Authoring reference:\n\n" + brief
    )


@mcp.prompt(title="Agent: build a valid KCF model from a domain")
def build_model(
    domain: Annotated[str, Field(description="Optional plain-language domain "
        "description; leave empty to ask the user first.")] = "",
    conventions: Annotated[str, Field(description="Optional house elicitation "
        "conventions, merged with any KCF_ELICITATION_GUIDE.")] = "",
) -> str:
    """Sub-agent script for the MODELLING half only: turn a domain into a checked,
    valid `.kcf` model (stop before code generation). Ideal to delegate to a
    model-building agent."""
    target = (f"The domain to model:\n\n{domain}\n" if domain.strip()
              else "First, ask the user to describe the domain (or point you at requirements).\n")
    house = "\n\n".join(x for x in (conventions.strip(), t.elicitation_guidance()) if x)
    house_block = f"\n\n**House elicitation conventions (apply these):**\n\n{house}\n" if house else ""
    return (
        "Your job: produce a machine-checked, **valid** KCF model of the user's domain. "
        "Stop at a valid model — do not generate code.\n\n"
        f"{target}{house_block}\n"
        "Drive it as a loop, maximizing the tools:\n"
        "1. Call **capabilities** and **elicitation_guide** to orient; **example_model** "
        "or **scaffold(profile)** for a starting shape.\n"
        "2. Draft a `.kcf` capturing entities, actors, events, lifecycles, "
        "relationships, and action contracts — invent nothing the user did not state.\n"
        "3. Call **next_action(source)** and do exactly what it says: fix syntax "
        "(**compile**), fix validity (analyzer errors), fill **required** gaps. Repeat "
        "until its verdict is `valid`.\n"
        "4. Enrich the sensible **recommended** gaps (**coverage** for the to-do list). "
        "For knowledge you infer rather than the user stating it, add it TAGGED "
        "(`extraction-method llm; confidence <0..1>; status inferred;`), then "
        "**review_queue** → show the user the bulk chunk for quick approval and the "
        "review chunk one by one → **confirm_synthetic** to govern it.\n"
        "5. Return the final valid `.kcf` (and, if you governed synthetic knowledge, the "
        "governed IR) plus a one-line readiness summary. Hand off to `generate_app`.\n\n"
        "Authoring reference:\n\n" + t.authoring_reference()["reference"]
    )


@mcp.prompt(title="Agent: generate an app from a valid KCF model")
def generate_app(
    stacks: Annotated[str, Field(description="Optional target stack id(s), e.g. "
        "'fastapi-sqlmodel-postgres, react-typescript-openapi'. Leave empty to ask.")] = "",
    instructions: Annotated[str, Field(description="Optional house code-gen conventions "
        "(ORM, auth, naming…), merged with any KCF_CODEGEN_OVERRIDES.")] = "",
) -> str:
    """Sub-agent script for the GENERATION half only: turn an already-valid model into a
    full application (backend, then frontend against its OpenAPI). Ideal to delegate to
    a generation agent once the model is built."""
    want = f"Target stack(s): {stacks}\n\n" if stacks.strip() else ""
    extra = f"\nHouse code-generation conventions to pass as `instructions`:\n\n{instructions}\n" if instructions.strip() else ""
    return (
        "Your job: generate a full application from an already-**valid** KCF model "
        "(paste the `.kcf`, or pass the governed IR). If it is not valid yet, use the "
        "`build_model` flow first.\n\n"
        f"{want}"
        "Maximize the tools in order:\n"
        "1. Call **next_action(source)** to confirm `readyToGenerate` and read its "
        "**generationPlan** (backend first, then frontend).\n"
        "2. Call **list_stacks** and pick/confirm a backend and a frontend stack.\n"
        "3. **codegen_prompt(stack=<backend>, source=… or model_ir=…, instructions=…)** "
        "→ run the returned system + user prompts to build the backend. It exposes an "
        "OpenAPI/Swagger document.\n"
        "4. **codegen_prompt(stack=<frontend>, …)** → run it against the backend's "
        "`/openapi.json` to build the UI.\n"
        "5. Each generation ends with a coverage self-audit (every construct → realized "
        "/ delegated / out-of-tier; `dropped: []`). Report it so the user sees nothing "
        "was lost." + extra
    )


# Resources — the same reference material, exposed so hosts can attach it as context
# (in addition to the callable tools above). Read-only documents, no inputs.

@mcp.resource("kcf://capabilities", title="KCF server capabilities",
              description="The end-to-end pipeline, tools, verdicts, and provenance vocabulary.",
              mime_type="application/json")
def resource_capabilities() -> str:
    import json as _json
    return _json.dumps(t.capabilities(), indent=2)


@mcp.resource("kcf://guide/elicitation", title="KCF elicitation process",
              description="How to interview a user and draft a .kcf model, dimension by dimension.",
              mime_type="text/markdown")
def resource_elicitation() -> str:
    guide = t.elicitation_process()
    house = guide.get("houseConventions")
    return guide["process"] + (f"\n\n## House elicitation conventions\n\n{house}\n" if house else "")


@mcp.resource("kcf://reference/authoring", title="KCF authoring reference",
              description="The .kcf syntax + vocabulary cheat-sheet.",
              mime_type="text/markdown")
def resource_authoring() -> str:
    return t.authoring_reference()["reference"]


@mcp.resource("kcf://reference/coverage-model", title="KCF coverage model",
              description="How coverage gaps are derived from grammar constructs.",
              mime_type="application/json")
def resource_coverage_model() -> str:
    import json as _json
    return _json.dumps(t.coverage_model_reference(), indent=2)


def main() -> None:
    mcp.run(transport=_TRANSPORT)


if __name__ == "__main__":
    main()
