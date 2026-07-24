"""Prove, from model structure, that claimed and required patterns are modelled.

A profile can declare that it requires patterns (``requiredPatterns``) and a
model author can claim to implement patterns (``implementedPatterns``). Today the
analyzer only checks that those *claims* are consistent. This tool checks the
*structure*: it evaluates each pattern's contract - a set of testable
obligations - against the normalized IR and reports, independently of the
author's claim (decision D-008), whether the pattern is actually present.

The engine is domain-agnostic. It contains no knowledge of any particular
pattern; every pattern is defined by data - a contract file whose obligations
reference roles by trait and kind, evaluated by the same obligation engine as the
coverage reporter. Contracts are discovered on a search path
(``KCF_PATTERN_CONTRACT_PATH``) so an overlay stack can add domain contracts that
the open-source engine evaluates without change.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from coverage_report import EVALUATORS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_ROOT = PROJECT_ROOT / "config" / "pattern-contracts"


def contract_roots() -> list[Path]:
    """Ordered contract search path. Directories in KCF_PATTERN_CONTRACT_PATH are
    searched before this stack's own contracts, so an overlay stack can supply
    domain-specific contracts to the domain-agnostic engine."""
    roots: list[Path] = []
    for entry in os.environ.get("KCF_PATTERN_CONTRACT_PATH", "").split(os.pathsep):
        entry = entry.strip()
        if entry:
            roots.append(Path(entry))
    roots.append(CONTRACTS_ROOT)
    return roots


def load_contracts() -> dict[str, dict]:
    """Load every contract on the search path, keyed by patternId. Earlier roots
    win, so an overlay may override a foundational contract."""
    contracts: dict[str, dict] = {}
    for root in contract_roots():
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            contract = json.loads(path.read_text(encoding="utf-8"))
            contracts.setdefault(contract["patternId"], contract)
    return contracts


def evaluate_pattern(model: dict, contract: dict) -> list[dict]:
    return [gap for obligation in contract["obligations"] for gap in EVALUATORS[obligation["obligation"]](model, obligation)]


# --- role vocabulary: the explicit interface between a pattern library and an
# --- organization's instance model ---------------------------------------------

def contract_role_errors(contract: dict) -> list[str]:
    """A contract must declare (in its `roles`) every trait its own obligations
    reference. This keeps each pattern's public interface complete and explicit."""
    declared = {role["trait"] for role in contract.get("roles", [])}
    errors = []
    for obligation in contract["obligations"]:
        trait = obligation.get("trait")
        if trait is not None and trait not in declared:
            errors.append(f"{contract['patternId']}: obligation {obligation['id']} uses undeclared role trait {trait!r}")
    return errors


def declared_roles(contracts: dict[str, dict]) -> dict[str, list[str]]:
    """Map every declared role trait to the pattern ids that declare it, across
    the whole loaded library set (the vocabulary an instance may draw on)."""
    roles: dict[str, set[str]] = {}
    for pattern_id, contract in contracts.items():
        for role in contract.get("roles", []):
            roles.setdefault(role["trait"], set()).add(pattern_id)
    return {trait: sorted(patterns) for trait, patterns in roles.items()}


def instance_traits(model: dict) -> dict[str, list[str]]:
    """Map each trait used on a concept to the concept identities that carry it."""
    usage: dict[str, list[str]] = {}
    for concept in model.get("concepts", []):
        identity = concept.get("qualifiedName") or concept.get("id")
        for trait in concept.get("traits") or []:
            usage.setdefault(trait, []).append(identity)
    return usage


def role_report(model: dict, contracts: dict[str, dict]) -> dict:
    """Check an instance's concept traits against the loaded role vocabulary.

    ``unknownTraits`` are traits the instance uses that no loaded pattern library
    declares - the boundary violations between organizational knowledge and the
    pattern libraries it claims to draw on."""
    declared = declared_roles(contracts)
    usage = instance_traits(model)
    return {
        "roleReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "declaredRoles": [{"trait": trait, "patterns": declared[trait]} for trait in sorted(declared)],
        "usage": [
            {"trait": trait, "concepts": sorted(usage[trait]), "declaredBy": declared.get(trait, [])}
            for trait in sorted(usage)
        ],
        "unknownTraits": sorted(trait for trait in usage if trait not in declared),
    }


def report(model: dict, contracts: dict[str, dict], pattern_ids: list[str] | None = None) -> dict:
    required = set(model.get("requiredPatterns", []))
    recommended = set(model.get("recommendedPatterns", []))
    claimed = set(model.get("implementedPatterns", []))
    scope = set(pattern_ids) if pattern_ids is not None else (required | recommended | claimed)

    results = []
    for pattern_id in sorted(scope):
        contract = contracts.get(pattern_id)
        entry = {
            "patternId": pattern_id,
            "hasContract": contract is not None,
            "required": pattern_id in required,
            "recommended": pattern_id in recommended,
            "claimed": pattern_id in claimed,
        }
        if contract is None:
            entry["status"] = "no-contract"
            entry["gaps"] = []
        else:
            gaps = evaluate_pattern(model, contract)
            entry["gaps"] = gaps
            entry["status"] = "incomplete" if any(gap["level"] == "required" for gap in gaps) else "satisfied"
        results.append(entry)

    summary = {
        "satisfied": sum(1 for entry in results if entry["status"] == "satisfied"),
        "incomplete": sum(1 for entry in results if entry["status"] == "incomplete"),
        "noContract": sum(1 for entry in results if entry["status"] == "no-contract"),
        "claimedButUnproven": sorted(entry["patternId"] for entry in results if entry["claimed"] and entry["status"] == "incomplete"),
        "requiredButAbsent": sorted(entry["patternId"] for entry in results if entry["required"] and entry["status"] == "incomplete"),
        "requiredWithoutContract": sorted(entry["patternId"] for entry in results if entry["required"] and entry["status"] == "no-contract"),
    }
    return {
        "patternReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "patternsChecked": sorted(scope),
        "results": results,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that a KCF model structurally satisfies its claimed and required pattern contracts.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--patterns", help="comma-separated pattern IDs to check instead of the model's own required/claimed sets")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    pattern_ids = [item for item in args.patterns.split(",") if item] if args.patterns else None
    result = report(model, load_contracts(), pattern_ids)

    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    summary = result["summary"]
    return 1 if (summary["claimedButUnproven"] or summary["requiredButAbsent"] or summary["requiredWithoutContract"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
