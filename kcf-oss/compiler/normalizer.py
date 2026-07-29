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
        "collectionTransforms": [], "events": [], "resources": [], "mutations": [], "units": [], "authorities": [], "processes": [],
        "calendars": [], "routes": [], "propositions": [], "predicates": [], "math": [], "allocations": [],
        "organizations": [], "information": [], "rules": [], "policies": [],
        "reasoning": [], "assertions": [], "identityResolutions": [],
        "knowledgeQueries": [], "skills": [], "capabilities": [],
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
            # Verbatim scalar/list fields (dimension `kind` classifier + EVENT
            # single-value fields carried as authored).
            for key in ("attributes", "traits", "metadata", "abstract", "conceptKind",
                        "occurrenceTime", "detectionTime", "correlationKeys",
                        "severity", "expectedness", "matchCondition",
                        "scale", "aggregation", "availability", "calculation",
                        "desiredState", "successes", "priority", "tradeoffs",
                        "geometry", "startValue", "endValue", "durationValue",
                        "recurrence", "timezone"):
                if declaration.values.get(key): concept[key] = declaration.values[key]
            # MEASURE numeric fields may legitimately be 0, so guard on None.
            for key in ("threshold", "target", "tolerance"):
                if declaration.values.get(key) is not None: concept[key] = declaration.values[key]
            # Single reference fields (qualified): MEASURE unit/period, ACTOR
            # communication, TEMPORAL calendar, SPATIAL contained-in, INTENT time-horizon.
            for key in ("unitRef", "periodRef", "communicationRef",
                        "containedIn", "calendarRef", "timeHorizon"):
                if declaration.values.get(key): concept[key] = qualify(declaration.values[key], namespace)
            # ACTOR capabilities/skills + WORK required capabilities/skills + EVENT
            # subject/source/observer/trigger/affect-lifecycle/evidence — qualified
            # reference lists resolved by the analyzer.
            for reflist in ("capabilities", "skills", "requiresCapability", "requiresSkill",
                            "subjects", "triggers", "sources", "observers",
                            "affectsLifecycle", "evidence", "roles", "authorities",
                            "responsibleFor", "accountableFor", "memberOf",
                            "performers", "inputs", "outputs", "outcomes",
                            "requiresResource", "requiresTool", "governedBy",
                            "triggeredBy", "emits", "compensateWith", "temporalRefs",
                            "stakeholders", "measures", "adjacentTo", "jurisdictions",
                            "spatialRoutes", "spatialCapacities"):
                if declaration.values.get(reflist):
                    concept[reflist] = [qualify(value, namespace) for value in declaration.values[reflist]]
            # WORK condition members (verbatim condition strings).
            for key in ("preconditions", "postconditions", "completions", "failures"):
                if declaration.values.get(key): concept[key] = declaration.values[key]
            # ENTITY structural fields: compositions / named references / embedded
            # collections (qualify their embedded refs), inline lifecycle binding, and
            # inline constraint-uses.
            for comp in declaration.values.get("compositions", []) or []:
                concept.setdefault("compositions", []).append({**comp, "target": qualify(comp["target"], namespace)})
            for ref in declaration.values.get("namedReferences", []) or []:
                concept.setdefault("namedReferences", []).append({**ref, "target": qualify(ref["target"], namespace)})
            for coll in declaration.values.get("collections", []) or []:
                concept.setdefault("collections", []).append({**coll, "of": qualify(coll["of"], namespace)})
            if declaration.values.get("lifecycleRef"):
                concept["lifecycleRef"] = qualify(declaration.values["lifecycleRef"], namespace)
            if declaration.values.get("constraints"):
                concept["constraints"] = [qualify(v, namespace) for v in declaration.values["constraints"]]
            # `immutable;` is projected as `event.mutable` for EVENTs (below). For any
            # other concept kind it used to parse and vanish — a silent no-op. Record it
            # as read-only mutability so it actually carries meaning: coverage exemption
            # (_is_exempt) and category reconciliation read `metadata.mutability`, and a
            # generator can suppress write/delete paths. Additive (metadata is open); an
            # explicit `mutability` already authored wins.
            if declaration.values.get("immutable") and concept["kind"] != "EVENT":
                concept.setdefault("metadata", {}).setdefault("mutability", "read-only")
            ir["concepts"].append(concept)
            record_source(ir["sourceMap"], concept["qualifiedName"], declaration)
            # Entity-embedded mutations project into the top-level mutations collection,
            # with the enclosing entity as subject and emitted events qualified.
            for mut in declaration.values.get("mutations", []) or []:
                # Identity is the bare id (like top-level actions) so a mutation folds
                # cleanly into the action stream at emit time (see effective_actions).
                entry = {"id": mut["name"], "subject": concept["qualifiedName"]}
                for field in ("operation", "scope", "selection", "atomicity",
                              "concurrency", "versionField", "idempotency"):
                    if mut.get(field) is not None:
                        entry[field] = mut[field]
                for field in ("mutates", "changes", "preconditions", "postconditions"):
                    if mut.get(field):
                        entry[field] = mut[field]
                if mut.get("emits"):
                    entry["emits"] = [qualify(e, namespace) for e in mut["emits"]]
                ir["mutations"].append(entry)
            if concept["kind"] == "EVENT":
                # Project the full declared event so the runtime/emitters can drive
                # orchestration off it (refs already namespace-qualified).
                event = {"id": declaration.name, "qualifiedName": concept["qualifiedName"],
                         "mutable": not declaration.values.get("immutable", False)}
                if concept.get("conceptKind"): event["eventKind"] = concept["conceptKind"]
                for field in ("subjects", "triggers", "sources", "observers",
                              "affectsLifecycle", "evidence", "correlationKeys"):
                    if concept.get(field): event[field] = concept[field]
                for field in ("occurrenceTime", "detectionTime", "severity",
                              "expectedness", "matchCondition"):
                    if concept.get(field) is not None: event[field] = concept[field]
                ir["events"].append(event)
            if concept["kind"] == "RESOURCE":
                resource = {"id": declaration.name, "qualifiedName": concept["qualifiedName"]}
                if declaration.values.get("conceptKind"): resource["resourceKind"] = declaration.values["conceptKind"]
                if declaration.values.get("capacity") is not None: resource["capacity"] = declaration.values["capacity"]
                # legacy metadata.capacity fallback (older hand-authored IR)
                elif "capacity" in declaration.values.get("metadata", {}): resource["capacity"] = declaration.values["metadata"]["capacity"]
                if declaration.values.get("availability"): resource["availability"] = declaration.values["availability"]
                if declaration.values.get("consumption"): resource["consumption"] = declaration.values["consumption"]
                if declaration.values.get("capacityUnit"): resource["capacityUnit"] = qualify(declaration.values["capacityUnit"], namespace)
                for src_key, dst_key in (("locationRef", "location"), ("ownerRef", "owner"),
                                         ("allocationPolicy", "allocationPolicy"), ("reservationPolicy", "reservationPolicy"),
                                         ("replenishmentRef", "replenishment"), ("costRef", "cost")):
                    if declaration.values.get(src_key): resource[dst_key] = qualify(declaration.values[src_key], namespace)
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
        elif declaration.kind == "skill":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace)}
            if declaration.values.get("level"): item["level"] = declaration.values["level"]
            if declaration.values.get("requires"): item["requires"] = qualify_list(declaration.values["requires"])
            if declaration.values.get("constraints"): item["constraints"] = qualify_list(declaration.values["constraints"])
            ir["skills"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "process":
            # Node ids are process-local; semantic refs (activity/uses/performer/
            # triggeredBy/outcome) are namespace-qualified.
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace)}
            nodes = []
            for node in declaration.values.get("nodes", []):
                n = dict(node)
                for ref_key in ("activity", "uses", "triggeredBy", "outcome"):
                    if n.get(ref_key): n[ref_key] = qualify(n[ref_key], namespace)
                nodes.append(n)
            item["nodes"] = nodes
            item["flows"] = declaration.values.get("flows", [])
            boundaries = []
            for boundary in declaration.values.get("boundaries", []):
                b = dict(boundary)
                if b.get("uses"): b["uses"] = qualify(b["uses"], namespace)
                boundaries.append(b)
            item["boundaries"] = boundaries
            lanes = []
            for lane in declaration.values.get("lanes", []):
                lane_copy = dict(lane)
                if lane_copy.get("performer"): lane_copy["performer"] = qualify(lane_copy["performer"], namespace)
                lanes.append(lane_copy)
            item["lanes"] = lanes
            ir["processes"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "allocation":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            for key in ("resource", "consumer", "reservation"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            ir["allocations"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "calendar":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            ir["calendars"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "route":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            for key in ("from", "to"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            if item.get("via"): item["via"] = qualify_list(item["via"])
            if item.get("constraints"): item["constraints"] = qualify_list(item["constraints"])
            ir["routes"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "proposition":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            ir["propositions"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "predicate":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            ir["predicates"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "math":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            for key in ("result", "model"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            ir["math"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "profile":
            # Operational/emitter profile block -> ir[<section>][<collection>].
            # Refs resolve by local id, so nothing is namespace-qualified here.
            section = declaration.values["section"]
            target = ir.setdefault(section, {})
            for collection, items in declaration.values["collections"].items():
                target.setdefault(collection, []).extend(items)
        elif declaration.kind == "authority":
            # Carry everything the parser captured (incl. knowledge-metadata:
            # evidence/confidence/classification/reviewed-by/recorded-at/...) then
            # qualify the structural references.
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace), **declaration.values}
            for key in ("subject", "target"):
                if item.get(key): item[key] = qualify(item[key], namespace)
            ir["authorities"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "capability":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace)}
            if declaration.values.get("requiresSkill"): item["requiresSkill"] = qualify_list(declaration.values["requiresSkill"])
            if declaration.values.get("outcome"): item["outcome"] = qualify_list(declaration.values["outcome"])
            if declaration.values.get("implementedBy"): item["implementedBy"] = qualify(declaration.values["implementedBy"], namespace)
            ir["capabilities"].append(item)
            record_source(ir["sourceMap"], item["qualifiedName"], declaration)
        elif declaration.kind == "unit":
            item = {"id": declaration.name, "qualifiedName": qualify(declaration.name, namespace)}
            for key in ("dimension", "symbol", "factor"):
                if declaration.values.get(key) is not None: item[key] = declaration.values[key]
            if declaration.values.get("base"): item["base"] = qualify(declaration.values["base"], namespace)
            ir["units"].append(item)
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
            # Qualify the LIFECYCLE-dimension semantic refs (state entry/exit actions,
            # transition trigger/requires-work/effect, temporal) so they resolve like
            # every other dimension; conditions (guard/invariant) stay verbatim.
            if lifecycle.get("temporalRefs"):
                lifecycle["temporalRefs"] = [qualify(ref, namespace) for ref in lifecycle["temporalRefs"]]
            state_bodies = {}
            for state, body in (lifecycle.get("stateBodies") or {}).items():
                new_body = dict(body)
                for key in ("entry", "exit"):
                    if new_body.get(key): new_body[key] = [qualify(ref, namespace) for ref in new_body[key]]
                state_bodies[state] = new_body
            if state_bodies:
                lifecycle["stateBodies"] = state_bodies
            transitions = []
            for transition in lifecycle.get("transitions", []):
                new_transition = dict(transition)
                for key in ("trigger", "requiresWork", "effect"):
                    if new_transition.get(key): new_transition[key] = [qualify(ref, namespace) for ref in new_transition[key]]
                transitions.append(new_transition)
            lifecycle["transitions"] = transitions
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
