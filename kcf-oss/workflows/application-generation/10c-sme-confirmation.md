# 10c - SME Confirmation of Synthetic Knowledge

## Gate

Synthetic (LLM-proposed) knowledge may become part of the model only after a
subject-matter expert confirms it. No synthetic record is treated as fact until
this gate records a reviewer decision. This gate guards against plausible but
wrong content and against automation bias.

## Prompt

```text
Present the validated proposals in domain/synthetic-proposals.md to the SME as a
review queue, ordered by level (required first) then by ascending confidence, so
the least certain proposals get the most scrutiny. For each proposal show: the
gap it fills, the proposed content, its confidence, its cited reasoning, and what
would make it wrong.

The SME records one decision per proposal: confirm, edit, or reject.

- confirm: the proposal is accepted as written.
- edit: the SME supplies corrected content; treat it as a new proposal and
  re-run validation before it can be confirmed.
- reject: the proposal is discarded and the gap remains open (or is recorded as
  a justified exclusion).

Record the decisions in domain/sme-decisions.json as
{"confirm": [<identity>...], "reject": [<identity>...]} and apply them:

python tools/kcf.py confirm [PROJECT_ROOT]/domain/synthetic-model-ir.json `
  --reviewer "[SME_IDENTITY]" --as-of "[ISO_TIMESTAMP]" `
  --decisions [PROJECT_ROOT]/domain/sme-decisions.json `
  --output [PROJECT_ROOT]/domain/confirmed-synthetic-ir.json

Confirmation stamps reviewedBy and recordedAt and flips an assertion's status
from inferred to asserted; the llm extraction-method is retained so the record's
synthetic origin stays auditable. Rejected records are removed.

Then fold the confirmed knowledge into the model:

python tools/kcf.py merge [PROJECT_ROOT]/domain/model-ir.json `
  [PROJECT_ROOT]/domain/confirmed-synthetic-ir.json `
  --id [MODEL_ID] --namespace [NAMESPACE] `
  --output [PROJECT_ROOT]/domain/model-ir.json

Re-run steps 10 and 10b. The loop - elicit, measure coverage, synthesize,
confirm, merge, re-measure - repeats until required gaps are zero or explicitly
excluded, with every synthetic contribution attributed to its reviewer.
```
