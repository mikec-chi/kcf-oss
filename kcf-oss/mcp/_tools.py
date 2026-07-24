"""KCF toolchain wrapped as plain, JSON-returning helper functions.

These carry no MCP dependency so they are unit-testable on their own;
``server.py`` registers them as MCP tools. Each is stateless: the caller (an
LLM) holds the ``.kcf`` text and passes it in, so the natural loop is
author → assess → read gaps → edit → assess → codegen_prompt.

kcf-oss stops at the semantic IR: there is no emitter here. Code generation is
the LLM prompt pack (``codegen/``); ``codegen_prompt`` assembles the ready-to-use
prompt for a chosen stack.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve the OSS toolchain: kcf-oss/ (for the `compiler` package) and
# kcf-oss/tools/ (flat tool modules). semantic-core is not needed at runtime for
# compile / assess / coverage / codegen.
_MCP_DIR = Path(__file__).resolve().parent
OSS_ROOT = _MCP_DIR.parent
for _entry in (OSS_ROOT, OSS_ROOT / "tools"):
    _text = str(_entry)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from compiler import compile_text  # noqa: E402
from semantic_analyzer import Analyzer  # noqa: E402
from assess import assess as _assess_ir  # noqa: E402
from coverage_report import report as _coverage_report, by_concept as _by_concept, load_coverage_model  # noqa: E402
from profile_resolver import resolve_profile  # noqa: E402
from scaffold import build_scaffold  # noqa: E402
from pattern_contracts import load_contracts  # noqa: E402
from review_queue import review_queue as _review_queue, by_segment as _review_by_segment  # noqa: E402
from confirm_synthetic import confirm as _confirm_synthetic  # noqa: E402

CODEGEN_DIR = OSS_ROOT / "codegen"
STACKS_DIR = CODEGEN_DIR / "stacks"
EXAMPLE_KCF = OSS_ROOT / "tests" / "domains" / "business-application.kcf"
AUTHORING_BRIEF = _MCP_DIR / "authoring-brief.md"
MAX_SOURCE_BYTES = 128 * 1024


def authoring_reference() -> dict:
    """A compact reference for writing `.kcf` model text (syntax + vocabulary +
    what 'valid' vs 'ready' means)."""
    return {"ok": True, "reference": AUTHORING_BRIEF.read_text(encoding="utf-8")}


# --- Self-description: what this server does, and the process it supports --------
# The provenance vocabulary is the grammar's own (see AUTHORING knowledge-metadata):
# it is what makes a synthetic gap-fill distinguishable from human-stated fact, and
# what the review queue keys on.
PROVENANCE_VOCABULARY = {
    "extraction-method": "How the record was produced. Use `llm` for a synthetic "
        "gap-fill; this is what the review queue keys on.",
    "extraction-model": "The model id that proposed it, e.g. \"claude-opus-4-8\".",
    "confidence": "Your calibrated 0..1 estimate. >= the review threshold (0.8) is "
        "offered for bulk approval; below it is queued for individual review.",
    "status (assertions)": "`inferred` for a synthetic assertion; confirmation flips "
        "it to `asserted`. Also: disputed | superseded | retracted | unknown.",
    "evidence": "A reference to the reasoning/source, or explicitly empty.",
    "reviewed-by / recorded-at": "Stamped by `confirm_synthetic` on approval — do not "
        "set these yourself; they mark a record as governed (human-confirmed) fact.",
}

ELICITATION_PROCESS = """\
The elicitation goal is a *valid* `.kcf` model that captures what the user actually
means — never invented detail. Work dimension by dimension, showing the model and
the `assess` verdict as you go, and ask before assuming.

1. Frame the domain. What is being run/tracked/decided? Who uses it, and what are
   the few things they most need it to do? Pick the closest `profile` (see
   `scaffold`), but let the user's facts, not the preset, drive the content.
2. Concepts (nouns). Elicit the core `entity`s and, for each, its `identity` and the
   attributes the user names — required vs optional. Mark reference/lookup data
   `mutability "read-only"`. Name the `actor`s (roles/principals), the `event`s
   (immutable facts), and any `work` (processes).
