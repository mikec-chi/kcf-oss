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


# Advisory data-management category (see semantic_analyzer.ENTITY_CATEGORIES). When an
# entity *states* one, coverage becomes appropriate rather than maximal — it rewards
# right-modeling, not max-modeling. Read-mostly reference/config data is exempt from
# write obligations; only transactional data is expected to carry a lifecycle (master
# data is a managed catalogue — CRUD/admin, but no operational state machine). When no
# category is stated, behavior is unchanged (obligations apply as before).
_WRITE_EXEMPT_CATEGORIES = {"reference", "config"}
_NO_LIFECYCLE_CATEGORIES = {"reference", "config", "master"}


def _category(concept: dict):
    return (concept.get("metadata") or {}).get("category")


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
        # reference/config/master entities are not operational state machines — do not
        # recommend a lifecycle for them (recommending one incentivized adding empty
        # lifecycles, which distorts the shape that record-nature is inferred from).
        if _category(concept) in _NO_LIFECYCLE_CATEGORIES:
            continue
        # Read-only / immutable data (an append-only ledger, an audit trail) has no
        # operational state machine either — records are never updated, so a lifecycle
        # cannot be satisfied except by an empty one. Honour the same exemption the CRUD
        # and set-operation evaluators do (metadata.mutability/readOnly + exemptTraits),
        # so an immutable transactional entity is not left with a permanently
        # unsatisfiable recommended gap.
        if _is_exempt(concept, obligation):
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
    # reference/config entities are read-mostly lookups/settings — exempt from write
    # obligations (CRUD-write / set / transform), same spirit as read-only.
    if meta.get("category") in _WRITE_EXEMPT_CATEGORIES:
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


def ev_concept_kind_targeted_by(model: dict, obligation: dict) -> list[dict]:
    """Advisory reachability: every concept of ``conceptKind`` must be the target of
    at least one relationship of ``rootKind`` — e.g. an EVENT must have a CAUSATION
    producer, or nothing can ever emit it. Domain-agnostic (reads only kinds)."""
    kind = obligation["conceptKind"]
    root_kind = obligation.get("rootKind")
    targeted = {
        relationship.get("target")
        for relationship in model.get("relationships", [])
        if not root_kind or relationship.get("rootKind") == root_kind
    }
    gaps = []
    for concept in model.get("concepts", []):
        if concept.get("kind") != kind:
            continue
        subject = _identity(concept)
        if subject not in targeted:
            qualifier = f" {root_kind}" if root_kind else ""
            gaps.append(gap(obligation, subject, f"{kind} {subject} is not the target of any{qualifier} relationship (no producer)"))
    return gaps


# --- P1: model-level readiness anchors --------------------------------------
# A schema-valid but empty model must NOT read as "ready". The obligations below
# are *model-level* (not per-element), so they are not vacuously satisfied when a
# model has no elements - they are the substance behind the assess `ready`
# verdict. Intentionally sparse packages (a vocabulary/term library) opt out of
# the substantive-content and profile-anchor obligations by declaring packageKind
# "vocabulary" (or a "minimal" profile); such a package is then judged only on the
# per-element obligations (identity, authorization, ...), which is correct for a
# definitions-only library.

_VOCABULARY_PACKAGE_KINDS = {"vocabulary"}
_MINIMAL_PROFILES = {"minimal"}

# Top-level collections that count as substantive domain content beyond `concepts`.
_SUBSTANTIVE_COLLECTIONS = (
    "relationships", "actions", "rules", "policies", "organizations",
    "information", "reasoning", "assertions", "events", "resources",
    "processes", "lifecycles", "collectionTransforms",
)


def _package_kind(model: dict):
    """The declared package kind, read from an optional top-level ``packageKind``
    or from ``extensions.package.packageKind`` (the contract-safe location, since
    ``extensions`` is an open bag). Returns None when undeclared."""
    kind = model.get("packageKind")
    if kind:
        return kind
    return ((model.get("extensions") or {}).get("package") or {}).get("packageKind")


def is_vocabulary_package(model: dict) -> bool:
    """A model that intentionally captures only definitions (a vocabulary/term
    library) rather than a whole application. It opts out of the substantive-
    content and profile-anchor obligations so an honest, sparse library is not
    forced to look like an application to be considered internally complete."""
    if _package_kind(model) in _VOCABULARY_PACKAGE_KINDS:
        return True
    return bool(model_profiles(model) & _MINIMAL_PROFILES)


def _domain_concepts(model: dict) -> list[dict]:
    return [concept for concept in model.get("concepts", []) if concept.get("kind")]


def ev_model_has_substantive_content(model: dict, obligation: dict) -> list[dict]:
    """The model must carry at least one substantive domain construct - a concept
    of a domain kind, or a non-empty knowledge/behavior collection. This is the
    obligation that makes an empty-but-valid model *not* ready: readiness requires
    captured knowledge, not merely a well-formed envelope."""
    if _domain_concepts(model):
        return []
    if any(model.get(name) for name in _SUBSTANTIVE_COLLECTIONS):
        return []
    return [gap(obligation, model.get("id", "<model>"),
                "model declares no substantive domain content (no concepts and no knowledge/behavior constructs)")]


def ev_at_least_one_action_effect(model: dict, obligation: dict) -> list[dict]:
    """The model must declare at least one action with one of the given effects -
    e.g. a business application must have at least one state-changing (command or
    transform) action, or it captures no behavior worth authorizing. Model-level,
    so it fires on an application that declares entities but no behavior."""
    effects = set(obligation.get("effects", []))
    for action in model.get("actions", []):
        if not effects or action.get("effect") in effects:
            return []
    label = "/".join(sorted(effects)) or "any"
    return [gap(obligation, model.get("id", "<model>"),
                f"model declares no {label}-effect action")]


