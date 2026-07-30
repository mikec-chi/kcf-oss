"""Structural validation for the OPEN review-envelope contract (weakness #7).

KCF-OSS records a human review decision as a portable envelope bound to the source + model revisions
it was made against. This tool validates the envelope STRUCTURALLY only - it deliberately does NOT
authenticate the reviewer, verify their authority, or check the signature cryptographically. Those are
an external platform's responsibility (identity, authority, key trust). A structurally-valid but
unsigned/unverified envelope is provenance metadata, never proof of governed approval.

Use it to (a) build a well-formed envelope from OSS-available facts, and (b) validate an envelope a
platform hands back before recording it against a confirmation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "review-envelope-v1.schema.json"

# Fields an external verifier signs over. KCF-OSS names them so signer/verifier agree on the payload,
# but does NOT itself compute or check any signature.
GOVERNED_FIELDS = ("reviewer", "reviewerRole", "authority", "decision", "constructIds",
                   "sourceRevision", "modelRevision", "recordedAt")


def build_envelope(*, reviewer: str, decision: str, construct_ids: list[str], source_revision: str,
                   model_revision: str, recorded_at: str, reviewer_role: str | None = None,
                   authority: str | None = None, rationale: str | None = None) -> dict:
    """Assemble a well-formed (unsigned) review envelope. An external platform may add signature/
    signatureAlgorithm afterward; KCF-OSS treats those as opaque."""
    return {
        "reviewEnvelopeVersion": "1.0.0",
        "reviewer": reviewer,
        "reviewerRole": reviewer_role,
        "authority": authority,
        "decision": decision,
        "constructIds": list(construct_ids),
        "sourceRevision": source_revision,
        "modelRevision": model_revision,
        "recordedAt": recorded_at,
        "rationale": rationale,
        "signature": None,
        "signatureAlgorithm": None,
    }


def signing_payload(envelope: dict) -> dict:
    """The canonical subset an external platform should sign/verify over. Returned so the signer and
    the verifier agree on exactly which fields are governed. KCF-OSS never signs it itself."""
    return {k: envelope.get(k) for k in GOVERNED_FIELDS}


def validate_envelope(envelope: dict) -> dict:
    """Structural validation only. Returns {ok, errors, signed}. `signed` reports whether a signature
    is present - it is NOT a verification result (KCF-OSS cannot and does not verify it)."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(envelope)]
    return {
        "ok": not errors,
        "errors": errors,
        "signed": bool(envelope.get("signature")),
        "note": "structural validation only; reviewer identity, authority, and signature are NOT verified by KCF-OSS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Structurally validate a KCF review envelope (no authentication).")
    parser.add_argument("envelope", type=Path)
    args = parser.parse_args()
    result = validate_envelope(json.loads(args.envelope.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
