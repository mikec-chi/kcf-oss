# Field report — an `ORDERING` relationship cannot be authored cleanly: `dimension` is required but not recognized

```yaml
<!-- kcf-field-report:v1 -->
id: ordering-dimension-qualifier-catch-22-20260729-03
kcfVersion: 1.11.0
commit: 549b566
phase: compile
area: analyzer
construct: relationship (ORDERING) / KNOWN_RELATIONSHIP_QUALIFIERS
severity: medium
title: ORDERING relationships require a `dimension` qualifier that is absent from KNOWN_RELATIONSHIP_QUALIFIERS, so every one is either an error or a warning
observation: >
  Two analyzer checks disagree about the `dimension` qualifier, and an `ORDERING`
  relationship has to fail one of them.

  `check_relationships` requires it — `if root == "ORDERING" and not
  quals.get("dimension")` reports an **error** (`kcf.relationship.ordering`,
  semantic_analyzer.py:201), correctly arguing that a sequence is meaningless without
  the dimension it orders along.

  The qualifier whitelist does not contain it — `KNOWN_RELATIONSHIP_QUALIFIERS`
  (semantic_analyzer.py:51) is `{cardinality, source-role, target-role, on-delete,
  inverse, validations, inferences, min, max}`, so the later loop over
  `rel["qualifiers"]` reports `Relationship qualifier 'dimension' is not recognized —
  verify it is not a typo` as a **warning**.

  Omit `dimension` and the model is invalid. Supply it — using the exact name and one
  of the exact values the error message suggests — and the model is valid but warns
  that the qualifier might be a typo. There is no third option: no other qualifier
  satisfies the ORDERING check, and the parser accepts arbitrary `{identifier scalar}`
  pairs so nothing catches this at parse time.
evidence:
  commands:
    - kcf compile ord-no-dim.kcf -o ir.json --validate    # exit 1, error
    - kcf compile ord-with-dim.kcf -o ir.json --validate  # exit 0, warning
  diagnostics:
    - "error: Ordering relationship must declare its dimension (e.g. workflow, temporal, version, priority)."
    - "warning: Relationship qualifier 'dimension' is not recognized - verify it is not a typo."
  snippet: |
    kcf model Ord profile business-application {
      namespace ord;
      entity Item { identity id: UUID; required name: String; }
      actor Clerk { }
      work StepA { }
      work StepB { }
      relationship p: PARTICIPATION Clerk -> StepA strength 1.0;
      relationship x: TRANSFORMATION StepA -> Item strength 1.0;

      relationship seq: ORDERING StepA -> StepB strength 1.0;
      //                                     ^ omitted  -> ERROR (invalid model)
      // relationship seq: ORDERING StepA -> StepB strength 1.0 dimension workflow;
      //                                     ^ supplied -> WARNING ("not recognized")
    }
impact: >
  Any model that sequences work hits this, which is most operational-system models: a
  process, pipeline, or approval chain is a chain of ORDERING edges. In ours, all 16
  process-ordering edges warn, and they are 16 of only 20 warnings in an otherwise
  clean 145-concept model — enough noise to bury the 4 warnings that are real domain
  findings. The deeper cost is that the warning is not actionable: it tells the author
  to check for a typo in a name the error message told them to use, so the honest
  response is to learn to ignore a diagnostic, which is corrosive to the value of the
  rest of them.
suggestedChange: >
  Add `"dimension"` to `KNOWN_RELATIONSHIP_QUALIFIERS`. It is already a required,
  load-bearing qualifier for one rootKind, which is precisely what that set exists to
  describe. Optionally also validate its *value* against the suggested vocabulary
  (`workflow`, `temporal`, `version`, `priority`, …) the way `on-delete` is checked
  against `ON_DELETE_POLICIES`, which would turn a spelling mistake into a real
  diagnostic instead of the current unconditional one.
  Worth a broader pass for the same class of bug: any qualifier a rule *requires* but
  the whitelist omits produces the same catch-22. A cheap guard is a test asserting
  every qualifier name referenced by an analyzer check is a member of the whitelist.
workaround: >
  Declared `dimension workflow` on all 16 ORDERING edges and accepted the warnings — a
  warning is preferable to an invalid model, and the qualifier does land correctly in
  `relationship.qualifiers` in the IR, so no meaning is lost.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. The snippet above is the whole reproducer — commenting one line swaps the
error for the warning.

Found while transcoding a 9-language DSL model family into KCF (145 concepts, 185
relationships, 18 lifecycles); `ORDERING` was the encoding for a business process's
step-to-step `next` edges. The resulting model reaches `ready: true` with 0 required
gaps, so this did not block the work — reporting it per the authoring brief's field-report
guidance.

Two smaller observations from the same build, not filed separately since they are
lower-value and I would rather not split this envelope:

- `source_coverage.IDENTITY_COLLECTIONS` omits `math`, `propositions`, and the profile
  sections, so `formula`, `proposition`, and `integration` constructs are in the
  compiled IR but can never be traced or counted toward source coverage. In our model
  that is 22 constructs invisible to the faithfulness check. Happy to file this as its
  own report if useful.
- The authoring grammar has no value-domain / allowed-values surface, so a source
  enumeration has no first-class home; we preserved 9 of them as `proposition` plus a
  free-form attribute qualifier, which a generator cannot machine-check.

## Triage result — ACCEPTED, fixed

Confirmed the catch-22: `kcf.relationship.ordering` (semantic_analyzer.py) **requires**
`dimension` on an ORDERING edge, but `dimension` was absent from
`KNOWN_RELATIONSHIP_QUALIFIERS`, so every valid ORDERING edge also tripped the advisory
"qualifier 'dimension' is not recognized" warning — a qualifier a check requires can never
be unrecognized. Added `"dimension"` to `KNOWN_RELATIONSHIP_QUALIFIERS`. Verified: an
ORDERING edge declaring `dimension workflow` now compiles with **zero** ordering errors and
**zero** not-recognized warnings. Regression-pinned in `run_conformance.py` (a `dimension`-in-
whitelist assertion — the report's suggested class guard). Value-vocabulary validation
(`workflow`/`temporal`/…) was considered but left open deliberately: the dimension vocabulary
is open-ended, so erroring on an unlisted value would trade one false diagnostic for another.
Advisory analyzer change only — no grammar / `model-ir-v1` / analyzer *contract* change (the
qualifier already parsed and landed in `relationship.qualifiers`).
