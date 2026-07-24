from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_SCHEMA = PROJECT_ROOT / "schemas" / "model-ir-v1.schema.json"
KNOWLEDGE_COLLECTIONS = (
    "organizations", "information", "rules", "policies", "reasoning",
    "assertions", "identityResolutions", "knowledgeQueries",
)


def indexed(model):
    return {c.get("qualifiedName") or c["id"]: c for c in model.get("concepts", [])}


def compare(old, new):
    before, after = indexed(old), indexed(new)
    changes = []
    for name in sorted(before.keys() - after.keys()):
        changes.append({"classification": "breaking", "subject": name, "change": "concept removed"})
    for name in sorted(after.keys() - before.keys()):
        changes.append({"classification": "compatible", "subject": name, "change": "concept added"})
    for name in sorted(before.keys() & after.keys()):
        a, b = before[name], after[name]
        if a.get("kind") != b.get("kind"):
            changes.append({"classification": "breaking", "subject": name, "change": "primary kind changed"})
        old_attrs = {x["name"]: x for x in a.get("attributes", [])}
        new_attrs = {x["name"]: x for x in b.get("attributes", [])}
        for attr in old_attrs.keys() - new_attrs.keys():
            changes.append({"classification": "breaking", "subject": f"{name}.{attr}", "change": "attribute removed"})
        for attr in new_attrs.keys() - old_attrs.keys():
            level = "breaking" if new_attrs[attr].get("required") and "default" not in new_attrs[attr] else "compatible"
            changes.append({"classification": level, "subject": f"{name}.{attr}", "change": "attribute added"})
        for attr in old_attrs.keys() & new_attrs.keys():
            if old_attrs[attr].get("type") != new_attrs[attr].get("type"):
                changes.append({"classification": "breaking", "subject": f"{name}.{attr}", "change": "attribute type changed"})
    if old.get("runtimeRequirements") != new.get("runtimeRequirements"):
        added = set(new.get("runtimeRequirements", [])) - set(old.get("runtimeRequirements", []))
        for requirement in sorted(added):
            changes.append({"classification": "breaking", "subject": requirement, "change": "runtime requirement added"})
    for collection in KNOWLEDGE_COLLECTIONS:
        old_items = {item.get("qualifiedName") or item["id"]: item for item in old.get(collection, [])}
        new_items = {item.get("qualifiedName") or item["id"]: item for item in new.get(collection, [])}
        for name in sorted(old_items.keys() - new_items.keys()):
            changes.append({"classification": "breaking", "subject": name, "change": f"{collection} declaration removed"})
        for name in sorted(new_items.keys() - old_items.keys()):
            changes.append({"classification": "compatible", "subject": name, "change": f"{collection} declaration added"})
        for name in sorted(old_items.keys() & new_items.keys()):
            if old_items[name] != new_items[name]:
                changes.append({"classification": "breaking", "subject": name, "change": f"{collection} semantics changed"})
    return changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    args = parser.parse_args()
    old = json.loads(args.old.read_text())
    new = json.loads(args.new.read_text())
    schema = json.loads(MODEL_SCHEMA.read_text(encoding="utf-8"))
    for label, model in (("old", old), ("new", new)):
        errors = list(Draft202012Validator(schema).iter_errors(model))
        if errors:
            raise SystemExit(f"{label} model does not conform to semantic IR schema: {errors[0].message}")
    changes = compare(old, new)
    recommended = "major" if any(c["classification"] == "breaking" for c in changes) else ("minor" if changes else "patch")
    print(json.dumps({"deltaVersion": "1.0.0", "recommendedVersionChange": recommended, "changes": changes}, indent=2))


if __name__ == "__main__":
    main()
