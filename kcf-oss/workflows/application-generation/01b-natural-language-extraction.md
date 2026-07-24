# 01b - Natural-Language Extraction with Source Traceability

## Gate

Used when the input is human-validated natural-language concepts (written with an
external LLM, customized to the business). The prose is validated *content*; the
model derived from it is a new, unvalidated *encoding*. This step makes that
encoding traceable and checkable so the later human review confirms fidelity to
the prose, not the business facts (already validated). It never asserts knowledge.

## Prompt

```text
Input: [SOURCE_PATH] (the validated natural-language concepts).

1. Segment the source into addressable units and write
   [PROJECT_ROOT]/domain/source-document.json (schema source-document-v1): one
   segment per material statement, each with a stable segmentId, its text, a kind
   (statement | heading | note | example | question), and validatedBy/validatedAt
   if known. Headings/notes are legitimate non-modeling segments.

2. Extract the model from the segments into
   [PROJECT_ROOT]/domain/model-ir.json. Prefer emitting IR directly for a large
   input (the compiler stops at the first parse error; direct IR is batch-checked).
   For every construct, record where it came from:
   - write [PROJECT_ROOT]/domain/source-trace.json (schema source-trace-v1)
     mapping each segmentId to the construct identities it produced;
   - stamp synthetic provenance in the grammar's vocabulary: extractionMethod
     llm, extractionModel "[MODEL_ID]", a calibrated confidence; assertions get
     status inferred. The prose is human-validated; the encoding is not - keep
     them distinct.

3. Run the front door in one command:

   python tools/kcf.py ingest [PROJECT_ROOT]/domain/model-ir.json `
     [PROJECT_ROOT]/domain/source-document.json `
     [PROJECT_ROOT]/domain/source-trace.json `
     --output [PROJECT_ROOT]/domain/ingest-report.json

   Read the report and resolve, in order:
   - schema/analyzer errors (the encoding is not buildable) - fix the IR;
   - sourceCoverage.danglingSegments / danglingConstructs - fix the trace;
   - sourceCoverage.unsourcedConstructs - constructs grounded in no prose: either
     cite the segment they belong to or remove them (do not invent domain facts);
   - sourceCoverage.uncoveredSegments - prose that produced nothing: extract the
     missing construct, or mark the segment kind heading/note if non-modeling;
   - assess coverage/pattern/role gaps - fill from the prose where stated, else
     defer to synthesis (02b/10b) and record the gap.

The phase passes when ingest reports valid=true, sourceComplete=true, and every
required assess gap is filled or explicitly deferred. Then hand off to the
by-segment review (10c) so an SME confirms, segment by segment, that each
construct faithfully captures the prose it cites.
```
