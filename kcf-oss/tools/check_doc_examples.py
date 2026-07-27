#!/usr/bin/env python3
"""Doc<->grammar drift gate.

Extracts every fenced ```kcf code block from the documentation and compiles the
*complete* ones against the current parser + analyzer. If a documented example stops
compiling — because the grammar moved and the docs didn't (or vice versa) — the build
fails. This is the cheap guard against the "docs were ahead of the compiler" drift.

What is compiled:
  - a ```kcf block that contains `kcf model ` (a complete model, not a fragment), and
  - has no placeholder tokens (`<Name>`, `...`, `…`, `[BRACKET]`) — those are templates.

What is skipped (intentionally illustrative), by an explicit opt-out only:
  - a block whose first non-blank line is `// doc-skip[: reason]`.

Run from the kcf-oss root:  python tools/check_doc_examples.py
"""
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from compiler import compile_text  # noqa: E402
from semantic_analyzer import Analyzer  # noqa: E402

BLOCK = re.compile(r"```kcf[ \t]*\n(.*?)```", re.DOTALL)
PLACEHOLDER = re.compile(r"<[A-Za-z]|\.\.\.|…|\[[A-Z]")
DOC_GLOBS = ["docs/*.md", "mcp/*.md", "codegen/*.md", "codegen/**/*.md", "*.md"]


def main():
    docs = sorted({p for pat in DOC_GLOBS for p in glob.glob(str(ROOT / pat), recursive=True)})
    total = compiled = skipped = 0
    failures = []
    for doc in docs:
        text = Path(doc).read_text(encoding="utf-8")
        rel = Path(doc).relative_to(ROOT).as_posix()
        for i, m in enumerate(BLOCK.finditer(text), 1):
            body = m.group(1)
            total += 1
            first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
            if first.startswith("// doc-skip"):
                skipped += 1
                continue
            if "kcf model " not in body or PLACEHOLDER.search(body):
                continue  # fragment / skeleton / template — not a complete example
            compiled += 1
            label = f"{rel} block #{i}"
            try:
                ir = compile_text(body, source=rel)
            except Exception as exc:  # noqa: BLE001
                failures.append((label, "compile: " + str(exc).splitlines()[0][:80]))
                continue
            errors = [d for d in Analyzer(ir).run() if d.get("severity") == "error"]
            if errors:
                failures.append((label, "analyzer: " + errors[0]["message"][:80]))

    print(f"doc kcf blocks: {total} total, {compiled} complete-compiled, {skipped} opt-out-skipped")
    if failures:
        print(f"\nFAIL — {len(failures)} documented example(s) do not compile:")
        for label, why in failures:
            print(f"  - {label}: {why}")
        print("\nFix the example or the grammar so they agree, or mark a genuinely "
              "illustrative block with a `// doc-skip: <reason>` first line.")
        return 1
    print("PASS — every complete documented kcf example compiles against the current grammar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
