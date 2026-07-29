"""The canonical six-stage KCF project journey (evidence → generated app).

`kcf.py` exposes small semantic tools (compile, assess, coverage, review-queue,
confirm, source-coverage, verify-realization, codegen prompt assembly). Historically a
user had to know which expert tool to run when. This module composes them into ONE
visible journey a person — or a coding agent — can follow without that expertise:

    1. add evidence      inputs/ + `kcf sources add`
    2. elicit            `kcf elicit`  (assembles the coding-agent prompt)
    3. review            `kcf review`  (human-readable model-summary.md)
    4. approve           `kcf approve` (stated / inferred / unresolved → review envelope)
    5. choose a stack    `kcf generate-plan --backend … --frontend …`
    6. generate + verify `kcf verify-project`

Everything here is orchestration over the existing engines — it adds no grammar, IR,
or analyzer semantics. It operates on a *project directory* (the scaffold `kcf init
--guided` produces), located by walking up to the nearest `kcf.project.json`; that file
is the durable state, and the stage is *derived* from filesystem + IR state so it can
never lie about where the project actually is.
"""
from __future__ import annotations

import json
from pathlib import Path

from compiler import compile_file, compile_text  # noqa: E402
from semantic_analyzer import Analyzer  # noqa: E402
from assess import assess as assess_model  # noqa: E402
from coverage_report import load_coverage_model, report as coverage_report  # noqa: E402
from review_queue import review_queue  # noqa: E402
from source_coverage import is_complete as source_complete, source_coverage  # noqa: E402
from semantic_delta import compare as semantic_compare  # noqa: E402

PROJECT_FILE = "kcf.project.json"

# Evidence modality inferred from a file, aligned with config/document-profiles/ so a
# registered source names a real document profile where one exists.
_KIND_BY_SUFFIX = {
    ".md": "prose", ".txt": "prose", ".rst": "prose",
    ".pdf": "document", ".doc": "document", ".docx": "document", ".odt": "document",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
    ".webp": "image", ".svg": "image", ".bmp": "image", ".tif": "image", ".tiff": "image",
    ".dbml": "schema", ".sql": "schema", ".prisma": "schema",
    ".mmd": "diagram", ".mermaid": "diagram",
    ".csv": "data", ".json": "data", ".yaml": "data", ".yml": "data", ".xml": "data",
}
STAGES = ("evidence", "elicitation", "review", "approval", "generation", "verification")


# --------------------------------------------------------------------------- project

class ProjectError(Exception):
    pass


