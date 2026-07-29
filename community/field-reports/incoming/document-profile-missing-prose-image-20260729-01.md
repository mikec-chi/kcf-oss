# Field report — no `prose` or `image` document profile ships, so declaring the default modality is penalized

```yaml
<!-- kcf-field-report:v1 -->
id: document-profile-missing-prose-image-20260729-01
kcfVersion: 1.11.0
commit: 5f8aba6
phase: model
area: source-fidelity
construct: config/document-profiles (kcf document-check)
severity: medium
title: No `prose` or `image` document profile ships, so a document that declares its modality fails document-check while one that omits it passes
observation: >
  `config/document-profiles/` ships three profiles — `flowchart`, `form`, `org-chart`.
  `check_document` resolves a profile by `documentKind`, and `is_conformant` fails a
  document whose declared kind has no profile. The two default modalities on the
  natural-language front door have no profile: plain prose (requirements text, a terms
  of reference, a specification) and images (a scan, a screenshot, a whiteboard photo).
  A document that honestly declares `documentKind: "prose"` therefore exits 1 with
  `hasProfile: false` and an empty `targetDimensions`, even though every segment kind it
  uses is in the `source-document-v1` enum and nothing about it is malformed.

  The incentive is the reportable part. `is_conformant` only tests a kind that is
  present (`if report["documentKind"] and not report["hasProfile"]`), so omitting
  `documentKind` skips the check and exits 0. The way to pass the input-side gate is to
  declare *less* provenance than you have. Segmenting a set of structured-DSL model
  files into source documents, we went from 9/9 non-conformant to 9/9 conformant by
  deleting the one field that recorded what the sources were — and lost the
  `targetDimensions` steer the profile mechanism exists to give.
evidence:
  commands:
    - kcf document-check requirements.source-document.json    # documentKind: prose -> exit 1
    - "python -c \"import json;d=json.load(open('requirements.source-document.json'));del d['documentKind'];json.dump(d,open('stripped.json','w'))\""
    - kcf document-check stripped.json                        # no documentKind -> exit 0
    - KCF_DOCUMENT_PROFILE_PATH=./local-profiles kcf document-check requirements.source-document.json   # with a local prose.json -> exit 0
  diagnostics:
    - "(no message — the report is JSON with \"hasProfile\": false, \"targetDimensions\": [], and a bare exit 1)"
  snippet: |
    {
      "sourceDocumentVersion": "1.0.0",
      "documentId": "requirements",
      "documentKind": "prose",
      "segments": [
        {"segmentId": "s1", "kind": "statement",
         "text": "Every Item must carry a unique tag."}
      ]
    }
    // kcf document-check -> exit 1, hasProfile: false, targetDimensions: [].
    // Delete the "documentKind" line -> exit 0. Declaring the modality is penalized.
impact: >
  Affects anyone entering through the natural-language front door, the documented path
  for turning real requirements into an IR. Two costs: the modality most sources
  actually are cannot pass the input-side gate, and the cheapest way to pass teaches
  users to strip modality metadata. `prose` is also the kind most in need of extraction
  guidance — unlike a flowchart or a form it legitimately yields constructs across many
  dimensions at once, and it has no structural cue marking where one assertion ends.
suggestedChange: >
  Ship `prose` and `image` profiles in `config/document-profiles/`. Both are pure data
  and need no engine change: we authored both, validated them against
  `document-profile-v1.schema.json`, and resolved them through
  `KCF_DOCUMENT_PROFILE_PATH` with no code modification — the overlay mechanism working
  as designed. Candidate content is in the triage notes below, lift-and-drop ready.
  For `image`, the load-bearing guidance is that every illegible or cropped region must
  become a `question` segment: a region that is silently not transcribed shrinks the
  coverage denominator, so the loss becomes invisible instead of reported — the same
  failure class as import-dbml-silent-noop-20260727-01, on the vision path.
  Separately, consider whether an unprofiled `documentKind` should warn rather than fail,
  so declaring a modality is never worse than omitting it.
workaround: >
  Authored both profiles locally and pointed `KCF_DOCUMENT_PROFILE_PATH` at them. All
  nine source documents then pass at exit 0 with `hasProfile: true` and a populated
  `targetDimensions`. Confirmed the check still bites: a document declaring
  `documentKind: "image"` with org-chart segment kinds (`position`, `reporting-line`)
  reports both in `unknownSegmentKinds` and exits 1.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@5f8aba6`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. `tools/document_profile.py`, both schemas, and the three shipped profiles are
