"""Measure source-relative coverage: does the model faithfully cover the prose?

Grammar coverage asks "is the model complete against the grammar's checklist?"
Source coverage asks the natural-language question: "does the extracted model
account for everything in the validated document, and is everything in the model
grounded in the document?" It reconciles a segmented source document against the
model IR via a side ``source-trace`` (segment -> construct identities), reporting
in both directions:

- ``uncoveredSegments`` - prose that produced no construct (missed extraction);
- ``unsourcedConstructs`` - constructs citing no segment (ungrounded additions);
- ``danglingSegments`` / ``danglingConstructs`` - trace links that reference a
  segment or construct that does not exist (integrity).

It proves neither that a construct *semantically* matches its segment (that is the
human's by-segment confirmation) nor that extraction was correct - it proves that
nothing was silently dropped or invented. Domain-agnostic: it reads only
identities and segment ids.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


IDENTITY_COLLECTIONS = (
    "concepts", "relationships", "lifecycles", "actions", "collectionTransforms",
    "organizations", "information", "rules", "policies", "reasoning",
    "assertions", "identityResolutions", "knowledgeQueries",
)


def construct_ids(model: dict) -> set[str]:
    identities: set[str] = set()
    for collection in IDENTITY_COLLECTIONS:
        for item in model.get(collection, []):
            identity = item.get("qualifiedName") or item.get("id")
            if identity:
                identities.add(identity)
    return identities


def source_coverage(document: dict, model: dict, trace: dict) -> dict:
    segment_ids = [segment["segmentId"] for segment in document.get("segments", [])]
    segment_set = set(segment_ids)
    constructs = construct_ids(model)

    covered: set[str] = set()
    sourced: set[str] = set()
    dangling_segments: set[str] = set()
    dangling_constructs: set[str] = set()

    for link in trace.get("links", []):
        segment_id = link["segmentId"]
        linked = link.get("constructs", [])
        if segment_id not in segment_set:
            dangling_segments.add(segment_id)
        real = [identity for identity in linked if identity in constructs]
        for identity in linked:
            if identity not in constructs:
                dangling_constructs.add(identity)
        sourced.update(real)
        if real and segment_id in segment_set:
            covered.add(segment_id)

    uncovered = [segment_id for segment_id in segment_ids if segment_id not in covered]
    return {
        "sourceCoverageReportVersion": "1.0.0",
        "document": document.get("documentId", "<document>"),
        "model": model.get("id", "<model>"),
        "counts": {
            "segments": len(segment_ids),
            "constructs": len(constructs),
            "coveredSegments": len(covered),
            "sourcedConstructs": len(sourced),
        },
        "uncoveredSegments": uncovered,
        "unsourcedConstructs": sorted(constructs - sourced),
        "danglingSegments": sorted(dangling_segments),
        "danglingConstructs": sorted(dangling_constructs),
    }


def is_complete(report: dict) -> bool:
    return not (
        report["uncoveredSegments"]
        or report["unsourcedConstructs"]
        or report["danglingSegments"]
        or report["danglingConstructs"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Report source-relative coverage of an extracted model against its validated prose.")
    parser.add_argument("document", type=Path, help="source-document-v1 JSON")
    parser.add_argument("model", type=Path, help="model IR JSON")
    parser.add_argument("trace", type=Path, help="source-trace-v1 JSON")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    report = source_coverage(
        json.loads(args.document.read_text(encoding="utf-8")),
        json.loads(args.model.read_text(encoding="utf-8")),
        json.loads(args.trace.read_text(encoding="utf-8")),
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if is_complete(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