def find_project(start: Path | None = None) -> Path:
    """Return the project root — the nearest ancestor holding kcf.project.json."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / PROJECT_FILE).is_file():
            return candidate
    raise ProjectError(
        f"no {PROJECT_FILE} found in {here} or its parents. Run `kcf init --guided <dir>` first.")


def load_project(root: Path) -> dict:
    return json.loads((root / PROJECT_FILE).read_text(encoding="utf-8"))


def save_project(root: Path, project: dict) -> None:
    (root / PROJECT_FILE).write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")


def kind_for(path: Path) -> str:
    return _KIND_BY_SUFFIX.get(path.suffix.lower(), "unknown")


# --------------------------------------------------------------------------- IR access

def _model_path(root: Path, project: dict) -> Path | None:
    model = project.get("model")
    if model and (root / model).is_file():
        return root / model
    return None


def _governed_ir_path(root: Path, project: dict) -> Path:
    return root / (project.get("governedIr") or "model/model-ir.governed.json")


def load_ir(root: Path, project: dict, *, prefer_governed: bool = False):
    """Compile the .kcf source of truth to IR (or read a governed/compiled IR).

    Returns (ir, error_message). Compiling the .kcf keeps the IR honest to the model —
    we never trust a hand-edited model-ir.json as the source of truth.
    """
    if prefer_governed:
        gov = _governed_ir_path(root, project)
        if gov.is_file():
            try:
                return json.loads(gov.read_text(encoding="utf-8")), None
            except json.JSONDecodeError as exc:
                return None, f"governed IR is not valid JSON: {exc}"
    source = _model_path(root, project)
    if source is not None:
        try:
            return compile_file(source), None
        except Exception as exc:  # parse/normalize error — surface it, don't crash the journey
            return None, f"model failed to compile: {exc}"
    ir_rel = project.get("ir")
    if ir_rel and (root / ir_rel).is_file():
        try:
            return json.loads((root / ir_rel).read_text(encoding="utf-8")), None
        except json.JSONDecodeError as exc:
            return None, f"IR is not valid JSON: {exc}"
    return None, "no model or IR found"


def _trace_and_document(root: Path, project: dict):
    conv = project.get("artifacts") or {}
    doc_rel, trace_rel = conv.get("sourceDocument"), conv.get("sourceTrace")
    doc = json.loads((root / doc_rel).read_text(encoding="utf-8")) if doc_rel and (root / doc_rel).is_file() else None
    trace = json.loads((root / trace_rel).read_text(encoding="utf-8")) if trace_rel and (root / trace_rel).is_file() else None
    return doc, trace


# --------------------------------------------------------------------------- sources

def add_sources(root: Path, target: Path) -> list[dict]:
    """Register a file (or every file under a directory) as evidence, appending to the
    source manifest and kcf.project.json. Returns the newly-added entries. The coding
    LLM performs extraction; KCF only records what evidence exists and its modality."""
    target = target.resolve()
    if not target.exists():
        raise ProjectError(f"no such path: {target}")
    def _is_evidence(p: Path) -> bool:
        return p.is_file() and p.name != ".gitkeep" and not p.name.startswith(".")
    files = sorted(p for p in target.rglob("*") if _is_evidence(p)) if target.is_dir() else [target]
    project = load_project(root)
    manifest = project.setdefault("sources", [])
    known = {entry["path"] for entry in manifest}
    added: list[dict] = []
    for f in files:
        try:
            rel = f.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = f.as_posix()  # outside the project tree — record the absolute path
        if rel in known:
            continue
        entry = {"id": Path(rel).stem, "path": rel, "kind": kind_for(f), "status": "registered"}
        manifest.append(entry)
        known.add(rel)
        added.append(entry)
    save_project(root, project)
    return added


# --------------------------------------------------------------------------- status

_SYNTHETIC_COLLECTIONS = ("assertions", "reasoning", "identityResolutions",
                          "knowledgeQueries", "rules", "policies", "relationships",
                          "information", "actions", "lifecycles")


def _synthetic_item_index(ir: dict) -> dict:
    """id -> the underlying IR item, for every collection the review queue can surface,
    plus concepts. Lets us read each decision's review state (which the queue's decision
    dicts don't carry)."""
    idx = {}
    for coll in _SYNTHETIC_COLLECTIONS:
        for item in ir.get(coll, []):
            key = item.get("qualifiedName") or item.get("id")
            if key:
                idx[key] = item
    for concept in ir.get("concepts", []):
        key = concept.get("qualifiedName") or concept.get("id")
        if key:
            idx[key] = concept
    return idx


def _is_reviewed(item: dict) -> bool:
    """A synthetic item has been approved once `confirm_synthetic` stamped it (reviewedBy
    / confirmedAgainstSource, or status flipped inferred→asserted). Concepts carry the
    stamp under metadata."""
    meta = item.get("metadata") or {}
    return bool(item.get("reviewedBy") or meta.get("reviewedBy")
                or item.get("confirmedAgainstSource") or meta.get("confirmedAgainstSource")
                or item.get("status") == "asserted")


def _pending(ir: dict):
    """The PENDING synthetic (LLM-proposed) decisions, already-reviewed ones excluded,
    split into (inferred, unresolved): inferred = a confidence is present (approvable);
    unresolved = no confidence (insufficiently supported). Each is a review-queue decision
    dict carrying `id`, `tier` (bulk=high-confidence / review), `confidence`, `summary`."""
    queue = review_queue(ir)
    idx = _synthetic_item_index(ir)
    inferred, unresolved = [], []
    for d in queue.get("decisions", []):
        if _is_reviewed(idx.get(d["id"], {})):
            continue
        (inferred if d.get("confidence") is not None else unresolved).append(d)
    return inferred, unresolved


def _stated_count(ir: dict) -> int:
    """Directly-supported constructs: identity-bearing items that are NOT synthetic
    (never entered the review queue). Informational — they need no approval."""
    synthetic = {d["id"] for d in review_queue(ir).get("decisions", [])}
    total = 0
    for coll in _SYNTHETIC_COLLECTIONS + ("concepts", "collectionTransforms", "processes", "events"):
        for item in ir.get(coll, []):
            key = item.get("qualifiedName") or item.get("id")
            if key and key not in synthetic:
                total += 1
    return total


