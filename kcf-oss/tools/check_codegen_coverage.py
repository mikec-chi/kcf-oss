#!/usr/bin/env python3
"""Cross-stage codegen-coverage gate.

For every IR construct a codegen LLM must handle, assert it survives the whole
pipeline:

  A. Elicit    — the elicitation process prompts for it (mcp/_tools.py)
  B. IR        — authoring it populates the IR (proven by compiling the reference
                 models and taking the union of what they produce)
  C. Codegen   — it is mapped in CONSTRUCT_COVERAGE.md AND shown in a worked example
                 (a stack EXAMPLE.md coverage audit, or COOKBOOK.md)

This is the guard against "documented but never realizable": add a concept kind or a
profile block to the grammar and forget to elicit/map/exemplify it, and this fails.

Run from the kcf-oss root:  python tools/check_codegen_coverage.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from compiler import compile_file  # noqa: E402

# Reference models whose union must exercise every codegen-relevant construct.
REFERENCE_MODELS = ["business-application", "entity-rich", "quantitative",
                    "analytics-ai", "capability-skill", "profiles", "knowledge-ops"]

# A few concept "kinds" in the schema enum materialize as their own top-level array
# rather than a `concepts[]` entry — reachability is proven by the array's presence.
KIND_IR_ALIAS = {"LIFECYCLE": ["lifecycles"], "LOGIC": ["propositions", "predicates"],
                 "MATH": ["math"], "RULE": ["rules"]}

# Constructs excused from stage B (IR-reachability by authoring) with the reason.
IR_AUTHORING_EXCEPTIONS = {
    "plans": "IR-supported but not yet in the ergonomic authoring surface (tracked)",
}

# Profile sections (each authored as a top-level block → ir[section]).
PROFILE_SECTIONS = ["integration", "security", "lineage", "architecture",
                    "experience", "design", "analytics", "ai"]

# Tail top-level arrays that must be elicited + IR-reachable + exampled.
TAIL_ARRAYS = ["calendars", "routes", "units", "propositions", "predicates", "math",
               "information", "reasoning", "organizations", "authorities",
               "capabilities", "skills", "allocations", "mutations", "processes",
               "assertions", "identityResolutions", "knowledgeQueries"]

# Elicitation synonyms (a construct counts as "elicited" if any token appears).
ELICIT_TOKENS = {
    "ORGANIZATIONAL": ["organization"], "LOGIC": ["proposition", "predicate"],
    "MATH": ["formula", "function", "optimize", "distribution", "simulation"],
    "identityResolutions": ["identity-resolution"],
    "knowledgeQueries": ["knowledge-query"], "units": ["unit"],
    "propositions": ["proposition"], "predicates": ["predicate"],
    "calendars": ["calendar"], "routes": ["route"], "allocations": ["allocation"],
    "mutations": ["mutation"], "processes": ["process"], "assertions": ["assertion"],
    "organizations": ["organization"], "authorities": ["authority"],
    "capabilities": ["capability"], "skills": ["skill"], "information": ["information"],
    "reasoning": ["reasoning"], "math": ["formula", "math"],
}


def _tokens_for(name):
    return [t.lower() for t in ELICIT_TOKENS.get(name, [name.rstrip("s").lower()])]


def main():
    schema = json.loads((ROOT / "schemas" / "model-ir-v1.schema.json").read_text("utf-8"))
    concept_kinds = schema["$defs"]["concept"]["properties"]["kind"]["enum"]

    elicit = (ROOT / "mcp" / "_tools.py").read_text("utf-8").lower()
    coverage = (ROOT / "codegen" / "CONSTRUCT_COVERAGE.md").read_text("utf-8").lower()
    cookbook = (ROOT / "codegen" / "COOKBOOK.md").read_text("utf-8").lower()
    examples = "\n".join(p.read_text("utf-8")
                         for p in (ROOT / "codegen" / "stacks").glob("*/EXAMPLE.md")).lower()
    codegen_corpus = cookbook + "\n" + examples  # stage C "shown" corpus

    # Stage B: union of IR keys + concept kinds the reference models actually produce.
    ir_keys, ir_kinds = set(), set()
    for name in REFERENCE_MODELS:
        ir = compile_file(ROOT / "tests" / "domains" / f"{name}.kcf")
        ir_keys |= {k for k, v in ir.items() if v}
        ir_kinds |= {c.get("kind") for c in ir.get("concepts", [])}

    rows, failures = [], []

    def check(label, elicited, reachable, mapped, shown, ir_exc=None):
        ok = elicited and (reachable or ir_exc) and mapped and shown
        b = "exc" if (ir_exc and not reachable) else ("ok" if reachable else "MISS")
        rows.append((label, "ok" if elicited else "MISS", b,
                     "ok" if mapped else "MISS", "ok" if shown else "MISS"))
        if not ok:
            failures.append(label)

    # Concept-kind dimensions
    for kind in concept_kinds:
        toks = _tokens_for(kind)
        elicited = any(t in elicit for t in toks) or kind.lower() in elicit
        reachable = kind in ir_kinds or any(a in ir_keys for a in KIND_IR_ALIAS.get(kind, []))
        mapped = kind.lower() in coverage
        shown = kind.lower() in codegen_corpus
        check(f"kind {kind}", elicited, reachable, mapped, shown)

    # Profile sections
    for sec in PROFILE_SECTIONS:
        check(f"profile {sec}", sec in elicit, sec in ir_keys, sec in coverage,
              sec in codegen_corpus)

    # Tail arrays
    for arr in TAIL_ARRAYS:
        toks = _tokens_for(arr)
        elicited = any(t in elicit for t in toks)
        reachable = arr in ir_keys
        mapped = any(t in coverage for t in toks) or arr.lower() in coverage
        shown = any(t in codegen_corpus for t in toks) or arr.lower() in codegen_corpus
        check(f"array {arr}", elicited, reachable, mapped, shown)

    # Known authoring-surface exceptions (must be documented, not silently absent).
    for name, reason in IR_AUTHORING_EXCEPTIONS.items():
        documented = name.lower() in coverage
        rows.append((f"except {name}", "-", "exc" if documented else "MISS",
                     "ok" if documented else "MISS", "-"))
        if not documented:
            failures.append(f"{name} (undocumented authoring exception)")

    # Report
    w = max(len(r[0]) for r in rows)
    print(f"{'construct':<{w}}  elicit  IR    map   shown")
    for label, a, b, c, d in rows:
        print(f"{label:<{w}}  {a:<6}  {b:<4}  {c:<4}  {d}")

    if failures:
        print(f"\nFAIL — {len(failures)} construct(s) not covered end to end:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASS — all {len(rows)} constructs elicited + IR-reachable + shown "
          f"(with {len(IR_AUTHORING_EXCEPTIONS)} documented authoring exception).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
