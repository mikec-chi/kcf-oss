from __future__ import annotations

from collections import defaultdict
import copy
import json
import random
from pathlib import Path

from assess import assess
from coverage_report import load_coverage_model, report as coverage_report
from merge_models import merge
from pattern_contracts import load_contracts, role_report
from semantic_analyzer import Analyzer
from semantic_delta import compare


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    return json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))


def _gap_keys(model: dict) -> set[tuple]:
    report = coverage_report(model, load_coverage_model())
    return {(gap["gapId"], gap["subject"]) for gap in report["gaps"]}


def _required_gap_ids(model: dict) -> set[str]:
    report = coverage_report(model, load_coverage_model())
    return {gap["gapId"] for gap in report["gaps"] if gap["level"] == "required"}


def metamorphic() -> None:
    """Adversarial / metamorphic invariants: relationships that must hold between a
    model and a transformed version of it, whatever the specific content. These
    catch whole classes of regression a single fixture cannot - e.g. that no future
    change ever lets an empty model read as ready, or that reordering a collection
    silently changes a verdict."""
    contracts = load_contracts()

    # (1) An empty application is never ready - the flagship readiness invariant.
    empty = {
        "$schema": "../schemas/model-ir-v1.schema.json", "irVersion": "1.0.0",
        "id": "EmptyProp", "module": "KCF", "namespace": "prop",
        "profile": "business-application", "profiles": ["business-application"],
        "concepts": [],
    }
    assert not assess(empty)["ready"], "empty application was ready"
    assert "coverage.model.substantive-content" in _required_gap_ids(empty), "empty app had no substantive-content gap"

    # A known-ready model is the base for the mutation invariants below.
    base = _load("tests/fixtures/walkthrough/support-ticket-ready.json")
    assert assess(base)["ready"], "known-ready base model was not ready (fixture drift)"

    # (2) Adding a required entity without an identity never preserves readiness.
    no_identity = copy.deepcopy(base)
    no_identity["concepts"].append({"id": "Orphan", "qualifiedName": "support.Orphan", "kind": "ENTITY", "attributes": [{"name": "label", "type": "String"}]})
    assert not assess(no_identity)["ready"], "adding an identity-less entity kept the model ready"
    assert "coverage.entity.identity" in _required_gap_ids(no_identity), "identity-less entity produced no identity gap"

    # (3) Removing authorization from a state-changing action always adds a gap.
    deauthed = copy.deepcopy(base)
    changed = False
    for action in deauthed["actions"]:
        if action.get("effect") in ("command", "transform") and action.get("authorization"):
            del action["authorization"]
            changed = True
    assert changed, "base model had no authorized state-changing action to strip (fixture drift)"
    assert "coverage.action.authorization" in _required_gap_ids(deauthed), "de-authorizing an action produced no authorization gap"
    assert not assess(deauthed)["ready"], "a model with an unauthorized state-changing action was ready"

    # (4) Recommended gaps never become blocking. Removing the recommended
    # transformation leaves the model ready (requiredGaps stay 0) while raising the
    # recommended count - a recommendation must never silently gate readiness.
    no_transform = copy.deepcopy(base)
    no_transform.pop("collectionTransforms", None)
    base_rec = coverage_report(base, load_coverage_model())["summary"]["recommended"]
    less_rec = coverage_report(no_transform, load_coverage_model())["summary"]["recommended"]
    assert less_rec > base_rec, "removing the transformation did not raise the recommended-gap count"
    assert assess(no_transform)["ready"], "a recommended gap blocked readiness"

    # (5) Reordering IR collections never changes any verdict (order-independence).
    shuffled = copy.deepcopy(base)
    shuffled["concepts"] = list(reversed(shuffled["concepts"]))
    shuffled["actions"] = list(reversed(shuffled["actions"]))
    assert _gap_keys(shuffled) == _gap_keys(base), "reordering collections changed the coverage gaps"
    assert assess(shuffled)["ready"] == assess(base)["ready"], "reordering collections changed the ready verdict"
    assert compare(base, shuffled) == [], "reordering collections produced a semantic delta"

    # (6) Profile-order independence: reversing the declared profiles list is inert.
    reprofiled = copy.deepcopy(base)
    reprofiled["profiles"] = list(reversed(reprofiled["profiles"]))
    assert _gap_keys(reprofiled) == _gap_keys(base), "reversing the profiles list changed the coverage gaps"

    # (7) Merge is order-independent, and renaming an identity via a valid identity
    # map preserves merge meaning (the cross-namespace alias folds into the canonical
    # identity rather than producing a second concept).
    merge_a = _load("tests/fixtures/merge/customer-orders-a.json")
    merge_b = _load("tests/fixtures/merge/customer-orders-b.json")
    unified_ab, _ = merge([merge_a, merge_b], "Prop", "shop")
    unified_ba, _ = merge([merge_b, merge_a], "Prop", "shop")
    assert {c["qualifiedName"] for c in unified_ab["concepts"]} == {c["qualifiedName"] for c in unified_ba["concepts"]}, "merge was not order-independent"
    alias = _load("tests/fixtures/merge/crm-alias.json")
    aliased, _ = merge([merge_a, alias], "Prop", "shop")
    names = {c["qualifiedName"] for c in aliased["concepts"]}
    assert "shop.Customer" in names and "crm.Client" not in names, "identity-map rename did not preserve merge meaning"

    # (8) An unknown construct cannot silently pass: an undeclared instance trait is
    # always surfaced as an unknown trait, never accepted by default.
    tainted = copy.deepcopy(base)
    tainted["concepts"][0].setdefault("traits", []).append("zzz-not-a-real-role")
    assert "zzz-not-a-real-role" in role_report(tainted, contracts)["unknownTraits"], "an undeclared trait was silently accepted"