def status(root: Path) -> dict:
    project = load_project(root)
    inputs_dir = root / "inputs"
    evidence_files = [p for p in inputs_dir.rglob("*") if p.is_file() and p.name != ".gitkeep"] if inputs_dir.is_dir() else []
    manifest = project.get("sources", [])
    registered_paths = {e["path"] for e in manifest}
    unregistered = [p.relative_to(root).as_posix() for p in evidence_files
                    if p.relative_to(root).as_posix() not in registered_paths]

    ir, ir_error = load_ir(root, project)
    valid = None
    required_gaps = recommended_gaps = None
    ready = None
    diagnostics: list = []
    if ir is not None:
        diagnostics = Analyzer(ir).run()
        valid = not any(d["severity"] == "error" for d in diagnostics)
        cov = coverage_report(ir, load_coverage_model())["summary"]
        required_gaps, recommended_gaps = cov["required"], cov["recommended"]
        ready = assess_model(ir)["ready"] if valid else False

    pending_inferred = pending_unresolved = None
    if ir is not None and valid:
        inferred, unresolved = _pending(ir)
        pending_inferred, pending_unresolved = len(inferred), len(unresolved)

    stack = project.get("stack") or {}
    review_done = (root / (project.get("artifacts", {}).get("reviewPacket") or "review/model-summary.md")).is_file()
    envelope_done = (root / (project.get("artifacts", {}).get("reviewEnvelope") or "review/approval.json")).is_file()
    generated = bool(project.get("generation", {}).get("generated")) or (root / "generated").is_dir()
    verified = (root / (project.get("artifacts", {}).get("verificationReport") or "review/verification.json")).is_file()

    stage, next_action = _derive_stage(
        evidence_files=evidence_files, manifest=manifest, ir=ir, valid=valid,
        required_gaps=required_gaps, review_done=review_done,
        pending_inferred=pending_inferred, pending_unresolved=pending_unresolved,
        envelope_done=envelope_done, stack=stack, generated=generated, verified=verified,
        ir_error=ir_error)

    return {
        "project": project.get("name"),
        "stage": stage,
        "sourcesFound": len(manifest),
        "evidenceFilesUnregistered": unregistered,
        "modelValid": valid,
        "modelReady": ready,
        "requiredGaps": required_gaps,
        "recommendedGaps": recommended_gaps,
        "pendingReview": None if pending_inferred is None else {"inferred": pending_inferred, "unresolved": pending_unresolved},
        "selectedStacks": {"backend": stack.get("backend"), "frontend": stack.get("frontend"), "deployment": stack.get("deployment")},
        "generation": "done" if generated else "not-started",
        "realizationVerified": verified,
        "modelError": ir_error,
        "next": next_action,
    }


def _derive_stage(**s) -> tuple[str, str]:
    """Derive the current stage and the single recommended next action from real state."""
    if s["ir_error"] and not s["manifest"] and not s["evidence_files"]:
        return "evidence", "Add evidence under inputs/, then `kcf sources add <path>`."
    if not s["evidence_files"] and not s["manifest"]:
        return "evidence", "Drop requirements/docs/screenshots/schemas under inputs/, then `kcf sources add <path>`."
    if s["ir"] is None or s["valid"] is False:
        # Evidence present but no valid model yet → still eliciting/authoring.
        if not s["manifest"]:
            return "evidence", "Register your evidence: `kcf sources add inputs/`."
        return "elicitation", "Run `kcf elicit` and have the coding agent author model/*.kcf until it compiles clean."
    if not s["manifest"]:
        return "elicitation", "Register the evidence the model is built from: `kcf sources add inputs/`."
    if not s["review_done"]:
        return "review", "Generate the human-readable review: `kcf review --open`."
    if (s["pending_inferred"] or 0) > 0 or (s["pending_unresolved"] or 0) > 0 or not s["envelope_done"]:
        pend = (s["pending_inferred"] or 0) + (s["pending_unresolved"] or 0)
        return "approval", f"Approve the model ({pend} item(s) pending): `kcf approve --reviewer <you>`."
    if not (s["stack"].get("backend") or s["stack"].get("frontend")):
        return "generation", "Choose a stack and assemble prompts: `kcf generate-plan --backend fastapi-sqlmodel-postgres --frontend react-typescript-openapi`."
    if not s["generated"]:
        return "generation", "Run the assembled prompts in plans/ to generate the app, then `kcf verify-project`."
    if not s["verified"]:
        return "verification", "Verify the generated app: `kcf verify-project`."
    return "verification", "Done — model, code, and verification are in sync. Re-run `kcf verify-project` after any change."


# --------------------------------------------------------------------------- elicit

