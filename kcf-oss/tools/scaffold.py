"""Produce a single pattern-seeding scaffold from a profile and/or pattern set.

Simplification A: instead of resolving a profile and then separately reading each
pattern contract, this aggregates both into one artifact an LLM can consume in a
single step - the modules in play, the required/recommended/prohibited patterns,
the roles (traits) to fulfil, and the obligations to satisfy.

Domain-agnostic: it resolves any profile (via KCF_PRESET_PATH) and loads any
contracts (via KCF_PATTERN_CONTRACT_PATH); it contains no pattern-specific logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pattern_contracts import load_contracts
from profile_resolver import ProfileError, resolve_profile


def build_scaffold(profile: str | None, extra_patterns: list[str] | None, contracts: dict[str, dict]) -> dict:
    modules: list[str] = []
    required: list[str] = []
    recommended: list[str] = []
    prohibited: list[str] = []
    if profile:
        resolved = resolve_profile(profile)
        modules = resolved["modules"]
        required = list(resolved["requiredPatterns"])
        recommended = list(resolved["recommendedPatterns"])
        prohibited = list(resolved["prohibitedPatterns"])
    for pattern_id in extra_patterns or []:
        if pattern_id not in required:
            required.append(pattern_id)

    scope = list(dict.fromkeys([*required, *recommended]))
    role_index: dict[str, dict] = {}
    obligations = []
    for pattern_id in scope:
        contract = contracts.get(pattern_id)
        obligations.append({
            "patternId": pattern_id,
            "hasContract": contract is not None,
            "items": [] if contract is None else [
                {key: obligation[key] for key in ("id", "obligation", "level", "trait", "conceptKind", "effect") if key in obligation}
                for obligation in contract["obligations"]
            ],
        })
        if contract is None:
            continue
        for role in contract.get("roles", []):
            entry = role_index.setdefault(role["trait"], {"trait": role["trait"], "fromPatterns": []})
            entry["fromPatterns"].append(pattern_id)
            for key in ("title", "description", "conceptKind"):
                if key in role and key not in entry:
                    entry[key] = role[key]

    notes = []
    if prohibited:
        notes.append(f"Do NOT introduce these anti-patterns: {', '.join(prohibited)}.")
    missing = [pattern_id for pattern_id in required if pattern_id not in contracts]
    if missing:
        notes.append(f"No contract loaded for required pattern(s): {', '.join(missing)}. Model them from first principles.")
    notes.append("Tag each synthesized concept with its role trait and metadata.seededFrom = the pattern id; mark synthetic knowledge extractionMethod=llm with a calibrated confidence.")

    return {
        "scaffoldVersion": "1.0.0",
        "profile": profile,
        "modules": modules,
        "patterns": {"required": required, "recommended": recommended, "prohibited": prohibited},
        "roles": [role_index[trait] for trait in sorted(role_index)],
        "obligations": obligations,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a one-shot pattern-seeding scaffold (profile + roles + obligations).")
    parser.add_argument("--profile", help="profile/preset id (e.g. procure-to-pay)")
    parser.add_argument("--patterns", help="comma-separated extra pattern ids to include")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()
    if not args.profile and not args.patterns:
        parser.error("provide --profile and/or --patterns")

    extra = [item for item in args.patterns.split(",") if item] if args.patterns else []
    try:
        scaffold = build_scaffold(args.profile, extra, load_contracts())
    except ProfileError as error:
        print(f"ERROR {error}")
        return 2
    text = json.dumps(scaffold, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
