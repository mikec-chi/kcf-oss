"""Multi-axis, closed-world completeness for a KCF model.

`assess` answers "is this model ready?" as a readiness verdict. Completeness is a
different, larger question - "have we captured everything we said we would?" - and
it is only meaningful against a *declared scope*. This tool composes the existing
engines (analyzer, coverage/assess, pattern proof, source coverage) and adds a
declared-scope axis: every capability the scope says is in-scope must map to at
least one model construct.

It reports the axes SEPARATELY rather than collapsing them to one boolean, and its
one summary flag - `closedWorldComplete` - is explicit that "complete" means
*against the declared scope*, never against an open world. Nothing here is
domain-specific: capabilities are matched to constructs by identity/trait/capability
string, so it works for any domain.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from assess import assess
from pattern_contracts import load_contracts, report as pattern_report
from semantic_analyzer import Analyzer
from source_coverage import is_complete as source_complete, source_coverage


def _model_capability_terms(model: dict) -> set[str]:
    """Every string a declared capability could reasonably map to: concept
    identities/traits/capabilities/skills, and the identities of behavior/knowledge
    constructs. Domain-agnostic - it reads structure, never domain vocabulary.

    Both the namespace-qualified form AND the bare local name are indexed: a capability
    authored as ``capability procure_to_pay;`` lands on the concept as
    ``cap.procure_to_pay``, so a scope naming the identical token the author typed
    (``procure_to_pay``) must still match. Indexing only the qualified form forced a
    stakeholder scope to restate internal identities to be coverable."""
    terms: set[str] = set()

    def add(value: object) -> None:
        if isinstance(value, str) and value:
            terms.add(value)
            if "." in value:
                terms.add(value.rsplit(".", 1)[-1])  # also the bare local name

    for concept in model.get("concepts", []):
        for field in ("qualifiedName", "id"):
            add(concept.get(field))
        for listed in ("traits", "capabilities", "skills"):
            for value in concept.get(listed) or []:
                add(value)
    for collection in ("actions", "processes", "capabilities", "skills", "rules", "policies", "events", "organizations"):
        for item in model.get(collection, []):
            if isinstance(item, dict):
                for field in ("qualifiedName", "id", "name"):
                    add(item.get(field))
    return terms


def _covers(capability: str, terms: set[str], lowered: set[str]) -> bool:
    return capability in terms or capability.lower() in lowered


def completeness(model: dict, scope: dict, document: dict | None = None, trace: dict | None = None) -> dict:
    diagnostics = Analyzer(model).run()
    errors = [item for item in diagnostics if item["severity"] == "error"]
    warnings = [item for item in diagnostics if item["severity"] == "warning"]

    verdict = assess(model)
    contracts = load_contracts()
    patterns = pattern_report(model, contracts)

    terms = _model_capability_terms(model)
    lowered = {term.lower() for term in terms}
    included = scope.get("includedCapabilities", [])
    covered = [capability for capability in included if _covers(capability, terms, lowered)]
    uncovered = [capability for capability in included if not _covers(capability, terms, lowered)]
    excluded = list(scope.get("excludedCapabilities", []))
    open_questions = list(scope.get("openQuestions", []))
    declared_sources = list(scope.get("sourceDocuments", []))

    # Source axis (R1). A scope that names its sources must have those sources
    # *evaluated* before it can be closed-world complete - declaring a provenance and
    # then supplying no evidence for it must NOT pass. States:
    #   not-applicable        - no sources declared; the axis does not gate completeness
    #   declared-not-evaluated- sources declared but no document/trace supplied -> blocks
    #   evaluated-complete     - evaluated, linkage complete
    #   evaluated-incomplete   - evaluated, linkage gaps -> blocks
    if document is not None and trace is not None:
        source_report = source_coverage(document, model, trace)
        source_complete_flag = bool(source_complete(source_report))
        source_axis = {
            "evaluated": True,
            "status": "evaluated-complete" if source_complete_flag else "evaluated-incomplete",
            "sourceComplete": source_complete_flag,
            "sourceConfirmed": bool(source_report.get("sourceConfirmed")),
            "sourceDocuments": declared_sources,
        }
    elif declared_sources:
        source_axis = {
            "evaluated": False,
            "status": "declared-not-evaluated",
            "sourceComplete": None,
            "sourceConfirmed": None,
            "sourceDocuments": declared_sources,
        }
    else:
        source_axis = {
            "evaluated": False,
            "status": "not-applicable",
            "sourceComplete": None,
            "sourceConfirmed": None,
            "sourceDocuments": [],
        }

    required_absent = list(patterns["summary"]["requiredButAbsent"])
    claimed_unproven = list(patterns["summary"]["claimedButUnproven"])

    # A meaningful closed-world scope must declare at least one capability, UNLESS it
    # explicitly declares a vocabulary/package scope (R2) - otherwise an empty scope
    # would trivially be "complete" while covering nothing.
    scope_kind = scope.get("packageKind")
    scope_meaningful = bool(included) or scope_kind in {"vocabulary", "package"}

    # Explicit blockers make "not complete" say WHY (more honest than a bare boolean).
    blockers: list[str] = []
    if not verdict["valid"]:
        blockers.append("structural-invalid")
    if verdict["checks"]["coverage"]["requiredGaps"]:
        blockers.append("required-coverage-gaps")
    if required_absent:
        blockers.append("required-patterns-absent")
    if claimed_unproven:
        blockers.append("patterns-claimed-unproven")
    if not scope_meaningful:
        blockers.append("empty-scope")
    if uncovered:
        blockers.append("scope-capabilities-uncovered")
    if open_questions:
        blockers.append("open-questions")
    if source_axis["status"] == "declared-not-evaluated":
        blockers.append("sources-declared-not-evaluated")
    elif source_axis["status"] == "evaluated-incomplete":
        blockers.append("source-incomplete")

    return {
        "completenessReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "closedWorldComplete": not blockers,
        "blockers": blockers,
        "axes": {
            "structural": {"valid": verdict["valid"], "errors": len(errors), "warnings": len(warnings)},
            "profile": {
                "satisfied": patterns["summary"]["satisfied"],
                "requiredButAbsent": required_absent,
                "claimedButUnproven": claimed_unproven,
            },
            "coverage": {
                "requiredGaps": verdict["checks"]["coverage"]["requiredGaps"],
                "recommendedGaps": verdict["checks"]["coverage"]["recommendedGaps"],
                "coverageStatus": verdict.get("coverageStatus", ""),
            },
            "declaredScope": {
                "declared": len(included),
                "meaningful": scope_meaningful,
                "covered": covered,
                "uncovered": uncovered,
                "excluded": excluded,
            },
            "source": source_axis,
            "openQuestions": open_questions,
            "unsupportedAreas": excluded,
            "boundaries": list(scope.get("declaredBoundaries", [])),
            "stakeholders": list(scope.get("stakeholders", [])),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report multi-axis, closed-world completeness for a KCF model against a declared scope.")
    parser.add_argument("model", type=Path)
    parser.add_argument("scope", type=Path)
    parser.add_argument("--document", type=Path, help="source document (with --trace, enables the source-fidelity axis)")
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    document = json.loads(args.document.read_text(encoding="utf-8")) if args.document else None
    trace = json.loads(args.trace.read_text(encoding="utf-8")) if args.trace else None
    report = completeness(model, scope, document, trace)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    # Make an uncovered capability actionable: name the nearest available term so the
    # operator sees WHY it did not match (usually a qualified/local-name or phrasing
    # mismatch) instead of guessing. Advisory only — it does not change the report or the
    # exit code.
    uncovered = report["axes"]["declaredScope"]["uncovered"]
    if uncovered:
        terms = sorted(_model_capability_terms(model))
        for capability in uncovered:
            near = difflib.get_close_matches(capability, terms, n=1, cutoff=0.6)
            hint = f" (nearest model term: {near[0]!r})" if near else " (no close model term; includedCapabilities must be construct identities — a bare or namespace-qualified name)"
            print(f"warning: scope capability {capability!r} matches no model construct{hint}", file=sys.stderr)
    return 0 if report["closedWorldComplete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