byte-identical at `070dfb3`, so the finding is not specific to the tip commit.

This is one finding about the shipped profile set rather than two — same mechanism, same
one-line cause, same shape of fix. Happy to split it into separate `prose` and `image`
envelopes if you would rather triage them independently.

Both candidate profiles validate clean against `schemas/document-profile-v1.schema.json`;
every entry in `segmentKinds` is drawn from the `source-document-v1` segment-kind enum
and has a `mapping` entry.

<details>
<summary><code>config/document-profiles/prose.json</code></summary>

```json
{
  "documentProfileVersion": "1.0.0",
  "documentKind": "prose",
  "title": "Prose / narrative source",
  "description": "An unstructured or lightly-structured written source — requirements text, a terms-of-reference document, a specification, meeting notes, or a structured-DSL model read as text. Meaning is carried by declarative statements under headings, rather than by a diagram's nodes and edges or a form's fields. The default modality for the natural-language front door.",
  "segmentKinds": ["heading", "section", "statement", "note", "example", "question"],
  "targetDimensions": ["ENTITY", "ACTOR", "WORK", "EVENT", "LIFECYCLE", "RULE", "RELATIONSHIP", "INFORMATION"],
  "mapping": [
    {"segmentKind": "statement", "producesKind": "*", "notes": "the load-bearing kind: a declarative sentence yields whichever construct it asserts — a thing (ENTITY), a doer (ACTOR), an activity (WORK), something that happened (EVENT), a state progression (LIFECYCLE), or a constraint (RULE). Classify per statement; do not assume one kind per document"},
    {"segmentKind": "heading", "producesKind": "INFORMATION", "notes": "a heading scopes the statements beneath it; keep it as a segment so that scope is addressable, but do not extract a construct from the heading alone"},
    {"segmentKind": "section", "producesKind": "INFORMATION", "notes": "a titled body of prose becomes an information record carrying sourceDocument provenance"},
    {"segmentKind": "note", "producesKind": "INFORMATION", "notes": "scope notes, caveats, and non-goals bound what the model should claim; they constrain extraction rather than adding constructs"},
    {"segmentKind": "example", "producesKind": "RULE", "notes": "a worked example usually illustrates a rule or a formula; extract the rule it demonstrates, not the example instance"},
    {"segmentKind": "question", "producesKind": "*", "notes": "an open question marks knowledge that is not yet settled — do not extract a construct; leave the gap open for the review/confirm step"}
  ],
  "guidance": [
    "Segment at the granularity of an independently-citable assertion — one statement per claim. A segment that carries two unrelated claims cannot be traced to two constructs.",
    "Prose is multi-dimensional: unlike a flowchart or a form, one document legitimately produces ENTITY, ACTOR, WORK, RULE, and LIFECYCLE constructs together. Do not force a single target dimension.",
    "Keep headings and notes as segments even though they rarely produce constructs — omitting them makes the coverage denominator understate the source, so an uncovered region looks covered.",
    "Do not extract a construct from a `question` segment or from prose hedged with 'may', 'could', or 'to be determined'. Unsettled knowledge belongs in the review queue, not the model.",
    "Respect explicit scope notes: a source that states it does not describe a capability must not yield constructs asserting that capability.",
    "Prose restates the same fact in several places. Cite every segment that grounds a construct, so removing one restatement does not orphan it."
  ]
}
```

</details>

<details>
<summary><code>config/document-profiles/image.json</code></summary>

