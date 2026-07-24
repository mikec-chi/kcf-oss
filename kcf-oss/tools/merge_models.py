"""Merge several validated KCF domain-model IRs into one unified IR.

This is the compiler-concept tool that turns multiple independently elicited
models (from different people, documents, forms, code, or flows) into the single
normalized semantic IR that becomes the complete structured context for building
an application.

Design principles, mirroring the rest of the stack:

- One identity, one record. Records are unioned by semantic identity
  (``qualifiedName`` for concept-like collections, ``id`` for behavioural ones).
- Cross-model reconciliation is explicit. The ``identityResolutions`` collection
  (``canonical`` / ``sameAs`` / ``mergeSources``) is honoured so a concept named
  differently in two models can be unified onto one canonical identity. Callers
  may supply additional aliases.
- No silent overwrite (decision D-005). Additive fields (reference lists,
  attributes) are unioned losslessly; a genuine scalar disagreement between two
  models for the same identity is reported as a conflict diagnostic with both
  values, never silently resolved.

The merge itself never mutates the inputs' meaning to force agreement; it either
combines compatibly or reports the conflict for a human or LLM to resolve.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_SCHEMA = PROJECT_ROOT / "schemas" / "model-ir-v1.schema.json"

# Collections whose records are identified by ``qualifiedName`` (falling back to
# ``id``), and collections identified by ``id`` alone.
QUALIFIED_COLLECTIONS = (
    "concepts", "organizations", "information", "rules", "policies",
    "reasoning", "assertions", "identityResolutions", "knowledgeQueries",
)
ID_COLLECTIONS = (
    "relationships", "lifecycles", "actions", "collectionTransforms",
    "events", "resources", "processes", "allocations", "plans",
)
# Collections always present in output (matches the normalizer's default shape).
CORE_COLLECTIONS = (
    "concepts", "relationships", "lifecycles", "actions", "collectionTransforms",
    "events", "resources", "organizations", "information", "rules", "policies",
    "reasoning", "assertions", "identityResolutions", "knowledgeQueries",
)
STRING_UNION_FIELDS = (
    "profiles", "modules", "requiredPatterns", "recommendedPatterns",
    "prohibitedPatterns", "implementedPatterns", "excludedPatterns",
    "runtimeRequirements",
)
DICT_SECTIONS = (
    "integration", "security", "lineage", "architecture", "experience",
    "design", "analytics", "ai",
)
SINGULAR = {
    "concepts": "concept", "relationships": "relationship", "lifecycles": "lifecycle",
    "actions": "action", "collectionTransforms": "transform", "events": "event",
    "resources": "resource", "processes": "process", "allocations": "allocation",
    "plans": "plan", "organizations": "organization", "information": "information",
    "rules": "rule", "policies": "policy", "reasoning": "reasoning",
    "assertions": "assertion", "identityResolutions": "identity",
    "knowledgeQueries": "query", "emitters": "emitter",
}


def diag(rule_id: str, subject: str, field: str, first, second) -> dict:
    return {
        "severity": "error",
        "ruleId": rule_id,
        "subject": subject,
        "field": field,
        "message": f"models disagree on '{field}' for '{subject}'",
        "values": [first, second],
    }


def local_part(qualified: str) -> str:
    return qualified.rsplit(".", 1)[-1]


def key_of(collection: str, item: dict) -> str:
    if collection in QUALIFIED_COLLECTIONS:
        return item.get("qualifiedName") or item["id"]
    return item["id"]


# --- identity aliasing --------------------------------------------------------

def harvest_alias(models: list[dict]) -> dict[str, str]:
    """Build an alias map (declared identity -> canonical identity) from every
    model's identity-resolution declarations."""
    alias: dict[str, str] = {}
    for model in models:
        for resolution in model.get("identityResolutions", []):
            canonical = resolution.get("canonical")
            if not canonical:
                continue
            for source in [*resolution.get("sameAs", []), *resolution.get("mergeSources", [])]:
                alias[source] = canonical
    return alias


