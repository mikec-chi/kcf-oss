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
import hashlib
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


def source_revision(text: str) -> str:
    """Stable revision id for an editable .kcf source: sha256 over its exact bytes. Callers bind a
    confirmation to this so a LATER source edit does not silently inherit the earlier approval."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_revision(model: dict) -> str:
    """Stable revision id for a compiled model IR: sha256 over its canonical JSON."""
    return "sha256:" + hashlib.sha256(json.dumps(model, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def confirm(model: dict, confirm_ids, reject_ids, reviewer: str, as_of: str, *,
            source_rev: str | None = None, model_rev: str | None = None):
    """Return ``(updated_model, report)`` after applying confirm/reject decisions.

    Weakness #4 - governance binding: a confirmation is recorded AGAINST the exact source + model
    revisions it was made on. ``model_rev`` defaults to a hash of the model IR; ``source_rev`` must be
    supplied by the caller (KCF-OSS cannot derive the .kcf revision from IR alone). The rule: no
    confirmed IR change is complete until it is reconciled into the editable source or explicitly
    recorded as an external overlay - so we stamp WHICH source revision was reviewed, and a downstream
    tool can detect drift when the live .kcf no longer hashes to that revision."""
    model = copy.deepcopy(model)
    confirm_set, reject_set = set(confirm_ids), set(reject_ids)
    overlap = confirm_set & reject_set
    if overlap:
        raise ValueError(f"identities both confirmed and rejected: {sorted(overlap)}")

    eff_model_rev = model_rev or model_revision(model)
    report = {"reviewer": reviewer, "asOf": as_of, "sourceRevision": source_rev,
              "modelRevision": eff_model_rev, "confirmed": [], "rejected": [], "notFound": []}
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
                _stamp_confirmed(collection, item, reviewer, as_of, source_rev, eff_model_rev)
                report["confirmed"].append(marker)
            retained.append(item)
        if collection in model:
            model[collection] = retained

    report["notFound"] = sorted((confirm_set | reject_set) - seen)
    report["confirmed"].sort()
    report["rejected"].sort()
    return model, report


def _stamp_confirmed(collection: str, item: dict, reviewer: str, as_of: str,
                     source_rev: str | None = None, model_rev: str | None = None) -> None:
    target = item.setdefault("metadata", {}) if collection == "concepts" else item
    target["reviewedBy"] = reviewer
    if collection == "concepts":
        target["recordedAt"] = as_of
    else:
        item.setdefault("recordedAt", as_of)
    # Bind the confirmation to the revisions it was made against (only when provided, to keep records
    # minimal and back-compatible). These let a later tool prove the live source still matches.
    if source_rev is not None:
        target["confirmedAgainstSource"] = source_rev
    if model_rev is not None:
        target["confirmedAgainstModel"] = model_rev
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
    parser.add_argument("--source", type=Path, help="the editable .kcf source; its sha256 is bound to each confirmation")
    parser.add_argument("--source-revision", help="explicit source revision id to bind (overrides --source hashing)")
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    confirm_ids, reject_ids = _decisions_from_args(args)
    source_rev = args.source_revision
    if source_rev is None and args.source:
        source_rev = source_revision(args.source.read_text(encoding="utf-8"))
    updated, report = confirm(model, confirm_ids, reject_ids, args.reviewer, args.as_of, source_rev=source_rev)

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
