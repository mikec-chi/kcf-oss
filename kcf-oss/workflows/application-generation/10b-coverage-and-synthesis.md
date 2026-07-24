# 10b - Knowledge Coverage and Synthetic Gap-Filling

## Gate

Runs after validation (step 10) passes. Measures whether the *valid* model is
also *complete*, then drafts - but does not commit - synthetic fills for the
gaps. Completeness is not correctness: this step reduces omission, it does not
prove the model is right. Human confirmation happens in step 10c.

## Prompt

```text
Measure knowledge coverage of [PROJECT_ROOT]/domain/model-ir.json:

python tools/kcf.py coverage-report [PROJECT_ROOT]/domain/model-ir.json `
  --output [PROJECT_ROOT]/domain/coverage-report.json

The report lists gaps (missing obligations) with a stable gapId, a level
(required | recommended | info), the subject, and the semantic dimension. A gap
means the grammar's checklist expects knowledge the model does not yet capture.

For every gap, in priority order (required first):

1. State what is missing and why the obligation exists.
2. Decide whether the gap is real or a legitimate domain exclusion. If it is an
   exclusion, record it as such - do not fabricate content to silence the tool.
3. For a real gap, propose the smallest plausible fill from general domain
   knowledge, expressed as AUTHORING .kcf for the owning dimension.
4. Tag every synthetic record with its provenance in the grammar's own
   vocabulary, never as bare fact:
   - extraction-method llm;
   - extraction-model "[MODEL_ID]";
   - confidence <your calibrated 0..1 estimate>;
   - for assertions, status inferred;
   - evidence: cite the reasoning or leave explicitly empty.
5. State, for each proposal, what evidence a human would need to confirm it and
   what could make it wrong.

Compile the synthetic proposals to
[PROJECT_ROOT]/domain/synthetic-model-ir.json and validate them with the
analyzer. Synthetic knowledge must pass the same schema and semantic checks as
human knowledge; fix proposals that do not.

Do NOT merge synthetic content into the model yet. Write the proposals and their
rationale to domain/synthetic-proposals.md and stop. The phase passes when every
required gap has either a validated synthetic proposal awaiting review or a
recorded, justified exclusion.
```