def reference_cycle(graph):
    indegree = defaultdict(int)
    nodes = set(graph)
    for source, targets in graph.items():
        nodes.update(targets)
        for target in targets: indegree[target] += 1
    queue = [node for node in nodes if indegree[node] == 0]
    visited = 0
    while queue:
        node = queue.pop()
        visited += 1
        for target in graph[node]:
            indegree[target] -= 1
            if indegree[target] == 0: queue.append(target)
    return visited != len(nodes)


def main() -> None:
    rng = random.Random(20260722)
    for size in range(2, 12):
        for _ in range(30):
            graph = defaultdict(set)
            for source in range(size):
                for target in range(size):
                    if source != target and rng.random() < 0.12: graph[source].add(target)
            assert Analyzer.has_cycle(graph) == reference_cycle(graph)

    base = {
        "$schema": "../schemas/model-ir-v1.schema.json", "irVersion": "1.0.0",
        "id": "PropertyModel", "module": "KCF",
        "concepts": [{"id": "Item", "qualifiedName": "test.Item", "kind": "ENTITY", "references": []}],
    }
    operations = ["update", "delete", "bulk-update", "bulk-delete"]
    for operation in operations:
        model = copy.deepcopy(base)
        model["actions"] = [{"id": "Mutate", "effect": "command", "operation": operation, "scope": "set" if operation.startswith("bulk") else "record", "target": "test.Item", "inputCardinality": "many", "outputCardinality": "many", "idempotency": "conditional"}]
        ids = {item["rule_id"] for item in Analyzer(model).run()}
        assert "stack.security.authorization" in ids
        if operation.startswith("bulk"):
            assert "action.set.selection-required" in ids and "action.set.atomicity" in ids

    assert compare(base, base) == []
    removed = copy.deepcopy(base); removed["concepts"] = []
    assert any(item["classification"] == "breaking" for item in compare(base, removed))
    added = copy.deepcopy(base); added["concepts"].append({"id": "Extra", "qualifiedName": "test.Extra", "kind": "ENTITY", "references": []})
    assert compare(base, added) == [{"classification": "compatible", "subject": "test.Extra", "change": "concept added"}]
    knowledge = copy.deepcopy(base)
    knowledge["assertions"] = [{"id": "Claim", "subject": "test.Item", "predicate": "active", "object": True, "status": "asserted"}]
    revised = copy.deepcopy(knowledge); revised["assertions"][0]["status"] = "retracted"
    assert any(item["classification"] == "breaking" and item["subject"] == "Claim" for item in compare(knowledge, revised))
    metamorphic()
    print("PASS deterministic relationship, action-safety, knowledge-evolution, semantic-version, and metamorphic/adversarial properties")


if __name__ == "__main__":
    main()
