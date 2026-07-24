from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = PROJECT_ROOT
MANIFEST_PATH = PROJECT_ROOT / "config" / "grammar-stack.json"
START = re.compile(r"(?m)(?:^|(?<=;))[ \t\r\n]*([A-Za-z][A-Za-z0-9-]*)[ \t]*=")
EXTERNAL = re.compile(r"\?\s*([A-Z][A-Z0-9-]*)\s+([a-z][A-Za-z0-9-]*)\s*\?")


def end_of_rule(text: str, start: int):
    quote = None
    special = False
    comment = False
    i = start
    while i < len(text):
        if comment:
            if text.startswith("*)", i):
                comment = False
                i += 1
        elif special:
            if text[i] == "?":
                special = False
        elif quote:
            if text[i] == quote:
                quote = None
        elif text.startswith("(*", i):
            comment = True
            i += 1
        elif text[i] in "\"'":
            quote = text[i]
        elif text[i] == "?":
            special = True
        elif text[i] == ";":
            return i + 1
        i += 1
    return None


def productions(text: str):
    for match in START.finditer(text):
        end = end_of_rule(text, match.end())
        if end:
            yield match.group(1), text[match.end():end]


def scrub(rhs: str):
    """Remove terminals, special sequences, and comments without mixing quote kinds."""
    result = []
    quote = None
    special = False
    comment = False
    i = 0
    while i < len(rhs):
        if comment:
            if rhs.startswith("*)", i):
                comment = False
                result.append("  ")
                i += 2
                continue
        elif special:
            if rhs[i] == "?":
                special = False
                result.append(" ")
        elif quote:
            if rhs[i] == quote:
                quote = None
                result.append(" ")
        elif rhs.startswith("(*", i):
            comment = True
            result.append("  ")
            i += 2
            continue
        elif rhs[i] == "?":
            special = True
            result.append(" ")
        elif rhs[i] in "\"'":
            quote = rhs[i]
            result.append(" ")
        else:
            result.append(rhs[i])
        i += 1
    return "".join(result)


def validate_file(path: Path):
    text = path.read_text(encoding="utf-8")
    errors = []
    rules = list(productions(text))
    starts = list(START.finditer(text))
    if len(rules) != len(starts):
        errors.append("one or more productions are unterminated")
    names = [name for name, _ in rules]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        errors.append("duplicate definitions: " + ", ".join(duplicates))
    defined = set(names)
    referenced = set()
    for name, rhs in rules:
        clean = scrub(rhs)
        stack = []
        pairs = {")": "(", "]": "[", "}": "{"}
        for char in clean:
            if char in "([{":
                stack.append(char)
            elif char in pairs:
                if not stack or stack.pop() != pairs[char]:
                    errors.append(f"{name}: unbalanced {char}")
                    break
        if stack:
            errors.append(f"{name}: unclosed grouping")
        referenced.update(re.findall(r"\b[a-z][a-z0-9-]*\b", clean))
    undefined = sorted(referenced - defined)
    if undefined:
        errors.append("undefined productions: " + ", ".join(undefined))
    if text.count("(*") != text.count("*)"):
        errors.append("unbalanced comments")
    return errors, len(rules), defined, text


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failed = False
    total = 0
    loaded = {}
    for module, spec in manifest["modules"].items():
        path = ROOT / spec["file"]
        if not path.exists():
            print(f"FAIL {module}: missing {spec['file']}")
            failed = True
            continue
        errors, count, defined, text = validate_file(path)
        loaded[module] = (defined, text)
        total += count
        if spec["start"] not in defined:
            errors.append(f"undefined start production {spec['start']}")
        declared = set(spec.get("imports", []))
        for target, rule in EXTERNAL.findall(text):
            if target not in declared:
                errors.append(f"undeclared import {target}.{rule}")
        if errors:
            failed = True
            print(f"FAIL {module} ({count} productions)")
            for error in errors:
                print("  " + error)
        else:
            print(f"PASS {module} ({count} productions)")
    for module, (defined, text) in loaded.items():
        for target, rule in EXTERNAL.findall(text):
            if target not in loaded or rule not in loaded[target][0]:
                print(f"FAIL {module}: unresolved {target}.{rule}")
                failed = True
    print(f"Checked {total} productions in {len(manifest['modules'])} modules.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