3. Relationships. How are concepts connected? Choose the `rootKind` that matches the
   meaning (composition/association/participation/governance/…), not just "has a".
4. Lifecycles. For anything with states ("open→closed", "draft→approved"), elicit the
   states and the *allowed* transitions — this becomes a state machine.
5. Actions (verbs) + contracts. For each thing users do, model a `command`/`query`/
   `transform`: its `operation`, `scope`, `target`, and the contract
   (idempotency/atomicity/concurrency and — required — `authorization`). Aim for full
   CRUD, a set/bulk op, and a data-transformation per entity where they make sense.
6. Rules & policies. Capture constraints, permissions, obligations, and derivations
   the user states as `rule`/`policy` — the invariants the app must enforce.
7. Supporting dimensions (use when the domain has them). Rich `event`s can classify
   themselves (`kind`) and **drive a lifecycle** (`affect-lifecycle`); `measure`s
   capture metrics (`unit`/`aggregation`/`threshold`); `temporal`/`spatial` capture
   time/geometry; `intent` captures goals; `proposition`/`formula` capture logic/math;
   and cross-cutting concerns are authored as top-level profile blocks
   (`integration`/`security`/`lineage`/`architecture`/`experience`/`design`/
   `analytics`/`ai`). See the authoring reference for the syntax — model these only
   when the user's domain actually implies them.
8. Check & iterate. `compile` to catch syntax, `assess` for the verdict, `coverage`
   for the gap to-do list. Fix required gaps; enrich or synthesize the recommended
   ones (see the gap-filling capability). Stop when the user confirms it reflects
   their domain and it is valid.