_AGENT_HEADERS = {
    "generic": "You are a coding agent driving a KCF elicitation.",
    "claude": "You are Claude Code driving a KCF elicitation for this project.",
    "codex": "You are Codex driving a KCF elicitation for this project.",
}


def elicit_prompt(root: Path, agent: str = "generic") -> str:
    project = load_project(root)
    header = _AGENT_HEADERS.get(agent, _AGENT_HEADERS["generic"])
    manifest = project.get("sources", [])
    if manifest:
        inventory = "\n".join(f"  - {e['path']}  ({e['kind']})" for e in manifest)
    else:
        inventory = "  (none registered yet — inventory inputs/ and run `kcf sources add`)"
    model_rel = project.get("model", "model/<Name>.kcf")
    return f"""\
{header}

# KCF elicitation — {project.get('name', 'project')}

Read `START_HERE.md`, `AGENTS.md`, and `kcf.project.json`. Then inventory everything
under `inputs/` and begin KCF elicitation from the registered evidence below. Ask only
the **highest-value unresolved questions**. Do **not** generate application code until
the model is approved (`kcf approve`).

## Registered evidence
{inventory}

## Produce
- a source inventory + a per-source `source-document` and `source-trace`;
- the domain scope and a controlled vocabulary;
- candidate concepts, relationships, and behaviors (commands/queries/lifecycles/rules);
- open questions; and a source trace linking every construct to the evidence that grounds it.

Author the model in `{model_rel}` (the editable semantic truth). Keep it compiling:

    kcf compile {model_rel} -o model/model-ir.json --validate
    kcf status

## Rules
- Treat files under `inputs/` as evidence; never invent domain facts not grounded there.
- Mark anything you propose but cannot ground as **inferred** (for review), never as stated.
- Edit `{model_rel}`; do not hand-edit model-ir.json.
- Stop at a compiling, valid model and hand back for `kcf review`.
"""


# --------------------------------------------------------------------------- review packet

def _humanize(identifier: str) -> str:
    local = identifier.rsplit(".", 1)[-1]
    out, prev = [], ""
    for i, ch in enumerate(local.replace("_", " ").replace("-", " ")):
        if ch == " ":
            out.append(" "); prev = ch; continue
        if i and ch.isupper() and prev and prev.islower():
            out.append(" ")
        out.append(ch); prev = ch
    words = [w for w in "".join(out).split() if w]
    return " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in words) or local


def _concepts_of(ir: dict, kind: str) -> list[dict]:
    return [c for c in ir.get("concepts", []) if c.get("kind") == kind]