def ev_at_least_one_of(model: dict, obligation: dict) -> list[dict]:
    """Presence anchor with alternatives: satisfied when the model has a concept of
    ``conceptKind`` OR any of the named ``collections`` is non-empty. One evaluator
    expresses profile anchors robustly whether a construct is realized as a concept
    (kind EVENT) or as a top-level collection (``events``), avoiding false gaps."""
    kind = obligation.get("conceptKind")
    if kind and any(concept.get("kind") == kind for concept in model.get("concepts", [])):
        return []
    for name in obligation.get("collections", []):
        if model.get(name):
            return []
    wanted = []
    if kind:
        wanted.append(f"a {kind} concept")
    wanted.extend(f"a non-empty '{name}'" for name in obligation.get("collections", []))
    return [gap(obligation, model.get("id", "<model>"), "model has none of: " + ", ".join(wanted or ["(nothing declared)"]))]


def ev_profile_declared(model: dict, obligation: dict) -> list[dict]:
    """A model should declare at least one profile (or an explicit ``minimal``
    profile / vocabulary packageKind). Recommended, not required: a profile-less
    fragment is a legitimate library, but declaring a profile is how a model
    states which completeness obligations it means to be judged against."""
    if model_profiles(model):
        return []
    return [gap(obligation, model.get("id", "<model>"),
                "model declares no profile; declare a profile (or packageKind 'vocabulary' / profile 'minimal') to state its intended scope")]


# --- P3: broader construct-family obligations -------------------------------
# The coverage model reached only a handful of the grammar's dimensions. These
# extend it to more construct families (relationships, resources, temporal,
# reasoning, provenance) so meta-coverage (tools/meta_coverage.py) has fewer
# policy-missing families. All are domain-agnostic - they read structure only.

def ev_relationships_when_multiple_entities(model: dict, obligation: dict) -> list[dict]:
    """A model with two or more entities but no relationships almost certainly
    under-captures the domain: entities rarely stand alone. Model-level and only
    fires once there is something to relate, so a single-entity model is exempt."""
    entities = [concept for concept in model.get("concepts", []) if concept.get("kind") == "ENTITY"]
    if len(entities) < 2 or model.get("relationships"):
        return []
    return [gap(obligation, model.get("id", "<model>"),
                f"model declares {len(entities)} entities but no relationships between them")]


def ev_reasoning_has_premises(model: dict, obligation: dict) -> list[dict]:
    """A reasoning step that states a conclusion with no premises is an assertion in
    disguise - its grounding is missing. Every reasoning item should cite premises."""
    gaps = []
    for item in model.get("reasoning", []):
        if isinstance(item, dict) and not item.get("premises"):
            gaps.append(gap(obligation, item.get("id"), f"reasoning {item.get('id')} states a conclusion with no premises"))
    return gaps


def ev_subsection_required_when_present(model: dict, obligation: dict) -> list[dict]:
    """Conditional completeness: if a cross-cutting section (e.g. `security`,
    `integration`) is declared at all, a named sub-field must be non-empty - a
    security posture with no controls, or an integration with no adapters, is
    incomplete. Fires only when the section is present, so a model that does not use
    the section is never nagged (distinct from the analyzer, which checks the section's
    internal references/math, not whether it was fleshed out)."""
    section = model.get(obligation["section"])
    if not section or not isinstance(section, dict):
        return []
    if section.get(obligation["requires"]):
        return []
    subject = model.get("id", "<model>")
    return [gap(obligation, subject, f"{obligation['section']} section is declared but has no {obligation['requires']}")]


def ev_knowledge_has_provenance(model: dict, obligation: dict) -> list[dict]:
    """Assertions and information in a knowledge model should carry provenance (a
    source document, an extraction method, or evidence) so a claim can be traced to
    where it came from - the difference between captured knowledge and hearsay."""
    gaps = []
    for collection in ("assertions", "information"):
        for item in model.get(collection, []):
            if not isinstance(item, dict):
                continue
            if not (item.get("sourceDocument") or item.get("extractionMethod") or item.get("evidence")):
                subject = item.get("qualifiedName") or item.get("id")
                gaps.append(gap(obligation, subject, f"{collection[:-1]} {subject} carries no provenance (sourceDocument/extractionMethod/evidence)"))
    return gaps


EVALUATORS = {
    "entity-has-identity": ev_entity_has_identity,
    "concept-kind-targeted-by": ev_concept_kind_targeted_by,
    "model-has-substantive-content": ev_model_has_substantive_content,
    "at-least-one-action-effect": ev_at_least_one_action_effect,
    "at-least-one-of": ev_at_least_one_of,
    "profile-declared": ev_profile_declared,
    "relationships-when-multiple-entities": ev_relationships_when_multiple_entities,
    "reasoning-has-premises": ev_reasoning_has_premises,
    "knowledge-has-provenance": ev_knowledge_has_provenance,
    "subsection-required-when-present": ev_subsection_required_when_present,
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
    vocabulary = is_vocabulary_package(model)
    gaps: list[dict] = []
    considered = 0
    for obligation in coverage_model["obligations"]:
        if not applies(profiles, obligation):
            continue
        # A vocabulary/minimal package opts out of the substantive-content and
        # profile-anchor obligations (see is_vocabulary_package); per-element
        # obligations still apply.
        if vocabulary and obligation.get("vocabularyExempt"):
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
