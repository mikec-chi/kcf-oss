"""Tier synthetic knowledge into an SME review queue.

Simplification C: a synthesized model is a flat pile of inferred records, and
asking a human to confirm each one invites automation bias and wastes attention
on textbook structure. This orders the synthetic records so the SME spends
judgment where it matters:

- ``review`` tier: low-confidence (or unscored) items - decided individually;
- ``bulk`` tier: high-confidence items - offered for bulk confirmation.

It only *organizes*; it confirms nothing. The output feeds ``confirm_synthetic``.
Synthetic knowledge is identified by the grammar's own provenance vocabulary
(``extractionMethod: llm``, an assertion ``status: inferred``, or a concept's
``metadata.seededFrom``), so this is domain-agnostic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


KNOWLEDGE_COLLECTIONS = (
    "organizations", "information", "rules", "policies",
    "reasoning", "assertions", "identityResolutions",
)
DEFAULT_HIGH_CONFIDENCE = 0.8


def _identity(item: dict) -> str:
    return item.get("qualifiedName") or item.get("id")


def _decision(identity, collection, confidence, summary, seeded_from, threshold):
    tier = "bulk" if (confidence is not None and confidence >= threshold) else "review"
    return {
        "id": identity,
        "collection": collection,
        "tier": tier,
        "confidence": confidence,
        "summary": summary,
        "seededFrom": seeded_from,
    }


def review_queue(model: dict, high_confidence: float = DEFAULT_HIGH_CONFIDENCE) -> dict:
    decisions = []
    for collection in KNOWLEDGE_COLLECTIONS:
        for item in model.get(collection, []):
            synthetic = item.get("extractionMethod") == "llm" or (collection == "assertions" and item.get("status") == "inferred")
            if not synthetic:
                continue
            summary = item.get("condition") or item.get("proposition") or item.get("predicate") or _identity(item)
            decisions.append(_decision(_identity(item), collection, item.get("confidence"), str(summary), item.get("seededFrom"), high_confidence))
    for concept in model.get("concepts", []):
        metadata = concept.get("metadata") or {}
        if metadata.get("extractionMethod") != "llm" and not metadata.get("seededFrom"):
            continue
        decisions.append(_decision(_identity(concept), "concepts", metadata.get("confidence"),
                                   f"{concept.get('kind', 'concept')} {_identity(concept)}", metadata.get("seededFrom"), high_confidence))

    # review tier first (least certain first), then bulk; stable by id within a tier
    tier_rank = {"review": 0, "bulk": 1}
    decisions.sort(key=lambda entry: (tier_rank[entry["tier"]], entry["confidence"] if entry["confidence"] is not None else -1.0, entry["id"]))

    review = sum(1 for entry in decisions if entry["tier"] == "review")
    return {
        "reviewQueueVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "highConfidenceThreshold": high_confidence,
        "counts": {"review": review, "bulk": len(decisions) - review, "total": len(decisions)},
        "decisions": decisions,
    }


def by_segment(model: dict, trace: dict, high_confidence: float = DEFAULT_HIGH_CONFIDENCE) -> dict:
    """Regroup the review queue by the source segment each construct came from,
    so the SME confirms 'this segment's prose -> these constructs' faithfully,
    paragraph by paragraph. Synthetic items with no trace link are surfaced
    separately (ungrounded)."""
    queue = review_queue(model, high_confidence)
    segment_of: dict[str, str] = {}
    for link in trace.get("links", []):
        for construct in link.get("constructs", []):
            segment_of.setdefault(construct, link["segmentId"])
    groups: dict[str, list] = {}
    unsourced: list = []
    for decision in queue["decisions"]:
        segment_id = segment_of.get(decision["id"])
        (groups.setdefault(segment_id, []) if segment_id is not None else unsourced).append(decision)
    return {
        "reviewBySegmentVersion": "1.0.0",
        "model": queue["model"],
        "bySegment": [{"segmentId": segment_id, "decisions": groups[segment_id]} for segment_id in sorted(groups)],
        "unsourced": unsourced,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a tiered SME review queue from a synthetic model.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--high-confidence", type=float, default=DEFAULT_HIGH_CONFIDENCE)
    parser.add_argument("--by-segment", type=Path, help="a source-trace-v1 JSON; group the queue by originating segment")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    if args.by_segment:
        result = by_segment(model, json.loads(args.by_segment.read_text(encoding="utf-8")), args.high_confidence)
    else:
        result = review_queue(model, args.high_confidence)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
