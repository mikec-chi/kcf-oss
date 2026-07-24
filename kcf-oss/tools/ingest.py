"""The natural-language front door: one report over an extracted model.

Bringing in externally-authored, human-validated natural-language concepts means
an LLM has already translated prose into a model IR plus a source-trace. This tool
turns that into a single readiness verdict rather than four separate runs: it
composes `assess` (validity + grammar coverage + pattern proof + role resolution)
with `source_coverage` (did the model faithfully cover the prose, and is every
construct grounded in it). It does not perform extraction and it does not confirm
knowledge - it reports whether the extraction is buildable and faithful, then the
by-segment review + confirm steps handle human sign-off.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from assess import assess
from source_coverage import is_complete, source_coverage


def ingest(model: dict, document: dict, trace: dict) -> dict:
    assessment = assess(model)
    coverage = source_coverage(document, model, trace)
    return {
        "ingestReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "document": document.get("documentId", "<document>"),
        "valid": assessment["valid"],
        "ready": assessment["ready"],
        "sourceComplete": is_complete(coverage),
        "assess": assessment,
        "sourceCoverage": coverage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest an extracted model: one report over validity, readiness, and source coverage.")
    parser.add_argument("model", type=Path)
    parser.add_argument("document", type=Path, help="source-document-v1 JSON")
    parser.add_argument("trace", type=Path, help="source-trace-v1 JSON")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    report = ingest(
        json.loads(args.model.read_text(encoding="utf-8")),
        json.loads(args.document.read_text(encoding="utf-8")),
        json.loads(args.trace.read_text(encoding="utf-8")),
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if (report["ready"] and report["sourceComplete"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
