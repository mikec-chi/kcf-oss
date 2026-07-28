"""Coverage of the coverage system (meta-coverage).

The coverage model (config/coverage-model.json) declares, per profile, the
obligations a domain model should satisfy. But which grammar *construct families*
does the coverage model itself say anything about? A family with no obligation is a
blind spot: a model can omit that whole dimension and never trip a gap. That blind
spot must be visible, not silent.

This tool enumerates the grammar's construct families (from grammar-stack.json,
minus the meta/tooling modules) and, for each, reports whether the coverage model
declares an obligation for it - with a registered evaluator and, ideally, fixtures.
Families with no obligation are reported as ``coverage-policy-missing``. The point is
honesty about the reach of the coverage system, not a demand that every dimension be
covered: some (emitter/advisory dimensions) legitimately have no completeness policy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from coverage_report import EVALUATORS, load_coverage_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_STACK = PROJECT_ROOT / "config" / "grammar-stack.json"


def _run_obligation(model: dict, obligation: dict) -> list:
    """Run one obligation's evaluator in isolation and return its gaps."""
    return EVALUATORS[obligation["obligation"]](model, obligation)


def verify_obligation_fixtures(coverage_model: dict, root: Path | None = None) -> dict:
    """For every obligation that declares fixtures, prove the obligation→evaluator→
    positive→negative chain actually holds: each 'satisfied' fixture must produce NO
    gap for the obligation, and each 'violated' fixture must produce one. This is what
    turns a declared fixture reference into demonstrated coverage-governance - a
    fixture that does not actually exercise the obligation is caught here."""
    root = root or PROJECT_ROOT
    results: dict[str, dict] = {}
    for obligation in coverage_model["obligations"]:
        fixtures = obligation.get("fixtures")
        if not fixtures:
            continue
        satisfied = fixtures.get("satisfied", [])
        violated = fixtures.get("violated", [])

        def _gaps(path: str) -> list:
            model = json.loads((root / path).read_text(encoding="utf-8"))
            return _run_obligation(model, obligation)

        positive_verified = bool(satisfied) and all(not _gaps(path) for path in satisfied)
        negative_verified = bool(violated) and all(_gaps(path) for path in violated)
        results[obligation["id"]] = {
            "fixtureDeclared": True,
            "positiveFixtureVerified": positive_verified,
            "negativeFixtureVerified": negative_verified,
            "regressionGateIncluded": positive_verified and negative_verified,
        }
    return results

# Modules that are meta/tooling rather than domain construct families - they carry no
# domain content a model could be "incomplete" about, so they are not meta-coverage
# families.
_NON_FAMILY_MODULES = {"KCF", "COMPILATION", "AUTHORING"}


def construct_families(stack: dict | None = None) -> list[str]:
    stack = stack or json.loads(GRAMMAR_STACK.read_text(encoding="utf-8"))
    return sorted(name for name in stack["modules"] if name not in _NON_FAMILY_MODULES)


def meta_coverage(coverage_model: dict, families: list[str] | None = None, verify_fixtures: bool = False, root: Path | None = None) -> dict:
    families = families if families is not None else construct_families()
    family_set = set(families)
    obligations = coverage_model["obligations"]

    fixture_results = verify_obligation_fixtures(coverage_model, root) if verify_fixtures else {}

    by_family: dict[str, list[dict]] = {family: [] for family in families}
    orphans: list[str] = []
    for obligation in obligations:
        dimension = obligation.get("dimension")
        if dimension in family_set:
            by_family[dimension].append(obligation)
        else:
            orphans.append(obligation["id"])

    # A family with no obligation is not necessarily a blind spot: coverage-model may
    # declare an explicit policy decision (conditional / intentionally-none) for it.
    # Only a family with neither obligations nor a declared decision is truly missing.
    family_policies = {name: policy for name, policy in coverage_model.get("familyPolicies", {}).items()
                       if name != "_comment"}

    rows = []
    without_policy = []
    for family in families:
        items = by_family[family]
        required = sum(1 for item in items if item["level"] == "required")
        recommended = sum(1 for item in items if item["level"] == "recommended")
        has_evaluator = all(item["obligation"] in EVALUATORS for item in items)
        has_fixtures = any(item.get("fixtures") for item in items)
        gated = any(fixture_results.get(item["id"], {}).get("regressionGateIncluded") for item in items)
        policy = family_policies.get(family)
        if items:
            status, reason = "covered", None
        elif policy:
            status, reason = policy["decision"], policy["reason"]
        else:
            status, reason = "coverage-policy-missing", None
            without_policy.append(family)
        rows.append({
            "family": family,
            "obligations": len(items),
            "required": required,
            "recommended": recommended,
            "hasEvaluator": has_evaluator,
            "hasFixtures": has_fixtures,
            "regressionGated": gated,
            "obligationIds": [item["id"] for item in items],
            "status": status,
            "policyReason": reason,
        })

    with_fixtures = [obligation["id"] for obligation in obligations if obligation.get("fixtures")]
    report = {
        "coverageMetaReportVersion": "1.0.0",
        "totalFamilies": len(families),
        "withPolicy": len(families) - len(without_policy),
        "withoutPolicy": without_policy,
        "orphanObligations": sorted(orphans),
        "families": rows,
        "fixtureGovernance": {
            "obligations": len(obligations),
            "fixtureDeclared": len(with_fixtures),
            "verified": verify_fixtures,
            "positiveVerified": sum(1 for result in fixture_results.values() if result["positiveFixtureVerified"]),
            "negativeVerified": sum(1 for result in fixture_results.values() if result["negativeFixtureVerified"]),
            "regressionGateIncluded": sorted(oid for oid, result in fixture_results.items() if result["regressionGateIncluded"]),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Report meta-coverage: which grammar construct families have a coverage policy.")
    parser.add_argument("--coverage-model", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any construct family has no coverage policy")
    parser.add_argument("--verify-fixtures", action="store_true", help="run each obligation's declared positive/negative fixtures")
    args = parser.parse_args()

    coverage_model = load_coverage_model(args.coverage_model) if args.coverage_model else load_coverage_model()
    report = meta_coverage(coverage_model, verify_fixtures=args.verify_fixtures)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.strict and report["withoutPolicy"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
