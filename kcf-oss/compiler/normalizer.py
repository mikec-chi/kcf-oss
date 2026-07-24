from __future__ import annotations

import json
from pathlib import Path
import sys

from .ast import Model
from .parser import parse
from .source_map import record_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from profile_resolver import resolve_modules, resolve_profile  # noqa: E402


def qualify(name: str | None, namespace: str) -> str | None:
    if name is None or "." in name:
        return name
    return f"{namespace}.{name}"


def normalize(model: Model) -> dict:
    namespace = model.namespace or model.name.lower()
    profiles = list(dict.fromkeys([model.profile, *model.extra_profiles]))
    resolutions = [resolve_profile(profile) for profile in profiles]
    requested = [module for resolution in resolutions for module in resolution["modules"]]
    modules = resolve_modules(requested)
    requirements = list(dict.fromkeys(item for resolution in resolutions for item in resolution["runtimeRequirements"]))
    required_patterns = list(dict.fromkeys(item for resolution in resolutions for item in resolution["requiredPatterns"]))
    recommended_patterns = list(dict.fromkeys(item for resolution in resolutions for item in resolution["recommendedPatterns"]))
    prohibited_patterns = list(dict.fromkeys(item for resolution in resolutions for item in resolution["prohibitedPatterns"]))
    lock_path = PROJECT_ROOT / "config" / "module-lock.json"
    locks = json.loads(lock_path.read_text(encoding="utf-8"))["modules"] if lock_path.exists() else {module: {"version": "1.0.0"} for module in modules}
    ir = {
        "$schema": "../schemas/model-ir-v1.schema.json",
        "irVersion": "1.0.0",
        "id": model.name,
        "module": "KCF",
        "namespace": namespace,
        "profile": model.profile,
        "profiles": profiles,
        "requiredPatterns": required_patterns,
        "recommendedPatterns": recommended_patterns,
        "prohibitedPatterns": prohibited_patterns,
        "implementedPatterns": list(dict.fromkeys(model.implemented_patterns)),
        "excludedPatterns": list(dict.fromkeys(model.excluded_patterns)),
        "modules": modules,
        "moduleVersions": {module: locks.get(module, {}).get("version", "1.0.0") for module in modules},
        "concepts": [], "relationships": [], "lifecycles": [], "actions": [],
        "collectionTransforms": [], "events": [], "resources": [],
        "organizations": [], "information": [], "rules": [], "policies": [],
        "reasoning": [], "assertions": [], "identityResolutions": [],
        "knowledgeQueries": [],
        "runtimeRequirements": requirements,
        "emitters": [{"id": name, "supports": requirements, "unsupportedPolicy": "error"} for name in dict.fromkeys(item for resolution in resolutions for item in resolution["emitters"])],
        "runtimeBindings": [],
        "sourceMap": {},
    }

    def qualify_list(values: list) -> list:
        return [qualify(value, namespace) if isinstance(value, str) else value for value in values]

    def add_concept(declaration, kind: str, references: list, metadata: dict) -> None:
        concept = {
            "id": declaration.name,
            "qualifiedName": qualify(declaration.name, namespace),
            "kind": kind,
            "references": list(dict.fromkeys(qualify_list(references))),
            "metadata": metadata,
        }
        ir["concepts"].append(concept)
        record_source(ir["sourceMap"], concept["qualifiedName"], declaration)

    for declaration in model.declarations:
        if declaration.kind == "concept":
            concept = {
                "id": declaration.name,
                "qualifiedName": qualify(declaration.name, namespace),
                "kind": declaration.values["kind"],
                "references": [qualify(value, namespace) for value in declaration.values.get("references", [])],
            }
            for key in ("attributes", "traits", "metadata", "abstract"):
                if declaration.values.get(key): concept[key] = declaration.values[key]
            ir["concepts"].append(concept)
            record_source(ir["sourceMap"], concept["qualifiedName"], declaration)
            if concept["kind"] == "EVENT":
                ir["events"].append({"id": declaration.name, "mutable": not declaration.values.get("immutable", False)})
            if concept["kind"] == "RESOURCE":
                resource = {"id": declaration.name}
                if "capacity" in declaration.values.get("metadata", {}): resource["capacity"] = declaration.values["metadata"]["capacity"]
                ir["resources"].append(resource)
        elif declaration.kind == "organization":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            for key in ("parent", "reviewedBy", "accessPolicy"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            for key in ("members", "roles", "authorityDomains", "owns", "accountableFor", "evidence"):
                item[key] = qualify_list(item.get(key, []))
            for report in item.get("reporting", []):
                report["source"] = qualify(report["source"], namespace)
                report["target"] = qualify(report["target"], namespace)
            item["escalations"] = [qualify_list(path) for path in item.get("escalations", [])]
            ir["organizations"].append(item)
            references = [
                *([item["parent"]] if item.get("parent") else []), *item["members"],
                *item["roles"], *item["authorityDomains"], *item["owns"],
                *item["accountableFor"], *item["evidence"],
                *(ref for report in item["reporting"] for ref in (report["source"], report["target"])),
                *(ref for path in item["escalations"] for ref in path),
            ]
            references += [item[key] for key in ("reviewedBy", "accessPolicy") if item.get(key)]
            add_concept(declaration, "ORGANIZATIONAL", references, {"organizationKind": item.get("organizationKind")})
        elif declaration.kind == "information":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            for key in ("subjects", "authors", "sources", "audiences", "evidence"):
                item[key] = qualify_list(item.get(key, []))
            for key in ("schema", "freshness", "reviewedBy", "accessPolicy"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            ir["information"].append(item)
            references = [*item["subjects"], *item["authors"], *item["sources"], *item["audiences"], *item["evidence"]]
            references += [item[key] for key in ("schema", "freshness", "reviewedBy", "accessPolicy") if item.get(key)]
            add_concept(declaration, "INFORMATION", references, {"informationKind": item.get("informationKind")})
        elif declaration.kind == "rule":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            for key in ("appliesTo", "effects", "exceptions", "evidence"):
                item[key] = qualify_list(item.get(key, []))
            for key in ("authority", "reviewedBy", "accessPolicy"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            ir["rules"].append(item)
            references = [*item["appliesTo"], *item["effects"], *item["exceptions"], *item["evidence"]]
            references += [item[key] for key in ("authority", "reviewedBy", "accessPolicy") if item.get(key)]
            add_concept(declaration, "RULE", references, {"ruleKind": item.get("ruleKind")})
        elif declaration.kind == "policy":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            item["authority"] = qualify(item.get("authority"), namespace)
            item["rules"] = qualify_list(item.get("rules", []))
            item["evidence"] = qualify_list(item.get("evidence", []))
            if item.get("reviewedBy"): item["reviewedBy"] = qualify(item["reviewedBy"], namespace)
            if item.get("accessPolicy"): item["accessPolicy"] = qualify(item["accessPolicy"], namespace)
            ir["policies"].append(item)
            refs = [item["authority"], *item["rules"], *item["evidence"]]
            if item.get("reviewedBy"): refs.append(item["reviewedBy"])
            if item.get("accessPolicy"): refs.append(item["accessPolicy"])
            add_concept(declaration, "RULE", refs, {"policy": True})
        elif declaration.kind == "reasoning":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            for key in ("premises", "evidence", "contradictions", "alternatives"):
                item[key] = qualify_list(item.get(key, []))
            if item.get("reviewedBy"): item["reviewedBy"] = qualify(item["reviewedBy"], namespace)
            if item.get("accessPolicy"): item["accessPolicy"] = qualify(item["accessPolicy"], namespace)
            ir["reasoning"].append(item)
            refs = [*item["premises"], *item["evidence"], *item["contradictions"], *item["alternatives"]]
            if item.get("reviewedBy"): refs.append(item["reviewedBy"])
            if item.get("accessPolicy"): refs.append(item["accessPolicy"])
            add_concept(declaration, "REASONING", refs, {"reasoningKind": item.get("reasoningKind")})
        elif declaration.kind == "assertion":
            item = {"id": declaration.name, **declaration.values}
            item["subject"] = qualify(item.get("subject"), namespace)
            if item.get("objectIsReference"): item["object"] = qualify(item.get("object"), namespace)
            item["qualifiedName"] = qualify(declaration.name, namespace)
            for key in ("supersedes", "derivedBy", "reviewedBy", "accessPolicy"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            item["evidence"] = qualify_list(item.get("evidence", []))
            item["contradicts"] = qualify_list(item.get("contradicts", []))
            ir["assertions"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "identity-resolution":
            item = {"id": declaration.name, **declaration.values}
            item["qualifiedName"] = qualify(declaration.name, namespace)
            item["canonical"] = qualify(item.get("canonical"), namespace)
            for key in ("sameAs", "mergeSources", "splitTargets", "evidence"):
                item[key] = qualify_list(item.get(key, []))
            if item.get("reviewedBy"): item["reviewedBy"] = qualify(item["reviewedBy"], namespace)
            if item.get("accessPolicy"): item["accessPolicy"] = qualify(item["accessPolicy"], namespace)
            ir["identityResolutions"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "knowledge-query":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            ir["knowledgeQueries"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "relationship":
            relationship = {"id": declaration.name, **declaration.values}
            relationship["definition"] = relationship.get("definition", declaration.name)
            relationship["source"] = qualify(relationship["source"], namespace)
            relationship["target"] = qualify(relationship["target"], namespace)
            ir["relationships"].append(relationship)
            record_source(ir["sourceMap"], declaration.name, declaration)
        elif declaration.kind == "lifecycle":
            lifecycle = {"id": declaration.name, **declaration.values}
            lifecycle["subject"] = qualify(lifecycle.get("subject"), namespace)
            initial = lifecycle.get("initial", [])
            lifecycle["initial"] = initial[0] if len(initial) == 1 else initial
            ir["lifecycles"].append(lifecycle)
            record_source(ir["sourceMap"], declaration.name, declaration)
        elif declaration.kind == "action":
            action = {"id": declaration.name, **declaration.values}
            action["target"] = qualify(action.get("target"), namespace)
            ir["actions"].append(action)
            record_source(ir["sourceMap"], declaration.name, declaration)
        elif declaration.kind == "collection":
            transform = {"id": declaration.name, **declaration.values}
            if "input" in transform and "inputSchema" not in transform: transform["inputSchema"] = transform.pop("input")
            if "output" in transform and "outputSchema" not in transform: transform["outputSchema"] = transform.pop("output")
            ir["collectionTransforms"].append(transform)
            record_source(ir["sourceMap"], declaration.name, declaration)
    return ir


def compile_text(text: str, source: str = "<memory>") -> dict:
    return normalize(parse(text, source))


def compile_file(path: Path) -> dict:
    resolved = path.resolve()
    try:
        source = resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        source = str(resolved)
    return compile_text(resolved.read_text(encoding="utf-8"), source)