def review_packet(root: Path) -> tuple[str, dict]:
    """Build the human-readable review/model-summary.md and return (markdown, meta).

    A person reviews THIS instead of the .kcf or JSON IR: what the app is, its actors,
    records, relationships, workflows, lifecycles, commands/queries, rules, permissions,
    integrations, implied screens, source coverage, inferred knowledge, open questions,
    and the three approval buckets (stated / inferred / unresolved)."""
    project = load_project(root)
    ir, err = load_ir(root, project)
    if ir is None:
        raise ProjectError(err or "no model to review")
    diagnostics = Analyzer(ir).run()
    valid = not any(d["severity"] == "error" for d in diagnostics)
    cov = coverage_report(ir, load_coverage_model())
    gaps = cov["gaps"]
    required = [g for g in gaps if g["level"] == "required"]
    recommended = [g for g in gaps if g["level"] != "required"]
    inferred, unresolved = _pending(ir) if valid else ([], [])
    stated_n = _stated_count(ir) if valid else 0
    doc, trace = _trace_and_document(root, project)
    src = source_coverage(doc, ir, trace) if (doc and trace) else None

    def names(items, key="qualifiedName"):
        return [i.get(key) or i.get("id") for i in items]

    def bullet_list(items):
        return "\n".join(f"- {i}" for i in items) or "- _none_"

    L = []
    L.append(f"# {project.get('name', 'Model')} — model review\n")
    L.append("_Generated by `kcf review`. Review this before inspecting the `.kcf` or the JSON IR._\n")
    L.append(f"**Model valid:** {'yes' if valid else 'NO — fix analyzer errors'}  ·  "
             f"**Required gaps:** {len(required)}  ·  **Recommended:** {len(recommended)}  ·  "
             f"**Pending approval:** {len(inferred)} inferred, {len(unresolved)} unresolved\n")

    L.append("## Application summary\n")
    L.append(f"{project.get('name', 'This application')} is a `{project.get('profile', 'business-application')}` "
             f"model with {len(_concepts_of(ir, 'ENTITY'))} managed record type(s), "
             f"{len(_concepts_of(ir, 'ACTOR'))} actor(s), {len(ir.get('actions', []))} command/query action(s), "
             f"and {len(ir.get('lifecycles', []))} lifecycle(s).\n")

    L.append("## Actors and responsibilities\n")
    L.append(bullet_list([f"**{_humanize(a.get('qualifiedName') or a['id'])}**"
                          + (f" — capabilities: {', '.join(_humanize(c) for c in a.get('capabilities', []))}" if a.get("capabilities") else "")
                          for a in _concepts_of(ir, "ACTOR")]) + "\n")

    L.append("## Managed records\n")
    for e in _concepts_of(ir, "ENTITY"):
        attrs = e.get("attributes", [])
        ids = [a["name"] for a in attrs if a.get("identity")]
        ro = (e.get("metadata") or {}).get("mutability") == "read-only"
        L.append(f"### {_humanize(e.get('qualifiedName') or e['id'])}"
                 + (" _(read-only)_" if ro else ""))
        L.append(bullet_list([f"`{a['name']}`: {a.get('type', '?')}"
                              + (" — identity" if a.get("identity") else "")
                              + (" — required" if a.get("required") else "")
                              for a in attrs]) + "\n")
    if not _concepts_of(ir, "ENTITY"):
        L.append("- _none_\n")

    L.append("## Relationships\n")
    L.append(bullet_list([f"`{r.get('rootKind', r.get('kind', '?'))}` {r.get('source')} → {r.get('target')}"
                          for r in ir.get("relationships", [])]) + "\n")

    L.append("## Commands and queries\n")
    L.append(bullet_list([f"**{_humanize(a.get('id'))}** — `{a.get('operation', '?')}` on {a.get('target', '?')}"
                          + (f" (auth: {a['authorization']})" if a.get("authorization") else "")
                          for a in ir.get("actions", [])]) + "\n")

    L.append("## Workflows and lifecycle diagrams\n")
    if ir.get("lifecycles"):
        for lc in ir["lifecycles"]:
            L.append(f"### {_humanize(lc.get('id'))} — for {lc.get('subject', '?')}")
            L.append("```mermaid\nstateDiagram-v2")
            for t in lc.get("transitions", []):
                frm = t.get("from") or t.get("source") or "?"
                to = t.get("to") or t.get("target") or "?"
                L.append(f"  {frm} --> {to}")
            L.append("```\n")
    else:
        L.append("- _none_\n")

    L.append("## Business rules\n")
    L.append(bullet_list([f"**{_humanize(r.get('id'))}** (`{r.get('ruleKind', '?')}`): {r.get('condition', '')}"
                          for r in ir.get("rules", [])]) + "\n")

    L.append("## Permissions\n")
    L.append(bullet_list([f"**{_humanize(p.get('id'))}** — authority {p.get('authority', '?')}"
                          for p in ir.get("policies", [])]) + "\n")

    L.append("## Integrations\n")
    adapters = (ir.get("integration") or {}).get("adapters", [])
    L.append(bullet_list([f"`{a.get('id')}`" for a in adapters]) + "\n")

    L.append("## Screens implied by the model\n")
    implied = []
    for e in _concepts_of(ir, "ENTITY"):
        n = _humanize(e.get("qualifiedName") or e["id"])
        implied += [f"{n} — list view", f"{n} — detail view"]
    if any(a.get("operation") == "create" for a in ir.get("actions", [])):
        implied.append("Create/edit forms per the create/update commands")
    L.append(bullet_list(implied) + "\n")

    L.append("## Source coverage\n")
    if src is not None:
        pct = round(100 * len(src.get("coveredSegments", [])) / max(1, len(src.get("coveredSegments", [])) + len(src.get("uncoveredSegments", []))))
        L.append(f"- Source-complete: **{source_complete(src)}** (~{pct}% of segments covered)\n")
    else:
        L.append("- _No source document/trace registered — run elicitation with a source trace to measure coverage._\n")

    L.append("## Inferred knowledge (needs approval)\n")
    L.append(bullet_list([f"`{d.get('id')}` ({d.get('tier')}) — {d.get('summary', '')}" for d in inferred]) + "\n")

    L.append("## Unresolved questions\n")
    L.append(bullet_list([f"`{d.get('id')}` — {d.get('summary', '')}" for d in unresolved]) + "\n")

    L.append("## Required gaps\n")
    L.append(bullet_list([f"{g['subject']}: {g['message']}" for g in required]) + "\n")

    L.append("## Recommended enrichment\n")
    L.append(bullet_list([f"{g['subject']}: {g['message']}" for g in recommended]) + "\n")

    L.append("## Approval buckets\n")
    L.append(f"- **Stated** (directly supported, no approval needed): {stated_n}\n"
             f"- **Inferred** (LLM-proposed, needs approval): {len(inferred)}\n"
             f"- **Unresolved** (contradictory / insufficient): {len(unresolved)}\n")
    L.append("\nApprove with, e.g.:\n\n```\nkcf approve --reviewer <you> --confirm <id1>,<id2> --reject <id3>\n"
             "kcf approve --reviewer <you> --all      # confirm every pending inferred item\n```\n")

    md = "\n".join(L)
    meta = {"valid": valid, "requiredGaps": len(required), "inferred": len(inferred),
            "unresolved": len(unresolved), "stated": stated_n}
    return md, meta