```json
{
  "documentProfileVersion": "1.0.0",
  "documentKind": "image",
  "title": "Image / scan / screenshot",
  "description": "A source that arrives as pixels rather than text — a photographed or scanned document, a screenshot of an existing system, a whiteboard or flip-chart photo. Extraction is two-stage: a vision model transcribes the image into segments, then those segments are extracted as usual. This profile governs the transcription, because that is where meaning is silently lost. Where the image clearly depicts a single known modality, prefer that modality's profile (`flowchart`, `form`, `org-chart`); use `image` when the content is mixed, partially legible, or not one of those.",
  "segmentKinds": ["heading", "section", "statement", "note", "question", "field", "cell", "node", "edge", "decision"],
  "targetDimensions": ["ENTITY", "ACTOR", "WORK", "EVENT", "LIFECYCLE", "RULE", "RELATIONSHIP", "INFORMATION"],
  "mapping": [
    {"segmentKind": "statement", "producesKind": "*", "notes": "transcribed body text behaves as prose — classify per statement into the construct it asserts"},
    {"segmentKind": "heading", "producesKind": "INFORMATION", "notes": "a title, banner, or column header scopes what follows; keep it addressable but extract no construct from it alone"},
    {"segmentKind": "section", "producesKind": "INFORMATION", "notes": "a visually delimited region (panel, boxed area, page) becomes an information record carrying sourceDocument provenance"},
    {"segmentKind": "field", "producesKind": "ENTITY.attribute", "notes": "a labelled input, form field, or screenshot column becomes a typed attribute; a printed value next to the label is an instance, not part of the model"},
    {"segmentKind": "cell", "producesKind": "ENTITY.attribute", "notes": "a table cell: the header row gives attributes, body rows give instances. Transcribe the header before the rows, and never infer a column that is cut off at the image edge"},
    {"segmentKind": "node", "producesKind": "WORK", "notes": "a box in a diagrammed process becomes a WORK concept"},
    {"segmentKind": "edge", "producesKind": "RELATIONSHIP", "notes": "a drawn arrow becomes an ORDERING relationship; arrow direction is meaning — if the arrowhead is not legible, emit a question segment instead of guessing"},
    {"segmentKind": "decision", "producesKind": "WORK", "notes": "a diamond or branch point becomes a WORK concept, with its conditions on the outgoing edges"},
    {"segmentKind": "note", "producesKind": "INFORMATION", "notes": "a margin annotation, stamp, or handwritten aside — often the caveat that bounds the rest of the image"},
    {"segmentKind": "question", "producesKind": "*", "notes": "the illegibility channel: anything cropped, blurred, obscured, or ambiguous becomes a question segment and produces no construct"}
  ],
  "guidance": [
    "Transcribe only what is legible. An image invites confabulation in a way text does not — a plausible-looking guess at a cropped column or a blurred arrowhead is indistinguishable from real content once it reaches the IR.",
    "Every illegible or ambiguous region gets a `question` segment. This is what makes the loss visible: an untranscribed region that is simply omitted makes the coverage denominator shrink, so the gap disappears instead of being reported.",
    "Record the image's own identity (file, page, figure number) in the segmentId, so a construct traces back to a specific image and not to 'the screenshots'.",
    "Distinguish schema from data. Screenshots and filled forms show instances; the model wants the attribute, the allowed values, and the rule — not the sample row.",
    "Set `validatedBy`/`validatedAt` on segments a human has confirmed against the original. Transcription is a lossy step and should carry sign-off before the model is built on it.",
    "If the image depicts a flowchart, form, or org chart cleanly, re-declare the document under that modality's profile instead — those profiles give sharper extraction guidance than this one.",
    "Spatial layout carries meaning that transcription drops: reading order, nesting, alignment into columns, and proximity grouping. State the grouping explicitly in the segment text rather than relying on segment order to imply it."
  ]
}
```

</details>

Context: this surfaced while ingesting a structured-DSL model family as text sources,
after confirming `kcf import-dbml` correctly declines those files — their `.dbml` is a
different dialect, and the exit-2 warning added for
import-dbml-silent-noop-20260727-01 fired exactly as intended.
