from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


CURRENT_VERSION = "1.0.0"
COLLECTIONS = [
    "concepts", "relationships", "lifecycles", "actions", "collectionTransforms",
    "processes", "events", "resources", "allocations", "plans", "emitters",
    "runtimeRequirements", "runtimeBindings", "organizations", "information",
    "rules", "policies", "reasoning", "assertions", "identityResolutions",
    "knowledgeQueries",
]


def migrate(model: dict, target: str = CURRENT_VERSION) -> tuple[dict, list[dict]]:
    if target != CURRENT_VERSION:
        raise ValueError(f"Unsupported target IR version {target!r}")
    result = copy.deepcopy(model)
    changes = []
    if not result.get("irVersion"):
        result["irVersion"] = CURRENT_VERSION
        changes.append({"path": "irVersion", "change": "added", "value": CURRENT_VERSION})
    if not result.get("$schema"):
        result["$schema"] = "../schemas/model-ir-v1.schema.json"
        changes.append({"path": "$schema", "change": "added", "value": result["$schema"]})
    if not result.get("module"):
        result["module"] = "KCF"
        changes.append({"path": "module", "change": "added", "value": "KCF"})
    for collection in COLLECTIONS:
        if collection not in result:
            result[collection] = []
            changes.append({"path": collection, "change": "added", "value": []})
    ordered = {key: result[key] for key in ("$schema", "irVersion", "id", "module") if key in result}
    ordered.update({key: value for key, value in result.items() if key not in ordered})
    return ordered, changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy KCF semantic IR to a supported version.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target", default=CURRENT_VERSION)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    migrated, changes = migrate(json.loads(args.source.read_text(encoding="utf-8")), args.target)
    args.output.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
    report = {"source": str(args.source), "targetVersion": args.target, "changes": changes}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
