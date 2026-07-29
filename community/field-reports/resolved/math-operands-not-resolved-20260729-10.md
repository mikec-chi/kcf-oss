# Field report — MATH expression operands are never resolved, so an AST whose leaves mean nothing still compiles clean

```yaml
<!-- kcf-field-report:v1 -->
id: math-operands-not-resolved-20260729-10
kcfVersion: 1.11.0
commit: 2071c8d
phase: compile
area: analyzer
construct: math (formula/function) expression ref nodes
severity: high
title: Expression `ref` operands are not resolved against declared attributes, so a formula referencing fields that exist nowhere compiles, validates and assesses ready
observation: >
  KCF parses a `formula` expression into a real AST — this is a genuine strength, and it
  is what makes the MATH dimension generatable in principle:

      {"op":"/","left":{"op":"-","left":{"ref":"cost"},
                        "right":{"ref":"residual"}},
                "right":{"op":"*","left":{"ref":"life_years"},"right":{"num":12}}}

  Nothing ever resolves those `ref` leaves. In a real 189-concept model, 13 of the 19
  distinct operands across 9 formulas resolve to **no declared attribute anywhere** —
  `accrued_total`, `hours_logged`, `effort_cost_total`, `planned_done_on_time`,
  `external_cost_total`, `window_days`, … The analyzer emitted **zero** diagnostics
  mentioning math, formula, or operand.

  The consequence is that the AST is decoration rather than a contract. A generator
  cannot emit `run_monthly_accrual` from it, because it has no way to know where
  `accrued_total` lives — or that it is not a field at all. The dimension that
  looks most machine-ready is not.

  KCF already performs precisely this class of check one dimension over: `assess` reports
  `roles.unknownTraits` when a concept trait fails to resolve to a declared role, and it
  is a *required* obligation. Expression operands get no equivalent.
evidence:
  commands:
    - kcf compile probe.kcf -o ir.json --validate      # exit 0, no diagnostics
    - kcf assess ir.json                               # valid: true, ready: true, requiredGaps: 0
    - "python -c \"import json;print(json.load(open('ir.json'))['math'][0]['expression'])\""
    - "python -c \"import json;ir=json.load(open('ir.json'));a={x['name'] for c in ir['concepts'] for x in (c.get('attributes') or [])};print('declared:',sorted(a))\""
  diagnostics:
    - "(none — exit 0; no diagnostic mentions math, formula, expression or operand)"
  snippet: |
    kcf model Probe profile business-application {
      namespace p;
      entity Order { identity id: UUID generated; required total: Decimal; }
      actor Clerk { }
      work Fulfil { kind TASK; }
      measure Margin { kind KPI; subject Order; }
      relationship pa: PARTICIPATION Clerk -> Fulfil strength 1.0;
      relationship tr: TRANSFORMATION Fulfil -> Order strength 1.0;

      // `discount_rate` and `handling_fee` are declared NOWHERE in this model.
      formula NetTotal { result Margin; expression total - discount_rate * handling_fee; }

      // ... obligation-complete remainder omitted
    }
    // compile --validate -> exit 0, no diagnostics
    // assess            -> valid: true, ready: true, requiredGaps: 0
    // declared attributes: ['id', 'total']      <- two of three operands are phantoms
impact: >
  Affects every model that uses MATH, and it silently caps what codegen can do with the
  one behavioural dimension KCF already parses properly. A model can pass every gate with
  formulas that are arithmetic over nothing. Downstream, the generator either guesses an
  operand's home (inventing meaning) or delegates the formula (dropping it) — we did the
  latter for all 9, and only discovered why when auditing why the generated app had no
  business logic.
  Severity is `high` rather than medium because the failure is silent, the check is
  cheap, and the affected dimension is one of the few that could otherwise be generated
  rather than hand-written.
suggestedChange: >
  Resolve `ref` nodes in every MATH expression (`formula`, `function`, `optimize`,
  `distribution`, `simulation`) against the attributes of the concepts in scope, plus
  declared measures, units and function parameters. Report an unresolved operand the way
  `unknownTraits` is reported.
  Two details from the data: the check needs a scope rule (a formula does not name the
  entity whose attributes it may use — ours relied on `result <measure>` and the measure's
  `subject`), and function parameters must be excluded since they are locally bound. A
  reasonable first cut is a *warning* listing unresolved operands, promoted to an error
  once models have been migrated, since existing models will fail immediately.
  This is an analyzer-only change: the IR shape already carries everything needed, so no
  `model-ir-v1` version bump is implied.
workaround: >
  We treated every formula as `delegated` in the realization manifest with a note, and
  wrote the calculations by hand from the source specification instead. Nothing verifies
  those hand-written calculations against the declared expressions.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. The snippet is the whole reproducer.

Found while auditing why a generated application contained no business logic despite the
model reporting `ready: true`. Filed together with four related reports —
`rule-conditions-opaque-strings-…-11`, `no-behavioural-coverage-obligations-…-12`,
`realization-ratio-not-reported-…-13`, and `no-procedure-surface-for-actions-…-14` — which
together describe why the structural half of a model generates beautifully and the
behavioural half does not generate at all.

This one is first in that set deliberately: it is the cheapest to fix, needs no contract
change, and is a precondition for making rule conditions useful (report `…-11`).

## Triage result — ACCEPTED, fixed

Confirmed: MATH expressions parsed to a real AST but `ref` leaves were never resolved, so a
formula over phantom fields compiled, validated, and assessed `ready`. Fixed in the analyzer
(`tools/semantic_analyzer.py`, `check_quantitative`): each `formula`'s expression operands are
now resolved against the attribute names of its result measure's subject entities, plus
locally-bound parameters and declared measure/unit names. An operand that resolves to nothing
emits an advisory **warning** under the existing `kcf.math.reference` rule (no new rule id, no
catalogue change) — mirroring how an unresolved trait is surfaced, and warning (not error) so
existing models aren't broken. Scope is skipped when it can't be determined (no result measure /
no subject), so there are no false positives. Verified: a phantom-operand formula warns; a
fully-declared one does not. Analyzer-only — the IR already carried the AST, so no
`model-ir-v1` change. This is the precondition for RFC-13 (parsed rule conditions), which reuses
the same operand resolution. Regression-pinned in `run_conformance.py`.
