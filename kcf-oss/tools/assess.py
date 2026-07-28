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


def assess(model: dict) -> dict:
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
        "domainComplete": "not-proven",
        "checks": checks,
    }


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
