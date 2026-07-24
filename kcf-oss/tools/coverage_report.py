"""Measure knowledge coverage of a domain model against the coverage model.

The EBNF grammars define what is *well-formed* and the semantic analyzer defines
what is *valid*. Neither answers "have we captured everything about this domain
that we should have?" That is a third axis - completeness - and it is derived
from, not embedded in, the grammar: ``config/coverage-model.json`` declares, per
profile, the obligations a model should satisfy, using the grammar's own
dimension and concept-kind vocabulary as the checklist.

This tool evaluates a normalized IR against that coverage model and emits a gap
report with stable ``gapId``s. A gap is a *missing obligation*, not an error: the
model may be perfectly valid yet incomplete. Gaps are the input to synthetic
gap-filling (an LLM proposes fills, tagged inferred/llm) and SME confirmation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "config" / "coverage-model.json"


def gap(obligation: dict, subject: str, message: str) -> dict:
    return {
        "gapId": obligation["id"],
        "level": obligation["level"],
        "dimension": obligation.get("dimension"),
        "subject": subject,
        "message": message,
        "obligation": obligation["obligation"],
    }


def _identity(item: dict) -> str:
    return item.get("qualifiedName") or item.get("id")


def ev_entity_has_identity(model: dict, obligation: dict) -> list[dict]:
    gaps = []
    for concept in model.get("concepts", []):
        if concept.get("kind") != obligation["conceptKind"]:
            continue
        if not any(attribute.get("identity") for attribute in concept.get("attributes", [])):
            subject = _identity(concept)
            gaps.append(gap(obligation, subject, f"{obligation['conceptKind']} {subject} has no identity attribute"))
    return gaps


def ev_concept_kind_has_lifecycle(model: dict, obligation: dict) -> list[dict]:
    subjects = {lifecycle.get("subject") for lifecycle in model.get("lifecycles", [])}
    gaps = []
    for concept in model.get("concepts", []):
        if concept.get("kind") != obligation["conceptKind"]:
            continue
        subject = _identity(concept)
        if subject not in subjects:
            gaps.append(gap(obligation, subject, f"{obligation['conceptKind']} {subject} has no lifecycle"))
    return gaps


def ev_action_effect_has_fields(model: dict, obligation: dict) -> list[dict]:
    effects = set(obligation.get("effects", []))
    fields = obligation.get("fields", [])
    gaps = []
    for action in model.get("actions", []):
        if effects and action.get("effect") not in effects:
            continue
        missing = [field for field in fields if not action.get(field)]
        if missing:
            gaps.append(gap(obligation, action.get("id"), f"action {action.get('id')} is missing {', '.join(missing)}"))
    return gaps


def ev_at_least_one_concept_kind(model: dict, obligation: dict) -> list[dict]:
    if any(concept.get("kind") == obligation["conceptKind"] for concept in model.get("concepts", [])):
        return []
    return [gap(obligation, model.get("id", "<model>"), f"no concept of kind {obligation['conceptKind']} is present")]


def ev_at_least_one_collection(model: dict, obligation: dict) -> list[dict]:
    if model.get(obligation["collection"]):
        return []
    return [gap(obligation, model.get("id", "<model>"), f"collection {obligation['collection']} is empty")]


def _has_trait(concept: dict, trait: str) -> bool:
    return trait in (concept.get("traits") or [])


def ev_concept_with_trait(model: dict, obligation: dict) -> list[dict]:
    """Domain-agnostic role check: at least one concept must bear a declared
    trait (optionally of a given kind). Contracts name roles by trait, never by
    literal concept name, so the same obligation works for any domain."""
    trait = obligation["trait"]
    kind = obligation.get("conceptKind")
    for concept in model.get("concepts", []):
        if _has_trait(concept, trait) and (kind is None or concept.get("kind") == kind):
            return []
    scope = f" of kind {kind}" if kind else ""
    return [gap(obligation, model.get("id", "<model>"), f"no concept bears the required trait '{trait}'{scope}")]


def ev_trait_concept_has_lifecycle(model: dict, obligation: dict) -> list[dict]:
    trait = obligation["trait"]
    subjects = {lifecycle.get("subject") for lifecycle in model.get("lifecycles", [])}
    gaps = []
    for concept in model.get("concepts", []):
        if _has_trait(concept, trait):
            subject = _identity(concept)
            if subject not in subjects:
                gaps.append(gap(obligation, subject, f"concept {subject} with trait '{trait}' has no lifecycle"))
    return gaps


def ev_trait_concept_has_action(model: dict, obligation: dict) -> list[dict]:
    trait = obligation["trait"]
    effect = obligation.get("effect")
    targets = {action.get("target") for action in model.get("actions", []) if not effect or action.get("effect") == effect}
    gaps = []
    for concept in model.get("concepts", []):
        if _has_trait(concept, trait):
            subject = _identity(concept)
            if subject not in targets:
                verb = f" {effect}" if effect else "n"
                gaps.append(gap(obligation, subject, f"concept {subject} with trait '{trait}' is not the target of a{verb} action"))
    return gaps


def ev_trait_linked_to_trait(model: dict, obligation: dict) -> list[dict]:
    """Relationship-shape check: every concept bearing ``trait`` must be connected
    by a relationship to some concept bearing ``linkedTrait`` (optionally of a
    given ``rootKind`` and ``direction``). Domain-agnostic: it names both ends by
    role, so it expresses shapes like 'a three-way-match must reference a
    purchase-order' without any literal names."""
    trait = obligation["trait"]
    linked_trait = obligation["linkedTrait"]
    root_kind = obligation.get("rootKind")
    direction = obligation.get("direction", "both")

    linked_ids = {_identity(concept) for concept in model.get("concepts", []) if _has_trait(concept, linked_trait)}
    relationships = [
        relationship for relationship in model.get("relationships", [])
        if not root_kind or relationship.get("rootKind") == root_kind
    ]
    gaps = []
    for concept in model.get("concepts", []):
        if not _has_trait(concept, trait):
            continue
        subject = _identity(concept)
        connected = any(
            (direction in ("out", "both") and relationship.get("source") == subject and relationship.get("target") in linked_ids)
            or (direction in ("in", "both") and relationship.get("target") == subject and relationship.get("source") in linked_ids)
            for relationship in relationships
        )
        if not connected:
            gaps.append(gap(obligation, subject, f"{trait} concept {subject} is not linked to a {linked_trait} concept"))
    return gaps


