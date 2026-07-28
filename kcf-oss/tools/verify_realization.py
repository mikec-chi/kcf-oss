"""Verify a codegen realization manifest against the IR (and optionally the repo).

The codegen pack ends every generation with a coverage self-audit whose goal is
``dropped: []`` - a lossless handoff (decision D-005). Historically that audit was
*prose*: the LLM asserting it dropped nothing. Prose is not evidence.

This tool consumes a machine-readable ``realization-manifest-v1`` and checks it:

  * every semantic identity in the IR has exactly one disposition (nothing silently
    dropped, nothing double-counted);
  * every ``realized``/``enriched`` identity carries artifact evidence (a file, and
    ideally a symbol) - no "realized" without something to point at;
  * every ``unsupported``/``deferred``/``delegated``/``out-of-tier`` identity carries
    an explicit note (an honest, recorded gap, not a silent one);
  * with ``--repo``, the referenced artifact/test files exist and (best-effort) the
    named symbols appear in them.

It is deliberately language-agnostic: it proves the *handoff* is accounted for and
grounded in real files. Running the generated tests / type-checker / compiler is a
per-stack execution harness (CI), layered on top of this structural verifier.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ir_identity import anonymous_identities, model_semantic_ids


# The realization verifier accounts for EVERY semantic identity the IR declares - it
# reuses the single authoritative inventory (ir_identity.model_semantic_ids) rather
# than a private subset, so profile/tail sections cannot be silently unverified.
def ir_identities(model: dict) -> dict[str, str]:
    return model_semantic_ids(model)


_EVIDENCE_DISPOSITIONS = {"realized", "enriched"}
_NOTE_DISPOSITIONS = {"delegated", "out-of-tier", "deferred", "unsupported"}


def _symbol_present(repo: Path, artifact: dict) -> tuple[bool, bool]:
    """(file_exists, symbol_present). Symbol check is a best-effort substring scan -
    enough to catch a manifest that points at a symbol the file does not define."""
    path = repo / artifact["path"]
    if not path.is_file():
        return False, False
    symbol = artifact.get("symbol")
    if not symbol:
        return True, True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True, False
    return True, symbol in text


def _evidence_level(ok: bool, repo_checked: bool, symbols_checked: bool, tests_present: bool) -> str:
    """How strongly the realization is grounded - NOT merely whether it is accounted.
    A green report without --repo is `accounted` (evidence declared, not checked); it
    must not imply grounded realization. Higher levels (test-executed, behavior-verified)
    require an execution harness this structural verifier does not run."""
    if not ok:
        return "none"
    if not repo_checked:
        return "accounted"
    if tests_present:
        return "test-present"
    if symbols_checked:
        return "symbol-verified"
    return "artifact-verified"


def verify(model: dict, manifest: dict, repo: Path | None = None) -> dict:
    identities = ir_identities(model)
    errors: list[dict] = []
    seen: dict[str, int] = {}
    by_disposition: dict[str, int] = {}
    symbols_checked = False
    tests_present = False

    for entry in manifest.get("dispositions", []):
        semantic_id = entry["semanticId"]
        disposition = entry["disposition"]
        by_disposition[disposition] = by_disposition.get(disposition, 0) + 1
        seen[semantic_id] = seen.get(semantic_id, 0) + 1

        if semantic_id not in identities:
            errors.append({"code": "unknown-identity", "semanticId": semantic_id,
                           "message": f"manifest references {semantic_id!r}, which is not a semantic identity in the IR"})
            continue
        if seen[semantic_id] == 2:
            errors.append({"code": "duplicate-disposition", "semanticId": semantic_id,
                           "message": f"{semantic_id!r} has more than one disposition"})

        artifacts = entry.get("artifacts", [])
        if disposition in _EVIDENCE_DISPOSITIONS and not artifacts:
            errors.append({"code": "realized-without-evidence", "semanticId": semantic_id,
                           "message": f"{semantic_id!r} is {disposition} but lists no artifacts (no evidence)"})
        if disposition in _NOTE_DISPOSITIONS and not (entry.get("note") or "").strip():
            errors.append({"code": "unsupported-without-note", "semanticId": semantic_id,
                           "message": f"{semantic_id!r} is {disposition} but gives no note (a gap must be explained, not silent)"})

        if repo is not None:
            for artifact in artifacts:
                exists, symbol_ok = _symbol_present(repo, artifact)
                if artifact.get("symbol"):
                    symbols_checked = True
                if not exists:
                    errors.append({"code": "missing-artifact-file", "semanticId": semantic_id,
                                   "message": f"artifact {artifact['path']!r} for {semantic_id!r} does not exist in the repo"})
                elif not symbol_ok:
                    errors.append({"code": "missing-artifact-symbol", "semanticId": semantic_id,
                                   "message": f"symbol {artifact.get('symbol')!r} not found in {artifact['path']!r} for {semantic_id!r}"})
            for test in entry.get("tests", []):
                tests_present = True
                exists, _ = _symbol_present(repo, test)
                if not exists:
                    errors.append({"code": "missing-test-file", "semanticId": semantic_id,
                                   "message": f"test {test['path']!r} for {semantic_id!r} does not exist in the repo"})

    accounted = {sid for sid in seen if sid in identities}
    for semantic_id in sorted(identities):
        if semantic_id not in accounted:
            errors.append({"code": "missing-disposition", "semanticId": semantic_id,
                           "message": f"{semantic_id!r} ({identities[semantic_id]}) has no disposition - it may have been silently dropped"})

    ok = not errors
    # tests-present only counts if every test file was actually found (no missing-test-file).
    tests_present = tests_present and not any(error["code"] == "missing-test-file" for error in errors)
    return {
        "realizationReportVersion": "1.0.0",
        "model": model.get("id", "<model>"),
        "stack": manifest.get("stack"),
        "repoChecked": repo is not None,
        "ok": ok,
        "evidenceLevel": _evidence_level(ok, repo is not None, symbols_checked, tests_present),
        "summary": {
            "identityCount": len(identities),
            "accountedFor": len(accounted),
            "missing": sum(1 for sid in identities if sid not in accounted),
            "byDisposition": by_disposition,
        },
        # Position-based fallback identities (section#index) - accounted but NOT stable
        # across reordering/versions. A durable manifest should give these items a stable id.
        "positionUnstableIdentities": anonymous_identities(model),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a codegen realization manifest against the IR (and optionally the generated repo).")
    parser.add_argument("model", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo", type=Path, help="path to the generated repository; enables artifact/test file+symbol checks")
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = verify(model, manifest, args.repo)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
