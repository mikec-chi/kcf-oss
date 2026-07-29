"""Document profiles: input-side extraction guidance keyed on document modality.

Where a pattern scaffold tells an LLM what to build for a business pattern, a
document profile tells it what to build for a *document type* - a flowchart's
nodes/edges become WORK concepts and ORDERING relationships, an org chart's boxes
and lines become the ORGANIZATION dimension, a form's fields become attributes and
rules. Profiles are pure data discovered on a search path
(``KCF_DOCUMENT_PROFILE_PATH``), so an overlay stack can add proprietary document
types without engine changes.

`check_document` validates a source document's declared kind and segment kinds
against the matching profile, catching a segmentation that drifts from the
modality it claims to be.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES_ROOT = PROJECT_ROOT / "config" / "document-profiles"


def profile_roots() -> list[Path]:
    roots: list[Path] = []
    for entry in os.environ.get("KCF_DOCUMENT_PROFILE_PATH", "").split(os.pathsep):
        entry = entry.strip()
        if entry:
            roots.append(Path(entry))
    roots.append(PROFILES_ROOT)
    return roots


def load_document_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for root in profile_roots():
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            profile = json.loads(path.read_text(encoding="utf-8"))
            profiles.setdefault(profile["documentKind"], profile)
    return profiles


def check_document(document: dict, profiles: dict[str, dict]) -> dict:
    document_kind = document.get("documentKind")
    profile = profiles.get(document_kind) if document_kind else None
    used = sorted({segment.get("kind") for segment in document.get("segments", []) if segment.get("kind")})
    known = set(profile["segmentKinds"]) if profile else set()
    warnings: list[str] = []
    if not document_kind:
        warnings.append(
            "no documentKind declared: extraction runs without a modality profile and the "
            "targetDimensions steer it provides. Declare the document's modality (e.g. prose, "
            "image, flowchart, form, org-chart)."
        )
    elif profile is None:
        warnings.append(
            f"documentKind '{document_kind}' has no profile on the search path "
            "(config/document-profiles or KCF_DOCUMENT_PROFILE_PATH): extraction runs without "
            "modality guidance. Add a profile for this kind, or re-declare an existing one."
        )
    return {
        "documentCheckVersion": "1.0.0",
        "document": document.get("documentId", "<document>"),
        "documentKind": document_kind,
        "hasProfile": profile is not None,
        "targetDimensions": profile["targetDimensions"] if profile else [],
        "usedSegmentKinds": used,
        "unknownSegmentKinds": [kind for kind in used if profile and kind not in known],
        "warnings": warnings,
    }


def is_conformant(report: dict) -> bool:
    # Conformance is about segmentation drift, not whether a profile happens to ship: a
    # segment kind foreign to a RESOLVED profile is the only hard failure. A missing or
    # unprofiled modality is a warning (see report["warnings"]) — declaring a modality
    # honestly must never score worse than omitting the field, which would only teach
    # users to strip provenance to pass the gate.
    return not report["unknownSegmentKinds"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a source document's segment kinds against its declared document profile.")
    parser.add_argument("document", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    document = json.loads(args.document.read_text(encoding="utf-8"))
    report = check_document(document, load_document_profiles())
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    import sys
    for warning in report["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    return 0 if is_conformant(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
