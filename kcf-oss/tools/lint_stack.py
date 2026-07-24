from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

from validate_stack import ROOT, EXTERNAL, productions, scrub


MANIFEST_PATH = ROOT / "config" / "grammar-stack.json"


def references(rhs, defined):
    return set(re.findall(r"\b[a-z][a-z0-9-]*\b", scrub(rhs))) & defined


def cycles(graph):
    found = set()
    visiting, visited = set(), set()
    def visit(node, path):
        if node in visiting:
            cycle = path[path.index(node):] + [node]
            rotations = [tuple(cycle[i:-1] + cycle[:i] + [cycle[i]]) for i in range(len(cycle)-1)]
            found.add(min(rotations))
            return
        if node in visited:
            return
        visiting.add(node)
        for target in graph[node]:
            visit(target, path + [target])
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node, [node])
    return found


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    warnings, errors = [], []
    module_names = set(manifest["modules"])
    graph = {
        module: set(spec.get("imports", [])) | set(spec.get("semanticImports", []))
        for module, spec in manifest["modules"].items()
    }
    for module, dependencies in graph.items():
        for dependency in sorted(dependencies - module_names):
            errors.append(f"{module}: unknown dependency {dependency}")
    allowed = {frozenset(pair) for pair in manifest.get("allowedTypeOnlyCycles", [])}
    for cycle in cycles(graph):
        members = frozenset(cycle[:-1])
        if members not in allowed:
            errors.append("undeclared import cycle: " + " -> ".join(cycle))
    exported = defaultdict(set)
    for spec in manifest["modules"].values():
        text = (ROOT / spec["file"]).read_text(encoding="utf-8")
        for target, rule in EXTERNAL.findall(text):
            exported[target].add(rule)
    for module, spec in manifest["modules"].items():
        text = (ROOT / spec["file"]).read_text(encoding="utf-8")
        rules = dict(productions(text))
        defined = set(rules)
        start = spec["start"]
        reached, pending = set(), [start, *exported[module]]
        while pending:
            name = pending.pop()
            if name in reached or name not in rules:
                continue
            reached.add(name)
            pending.extend(references(rules[name], defined) - reached)
        external_aliases = {name for name, rhs in rules.items() if EXTERNAL.search(rhs)}
        unreachable = sorted(defined - reached - external_aliases)
        if unreachable:
            warnings.append(f"{module}: unreachable productions: {', '.join(unreachable)}")
        used_imports = {target for target, _ in EXTERNAL.findall(text)}
        unused = set(spec.get("imports", [])) - used_imports
        if unused:
            warnings.append(f"{module}: unused grammar imports: {', '.join(sorted(unused))}")
        for name, rhs in rules.items():
            if re.search(r"\{\s*\[", scrub(rhs)):
                warnings.append(f"{module}.{name}: repetition contains nullable optional")
    for item in warnings:
        print("WARN", item)
    for item in errors:
        print("ERROR", item)
    print(f"Lint complete: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
