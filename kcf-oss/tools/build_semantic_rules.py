from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
SEMANTICS_ROOT = PROJECT_ROOT / "semantics"
CORE_ROOT = WORKSPACE_ROOT / "semantic-core"
KCF_SOURCE = SEMANTICS_ROOT / "SEMANTIC_VALIDATION.md"
CORE_SOURCE = CORE_ROOT / "semantics" / "semantic-rules.json"
OWNERSHIP_SOURCE = SEMANTICS_ROOT / "legacy-rule-ownership.json"
ANALYZER_SOURCE = PROJECT_ROOT / "tools" / "semantic_analyzer.py"
INVALID_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "invalid"
RULE = re.compile(r"^- `([^`]+)`: (.*)$")
RULE_ID = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$")


def extract_markdown(path: Path) -> list[dict]:
    rules = []
    heading = ""
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("##"):
            heading = raw.lstrip("# ")
        match = RULE.match(raw)
        if match:
            if current:
                rules.append(current)
            rule_id, text = match.groups()
            if not RULE_ID.fullmatch(rule_id):
                current = None
                continue
            current = {
                "id": rule_id,
                "source": "kcf",
                "section": heading,
                "severity": "warning" if "SHOULD" in text else "error",
                "requirement": text.strip(),
            }
        elif current and raw.startswith("  "):
            current["requirement"] += " " + raw.strip()
        elif current:
            rules.append(current)
            current = None
    if current:
        rules.append(current)
    return rules


def analyzer_handlers() -> dict[str, str]:
    tree = ast.parse(ANALYZER_SOURCE.read_text(encoding="utf-8"))
    handlers = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Analyzer":
            continue
        for method in node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for call in ast.walk(method):
                if not isinstance(call, ast.Call) or len(call.args) < 2:
                    continue
                if not isinstance(call.func, ast.Attribute) or call.func.attr != "report":
                    continue
                value = call.args[1]
                if isinstance(value, ast.Constant) and isinstance(value.value, str) and RULE_ID.fullmatch(value.value):
                    handlers[value.value] = method.name
    return handlers


def exercised_rule_ids() -> set[str]:
    spec = importlib.util.spec_from_file_location("kcf_semantic_analyzer", ANALYZER_SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    result = set()
    for path in sorted(INVALID_FIXTURES.glob("*.json")):
        model = json.loads(path.read_text(encoding="utf-8"))
        result.update(item["rule_id"] for item in module.Analyzer(model, validate_schema=False).run())
    return result


def aliases_by_new_id() -> dict[str, list[str]]:
    ownership = json.loads(OWNERSHIP_SOURCE.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for entry in ownership["rules"]:
        old_id, new_id = entry["oldId"], entry.get("newId")
        if new_id and old_id != new_id:
            result.setdefault(new_id, []).append(old_id)
    return result


def phase_for(rule_id: str) -> str:
    prefix = rule_id.split(".", 1)[0]
    return {
        "stack": "structural",
        "kcf": "concepts",
        "action": "actions",
        "relationship": "relationships",
        "lifecycle": "lifecycles",
        "process": "processes",
        "integration": "integration",
        "security": "security",
        "lineage": "lineage",
        "architecture": "emitters",
        "experience": "emitters",
        "design": "emitters",
        "analytics": "emitters",
        "ai": "emitters",
        "organization": "organizational-knowledge",
        "information": "organizational-knowledge",
        "rule": "organizational-knowledge",
        "reasoning": "organizational-knowledge",
        "knowledge": "organizational-knowledge",
    }.get(prefix, "dimensions")


def main() -> None:
    core = json.loads(CORE_SOURCE.read_text(encoding="utf-8"))["rules"]
    merged = {rule["id"]: dict(rule) for rule in core}
    for rule in extract_markdown(KCF_SOURCE):
        if rule["id"] in merged:
            owner = merged[rule["id"]]["source"]
            merged[rule["id"]].update(rule)
            merged[rule["id"]]["source"] = owner
        else:
            merged[rule["id"]] = rule

    handlers = analyzer_handlers()
    exercised = exercised_rule_ids()
    aliases = aliases_by_new_id()
    for rule_id, rule in merged.items():
        if rule_id in exercised:
            rule["enforcement"] = "automated"
        elif rule_id in handlers:
            rule["enforcement"] = "partially-automated"
        elif rule["severity"] == "error":
            rule["enforcement"] = "manual-review"
        else:
            rule["enforcement"] = "profile-dependent"
        rule["phase"] = phase_for(rule_id)
        if rule_id in handlers:
            rule["handler"] = handlers[rule_id]
        if rule_id in aliases:
            rule["aliases"] = sorted(aliases[rule_id])

    output = {
        "$schema": "./semantic-rules.schema.json",
        "version": "2.2.0",
        "sources": [
            CORE_SOURCE.relative_to(WORKSPACE_ROOT).as_posix(),
            KCF_SOURCE.relative_to(WORKSPACE_ROOT).as_posix(),
        ],
        "rules": sorted(merged.values(), key=lambda item: item["id"]),
    }
    (SEMANTICS_ROOT / "semantic-rules.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    counts = {}
    for rule in output["rules"]:
        counts[rule["enforcement"]] = counts.get(rule["enforcement"], 0) + 1
    coverage = {
        "catalogueVersion": output["version"],
        "totalRules": len(output["rules"]),
        "counts": counts,
        "unclassified": [],
        "automatedRuleIds": sorted(exercised),
        "partiallyAutomatedRuleIds": sorted(set(handlers) - exercised),
    }
    (SEMANTICS_ROOT / "coverage.json").write_text(
        json.dumps(coverage, indent=2) + "\n", encoding="utf-8"
    )
    fixture_index = {
        "version": "1.0.0",
        "positiveFixture": "../valid/transportation-ir.json",
        "negativeFixtures": ["../invalid/semantic-failures-ir.json", "../invalid/organizational-knowledge-invalid.json"],
        "automatedRuleIds": sorted(exercised),
        "policy": "Every automated rule is silent for the positive fixture and emitted by the negative fixture.",
    }
    fixture_root = PROJECT_ROOT / "tests" / "fixtures" / "rules"
    fixture_root.mkdir(parents=True, exist_ok=True)
    (fixture_root / "fixture-index.json").write_text(
        json.dumps(fixture_index, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(output['rules'])} KCF semantic rules; coverage={counts}")


if __name__ == "__main__":
    main()