# Operation families for CRUD coverage — a logical operation is "covered" when the
# entity is the target of any action whose `operation` falls in its family.
_CRUD_FAMILIES = {
    "create": {"create", "upsert", "bulk-create", "bulk-upsert"},
    "read": {"read", "query", "exists", "count"},
    "update": {"update", "patch", "replace", "upsert", "bulk-update", "bulk-patch", "bulk-upsert", "synchronize"},
    "delete": {"delete", "bulk-delete"},
}
_SET_SCOPES = {"set", "batch", "stream"}
_SET_OPERATIONS = {"bulk-create", "bulk-update", "bulk-patch", "bulk-delete", "bulk-upsert", "synchronize"}


def _is_exempt(concept: dict, obligation: dict) -> bool:
    """A concept opts out of write obligations (CRUD-write / set / transform) when
    it is read-only/reference/immutable. Declared via concept metadata
    (``mutability: "read-only"`` or ``readOnly: true``) so it never collides with
    the pattern role vocabulary; a declared role trait listed in the obligation's
    ``exemptTraits`` also exempts it."""
    meta = concept.get("metadata") or {}
    if meta.get("mutability") == "read-only" or meta.get("readOnly") is True:
        return True
    return bool(set(obligation.get("exemptTraits", [])) & set(concept.get("traits") or []))


def _kind_concepts(model: dict, obligation: dict):
    kind = obligation.get("conceptKind", "ENTITY")
    return [c for c in model.get("concepts", []) if c.get("kind") == kind]


def _target_operations(model: dict, subject: str) -> set:
    return {a.get("operation") for a in model.get("actions", []) if a.get("target") == subject}


def ev_concept_kind_has_crud(model: dict, obligation: dict) -> list[dict]:
    """Every entity is the target of create, read, update, and delete operations
    (synonym-aware). Read-only/reference/immutable entities need only read."""
    gaps = []
    for concept in _kind_concepts(model, obligation):
        if _is_exempt(concept, obligation):
            continue
        subject = _identity(concept)
        ops = _target_operations(model, subject)
        missing = [name for name, family in _CRUD_FAMILIES.items() if not (family & ops)]
        if missing:
            gaps.append(gap(obligation, subject, f"entity {subject} is missing CRUD operation(s): {', '.join(missing)}"))
    return gaps


