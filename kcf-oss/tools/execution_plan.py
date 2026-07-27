"""Classify sentence-like constructs by how they are realized.

KCF's grammars carry meaning-bearing, sentence-like constructs (rules,
propositions, queries, transform predicates). Some can be compiled and emitted
deterministically; some must be interpreted live by an LLM at runtime; and a
third class can be generated *once* into a runtime artifact by a code-generation
LLM (reviewed, then run deterministically). This tool assigns each condition-
bearing construct one of three dispositions:

- ``deterministic`` - the content is a structured, machine-evaluable expression;
  compile it to a guard/query with an emitter. No LLM.
- ``codegen`` - the content is a free-text but checkable predicate; a
  code-generation LLM turns it into a runtime artifact (a validator/query
  function) once, which is reviewed and then runs deterministically.
- ``runtime-llm`` - the content is an open-ended directive (an argument, a goal,
  a judgement) that must be interpreted live by an LLM at runtime.

The default is chosen from the construct type and whether the content is a
structured expression; the safe bias is that prose is NOT assumed deterministic.
An explicit ``executionMode`` on the element (or its ``metadata``) overrides the
default. Domain-agnostic: it reads only condition text, never domain names.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


MODES = {"deterministic", "codegen", "runtime-llm"}

# Only unambiguous, symbolic signals mark content as structured; English words
# ("is", "and", "in") appear in prose too, so they are deliberately excluded.
STRUCTURED = re.compile(r"(==|!=|<=|>=|[<>]|\bimplies\b)")
QUANTIFIED = re.compile(r"^\s*(all|any|exists|none)\b.*:")

# collection -> (field, default disposition when free-text and not overridden)
CONDITION_FIELDS = [
    ("rules", "condition", "codegen"),
    ("reasoning", "proposition", "runtime-llm"),
    ("reasoning", "conclusion", "runtime-llm"),
    ("collectionTransforms", "predicate", "codegen"),
    ("knowledgeQueries", "where", "codegen"),
]
SINGULAR = {"rules": "rule", "reasoning": "reasoning", "collectionTransforms": "transform", "knowledgeQueries": "query"}


def looks_structured(text: str) -> bool:
    return bool(STRUCTURED.search(text) or QUANTIFIED.search(text))


def _override(item: dict):
    return item.get("executionMode") or (item.get("metadata") or {}).get("executionMode")


def _reason(disposition: str, overridden: bool) -> str:
    if overridden:
        return "explicit executionMode override"
    return {
        "deterministic": "structured expression: compile to a deterministic guard/query with an emitter",
        "codegen": "free-text but checkable predicate: generate a runtime artifact once via a code-generation LLM, then run deterministically",
        "runtime-llm": "open-ended directive: carry as-is and interpret live via an LLM at runtime",
    }[disposition]


def execution_plan(model: dict) -> dict:
    elements = []
    for collection, field, default_mode in CONDITION_FIELDS:
        for item in model.get(collection, []):
            content = item.get(field)
            if not isinstance(content, str) or not content.strip():
                continue
            override = _override(item)
            if override in MODES:
                disposition, overridden = override, True
            elif looks_structured(content):
                disposition, overridden = "deterministic", False
            else:
                disposition, overridden = default_mode, False
            elements.append({
                "construct": SINGULAR[collection],
                "id": item.get("qualifiedName") or item.get("id", "<element>"),
                "field": field,
                "content": content,
                "disposition": disposition,
                "reason": _reason(disposition, overridden),
                "overridden": overridden,
            })
    summary = {
        "deterministic": sum(1 for entry in elements if entry["disposition"] == "deterministic"),
        "codegen": sum(1 for entry in elements if entry["disposition"] == "codegen"),
        "runtimeLlm": sum(1 for entry in elements if entry["disposition"] == "runtime-llm"),
    }
    return {"executionPlanVersion": "1.0.0", "model": model.get("id", "<model>"), "summary": summary, "elements": elements}


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan how each sentence-like construct is realized: deterministic emit, code-gen artifact, or runtime LLM.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    plan = execution_plan(json.loads(args.model.read_text(encoding="utf-8")))
    text = json.dumps(plan, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
