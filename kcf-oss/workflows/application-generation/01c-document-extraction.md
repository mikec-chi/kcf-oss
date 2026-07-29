# 01c - Document Extraction (prose / image / flowchart / org chart / form)

## Gate

Used when the input arrives as a document — prose (requirements text, a spec), an
image (a scan, screenshot, or whiteboard photo), or a structured/visual document
(flowchart, org chart, form). Each modality has a shipped document profile in
`config/document-profiles/` that steers extraction toward the dimensions it
typically yields. This step extracts it with the same traceability as 01b, guided
by the document profile for its modality. KCF does not read images - an LLM (or a
deterministic importer, where the source is machine-readable) produces the
segments and IR; this makes that step guided and checkable.

## Prompt

```text
Input: [DOCUMENT_PATH] of kind [DOCUMENT_KIND] (prose | image | flowchart | org-chart | form | ...).

1. If the document is machine-readable (e.g. a mermaid flowchart), import it
   deterministically instead of guessing its structure:

   python tools/kcf.py import-mermaid [DOCUMENT_PATH] --id [MODEL_ID] `
     --namespace [NAMESPACE] --output [PROJECT_ROOT]/domain/model-ir.json `
     --source-doc [PROJECT_ROOT]/domain/source-document.json `
     --trace [PROJECT_ROOT]/domain/source-trace.json

   Otherwise read the document profile and extract by hand:

   Consult the profile for [DOCUMENT_KIND] (config/document-profiles): it declares
   the segment kinds to use, the target dimensions, and how each segment maps to a
   construct - flowchart nodes/edges -> WORK concepts + ORDERING relationships;
   org-chart positions/lines -> the ORGANIZATION dimension (members, roles,
   reporting, escalations); form fields/validation -> ENTITY attributes + RULEs +
   an INFORMATION record. Segment EVERY structural unit, and for diagrams capture
   every edge/line - that is where sequencing and relationships live and are
   easiest to drop. Write source-document.json (set documentKind), model-ir.json,
   and source-trace.json, stamping extractionMethod llm + confidence on
   LLM-produced content.

2. Check the segmentation against the modality, then run the front door:

   python tools/kcf.py document-check [PROJECT_ROOT]/domain/source-document.json
   python tools/kcf.py ingest [PROJECT_ROOT]/domain/model-ir.json `
     [PROJECT_ROOT]/domain/source-document.json `
     [PROJECT_ROOT]/domain/source-trace.json

   Resolve unknownSegmentKinds (segmentation drifted from the modality), then the
   ingest report's source-coverage and assess gaps as in 01b.

Segmentation fidelity for a raster image cannot be verified by any tool - the
by-segment review (10c) is where a human confirms the segments match the document.
The phase passes when document-check is conformant and ingest reports valid=true
and sourceComplete=true.
```
