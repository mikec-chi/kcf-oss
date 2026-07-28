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
import hashlib
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


# The encoding-review lifecycle (P5). Linkage (trace-linked) proves nothing was
# dropped or invented; it does NOT prove the encoding faithfully means the source.
# That is a review that walks: trace-linked -> encoding-reviewed (a human checked the
# encoding) -> semantically-confirmed (a human confirmed it means the source). disputed
# / superseded are off-path. A construct is "confirmed" once its encoding is reviewed.
_CONFIRMED_STATES = {"encoding-reviewed", "semantically-confirmed"}
_OFFPATH_STATES = {"disputed", "superseded"}
_STATE_RANK = {"trace-linked": 0, "encoding-reviewed": 1, "semantically-confirmed": 2, "disputed": -1, "superseded": -2}


def _excerpt_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def confirmation_issues(record: dict, link_constructs: set[str], segment_text: str | None) -> list[str]:
    """Governance a confirmation record must satisfy before it may count as confirming
    (R3). A record that merely says ``reviewState: semantically-confirmed`` proves
    nothing - anyone can type that. To count, it must name WHO reviewed it and WHEN,
    record an ``accept`` disposition and the source version, be about a construct the
    link actually claims, and carry an excerpt hash that MATCHES the referenced source
    segment (so the encoding cannot be confirmed against text that has since changed or
    that was never there). Returns the list of failed requirements (empty = governed)."""
    issues: list[str] = []
    if record.get("reviewerDisposition") != "accept":
        issues.append("disposition-not-accept")
    if not record.get("reviewer"):
        issues.append("missing-reviewer")
    if not record.get("reviewedAt"):
        issues.append("missing-reviewedAt")
    if not record.get("sourceVersion"):
        issues.append("missing-sourceVersion")
    if record.get("semanticIdentity") not in link_constructs:
        issues.append("identity-not-in-link")
    excerpt_hash = record.get("sourceExcerptHash")
    if not excerpt_hash:
        issues.append("missing-sourceExcerptHash")
    elif segment_text is None:
        issues.append("segment-not-found")
    elif excerpt_hash != _excerpt_hash(segment_text):
        issues.append("excerpt-hash-mismatch")
    return issues


def source_coverage(document: dict, model: dict, trace: dict) -> dict:
    segments = {segment["segmentId"]: segment for segment in document.get("segments", [])}
    segment_ids = list(segments)
    segment_set = set(segment_ids)
    constructs = construct_ids(model)

    covered: set[str] = set()
    sourced: set[str] = set()
    dangling_segments: set[str] = set()
    dangling_constructs: set[str] = set()
    # All review states asserted about each sourced construct (resolved below).
    states_seen: dict[str, list[str]] = {}
    # Constructs with at least one GOVERNED confirming record (R3), and those whose
    # confirmation CLAIM failed governance (surfaced, never silently accepted).
    governed_confirmed: set[str] = set()
    ungoverned: dict[str, list[str]] = {}

    for link in trace.get("links", []):
        segment_id = link["segmentId"]
        linked = link.get("constructs", [])
        link_constructs = set(linked)
        if segment_id not in segment_set:
            dangling_segments.add(segment_id)
        real = [identity for identity in linked if identity in constructs]
        for identity in linked:
            if identity not in constructs:
                dangling_constructs.add(identity)
        sourced.update(real)
        for identity in real:
            states_seen.setdefault(identity, [])
        if real and segment_id in segment_set:
            covered.add(segment_id)
        segment_text = segments.get(segment_id, {}).get("text")
        for record in link.get("assertions", []):
            identity = record.get("semanticIdentity")
            if identity not in constructs:
                continue
            state = record.get("reviewState", "trace-linked")
            states_seen.setdefault(identity, []).append(state)
            if state in _CONFIRMED_STATES:
                issues = confirmation_issues(record, link_constructs, segment_text)
                if issues:
                    ungoverned.setdefault(identity, []).extend(issues)
                else:
                    governed_confirmed.add(identity)

    def _resolve(states: list[str]) -> str:
        # Off-path (disputed/superseded) dominates: a disputed encoding is not
        # confirmed even if another record claims it is. Otherwise the highest rank.
        offpath = [state for state in states if state in _OFFPATH_STATES]
        if offpath:
            return min(offpath, key=lambda state: _STATE_RANK.get(state, 0))
        return max([*states, "trace-linked"], key=lambda state: _STATE_RANK.get(state, 0))

    review_state = {identity: _resolve(states) for identity, states in states_seen.items()}
    uncovered = [segment_id for segment_id in segment_ids if segment_id not in covered]
    disputed = {identity for identity, state in review_state.items() if state in _OFFPATH_STATES}
    # A construct is confirmed only when it has a GOVERNED confirming record AND is not
    # disputed - an ungoverned or disputed encoding is never counted as confirmed.
    confirmed = {identity for identity in governed_confirmed if identity not in disputed}
    unconfirmed = sorted(sourced - confirmed)
    ungoverned_confirmations = [
        {"identity": identity, "issues": sorted(set(ungoverned[identity]))}
        for identity in sorted(ungoverned)
        if identity not in confirmed
    ]
    state_counts: dict[str, int] = {}
    for state in review_state.values():
        state_counts[state] = state_counts.get(state, 0) + 1

    report = {
        "sourceCoverageReportVersion": "1.0.0",
        "document": document.get("documentId", "<document>"),
        "model": model.get("id", "<model>"),
        "counts": {
            "segments": len(segment_ids),
            "constructs": len(constructs),
            "coveredSegments": len(covered),
            "sourcedConstructs": len(sourced),
            "confirmedConstructs": len(confirmed),
        },
        "uncoveredSegments": uncovered,
        "unsourcedConstructs": sorted(constructs - sourced),
        "danglingSegments": sorted(dangling_segments),
        "danglingConstructs": sorted(dangling_constructs),
        "reviewStates": state_counts,
        "unconfirmedConstructs": unconfirmed,
        "disputedConstructs": sorted(disputed),
        "ungovernedConfirmations": ungoverned_confirmations,
    }
    report["sourceComplete"] = is_complete(report)
    # source-confirmed is strictly stronger than source-complete: linkage complete AND
    # every sourced construct's encoding reviewed AND nothing disputed/superseded.
    report["sourceConfirmed"] = (
        report["sourceComplete"]
        and bool(sourced)
        and not unconfirmed
        and not disputed
    )
    return report


def is_complete(report: dict) -> bool:
    return not (
        report["uncoveredSegments"]
        or report["unsourcedConstructs"]
        or report["danglingSegments"]
        or report["danglingConstructs"]
    )


def is_confirmed(report: dict) -> bool:
    return bool(report.get("sourceConfirmed"))


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
