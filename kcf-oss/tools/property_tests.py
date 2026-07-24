from __future__ import annotations

from collections import defaultdict
import copy
import random

from semantic_analyzer import Analyzer
from semantic_delta import compare


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
    print("PASS deterministic relationship, action-safety, knowledge-evolution, and semantic-version properties")


if __name__ == "__main__":
    main()
