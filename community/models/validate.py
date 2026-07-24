#!/usr/bin/env python3
"""Validate every community model: each must compile and be `valid` (analyzer-clean).

Run from the repo root:

    python community/models/validate.py

Exits non-zero if any model fails, so CI (and you, before a PR) can gate on it.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent      # community/models
REPO_ROOT = HERE.parents[1]                  # repo root (community/ is top-level)
OSS = REPO_ROOT / "kcf-oss"
for _p in (OSS, OSS / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from compiler import compile_text            # noqa: E402
from semantic_analyzer import Analyzer        # noqa: E402


def main() -> int:
    models = sorted(HERE.glob("*/model.kcf"))
    if not models:
        print("No community models found (community/models/*/model.kcf).")
        return 0

    failures = 0
    for path in models:
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            ir = compile_text(path.read_text(encoding="utf-8"), source=rel)
        except ValueError as exc:  # LexError / ParseError -> "source:line:col: ..."
            print(f"FAIL  {rel}  (compile)  {exc}")
            failures += 1
            continue
        errors = [d for d in Analyzer(ir).run() if d.get("severity") == "error"]
        if errors:
            print(f"FAIL  {rel}  (not valid — {len(errors)} analyzer error(s)):")
            for e in errors[:5]:
                print(f"        - {e.get('ruleId', '?')}: {e.get('message', '')}")
            failures += 1
        else:
            print(f"ok    {rel}")

    print(f"\n{len(models)} model(s) checked, {failures} failing.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
