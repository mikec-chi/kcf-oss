"""The one authoritative inventory of the semantic identities an IR declares.

Shared by every tool that must account for "every semantic identity" - the
realization verifier above all - so those inventories cannot silently diverge. The
failure this fixes (flagged in review): the realization verifier enumerated a
*subset* of IR sections, so whole profile/tail sections (integration, security,
lineage, architecture, experience, design, analytics, ai, calendars, routes, units,
authorities, allocations, ...) were unverified while the schema said "every semantic
identity". A single source of truth keeps the claim honest as the grammar grows.

Three shapes of IR-bearing section:
  * LIST_ID_SECTIONS   - arrays whose items carry a per-item identity;
  * STRING_ARRAY_SECTIONS - arrays of bare strings, each an identity;
  * SINGLETON_SECTIONS - one cross-cutting object each; present+non-empty is one
    identity named by the section (a profile block is realized as a whole).
"""

from __future__ import annotations

# Arrays whose items carry a per-item identity (qualifiedName | id | name).
LIST_ID_SECTIONS = (
    "concepts", "relationships", "lifecycles", "actions", "collectionTransforms",
    "organizations", "information", "rules", "policies", "reasoning", "assertions",
    "identityResolutions", "knowledgeQueries", "skills", "capabilities", "processes",
    "events", "resources", "mutations", "units", "authorities", "calendars", "routes",
    "propositions", "predicates", "math", "allocations", "plans", "emitters",
    "runtimeBindings",
)

# Cross-cutting profile sections: one openObject each; present+non-empty is one identity.
SINGLETON_SECTIONS = (
    "integration", "security", "lineage", "architecture", "experience", "design",
    "analytics", "ai",
)

# Arrays of bare strings: each string is an identity.
STRING_ARRAY_SECTIONS = ("runtimeRequirements",)

# Sections whose KEYS are identities: `extensions` is an open object of named packages.
# Each package becomes an identity (`extensions.<name>`) so a realization must give it a
# disposition (realized / delegated / opaque / unsupported) rather than letting arbitrary
# semantic content hide inside an unaccounted bag - preserving D-005 at the package level.
# (Finer identities WITHIN an extension package are that package's own responsibility; the
# realization manifest accounts for the package as a whole unless the package registers
# its own enumerator.)
EXTENSION_KEY_SECTIONS = ("extensions",)

# Top-level IR properties that are intentionally NOT semantic identities: envelope
# metadata, profile/pattern declarations, module bookkeeping, and cross-references
# covered elsewhere. Each carries a reason so a NEW identity-bearing section cannot
# slip in unclassified - the schema-to-inventory conformance check (see
# unclassified_ir_sections) fails until every top-level IR property is classified as
# a list/string-array/singleton identity source OR explicitly excluded here.
EXCLUDED_SECTIONS = {
    "$schema": "JSON Schema pointer (envelope).",
    "irVersion": "IR version scalar (envelope).",
    "id": "model id (envelope).",
    "module": "root module name (envelope).",
    "namespace": "namespace scalar (envelope).",
    "profile": "profile declaration (metadata).",
    "profiles": "profile declarations (metadata).",
    "packageKind": "package-kind declaration (metadata).",
    "requiredPatterns": "pattern-id declarations (references, not identities).",
    "recommendedPatterns": "pattern-id declarations (references).",
    "prohibitedPatterns": "pattern-id declarations (references).",
    "implementedPatterns": "pattern-id declarations (references).",
    "excludedPatterns": "pattern-id declarations (references).",
    "modules": "resolved module-name list (bookkeeping).",
    "moduleVersions": "module version map (bookkeeping).",
    "sourceMap": "span map keyed by existing identity (provenance, not a new identity).",
}


def unclassified_ir_sections(schema: dict) -> list[str]:
    """Every top-level property of the IR schema must be classified: a list-, string-,
    or singleton-identity source, OR explicitly excluded. Returns the properties that
    are not - so when the IR schema gains a new identity-bearing collection, the
    conformance gate fails until someone registers it here. Keeps 'every semantic
    identity' (model_semantic_ids) true as the IR grows, rather than silently omitting
    a new section from realization/accounting."""
    classified = (set(LIST_ID_SECTIONS) | set(STRING_ARRAY_SECTIONS) | set(SINGLETON_SECTIONS)
                  | set(EXTENSION_KEY_SECTIONS) | set(EXCLUDED_SECTIONS))
    return sorted(name for name in (schema.get("properties") or {}) if name not in classified)


def _item_identity(item, section: str, index: int) -> str:
    # Prefer a STABLE declared identity. The `section#index` fallback keeps accounting
    # exhaustive (nothing disappears) but is POSITION-BASED and therefore NOT stable
    # across reordering or versions - see anonymous_identities() / the realization
    # report's positionUnstableIdentities, and the "stable identity" item in IR-ROADMAP.
    if isinstance(item, dict):
        return item.get("qualifiedName") or item.get("id") or item.get("name") or f"{section}#{index}"
    if isinstance(item, str):
        return item
    return f"{section}#{index}"


def anonymous_identities(model: dict) -> list[str]:
    """Identities that fell back to a POSITION-BASED `section#index` because the item
    declared no qualifiedName/id/name. Accounting includes them, but they are not
    cross-version trace-stable - a durable realization manifest should give every
    identity-bearing item a stable id. Surfaced so consumers know which identities are
    not reorder-safe."""
    anonymous: list[str] = []
    for section in LIST_ID_SECTIONS:
        for index, item in enumerate(model.get(section) or []):
            if not (isinstance(item, dict) and (item.get("qualifiedName") or item.get("id") or item.get("name"))):
                anonymous.append(f"{section}#{index}")
    return anonymous


def model_semantic_ids(model: dict) -> dict[str, str]:
    """Every semantic identity the IR declares, mapped to the section it came from.
    This is the exhaustive set a realization (or any accounting) must cover - nothing
    IR-bearing is omitted, so 'accounted for' really means all of it."""
    identities: dict[str, str] = {}
    for section in LIST_ID_SECTIONS:
        for index, item in enumerate(model.get(section) or []):
            identities.setdefault(_item_identity(item, section, index), section)
    for section in STRING_ARRAY_SECTIONS:
        for value in model.get(section) or []:
            if value:
                identities.setdefault(value, section)
    for section in SINGLETON_SECTIONS:
        block = model.get(section)
        if not block:
            continue
        # A profile section (experience/design/security/…) is not one opaque identity:
        # its declared members (views, tokens, controls, threats, adapters, …) are each a
        # semantic identity a realization must account for individually. Otherwise a
        # manifest that builds NONE of the declared screens verifies clean (disposition the
        # section with one note) while an honest per-screen `delegated` entry is rejected as
        # an unknown identity — the same inverted incentive as the resolved
        # document-profile report. (Report profile-members-not-identities-20260729-15.)
        members_found = False
        if isinstance(block, dict):
            for key, value in block.items():
                if not isinstance(value, list):
                    continue
                for index, item in enumerate(value):
                    if isinstance(item, dict):
                        member = item.get("id") or item.get("qualifiedName") or item.get("name") or f"{section}.{key}#{index}"
                        identities.setdefault(member, f"{section}.{key}")
                        members_found = True
        # A section with no enumerable members stays one opaque identity (back-compatible).
        if not members_found:
            identities.setdefault(section, section)
    for section in EXTENSION_KEY_SECTIONS:
        for key in (model.get(section) or {}):
            identities.setdefault(f"{section}.{key}", section)
    return identities