def review_html(markdown: str, title: str) -> str:
    """A minimal, dependency-free HTML wrapper so `--open` shows the packet in a browser
    (mermaid blocks render via the CDN script; the Markdown body is shown verbatim in a
    <pre> so the file is self-contained and needs no build step)."""
    import html
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true}});</script>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
pre{{white-space:pre-wrap}}</style></head><body>
<pre>{html.escape(markdown)}</pre></body></html>"""


# --------------------------------------------------------------------------- approve

def approve(root: Path, reviewer: str, *, confirm_ids=None, reject_ids=None,
            confirm_all: bool = False, as_of: str) -> dict:
    """Apply approval decisions and emit a governed IR + a review envelope.

    Composes the review queue (inferred / unresolved), `confirm_synthetic`, and a review
    envelope (the portable, unsigned review-decision contract). Confirm the inferred items
    you name (or every pending inferred item with `confirm_all`); unresolved items are left
    for follow-up unless explicitly named. Directly-supported (stated) constructs are not
    synthetic and need no confirmation. Returns a summary.

    Degrades gracefully: the governed source/model revision helpers and the review-envelope
    builder are used when present, and a minimal inline equivalent otherwise, so the journey
    works against any KCF-OSS build."""
    import hashlib
    from confirm_synthetic import confirm as confirm_synthetic

    project = load_project(root)
    source = _model_path(root, project)
    ir, err = load_ir(root, project)
    if ir is None:
        raise ProjectError(err or "no model to approve")
    if any(d["severity"] == "error" for d in Analyzer(ir).run()):
        raise ProjectError("model is not valid - fix analyzer errors before approving")

    inferred, unresolved = _pending(ir)
    confirm_set = list(confirm_ids or [])
    if confirm_all:
        confirm_set += [d["id"] for d in inferred]
    reject_set = list(reject_ids or [])
    confirm_set = list(dict.fromkeys(confirm_set))

    src_text = source.read_text(encoding="utf-8") if source else ""
    source_rev = "sha256:" + hashlib.sha256(src_text.encode("utf-8")).hexdigest()
    model_rev = "sha256:" + hashlib.sha256(json.dumps(ir, sort_keys=True).encode("utf-8")).hexdigest()
    governed, report = confirm_synthetic(ir, confirm_set, reject_set, reviewer, as_of)

    try:  # the governed review-envelope contract, when this build ships it
        from review_envelope import build_envelope, validate_envelope
        envelope = build_envelope(
            reviewer=reviewer, decision="accept", construct_ids=confirm_set,
            source_revision=source_rev, model_revision=model_rev,
            recorded_at=as_of, rationale="approved via `kcf approve`")
        env_valid = validate_envelope(envelope)["ok"]
    except ImportError:
        envelope = {"reviewEnvelopeVersion": "1.0.0", "reviewer": reviewer,
                    "reviewerRole": None, "authority": None, "decision": "accept",
                    "constructIds": confirm_set, "sourceRevision": source_rev,
                    "modelRevision": model_rev, "recordedAt": as_of,
                    "rationale": "approved via `kcf approve`",
                    "signature": None, "signatureAlgorithm": None}
        env_valid = True

    artifacts = project.setdefault("artifacts", {})
    gov_rel = artifacts.get("governedIr") or "model/model-ir.governed.json"
    env_rel = artifacts.get("reviewEnvelope") or "review/approval.json"
    (root / gov_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / env_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / gov_rel).write_text(json.dumps(governed, indent=2) + "\n", encoding="utf-8")
    (root / env_rel).write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    artifacts["governedIr"] = gov_rel
    artifacts["reviewEnvelope"] = env_rel
    project["governedIr"] = gov_rel
    save_project(root, project)

    remaining_inferred, remaining_unresolved = _pending(governed)
    return {
        "reviewer": reviewer,
        "confirmed": confirm_set,
        "rejected": reject_set,
        "notFound": report.get("notFound", []),
        "envelope": env_rel,
        "governedIr": gov_rel,
        "envelopeValid": env_valid,
        "remaining": {"inferred": len(remaining_inferred), "unresolved": len(remaining_unresolved)},
    }


# --------------------------------------------------------------------------- generate-plan

_TIER_REALIZES = {
    "backend": "persistence, the full action contract (create/read/update/delete/upsert/bulk), "
               "rules/policies, events, org/authority, and an OpenAPI/Swagger interface.",
    "frontend": "list/detail/forms per entity, lifecycle controls, dashboards, and role-gated UI, "
                "generated against the backend's OpenAPI and calling it for everything the server owns.",
    "platform": "the platform's native custom objects, scripts, workflows, and validations.",
}


def generate_plan(root: Path, *, backend: str | None = None, frontend: str | None = None,
                  deployment: str = "docker-compose", instructions: str = "") -> dict:
    """Assemble deterministic backend/frontend codegen prompt packages (CLI exposure of
    the MCP `codegen_prompt` assembly). KCF does not emit code - it packages the durable
    system prompt + governed IR + coverage guidance + the stack's single-shot example
    into a prompt the coding agent runs. Writes plans/<tier>-prompt.md + plans/README.md."""
    import sys
    _kcf_oss = Path(__file__).resolve().parents[1]
    if str(_kcf_oss / "mcp") not in sys.path:
        sys.path.insert(0, str(_kcf_oss / "mcp"))
    from _tools import codegen_prompt  # mcp/_tools.py - lazy import (keeps core light)

    project = load_project(root)
    ir, err = load_ir(root, project, prefer_governed=True)
    if ir is None:
        raise ProjectError(err or "no model to plan from")
    if any(d["severity"] == "error" for d in Analyzer(ir).run()):
        raise ProjectError("model is not valid - fix analyzer errors before planning generation")

    plans_dir = root / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    written, chosen = [], {}
    for tier, stack in (("backend", backend), ("frontend", frontend)):
        if not stack:
            continue
        result = codegen_prompt(source="", stack=stack, instructions=instructions, model_ir=ir)
        if not result.get("ok"):
            raise ProjectError(f"could not assemble the {tier} plan for stack '{stack}': {result.get('error')}")
        rel = f"plans/{tier}-prompt.md"
        prompt = (f"<!-- KCF codegen plan: tier={result.get('tier')} stack={stack}. "
                  "Install the SYSTEM PROMPT as the system message, then send the USER PROMPT. -->\n\n"
                  "# SYSTEM PROMPT\n\n" + result["systemPrompt"]
                  + "\n\n---\n\n# USER PROMPT\n\n" + result["userPrompt"] + "\n")
        (root / rel).write_text(prompt, encoding="utf-8")
        written.append(rel)
        chosen[tier] = stack

    cov = coverage_report(ir, load_coverage_model())["gaps"]
    required = [g for g in cov if g["level"] == "required"]
    recommended = [g for g in cov if g["level"] != "required"]

    readme = [f"# Generation plan - {project.get('name', 'project')}\n",
              "Run each prompt below with your coding agent (backend first, then frontend).",
              "KCF assembled them; it does not emit the code itself.\n"]
    for tier in ("backend", "frontend"):
        if tier in chosen:
            readme.append(f"## {tier.title()} - `{chosen[tier]}`  -> `plans/{tier}-prompt.md`")
            readme.append(f"Will realize: {_TIER_REALIZES[tier]}\n")
    readme.append(f"## Deployment\n{deployment}\n")
    readme.append("## Remaining recommended gaps\n"
                  + ("\n".join(f"- {g['subject']}: {g['message']}" for g in recommended) or "- none") + "\n")
    readme.append("## Required gaps (should be 0 before generating)\n"
                  + ("\n".join(f"- {g['subject']}: {g['message']}" for g in required) or "- none") + "\n")
    readme.append("Unsupported constructs and delegated platform concerns are reported by each "
                  "prompt's coverage self-audit when you run it; verify with `kcf verify-project`.\n")
    (plans_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")
    written.append("plans/README.md")

    stack = project.setdefault("stack", {})
    stack.update({"backend": backend, "frontend": frontend, "deployment": deployment})
    project.setdefault("artifacts", {})["plans"] = "plans/"
    save_project(root, project)
    return {"written": written, "stacks": chosen, "deployment": deployment,
            "requiredGaps": len(required), "recommendedGaps": len(recommended)}


# --------------------------------------------------------------------------- verify-project

def verify_project(root: Path) -> dict:
    """Combined project verification: compile + assess + source coverage + pending-review
    check + semantic delta (governed vs current) + realization verification + model/code
    drift. Produces the final report card the six-stage journey ends on."""
    project = load_project(root)
    checks: dict = {}
    ir, err = load_ir(root, project)
    if ir is None:
        return {"ok": False, "error": err, "checks": checks}

    diagnostics = Analyzer(ir).run()
    valid = not any(d["severity"] == "error" for d in diagnostics)
    checks["modelValid"] = valid
    verdict = assess_model(ir) if valid else {"ready": False}
    cov = coverage_report(ir, load_coverage_model())["summary"]
    checks["requiredGaps"] = cov["required"]
    checks["modelReady"] = verdict.get("ready")

    doc, trace = _trace_and_document(root, project)
    if doc and trace:
        src = source_coverage(doc, ir, trace)
        total = len(src.get("coveredSegments", [])) + len(src.get("uncoveredSegments", []))
        checks["sourceCoveragePct"] = round(100 * len(src.get("coveredSegments", [])) / max(1, total))
        checks["sourceComplete"] = source_complete(src)
    else:
        checks["sourceCoveragePct"] = None
        checks["sourceComplete"] = None

    if valid:
        inferred, unresolved = _pending(ir)
        checks["pendingReview"] = {"inferred": len(inferred), "unresolved": len(unresolved)}
    else:
        checks["pendingReview"] = None

    # Model/code drift: the governed (approved) IR vs the current compiled IR. A non-empty
    # semantic delta means the editable model changed since approval and must be re-reviewed.
    gov_rel = (project.get("artifacts") or {}).get("governedIr") or project.get("governedIr")
    if gov_rel and (root / gov_rel).is_file():
        governed = json.loads((root / gov_rel).read_text(encoding="utf-8"))
        delta = semantic_compare(governed, ir)
        n = sum(len(v) for v in delta.values()) if isinstance(delta, dict) else len(delta or [])
        checks["driftFromApproved"] = n
        checks["delta"] = delta
    else:
        checks["driftFromApproved"] = None

    # Realization verification, if the agent produced a manifest.
    manifest_rel = (project.get("artifacts") or {}).get("realizationManifest") or "generated/realization-manifest.json"
    if (root / manifest_rel).is_file():
        from verify_realization import verify as verify_realization
        manifest = json.loads((root / manifest_rel).read_text(encoding="utf-8"))
        repo = (root / "generated") if (root / "generated").is_dir() else None
        realization = verify_realization(ir, manifest, repo)
        checks["realizationAccounted"] = realization.get("ok")
    else:
        checks["realizationAccounted"] = None

    ok = bool(valid and cov["required"] == 0
              and (checks["pendingReview"] or {"inferred": 0, "unresolved": 0}) == {"inferred": 0, "unresolved": 0}
              and (checks["driftFromApproved"] in (0, None))
              and (checks["realizationAccounted"] in (True, None)))
    result = {"ok": ok, "checks": checks}

    artifacts = project.setdefault("artifacts", {})
    report_rel = artifacts.get("verificationReport") or "review/verification.json"
    (root / report_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / report_rel).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    artifacts["verificationReport"] = report_rel
    save_project(root, project)
    return result


def report_card(result: dict) -> str:
    """Render verify_project() as the one final report the user reads."""
    c = result.get("checks", {})
    def yn(v):
        return "Yes" if v is True else "No" if v is False else "-"
    pend = c.get("pendingReview") or {}
    lines = [
        f"Model valid:                 {yn(c.get('modelValid'))}",
        f"Required gaps:               {c.get('requiredGaps', '-')}",
        f"Source coverage:             {('%d%%' % c['sourceCoveragePct']) if c.get('sourceCoveragePct') is not None else '-'}",
        f"Unresolved decisions:        {pend.get('unresolved', '-')}",
        f"Pending inferred items:      {pend.get('inferred', '-')}",
        f"Realization accounted:       {yn(c.get('realizationAccounted')) if c.get('realizationAccounted') is not None else '-'}",
        f"Model/code drift:            {'None' if c.get('driftFromApproved') in (0, None) else c.get('driftFromApproved')}",
        f"Overall:                     {'PASS' if result.get('ok') else 'NOT READY'}",
    ]
    return "\n".join(lines)