def resolve_transitive(alias: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for source in alias:
        seen, current = set(), source
        while current in alias and current not in seen:
            seen.add(current)
            current = alias[current]
        resolved[source] = current
    return resolved


def rewrite(value, alias: dict[str, str]):
    """Replace every aliased identity string, at any depth, with its canonical."""
    if isinstance(value, dict):
        return {key: rewrite(item, alias) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite(item, alias) for item in value]
    if isinstance(value, str):
        return alias.get(value, value)
    return value


def canonicalize(model: dict) -> dict:
    """After aliasing, keep each qualified record's ``id`` consistent with its
    (possibly rewritten) ``qualifiedName`` so aliased records fold cleanly."""
    for collection in QUALIFIED_COLLECTIONS:
        for item in model.get(collection, []):
            qualified = item.get("qualifiedName")
            if qualified:
                item["id"] = local_part(qualified)
    return model


# --- value merging ------------------------------------------------------------

def union_list(first: list, second: list) -> list:
    combined, seen, result = [*first, *second], set(), []
    for entry in combined:
        marker = json.dumps(entry, sort_keys=True) if isinstance(entry, (dict, list)) else entry
        if marker not in seen:
            seen.add(marker)
            result.append(entry)
    return result


def merge_attributes(first: list, second: list, subject: str, diagnostics: list) -> list:
    order: list[str] = []
    by_name: dict[str, dict] = {}
    for attribute in [*first, *second]:
        name = attribute["name"]
        if name not in by_name:
            by_name[name] = attribute
            order.append(name)
            continue
        merged = dict(by_name[name])
        for key, value in attribute.items():
            if key not in merged:
                merged[key] = value
            elif merged[key] != value:
                diagnostics.append(diag("merge.attribute.conflict", f"{subject}.{name}", key, merged[key], value))
        by_name[name] = merged
    return [by_name[name] for name in order]


def merge_dict(first: dict, second: dict, subject: str, field: str, diagnostics: list) -> dict:
    result = dict(first)
    for key, value in second.items():
        if key not in result:
            result[key] = value
        elif result[key] != value:
            existing = result[key]
            if isinstance(existing, list) and isinstance(value, list):
                result[key] = union_list(existing, value)
            elif isinstance(existing, dict) and isinstance(value, dict):
                result[key] = merge_dict(existing, value, subject, f"{field}.{key}", diagnostics)
            else:
                diagnostics.append(diag("merge.field.conflict", subject, f"{field}.{key}", existing, value))
    return result


def merge_records(collection: str, first: dict, second: dict, subject: str, diagnostics: list) -> dict:
    result = dict(first)
    for key, value in second.items():
        if key not in result:
            result[key] = value
            continue
        existing = result[key]
        if existing == value:
            continue
        if key == "attributes" and isinstance(existing, list) and isinstance(value, list):
            result[key] = merge_attributes(existing, value, subject, diagnostics)
        elif isinstance(existing, list) and isinstance(value, list):
            result[key] = union_list(existing, value)
        elif isinstance(existing, dict) and isinstance(value, dict):
            result[key] = merge_dict(existing, value, subject, key, diagnostics)
        else:
            rule = "merge.concept.conflict" if (collection == "concepts" and key == "kind") \
                else f"merge.{SINGULAR.get(collection, 'record')}.conflict"
            diagnostics.append(diag(rule, subject, key, existing, value))
    return result


def fold_collection(collection: str, models: list[dict], diagnostics: list) -> list:
    order: list[str] = []
    by_key: dict[str, dict] = {}
    for model in models:
        for item in model.get(collection, []):
            identity = key_of(collection, item)
            if identity in by_key:
                by_key[identity] = merge_records(collection, by_key[identity], item, identity, diagnostics)
            else:
                by_key[identity] = item
                order.append(identity)
    return [by_key[identity] for identity in order]


# --- top-level merge ----------------------------------------------------------

def merge(models: list[dict], model_id: str, namespace: str, extra_alias: dict[str, str] | None = None):
    """Merge ``models`` into one IR. Returns ``(unified_ir, diagnostics)``.

    ``diagnostics`` is empty when every model was combined losslessly; a
    non-empty list means at least one pair of models disagreed on a scalar for a
    shared identity and the disagreement must be resolved at the source.
    """
    if not models:
        raise ValueError("merge requires at least one model")
    diagnostics: list = []

    alias = harvest_alias(models)
    if extra_alias:
        alias.update(extra_alias)
    alias = resolve_transitive(alias)
    prepared = [canonicalize(rewrite(model, alias)) for model in models]

    unified: dict = {
        "$schema": "../schemas/model-ir-v1.schema.json",
        "irVersion": "1.0.0",
        "id": model_id,
        "module": "KCF",
        "namespace": namespace,
    }
    profile = next((model.get("profile") for model in prepared if model.get("profile")), None)
    if profile:
        unified["profile"] = profile

    for field in STRING_UNION_FIELDS:
        values: list = []
        for model in prepared:
            values = union_list(values, model.get(field, []))
        if field == "modules" and "KCF" not in values:
            values = ["KCF", *values]
        if values:
            unified[field] = values

    module_versions: dict[str, str] = {}
    for model in prepared:
        for module, version in model.get("moduleVersions", {}).items():
            if module in module_versions and module_versions[module] != version:
                diagnostics.append(diag("merge.module.version.conflict", module, "version", module_versions[module], version))
            else:
                module_versions.setdefault(module, version)
    if module_versions:
        unified["moduleVersions"] = module_versions

    for collection in [*CORE_COLLECTIONS, *(c for c in ID_COLLECTIONS if c not in CORE_COLLECTIONS)]:
        folded = fold_collection(collection, prepared, diagnostics)
        if collection in CORE_COLLECTIONS or folded:
            unified[collection] = folded

    emitters = fold_collection("emitters", prepared, diagnostics) if any(m.get("emitters") for m in prepared) else []
    if emitters:
        unified["emitters"] = emitters

    bindings: list = []
    for model in prepared:
        bindings = union_list(bindings, model.get("runtimeBindings", []))
    if bindings:
        unified["runtimeBindings"] = bindings

    for section in DICT_SECTIONS:
        present = [model[section] for model in prepared if model.get(section)]
        if present:
            accumulator = present[0]
            for other in present[1:]:
                accumulator = merge_dict(accumulator, other, section, section, diagnostics)
            unified[section] = accumulator

    extensions: dict = {}
    for model in prepared:
        for key, value in model.get("extensions", {}).items():
            extensions[key] = merge_dict(extensions[key], value, f"extensions.{key}", key, diagnostics) if key in extensions else value
    if extensions:
        unified["extensions"] = extensions

    source_map: dict = {}
    for model in prepared:
        for key, value in model.get("sourceMap", {}).items():
            source_map.setdefault(key, value)  # first source wins; provenance, not meaning
    if source_map:
        unified["sourceMap"] = source_map

    return unified, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge KCF domain models into one unified semantic IR.")
    parser.add_argument("models", type=Path, nargs="+", help="two or more model IR files")
    parser.add_argument("--id", required=True, help="identifier for the unified model")
    parser.add_argument("--namespace", required=True, help="default namespace for the unified model")
    parser.add_argument("--output", "-o", type=Path, help="write the unified IR here")
    parser.add_argument("--identity-map", type=Path, help="JSON object of extra {declaredId: canonicalId} aliases")
    parser.add_argument("--report", type=Path, help="write the merge report (diagnostics) here")
    parser.add_argument("--analyze", action="store_true", help="also run the semantic analyzer on the unified model")
    args = parser.parse_args()

    models = [json.loads(path.read_text(encoding="utf-8")) for path in args.models]
    extra_alias = json.loads(args.identity_map.read_text(encoding="utf-8")) if args.identity_map else None
    unified, diagnostics = merge(models, args.id, args.namespace, extra_alias)

    schema = json.loads(MODEL_SCHEMA.read_text(encoding="utf-8"))
    schema_errors = [error.message for error in Draft202012Validator(schema).iter_errors(unified)]

    analyzer_diagnostics: list = []
    if args.analyze:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from semantic_analyzer import Analyzer  # noqa: E402
        analyzer_diagnostics = Analyzer(unified).run()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(unified, indent=2) + "\n", encoding="utf-8")

    report = {
        "mergeVersion": "1.0.0",
        "unifiedModel": args.id,
        "sources": [model.get("id") for model in models],
        "schemaValid": not schema_errors,
        "schemaErrors": schema_errors,
        "conflicts": diagnostics,
        "analyzerDiagnostics": analyzer_diagnostics,
    }
    report_text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(report_text, encoding="utf-8")
    else:
        print(report_text, end="")

    if schema_errors or diagnostics:
        return 1
    if any(item.get("severity") == "error" for item in analyzer_diagnostics):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
