"""Apply SME decisions to synthetic (LLM-proposed) knowledge in a model IR.

Synthetic gap-fills enter the model like any other knowledge, but carry their
provenance in the grammar's own vocabulary: ``extractionMethod: "llm"``,
``extractionModel``, ``confidence``, and (for assertions) ``status: "inferred"``.
They are therefore always distinguishable from human-elicited fact and are never
silently promoted.

An SME reviews each proposal and decides confirm / reject. This tool applies
those decisions deterministically:

- confirm: stamp ``reviewedBy`` and ``recordedAt``; flip an assertion's
  ``status`` from ``inferred`` to ``asserted``. The record becomes governed fact.
- reject: remove the record entirely.

``recordedAt`` is passed in (``--as-of``) so the transition is reproducible.
Records left in neither list keep their inferred/unreviewed provenance.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


# Collections whose records carry knowledgeMetadata (reviewedBy / recordedAt).
KNOWLEDGE_COLLECTIONS = (
    "organizations", "information", "rules", "policies",
    "reasoning", "assertions", "identityResolutions",
)
REVIEWABLE_COLLECTIONS = ("concepts", *KNOWLEDGE_COLLECTIONS)


def identity(item: dict) -> str:
    return item.get("qualifiedName") or item.get("id")


def confirm(model: dict, confirm_ids, reject_ids, reviewer: str, as_of: str):
    """Return ``(updated_model, report)`` after applying confirm/reject decisions."""
    model = copy.deepcopy(model)
    confirm_set, reject_set = set(confirm_ids), set(reject_ids)
    overlap = confirm_set & reject_set
    if overlap:
        raise ValueError(f"identities both confirmed and rejected: {sorted(overlap)}")

    report = {"reviewer": reviewer, "asOf": as_of, "confirmed": [], "rejected": [], "notFound": []}
    seen: set[str] = set()

    for collection in REVIEWABLE_COLLECTIONS:
        retained = []
        for item in model.get(collection, []):
            marker = identity(item)
            if marker in reject_set:
                seen.add(marker)
                report["rejected"].append(marker)
                continue
            if marker in confirm_set:
                seen.add(marker)
                _stamp_confirmed(collection, item, reviewer, as_of)
                report["confirmed"].append(marker)
            retained.append(item)
        if collection in model:
            model[collection] = retained

    report["notFound"] = sorted((confirm_set | reject_set) - seen)
    report["confirmed"].sort()
    report["rejected"].sort()
    return model, report


def _stamp_confirmed(collection: str, item: dict, reviewer: str, as_of: str) -> None:
    if collection == "concepts":
        metadata = item.setdefault("metadata", {})
        metadata["reviewedBy"] = reviewer
        metadata["recordedAt"] = as_of
        return
    item["reviewedBy"] = reviewer
    item.setdefault("recordedAt", as_of)
    if collection == "assertions" or "status" in item:
        item["status"] = "asserted"


def _decisions_from_args(args) -> tuple[list[str], list[str]]:
    confirm_ids: list[str] = []
    reject_ids: list[str] = []
    if args.decisions:
        payload = json.loads(args.decisions.read_text(encoding="utf-8"))
        confirm_ids += payload.get("confirm", [])
        reject_ids += payload.get("reject", [])
    if args.confirm:
        confirm_ids += [item for chunk in args.confirm for item in chunk.split(",") if item]
    if args.reject:
        reject_ids += [item for chunk in args.reject for item in chunk.split(",") if item]
    return confirm_ids, reject_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply SME confirm/reject decisions to synthetic knowledge in a KCF model IR.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--reviewer", required=True, help="the SME identity to record as reviewedBy")
    parser.add_argument("--as-of", required=True, help="ISO timestamp to record as recordedAt")
    parser.add_argument("--decisions", type=Path, help="JSON file: {\"confirm\": [...], \"reject\": [...]}")
    parser.add_argument("--confirm", action="append", help="comma-separated identities to confirm")
    parser.add_argument("--reject", action="append", help="comma-separated identities to reject")
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    confirm_ids, reject_ids = _decisions_from_args(args)
    updated, report = confirm(model, confirm_ids, reject_ids, args.reviewer, args.as_of)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    report_text = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(report_text, encoding="utf-8")
    else:
        print(report_text, end="")
    return 1 if report["notFound"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
