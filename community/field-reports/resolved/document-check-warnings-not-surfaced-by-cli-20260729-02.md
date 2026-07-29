# Field report — `document-check` warnings never reach stderr through the `kcf` CLI

```yaml
<!-- kcf-field-report:v1 -->
id: document-check-warnings-not-surfaced-by-cli-20260729-02
kcfVersion: 1.11.0
commit: fbacd1a
phase: model
area: tooling
construct: kcf document-check (tools/kcf.py)
severity: low
title: The new document-check `warnings` are printed to stderr only by document_profile.py's own main(), not by the `kcf document-check` CLI path
observation: >
  The 2026-07-29 fix for document-profile-missing-prose-image-20260729-01 added a
  `warnings` field to the document-check report and prints each entry to stderr. The
  stderr half only runs in `tools/document_profile.py`'s own `main()`. The `kcf` CLI
  has a separate handler (`tools/kcf.py:323-327`) that calls `check_document` directly,
  writes the JSON, and returns — so no warning is ever printed:

      if args.command == "document-check":
          document = json.loads(args.document.read_text(encoding="utf-8"))
          report = check_document(document, load_document_profiles())
          write_json(report, args.output)
          return 0 if is_conformant(report) else 1

  So a document that omits `documentKind` exits 0 with zero stderr output through the
  documented entry point, and one run as `python tools/document_profile.py` emits the
  204-byte warning. The `warnings` array itself is correct in both cases — the signal
  exists in the report, it just never reaches the operator unless they parse the JSON.

  This is the residue of the fix rather than a regression: conformance scoring was
  corrected, so declaring a modality is no longer worse than omitting it. But the
  visible consequence of omitting it was supposed to be a warning, and via the CLI
  there is none — so the two options still look identical to anyone reading terminal
  output. The CHANGELOG entry and the commit message both state "also to stderr", so
  the docs currently describe behavior the CLI does not have.
evidence:
  commands:
    - "python -c \"import json;d=json.load(open('doc.json'));del d['documentKind'];json.dump(d,open('stripped.json','w'))\""
    - kcf document-check stripped.json >out.json 2>err.txt   # exit 0; err.txt is 0 bytes
    - "python -c \"import json;print(json.load(open('out.json'))['warnings'])\"   # -> the warning IS in the report"
    - python kcf-oss/tools/document_profile.py stripped.json >/dev/null 2>err2.txt   # err2.txt is 204 bytes
  diagnostics:
    - "(via kcf document-check: no stderr output at all)"
    - "warning: no documentKind declared: extraction runs without a modality profile and the targetDimensions steer it provides. Declare the document's modality (e.g. prose, image, flowchart, form, org-chart).   # only via document_profile.py"
  snippet: |
    {
      "sourceDocumentVersion": "1.0.0",
      "documentId": "requirements",
      "segments": [
        {"segmentId": "s1", "kind": "statement",
         "text": "Every Item must carry a unique tag."}
      ]
    }
    // kcf document-check      -> exit 0, stderr empty,      report.warnings = [1 warning]
    // document_profile.py     -> exit 0, stderr 204 bytes,  report.warnings = [1 warning]
impact: >
  Low but self-undermining: the warning exists to make an undeclared or unprofiled
  modality visible, and the path almost everyone uses is the one that hides it. Anyone
  checking exit codes and terminal output — a person at a prompt, a CI step, a coding
  agent reading tool output — sees a clean pass and no reason to declare the modality.
  It also makes the CHANGELOG claim inaccurate for the CLI.
suggestedChange: >
  Print `report["warnings"]` to stderr in the `kcf.py` document-check handler, matching
  the idiom the `import-dbml` handler in the same file already uses (`tools/kcf.py`,
  the 0-tables guard added for import-dbml-silent-noop-20260727-01). Two lines after
  `write_json`:

      for warning in report["warnings"]:
          print(f"warning: {warning}", file=sys.stderr)

  Better still, factor the emit into `document_profile.py` (e.g. `emit_warnings(report)`)
  and call it from both entry points, so the next handler cannot drift the same way.
  Worth a look at whether any other report-producing tool has warnings the CLI drops.
  Note also that `warnings` is not asserted anywhere in `run_conformance.py`, so no
  fixture currently pins this behavior at either entry point.
workaround: >
  Read `warnings` out of the JSON report rather than relying on stderr:
  `kcf document-check doc.json | python -c "import json,sys;print(json.load(sys.stdin)['warnings'])"`.
domainSanitized: true
```

## Notes for triage

Follow-up to [`document-profile-missing-prose-image-20260729-01`](../resolved/document-profile-missing-prose-image-20260729-01.md),
found while re-verifying that report's fix from the CLI. The profile half of that fix is
confirmed working: `prose`/`image` resolve with no `KCF_DOCUMENT_PROFILE_PATH` overlay,
nine `prose` documents check conformant with `warnings: []`, an unprofiled kind now warns
instead of failing, and genuine drift (an `image` document using `position` /
`reporting-line`) still exits 1. Only the stderr emission is missing, and only on the CLI
path.

Reproduced on `mikec-chi/kcf-oss@fbacd1a`, grammar-stack 1.11.0, Python 3.12.10 on Windows.

## Triage result — ACCEPTED, fixed

Correct, and a fair catch on the prior fix's own residue: the `warnings` were printed to stderr
only by `document_profile.py`'s `main()`, while the documented entry point — the `kcf
document-check` handler in `tools/kcf.py` — called `check_document`, wrote the JSON, and returned
without emitting them. So via the CLI a document that omitted `documentKind` exited 0 with empty
stderr, and the CHANGELOG's "also to stderr" was inaccurate for that path.

Fixed per the report's better suggestion — factor the emit so a handler cannot drift again: a shared
`emit_warnings(report, stream=None)` helper now lives in `tools/document_profile.py` and is called
by **both** entry points (`document_profile.py:main()` and the `kcf document-check` handler in
`tools/kcf.py`). Reproduced the report's exact scenario through the CLI: `kcf document-check` on a
document with no `documentKind` now writes the 204-byte `warning:` line to stderr and still exits 0
(byte-for-byte what `document_profile.py` produced). The CHANGELOG entry for the `-01` fix was
corrected to describe the shared emitter rather than a single path.

The behavior was previously unpinned; it is now regression-gated in `tools/run_conformance.py`
(part of `kcf check`): a profiled `prose` document is conformant with `warnings == []`; a document
with no `documentKind` and a declared-but-unprofiled kind are each conformant **with one warning**
(declaring is never worse than omitting); and `emit_warnings` writes the warning to a supplied
stream. `kcf check` + `check_handoff.py` green. Tooling/DX only — no grammar / `model-ir-v1` /
analyzer *contract* change.
