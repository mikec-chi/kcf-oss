from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_stack import ROOT, EXTERNAL, productions


MANIFEST_PATH = ROOT / "config" / "grammar-stack.json"


TOKEN = re.compile(
    r'''(?P<special>\?[^?]*\?)|(?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|'''
    r'''(?P<identifier>[A-Za-z][A-Za-z0-9-]*)|(?P<other>.)''', re.S
)


def load():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    grammars = {}
    for module, spec in manifest["modules"].items():
        grammars[module] = dict(productions((ROOT / spec["file"]).read_text(encoding="utf-8")))
    return manifest, grammars


def resolve(module: str):
    manifest, grammars = load()
    if module not in grammars:
        raise ValueError(f"unknown module {module}")
    start = manifest["modules"][module]["start"]
    pending = [(module, start)]
    emitted = set()
    lines = [f"(* Resolved KCF grammar: {module}. *)"]
    while pending:
        owner, name = pending.pop()
        if (owner, name) in emitted:
            continue
        if owner not in grammars or name not in grammars[owner]:
            raise ValueError(f"unresolved production {owner}.{name}")
        emitted.add((owner, name))
        rhs = grammars[owner][name]
        exact = re.fullmatch(r"\s*\?\s*([A-Z][A-Z0-9-]*)\s+([a-z][A-Za-z0-9-]*)\s*\?\s*;", rhs)
        if exact:
            target, target_rule = exact.groups()
            rendered = f"{target.lower()}--{target_rule} ;"
            pending.append((target, target_rule))
        else:
            parts = []
            for token in TOKEN.finditer(rhs):
                kind, value = token.lastgroup, token.group()
                if kind == "identifier" and value in grammars[owner]:
                    parts.append(f"{owner.lower()}--{value}")
                    pending.append((owner, value))
                elif kind == "special":
                    match = EXTERNAL.fullmatch(value)
                    if match:
                        target, target_rule = match.groups()
                        parts.append(f"{target.lower()}--{target_rule}")
                        pending.append((target, target_rule))
                    else:
                        parts.append(value)
                else:
                    parts.append(value)
            rendered = "".join(parts)
        lines.append(f"{owner.lower()}--{name} = {rendered}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module")
    parser.add_argument("output", nargs="?", type=Path)
    args = parser.parse_args()
    text = resolve(args.module)
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
