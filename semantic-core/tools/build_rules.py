from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEMANTICS_ROOT = PROJECT_ROOT / "semantics"
SOURCES = [SEMANTICS_ROOT / "stack-rules.md", SEMANTICS_ROOT / "action-rules.md"]
RULE = re.compile(r"^- `([^`]+)`: (.*)$")
RULE_ID = re.compile(r"^(?:stack|action)(?:\.[a-z0-9-]+)+$")


def extract(path: Path) -> list[dict]:
    rules: list[dict] = []
    heading = ""
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("##"):
            heading = raw.lstrip("# ")
        match = RULE.match(raw)
        if match:
            if current:
                rules.append(current)
            rule_id, requirement = match.groups()
            if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", rule_id):
                current = None
                continue
            if not RULE_ID.fullmatch(rule_id):
                raise ValueError(f"Non-neutral stable rule {rule_id!r} in {path}")
            current = {
                "id": rule_id,
                "source": "semantic-core",
                "section": heading,
                "severity": "warning" if "SHOULD" in requirement else "error",
                "requirement": requirement.strip(),
            }
        elif current and raw.startswith("  "):
            current["requirement"] += " " + raw.strip()
        elif current:
            rules.append(current)
            current = None
    if current:
        rules.append(current)
    return rules


def main() -> None:
    merged = {}
    for path in SOURCES:
        for rule in extract(path):
            if rule["id"] in merged:
                raise ValueError(f"Duplicate semantic-core rule {rule['id']}")
            merged[rule["id"]] = rule
    output = {
        "$schema": "./semantic-rules.schema.json",
        "version": "1.0.0",
        "sources": [path.relative_to(PROJECT_ROOT).as_posix() for path in SOURCES],
        "rules": sorted(merged.values(), key=lambda item: item["id"]),
    }
    target = SEMANTICS_ROOT / "semantic-rules.json"
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(output['rules'])} shared semantic rules")


if __name__ == "__main__":
    main()
