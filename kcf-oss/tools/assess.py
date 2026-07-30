"""One unified readiness verdict for a model IR.

Simplification B: the self-check loop needs validity AND completeness AND pattern
proof AND role resolution. Rather than running four tools and reconciling four
outputs, this composes them into one report with a single ``ready`` verdict and a
single exit code. It adds no new checking logic - it calls the existing engines.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from coverage_report import load_coverage_model, report as coverage_report
from pattern_contracts import load_contracts, report as pattern_report, role_report
from semantic_analyzer import Analyzer


def _behavioural_completeness(model: dict, diagnostics: list) -> dict:
    """An honest, SEPARATE axis: is the behavioural half of the model machine-realizable,
    or will it only scaffold? Reported ALONGSIDE `ready` (which means structurally
    buildable), never folded into it - the mirror of `domainComplete: not-proven`. A
    structural gate cannot distinguish a model that generates an application from one that
    generates a skeleton; this makes the difference visible. (Report
    no-behavioural-coverage-obligations-20260729-12.)"""
    rules = model.get("rules", [])
    parsed = sum(1 for rule in rules if isinstance(rule.get("condition"), dict))
    invoke = [a for a in model.get("actions", []) if a.get("operation") == "invoke"]
    with_procedure = sum(1 for a in invoke if a.get("procedure"))
    formulas = model.get("math", [])
    measures = [c for c in model.get("concepts", []) if c.get("kind") == "MEASURE"]
    unresolved_operands = sum(1 for d in diagnostics
                              if d.get("rule_id") == "kcf.math.reference" and d.get("severity") == "warning")
    present = bool(rules or invoke or formulas)
    realizable = present and parsed == len(rules) and with_procedure == len(invoke) and unresolved_operands == 0
    status = "not-applicable" if not present else "realizable" if realizable else "not-proven"
    return {
        "status": status,
        "rules": {"withParsedCondition": parsed, "total": len(rules)},
        "invokeActions": {"withProcedure": with_procedure, "total": len(invoke)},
        "formulas": len(formulas),
        "measures": len(measures),
        "expressionOperandsUnresolved": unresolved_operands,
        "note": ("Reported separately from `ready` (structurally buildable). `not-proven` "
                 "means the behavioural half is present but not machine-realizable as "
                 "declared, so code generation will scaffold it: rule conditions are opaque "
                 "strings (IR-ROADMAP RFC-13) and invoke actions carry no procedure "
                 "(RFC-14). Not folded into `ready`."),
    }


def assess(model: dict, source_coverage: dict | None = None) -> dict:
    diagnostics = Analyzer(model).run()
    error_ids = sorted({item["rule_id"] for item in diagnostics if item["severity"] == "error"})
    valid = not error_ids

    coverage = coverage_report(model, load_coverage_model())
    contracts = load_contracts()
    patterns = pattern_report(model, contracts)
    roles = role_report(model, contracts)

    checks = {
        "validity": {"valid": valid, "errorRuleIds": error_ids},
        "coverage": {
            "requiredGaps": coverage["summary"]["required"],
            "recommendedGaps": coverage["summary"]["recommended"],
            "requiredGapIds": sorted({gap["gapId"] for gap in coverage["gaps"] if gap["level"] == "required"}),
        },
        "patterns": {
            "satisfied": patterns["summary"]["satisfied"],
            "requiredButAbsent": patterns["summary"]["requiredButAbsent"],
            "claimedButUnproven": patterns["summary"]["claimedButUnproven"],
            "requiredWithoutContract": patterns["summary"]["requiredWithoutContract"],
        },
        "roles": {"unknownTraits": roles["unknownTraits"]},
    }
    ready = (
        valid
        and checks["coverage"]["requiredGaps"] == 0
        and not checks["patterns"]["requiredButAbsent"]
        and not checks["patterns"]["claimedButUnproven"]
        and not checks["patterns"]["requiredWithoutContract"]
        and not checks["roles"]["unknownTraits"]
    )

    # Richer verdict than a lone boolean (D-roadmap P1): the single `ready` flag is
    # lossy - it cannot distinguish "empty envelope" from "one recommended gap
    # away". These three axes report *what kind* of readiness holds without
    # overclaiming. `domainComplete` is always "not-proven": coverage is a
    # necessary, never a sufficient, condition for real domain completeness - the
    # obligations prove structure is present, not that the domain was fully
    # captured. That remains a human judgement (see P2 scope / P5 source-confirmed).
    required_gap_ids = set(checks["coverage"]["requiredGapIds"])
    if not valid:
        coverage_status = "invalid"
    elif "coverage.model.substantive-content" in required_gap_ids:
        coverage_status = "no-substantive-content"
    elif checks["coverage"]["requiredGaps"] or not ready:
        coverage_status = "anchors-missing"
    elif checks["coverage"]["recommendedGaps"]:
        coverage_status = "required-obligations-met"
    else:
        coverage_status = "profile-obligations-complete"

    if ready:
        ready_for = ["codegen-handoff", "review"]
    elif valid:
        ready_for = ["review"]
    else:
        ready_for = []

    return {
        "assessReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "valid": valid,
        "ready": ready,
        "coverageStatus": coverage_status,
        "readyFor": ready_for,
        "readinessLadder": _readiness_ladder(valid, ready, checks, source_coverage),
        # Operational/deployment readiness (security review, data migration, deployment, production
        # evidence) is out of scope for KCF-OSS and is NOT enumerated here — an external assurance
        # overlay owns and evaluates that ladder. This is the honest de-overclaim of `ready`.
        "deploymentReadiness": "not-evaluated-here",
        "domainComplete": "not-proven",
        "behaviourallyComplete": _behavioural_completeness(model, diagnostics),
        "checks": checks,
    }


# The readiness LADDER (D-roadmap P1 / weakness #8): `ready: true` reads to an ordinary user as
# "production ready", but KCF-OSS only proves MODEL-VALIDITY readiness (it compiled, it is valid, its
# obligations are met, its source is linked/confirmed). KCF-OSS enumerates ONLY the model-validity
# rungs — the ones derivable from the open toolchain (compile/analyze/coverage/source-trace). Anything
# beyond codegen-handoff — security review, data-migration review, deployment review, production
# evidence — is an OPERATIONAL assurance/deployment progression that KCF-OSS neither owns nor evaluates;
# it is signalled generically (see `deploymentReadiness`) and left to an external assurance overlay,
# which defines and evaluates its own ladder. KCF-OSS does not publish that operational taxonomy.
_MODEL_VALIDITY_RUNGS = ("syntax-ready", "semantic-ready", "coverage-ready",
                         "source-linked", "source-confirmed", "codegen-ready")


def _readiness_ladder(valid: bool, ready: bool, checks: dict, source_coverage: dict | None) -> list:
    """Report each MODEL-VALIDITY readiness rung with its satisfied/unsatisfied evidence. Operational/
    deployment readiness is out of scope for KCF-OSS (see `deploymentReadiness` in the report)."""
    def rung(level, satisfied, unsatisfied):
        return {"level": level, "scope": "model-validity", "satisfied": bool(satisfied),
                "unsatisfied": list(unsatisfied)}

    ladder = []
    # syntax-ready: we hold a compiled IR, so it parsed. (assess() receives an already-compiled model.)
    ladder.append(rung("syntax-ready", True, []))
    # semantic-ready: no analyzer errors.
    ladder.append(rung("semantic-ready", valid,
                       [] if valid else [f"analyzer error: {rid}" for rid in checks["validity"]["errorRuleIds"]]))
    # coverage-ready: required obligations met + patterns proven + roles resolved.
    cov_unmet = []
    if checks["coverage"]["requiredGaps"]:
        cov_unmet += [f"required gap: {gid}" for gid in checks["coverage"].get("requiredGapIds", [])]
    cov_unmet += [f"pattern absent: {p}" for p in checks["patterns"]["requiredButAbsent"]]
    cov_unmet += [f"pattern unproven: {p}" for p in checks["patterns"]["claimedButUnproven"]]
    cov_unmet += [f"pattern without contract: {p}" for p in checks["patterns"]["requiredWithoutContract"]]
    cov_unmet += [f"unknown role trait: {t}" for t in checks["roles"]["unknownTraits"]]
    ladder.append(rung("coverage-ready", ready and not cov_unmet, cov_unmet))
    # source-linked / source-confirmed: require a source-coverage report; if none was provided, the
    # evidence is simply absent (not failed) - reported honestly as unsatisfied-for-lack-of-evidence.
    if source_coverage is None:
        ladder.append(rung("source-linked", False,
                           ["no source-coverage report provided (run source_coverage)"]))
        ladder.append(rung("source-confirmed", False,
                           ["no source-coverage report provided (run source_coverage)"]))
    else:
        linked = bool(source_coverage.get("sourceComplete"))
        confirmed = bool(source_coverage.get("sourceConfirmed"))
        ladder.append(rung("source-linked", linked,
                           [] if linked else [f"uncovered: {u}" for u in source_coverage.get("uncoveredSegments", [])[:5]]
                           + [f"unsourced: {u}" for u in source_coverage.get("unsourcedConstructs", [])[:5]]))
        ladder.append(rung("source-confirmed", confirmed,
                           [] if confirmed else ["source linkage present but not governed-confirmed"]))
    # codegen-ready: the OSS handoff bar == `ready` (valid + coverage). This is the ceiling KCF-OSS proves.
    ladder.append(rung("codegen-ready", ready, [] if ready else ["model not yet `ready`"]))
    return ladder


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess a KCF model's readiness (validity, coverage, pattern proof, roles) in one report.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    result = assess(model)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