Discipline: one concept = one primary kind (connect cross-cutting meaning with
relationships); events are immutable (corrections are new events); if the user did
not state a field/status/rule, ask — do not fabricate it as fact.\
"""


def capabilities() -> dict:
    """A self-describing manifest: the phases this server supports end to end, the
    tool for each, the coverage/construct model, and the provenance vocabulary that
    powers synthetic gap-filling. Call this to orient before doing anything."""
    return {
        "ok": True,
        "server": "kcf",
        "summary": "Turn a domain into a complete, machine-checked semantic model, "
                   "then generate code from it — knowledge coding = semantic modeling "
                   "+ vibe coding. You (the assistant) hold the model text and pass it "
                   "into each tool.",
        "pipeline": [
            {"phase": "1. Orient", "does": "Learn the syntax and the process.",
             "tools": ["capabilities", "authoring_reference", "elicitation_guide",
                       "coverage_model", "example_model", "scaffold"]},
            {"phase": "2. Elicit & model", "does": "Interview the user and draft a "
                      ".kcf model, dimension by dimension, inventing nothing.",
             "tools": ["elicitation_guide", "scaffold", "compile"]},
            {"phase": "3. Check", "does": "Compile, get the readiness verdict, and list "
                      "coverage gaps (missing obligations per construct).",
             "tools": ["compile", "assess", "coverage", "coverage_model"]},
            {"phase": "4. Fill gaps (synthetic)", "does": "Propose smallest-plausible "
                      "fills for gaps, tagged with provenance (extraction-method llm; "
                      "confidence …; status inferred) so they stay distinguishable.",
             "tools": ["coverage", "coverage_model", "compile"]},
            {"phase": "5. Review & approve", "does": "Tier the synthetic fills into a "
                      "bulk tier (mass-approve to move fast) and a review tier "
                      "(decide individually to be rigorous), then apply the decisions.",
             "tools": ["review_queue", "confirm_synthetic"]},
            {"phase": "6. Generate", "does": "Assemble the code-generation prompt for a "
                      "chosen stack from the valid (governed) model, then run it.",
             "tools": ["list_stacks", "codegen_prompt"]},
        ],
        "agentLoop": "To drive this autonomously: call `next_action(source)` after every "
            "edit — it returns the single best next tool + why, and `readyToGenerate`. "
            "Loop: draft/fix -> next_action -> act, until `readyToGenerate` is true; then "
            "follow the returned `generationPlan` (backend, then frontend against its "
            "OpenAPI). Two guided prompts scope this for sub-agents: `build_model` "
            "(prose -> valid model) and `generate_app` (valid model -> generated app); "
            "`model_domain` runs both end to end.",
        "verdicts": {
            "valid": "Analyzer-clean (identities present, references resolve). The gate "
                     "for code generation.",
            "ready": "Also complete — zero required coverage gaps, patterns proven, "
                     "roles resolved. The completeness goal, not a gate.",
        },
        "coverageDimensions": ["ENTITY", "LIFECYCLE", "ACTION", "RULE", "ACTOR",
                                "MEASURE"],
        "provenanceVocabulary": PROVENANCE_VOCABULARY,
        "syntheticGapFilling": "Coverage gaps can be filled with general domain "
            "knowledge the LLM proposes. Every such fill is tagged in the grammar's own "
            "provenance vocabulary (never as bare fact), so `review_queue` can offer "
            "high-confidence fills for one-click bulk approval and route the rest to "
            "individual review, and `confirm_synthetic` records who approved what.",
        "tuning": "House conventions tune both ends without forking: "
            "KCF_ELICITATION_GUIDE (or the model_domain `conventions` arg) for the "
            "questions asked; KCF_CODEGEN_OVERRIDES (or codegen_prompt `instructions`) "
            "for how code is generated.",
        "livingModel": "The model is the source of truth; code is a projection of it. "
            "Prevent drift: read the model before coding; for any change that alters "
            "meaning (new field/action/rule/status/relationship) update the .kcf FIRST "
            "(compile --validate, assess) then generate; if code was vibe-coded "
            "directly, RECONCILE the model to match before building further (ask when "
            "intent is ambiguous). Annotate each artifact with the construct it "
            "realizes. `kcf init` seeds a project wired for this loop; the full "
            "protocol is codegen/MODEL_SYNC.md.",
    }


def elicitation_process() -> dict:
    """The built-in elicitation process (how to interview the user and draft a model),
    plus any house conventions from KCF_ELICITATION_GUIDE."""
    return {
        "ok": True,
        "process": ELICITATION_PROCESS,
        "houseConventions": elicitation_guidance() or None,
    }


def coverage_model_reference() -> dict:
    """Explain how coverage gaps are identified from grammar constructs: the
    obligations (per profile), their dimension/construct and required/recommended
    level, how entities opt out, and the provenance vocabulary for filling gaps.
    This is the *reference* for how `coverage(source)` works, independent of any model."""
    model = load_coverage_model()
    obligations = [{
        "gapId": o["id"],
        "title": o["title"],
        "level": o["level"],
        "dimension": o.get("dimension"),
        "construct": o.get("conceptKind") or o.get("effects") or o.get("collection") or "model",
        "appliesToProfiles": o["profiles"],
        "exemptWhen": o.get("exemptTraits"),
    } for o in model["obligations"]]
    return {
        "ok": True,
        "coverageModelVersion": model.get("coverageModelVersion"),
        "howItWorks": "The EBNF grammar defines what is *well-formed*; the analyzer "
            "defines what is *valid*; coverage is a third axis — *completeness*. It is "
            "derived from the grammar's own dimension/concept vocabulary: each "
            "obligation checks that a construct the model uses also carries the "
            "knowledge it implies (e.g. an ENTITY should have an identity, a lifecycle, "
            "CRUD). A gap is a missing obligation, not an error — the model can be valid "
            "yet incomplete.",
        "levels": {
            "required": "Must be fixed to be `ready` (and identity/authorization are "
                        "part of being usable). Fix these first.",
            "recommended": "Enrichment — realize it, synthesize a tagged fill, or "
                           "record a justified exclusion (e.g. mark reference data "
                           "read-only to exempt it).",
            "info": "Advisory.",
        },
        "exemption": "An entity opts out of write obligations (CRUD-write / set / "
            "transform) when it is reference/immutable: declare `mutability \"read-only\"` "
            "(or a role trait listed in the obligation's exemptTraits).",
        "obligations": obligations,
        "provenanceVocabulary": PROVENANCE_VOCABULARY,
    }


# --- Tuning: inject house conventions into elicitation / code generation --------
# Resolve overrides from an explicit string (per call) and/or a file named by an
# env var (per project — set once in an MCP host config). Teams tune the prompts
# without forking anything.

def _resolve_overrides(explicit: str, env_var: str) -> str:
    parts = []
    if explicit and explicit.strip():
        parts.append(explicit.strip())
    path = os.environ.get(env_var)
    if path:
        try:
            text = Path(path).read_text(encoding="utf-8").strip()
            if text:
                parts.append(text)
        except OSError:
            pass
    return "\n\n".join(parts)


def elicitation_guidance() -> str:
    """House elicitation guidance (from KCF_ELICITATION_GUIDE), or ''."""
    return _resolve_overrides("", "KCF_ELICITATION_GUIDE")


def _compile_or_error(source: str):
    """Return (ir, None) or (None, error_dict)."""
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return None, {"ok": False, "error": f"source exceeds {MAX_SOURCE_BYTES // 1024} KB limit"}
    try:
        return compile_text(source, source="<mcp>"), None
    except ValueError as exc:  # LexError / ParseError carry "source:line:col: …"
        return None, {"ok": False, "stage": "compile", "error": str(exc)}


def compile_model(source: str) -> dict:
    """Compile ``.kcf`` text into normalized semantic IR (with diagnostics)."""
    ir, err = _compile_or_error(source)
    if err:
        return err
    diagnostics = Analyzer(ir).run()
    valid = not any(d.get("severity") == "error" for d in diagnostics)
    return {"ok": True, "valid": valid, "ir": ir, "diagnostics": diagnostics}


def assess_model(source: str) -> dict:
    """Compile then assess: the readiness verdict (validity + coverage + patterns
    + roles). Generation only needs ``valid``; ``ready`` is the completeness goal."""
    ir, err = _compile_or_error(source)
    if err:
        return err
    report = _assess_ir(ir)
    cov = report["checks"]["coverage"]
    return {
        "ok": True,
        "valid": report["valid"],
        "ready": report["ready"],
        "requiredGaps": cov["requiredGaps"],
        "recommendedGaps": cov.get("recommendedGaps", 0),
        "requiredGapIds": cov.get("requiredGapIds", []),
        "checks": report["checks"],
    }


def coverage_report(source: str, by_concept: bool = False) -> dict:
    """The coverage gap list — the enrichment to-do list. ``required`` gaps are
    essential; ``recommended`` gaps (CRUD/set/lifecycle/transformation) are
    guidance you (or an LLM) can fill as tagged synthetic knowledge."""
    ir, err = _compile_or_error(source)
    if err:
        return err
    report = _coverage_report(ir, load_coverage_model())
    if by_concept:
        return {"ok": True, "byConcept": _by_concept(report)}
    return {"ok": True, "summary": report["summary"], "gaps": report["gaps"]}


# --- Agent driver: turn the pipeline into a self-navigating loop -----------------
# An autonomous agent maximizes the toolset by calling `next_action` after every
# edit: it always returns the single best next tool + why, so the agent can drive
# draft -> valid -> (fill/review) -> generate without guessing the order.

def _has_synthetic(ir: dict) -> bool:
    try:
        return _review_queue(ir, 0.8)["counts"]["total"] > 0
    except Exception:  # pragma: no cover - defensive
        return False


def generation_plan() -> list:
    """The ordered stack-generation steps for a full application: backend first (it
    exposes the OpenAPI), then frontend bound to it."""
    stacks = list_stacks()["stacks"]
    backend = [s["id"] for s in stacks if s.get("tier", "backend") == "backend"]
    frontend = [s["id"] for s in stacks if s.get("tier") == "frontend"]
    steps = [{
        "step": 1, "tool": "codegen_prompt", "tier": "backend",
        "note": "Generate the backend first; it exposes an OpenAPI/Swagger document.",
        "stackChoices": backend,
    }]
    if frontend:
        steps.append({
            "step": 2, "tool": "codegen_prompt", "tier": "frontend",
            "note": "Generate the frontend against the backend's /openapi.json.",
            "stackChoices": frontend,
        })
    return steps


def next_action(source: str = "") -> dict:
    """The pipeline driver: given the current ``.kcf`` (or empty), return the single
    best next step so an agent can drive the whole build->generate loop autonomously.
    Call it after every edit and act on ``recommendedTool``; when ``readyToGenerate``
    is true, follow ``generationPlan``."""
    if not source.strip():
        return {"ok": True, "phase": "elicit", "verdict": None, "readyToGenerate": False,
                "recommendedTool": "elicitation_guide", "recommendedArgs": {},
                "rationale": "No model yet. Read the elicitation process, draft a `.kcf` "
                             "capturing the user's domain (invent nothing), then call "
                             "next_action again."}

    ir, err = _compile_or_error(source)
    if err:
        return {"ok": True, "phase": "fix-syntax", "verdict": "ill-formed",
                "readyToGenerate": False, "blocking": err.get("error"),
                "recommendedTool": "compile", "recommendedArgs": {"source": "<corrected .kcf>"},
                "rationale": "The model does not compile. Fix the reported syntax error, "
                             "then call next_action again."}

    diagnostics = Analyzer(ir).run()
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    if errors:
        return {"ok": True, "phase": "fix-validity", "verdict": "well-formed",
                "readyToGenerate": False, "blocking": errors,
                "recommendedTool": "compile", "recommendedArgs": {"source": "<corrected .kcf>"},
                "rationale": "The model compiles but is not valid. Resolve the analyzer "
                             "errors listed in `blocking`, then call next_action again."}

    report = _coverage_report(ir, load_coverage_model())
    required = [g for g in report["gaps"] if g["level"] == "required"]
    recommended = [g for g in report["gaps"] if g["level"] == "recommended"]

    if required:
        return {"ok": True, "phase": "fill-required", "verdict": "valid",
                "readyToGenerate": False, "requiredGaps": required,
                "recommendedTool": "coverage", "recommendedArgs": {"source": "<source>"},
                "rationale": "Valid but incomplete: required obligations are unmet (e.g. a "
                             "missing identity or authorization). Realize them in the "
                             "`.kcf`, then call next_action again."}

    if _has_synthetic(ir):
        return {"ok": True, "phase": "review-synthetic", "verdict": "valid",
                "readyToGenerate": True, "recommendedGaps": recommended,
                "recommendedTool": "review_queue", "recommendedArgs": {"source": "<source>"},
                "rationale": "Valid, and the model carries synthetic (LLM-proposed) "
                             "knowledge. Tier it with review_queue, then confirm_synthetic "
                             "(bulk-approve the confident chunk; review the rest) so the "
                             "user governs it before you generate.",
                "generationPlan": generation_plan()}

    return {"ok": True, "phase": "generate", "verdict": "valid", "readyToGenerate": True,
            "recommendedGaps": recommended,
            "recommendedTool": "list_stacks", "recommendedArgs": {},
            "rationale": "Valid — ready to generate. Optionally realize the recommended "
                         "gaps first (or synthesize + review them). Then follow "
                         "generationPlan: generate the backend, then the frontend against "
                         "its OpenAPI.",
            "generationPlan": generation_plan()}


def scaffold(profile: str, patterns: list | None = None) -> dict:
    """A pattern-seeding brief for a profile: module closure + roles + obligations
    to author against. A starting point, not a finished model."""
    try:
        return {"ok": True, "scaffold": build_scaffold(profile, patterns or [], load_contracts())}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "error": f"scaffold: {exc}"}


def resolve_profile_closure(preset: str) -> dict:
    """The resolved module + pattern closure for a profile preset."""
    try:
        return {"ok": True, "profile": resolve_profile(preset)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "error": f"unknown preset: {preset}"}


def list_stacks() -> dict:
    """The tech stacks that ship a single-shot codegen example."""
    stacks = []
    if STACKS_DIR.exists():
        for sj in sorted(STACKS_DIR.glob("*/stack.json")):
            m = json.loads(sj.read_text(encoding="utf-8"))
            stacks.append({"id": m["id"], "title": m.get("title", m["id"]), "tier": m.get("tier", "backend")})
    return {"ok": True, "stacks": stacks}


def example_model() -> dict:
    """A small, ready sample ``.kcf`` model to start from."""
    return {"ok": True, "source": EXAMPLE_KCF.read_text(encoding="utf-8")}


def codegen_prompt(source: str, stack: str, instructions: str = "",
                   model_ir: dict | None = None) -> dict:
    """Assemble the ready-to-paste LLM code-generation prompt for a chosen stack:
    the durable system prompt + this model's IR + coverage guidance + the stack's
    single-shot example. Requires a **valid** model (not a fully ``ready`` one).

    Generate from either ``source`` (``.kcf`` text, compiled here) or a pre-compiled
    ``model_ir`` — pass the governed IR returned by ``confirm_synthetic`` to generate
    from the reviewed, human-approved model.

    Tune it: pass ``instructions`` (house conventions — e.g. "use async SQLAlchemy;
    JWT auth; add OpenTelemetry") and/or set ``KCF_CODEGEN_OVERRIDES`` to a Markdown
    file. Both are injected as a highest-priority 'House conventions' section that
    overrides the example where they conflict (the coverage self-audit still holds).
    """
    if ".." in stack or "/" in stack or not (STACKS_DIR / stack / "stack.json").exists():
        return {"ok": False, "error": f"unknown stack: {stack}. Use list_stacks()."}
    if model_ir is not None:
        ir = model_ir
    else:
        ir, err = _compile_or_error(source)
        if err:
            return err
    diagnostics = Analyzer(ir).run()
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    if errors:
        return {"ok": False, "valid": False,
                "error": "model is not valid (fix analyzer errors before generating)",
                "diagnostics": errors}

    stack_dir = STACKS_DIR / stack
    meta = json.loads((stack_dir / "stack.json").read_text(encoding="utf-8"))
    tier = meta.get("tier", "backend")
    system_prompt = (CODEGEN_DIR / "system-prompt.md").read_text(encoding="utf-8")
    example = (stack_dir / "EXAMPLE.md").read_text(encoding="utf-8")
    ir_json = json.dumps(ir, indent=2)

    gaps = _coverage_report(ir, load_coverage_model())["gaps"]
    guidance = ("\n".join(f"- [{g['level']}] {g['subject']}: {g['message']}" for g in gaps)
                or "- none — the model is complete (ready).")
    guidance_block = (
        "\n\n## Coverage guidance (enrichment — not blocking)\n\nThe model is valid. "
        "Realize the coverage gaps that make sense for the domain and note any you "
        "skip; `required` gaps are the important ones:\n\n" + guidance + "\n"
    )

    house = _resolve_overrides(instructions, "KCF_CODEGEN_OVERRIDES")
    house_block = (
        "\n\n## House conventions (HIGHEST PRIORITY)\n\nApply these; they override the "
        "single-shot example and defaults where they conflict. Still honor the action "
        "contracts, never drop declared meaning, and finish with the coverage "
        "self-audit:\n\n" + house + "\n"
    ) if house else ""

    if tier == "frontend":
        user_prompt = (
            f"Tier: frontend. Generate the frontend for the whole model, targeting the "
            f"`{stack}` stack. Generate a typed API client from your backend's OpenAPI "
            f"(paste it where marked) and call it for all data and actions; delegate "
            f"everything the server owns; realize views, forms, lifecycle controls, and "
            f"role-gated UI per the example. Finish with the coverage self-audit.\n\n"
            f"## The model (meaning + UX intent)\n\n```json\n{ir_json}\n```\n\n"
            f"## The backend OpenAPI (bind to this)\n\n```json\n"
            f"<PASTE YOUR BACKEND'S /openapi.json HERE>\n```\n{guidance_block}\n"
            f"## The single-shot example to imitate\n\n{example}{house_block}"
        )
    else:
        user_prompt = (
            f"Tier: backend. Generate the implementation for the whole model from the "
            f"KCF IR below, targeting the `{stack}` stack. Follow the single-shot example "
            f"exactly; realize what the IR declares, expose an OpenAPI/Swagger interface "
            f"by default, and finish with the coverage self-audit.\n\n"
            f"## The model (authoritative specification)\n\n```json\n{ir_json}\n```\n"
            f"{guidance_block}\n## The single-shot example to imitate\n\n{example}{house_block}"
        )
    return {"ok": True, "stack": stack, "tier": tier,
            "systemPrompt": system_prompt, "userPrompt": user_prompt}


# --- Synthetic gap-fill review & approval ---------------------------------------
# The LLM proposes fills for coverage gaps, tagged with provenance (see
# PROVENANCE_VOCABULARY). These two tools let the user approve them fast (bulk) or
# rigorously (one by one), then govern the model. They operate on a compiled IR
# (from `compile`), because provenance/status live in the IR.

def _as_ir(model_ir: dict | None, source: str):
    """Accept a pre-compiled IR dict or `.kcf` source; return (ir, None) or (None, err)."""
    if model_ir is not None:
        return model_ir, None
    if not source:
        return None, {"ok": False, "error": "pass either model_ir (from compile) or source"}
    return _compile_or_error(source)


def review_queue(model_ir: dict | None = None, source: str = "",
                 high_confidence: float = 0.8, source_trace: dict | None = None) -> dict:
    """Tier the synthetic (LLM-proposed) knowledge in a model into an approval queue,
    so the user can move fast or be rigorous:

    - `bulk` tier — high-confidence fills (>= `high_confidence`): offer these for
      one-click **mass approval** in chunks when the user just wants to get through it.
    - `review` tier — low-confidence/unscored fills: surface these for **individual**
      decisions when the user wants to be rigorous.

    Only records tagged synthetic (`extraction-method llm`, an assertion `status
    inferred`, or a concept `metadata.seededFrom`) appear — human-stated fact is never
    queued. Pass a `source_trace` (source-trace-v1) to group the queue by the source
    segment each fill came from instead. Returns the queue with per-item ids you then
    pass to `confirm_synthetic`. Provide `model_ir` (from `compile`) or `.kcf` `source`."""
    ir, err = _as_ir(model_ir, source)
    if err:
        return err
    if source_trace is not None:
        return {"ok": True, **_review_by_segment(ir, source_trace, high_confidence)}
    return {"ok": True, **_review_queue(ir, high_confidence)}


def confirm_synthetic(confirm: list | None = None, reject: list | None = None,
                      model_ir: dict | None = None, source: str = "",
                      reviewer: str = "sme", as_of: str = "") -> dict:
    """Apply the user's approve/reject decisions to the synthetic knowledge in a model
    and return the **governed** IR (pass it to `codegen_prompt(model_ir=…)`).

    - `confirm`: ids to approve (from `review_queue`) — bulk-approve a whole chunk by
      passing all its ids, or approve individually. Confirmed records are stamped
      `reviewedBy`/`recordedAt` and an assertion's `status` flips inferred→asserted:
      they become governed fact.
    - `reject`: ids to drop — the record is removed.
    - Records in neither list keep their inferred/unreviewed provenance.

    `reviewer` records who approved; `as_of` is the ISO timestamp recorded (defaults to
    now, UTC). Returns `{ok, model, report}` where `report` lists confirmed/rejected/
    notFound. Provide `model_ir` (from `compile`) or `.kcf` `source`."""
    ir, err = _as_ir(model_ir, source)
    if err:
        return err
    stamp = as_of.strip() or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        updated, report = _confirm_synthetic(ir, confirm or [], reject or [], reviewer, stamp)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "model": updated, "report": report}
