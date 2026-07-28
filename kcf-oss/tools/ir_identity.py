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


def _item_identity(item, section: str, index: int) -> str:
    if isinstance(item, dict):
        return item.get("qualifiedName") or item.get("id") or item.get("name") or f"{section}#{index}"
    if isinstance(item, str):
        return item
    return f"{section}#{index}"


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
        if model.get(section):
            identities.setdefault(section, section)
    return identities