def ev_concept_kind_has_set_operation(model: dict, obligation: dict) -> list[dict]:
    """Every non-exempt entity is the target of a set/bulk operation
    (scope set|batch|stream, or a bulk-* operation)."""
    actions = model.get("actions", [])
    gaps = []
    for concept in _kind_concepts(model, obligation):
        if _is_exempt(concept, obligation):
            continue
        subject = _identity(concept)
        has_set = any(a.get("target") == subject and (a.get("scope") in _SET_SCOPES or a.get("operation") in _SET_OPERATIONS) for a in actions)
        if not has_set:
            gaps.append(gap(obligation, subject, f"entity {subject} has no set/bulk operation (scope set|batch|stream, or a bulk-* operation)"))
    return gaps


def ev_at_least_one_transformation(model: dict, obligation: dict) -> list[dict]:
    """The model declares at least one data-transformation (a collectionTransform
    or a transform-effect action). Data transformations operate over collections,
    not single records, so this is a model-level obligation - but it only applies
    when the model has at least one non-exempt entity to transform."""
    non_exempt = [c for c in _kind_concepts(model, obligation) if not _is_exempt(c, obligation)]
    if not non_exempt:
        return []
    has_transform = bool(model.get("collectionTransforms")) or any(
        a.get("effect") == "transform" for a in model.get("actions", [])
    )
    if has_transform:
        return []
    return [gap(obligation, model.get("id", "<model>"),
                "model declares no data-transformation (a collectionTransform or a transform-effect action)")]


EVALUATORS = {
    "entity-has-identity": ev_entity_has_identity,
    "concept-kind-has-crud": ev_concept_kind_has_crud,
    "concept-kind-has-set-operation": ev_concept_kind_has_set_operation,
    "at-least-one-transformation": ev_at_least_one_transformation,
    "concept-kind-has-lifecycle": ev_concept_kind_has_lifecycle,
    "action-effect-has-fields": ev_action_effect_has_fields,
    "at-least-one-concept-kind": ev_at_least_one_concept_kind,
    "at-least-one-collection": ev_at_least_one_collection,
    "concept-with-trait": ev_concept_with_trait,
    "trait-concept-has-lifecycle": ev_trait_concept_has_lifecycle,
    "trait-concept-has-action": ev_trait_concept_has_action,
    "trait-linked-to-trait": ev_trait_linked_to_trait,
}


def model_profiles(model: dict) -> set[str]:
    profiles = set(model.get("profiles", []))
    if model.get("profile"):
        profiles.add(model["profile"])
    return profiles


def applies(profiles: set[str], obligation: dict) -> bool:
    scope = obligation["profiles"]
    return "*" in scope or bool(profiles & set(scope))


def report(model: dict, coverage_model: dict) -> dict:
    profiles = model_profiles(model)
    gaps: list[dict] = []
    considered = 0
    for obligation in coverage_model["obligations"]:
        if not applies(profiles, obligation):
            continue
        considered += 1
        gaps.extend(EVALUATORS[obligation["obligation"]](model, obligation))
    summary = {
        "required": sum(1 for item in gaps if item["level"] == "required"),
        "recommended": sum(1 for item in gaps if item["level"] == "recommended"),
        "info": sum(1 for item in gaps if item["level"] == "info"),
        "totalGaps": len(gaps),
    }
    return {
        "coverageReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "profiles": sorted(profiles),
        "obligationsConsidered": considered,
        "summary": summary,
        "gaps": gaps,
    }


def by_concept(gap_report: dict) -> dict:
    """Regroup a flat gap report into a per-subject, dimension-by-dimension view -
    the review unit for a human validating a synthesized concept."""
    buckets: dict[str, list] = {}
    for item in gap_report["gaps"]:
        buckets.setdefault(item["subject"], []).append({
            "gapId": item["gapId"],
            "level": item["level"],
            "dimension": item.get("dimension"),
            "message": item["message"],
        })
    return {
        "coverageByConceptVersion": "1.0.0",
        "model": gap_report["model"],
        "subjects": [{"subject": subject, "gaps": buckets[subject]} for subject in sorted(buckets)],
    }


def load_coverage_model(path: Path | None = None) -> dict:
    return json.loads((path or DEFAULT_MODEL).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Report knowledge-coverage gaps for a KCF model IR.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--coverage-model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit non-zero on recommended gaps too, not only required")
    parser.add_argument("--by-concept", action="store_true", help="group gaps per concept (dimension-by-dimension review view)")
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    coverage_model = load_coverage_model(args.coverage_model)
    result = report(model, coverage_model)
    output_document = by_concept(result) if args.by_concept else result

    text = json.dumps(output_document, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    if result["summary"]["required"]:
        return 1
    if args.strict and result["summary"]["recommended"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
