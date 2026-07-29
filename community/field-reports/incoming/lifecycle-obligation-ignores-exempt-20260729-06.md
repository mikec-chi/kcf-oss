# Field report — the lifecycle obligation exempts by category only, so a read-only entity is still recommended a lifecycle

```yaml
<!-- kcf-field-report:v1 -->
id: lifecycle-obligation-ignores-exempt-20260729-06
kcfVersion: 1.11.0
commit: 549b566
phase: assess
area: coverage-model
construct: coverage.entity.lifecycle (ev_concept_kind_has_lifecycle)
severity: medium
title: ev_concept_kind_has_lifecycle never calls _is_exempt, so a read-only/immutable transactional entity still attracts a lifecycle recommendation
observation: >
  `coverage_report.py` has one exemption helper, `_is_exempt` (lines 201-208), which
  exempts a concept when `metadata.mutability == "read-only"`, when
  `metadata.readOnly is True`, when its `category` is write-exempt, or when one of its
  declared role traits appears in the obligation's `exemptTraits`.

  `ev_concept_kind_has_crud` calls it. `ev_concept_kind_has_set_operation` calls it.
  `ev_concept_kind_has_lifecycle` (line 67) does not — it skips only on
  `_category(concept) in _NO_LIFECYCLE_CATEGORIES`. The asymmetry is visible in the same
  file, a few dozen lines apart.

  The consequence is that a `transactional` entity explicitly marked
  `mutability "read-only"` — an append-only ledger, an audit trail — is exempted from
  CRUD and set-operation obligations but still reported as `ENTITY <x> has no lifecycle`.
  Records that are never updated cannot have a state machine, so the recommendation
  cannot be satisfied except by adding an empty lifecycle.

  That is precisely the incentive `coverage-over-modeling-20260727-01` was accepted and
  resolved to remove. The fix there made the lifecycle obligation category-aware, which
  covered reference/config/master data. Immutable transactional data falls through the
  same hole: it is transactional by category, so the category test does not save it, and
  the read-only test that would is never reached.
evidence:
  commands:
    - kcf compile ledger.kcf -o ir.json --validate
    - kcf coverage-report ir.json          # -> coverage.entity.lifecycle for the read-only entity
    - "python -c \"import re,pathlib;s=pathlib.Path('kcf-oss/tools/coverage_report.py').read_text();b=re.search(r'def ev_concept_kind_has_lifecycle.*?(?=\\ndef )',s,re.S).group(0);print('_is_exempt called:', '_is_exempt' in b)\"   # -> False"
    - "python -c \"import re,pathlib;s=pathlib.Path('kcf-oss/tools/coverage_report.py').read_text();b=re.search(r'def ev_concept_kind_has_crud.*?(?=\\ndef )',s,re.S).group(0);print('_is_exempt called:', '_is_exempt' in b)\"   # -> True"
  diagnostics:
    - "[recommended] coverage.entity.lifecycle: ENTITY m.Ledger has no lifecycle"
  snippet: |
    kcf model M profile operational-system {
      namespace m;
      entity Ledger {
        identity id: UUID generated;
        required amount: Decimal readonly;
        category transactional;        // it IS transactional
        mutability "read-only";        // and append-only: entries are never modified
      }
      // ... obligation-complete remainder omitted
    }
    // coverage-report:
    //   coverage.entity.crud            -> EXEMPT   (_is_exempt honours read-only)
    //   coverage.entity.set-operation   -> EXEMPT   (same)
    //   coverage.entity.lifecycle       -> GAP      (evaluator never checks)
impact: >
  Any operational or financial domain with append-only data — ledgers, audit trails,
  event stores, meter readings, posting journals — carries one permanently unsatisfiable
  recommended gap per such entity, and the only way to clear it is the empty lifecycle
  that degrades the shape signal other tooling infers record-nature from. In our model
  2 of 20 remaining lifecycle gaps are exactly this, on entities whose source explicitly
  tags them immutable.
suggestedChange: >
  Call `_is_exempt(concept, obligation)` in `ev_concept_kind_has_lifecycle`, as the CRUD
  and set-operation evaluators already do. Read-only and immutable data is not an
  operational state machine, which is the same reasoning the category check already
  encodes.
  Adding `"read-only"` and `"immutable"` to `exemptTraits` on `coverage.entity.lifecycle`
  in `config/coverage-model.json` would also help, but only once the evaluator consults
  the helper — as written the obligation's own `exemptTraits` are unreachable for this
  gap, which is worth checking for across the other evaluators too.
  A negative fixture would pin it: a `transactional` + `mutability "read-only"` entity
  that must NOT produce `coverage.entity.lifecycle`.
workaround: >
  None that is honest. We left the gaps open and documented why, rather than adding
  empty lifecycles. Re-tagging the entities `reference` would silence the obligation but
  would be a lie about their nature and would then fight the analyzer's own
  category/shape reconciliation.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Filed together with `entity-immutable-declaration-dropped-20260729-05`. The two compound:
the grammar's `immutable;` declaration is discarded for entities, and the metadata
encoding that *does* work still fails to exempt the lifecycle obligation. So there is
currently no way to model an append-only entity without leaving a recommended gap open.

This looks like the same root cause as `coverage-over-modeling-20260727-01` — the
worked example in [`../TEMPLATE.md`](../TEMPLATE.md), whose note records that it was
triaged and that "`kcf assess` coverage is now category-aware". Worth checking whether
that fix belonged in `_is_exempt` rather than in a category list inside the evaluator,
since the category list is exactly what left this second hole.
