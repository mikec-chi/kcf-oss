from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_ROOT = PROJECT_ROOT / "grammars"


def normalized(text: str):
    lines = [line.rstrip().replace("\t", "    ") for line in text.replace("\r\n", "\n").split("\n")]
    result = "\n".join(lines).rstrip() + "\n"
    return result


def main():
    parser = argparse.ArgumentParser(description="Normalize KCF EBNF whitespace and line endings.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    changed = []
    for path in sorted(GRAMMAR_ROOT.rglob("*.ebnf")):
        original = path.read_text(encoding="utf-8")
        result = normalized(original)
        if original != result:
            changed.append(str(path.relative_to(PROJECT_ROOT)))
            if args.write:
                path.write_text(result, encoding="utf-8", newline="\n")
    if changed:
        print(("Normalized" if args.write else "Needs normalization") + ": " + ", ".join(changed))
    else:
        print("PASS canonical whitespace and line endings")
    return 0 if args.write or not changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
