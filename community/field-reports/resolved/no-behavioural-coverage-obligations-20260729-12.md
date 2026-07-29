# Field report — coverage has no behavioural obligation, so `ready: true` is reachable with every rule and procedure absent

```yaml
<!-- kcf-field-report:v1 -->
id: no-behavioural-coverage-obligations-20260729-12
kcfVersion: 1.11.0
commit: 2071c8d
phase: assess
area: coverage-model
construct: config/coverage-model.json (obligation set) / assess readiness verdict
severity: high
title: No coverage obligation examines rule conditions, expression operands or action procedures, so assess reports ready for a model whose entire behaviour is unexpressed
observation: >
  `kcf assess` reported `valid: true`, `ready: true`, `coverageStatus:
  required-obligations-met`, `requiredGaps: 0`, `readyFor: [codegen-handoff, review]` for
  a 189-concept model in which:

    * 51 of 51 rule conditions were unparsed strings (nothing could evaluate them);
    * 13 of 19 MATH expression operands resolved to no declared attribute;
    * 14 `invoke` actions had no procedure anywhere in the IR;
    * 15 measures were named with no calculation.

  Every one of the 16 obligations considered is structural — CRUD, set operations,
  lifecycle presence, event producers, dimension presence. Searching the whole coverage
  model for an obligation touching rule conditions or action procedures returns exactly
  two hits, and both are about *authorization*
  (`coverage.action.authorization`,
  `coverage.business-application.state-changing-action`).

  So the readiness gate is structurally incapable of distinguishing **a model that
  generates an application** from **a model that generates a scaffold**. Ours was the
  second, and it passed every gate. We handed the IR to code generation exactly as the
  `codegen/generate-backend.md` prompt instructs ("The `model-ir.json` is the one
  `kcf assess` reported `ready: true`") and got a structural skeleton — correctly, because
  the prompt also says "realize only what the IR declares", and the IR declared no
  behaviour.

  `assess` already models this kind of honesty one level up: `domainComplete: not-proven`
  is exactly the right instinct — it refuses to claim the domain is captured. The same
  refusal is missing for behaviour.
evidence:
  commands:
    - kcf compile probe.kcf -o ir.json --validate
    - kcf assess ir.json          # -> valid: true, ready: true, requiredGaps: 0
    - kcf coverage-report ir.json # -> no gap mentions a condition, operand or procedure
    - "python -c \"import json,re;cm=json.load(open('kcf-oss/config/coverage-model.json'));ids=re.findall(r'\\\"id\\\": \\\"(coverage[^\\\"]+)\\\"',json.dumps(cm));print([i for i in ids if any(k in i for k in ('rule','math','logic','procedure','behav'))])\"   # -> []"
  diagnostics:
    - "assess: {\"valid\": true, \"ready\": true, \"coverageStatus\": \"required-obligations-met\", \"requiredGaps\": 0}"
    - "(no gap, warning or note about unparsed conditions, unresolved operands, or absent procedures)"
  snippet: |
    kcf model Probe profile business-application {
      namespace p;
      entity Order { identity id: UUID generated; required total: Decimal; }
      actor Clerk { }
      work Fulfil { kind TASK; }
      measure Margin { kind KPI; subject Order; }
      relationship pa: PARTICIPATION Clerk -> Fulfil strength 1.0;
      relationship tr: TRANSFORMATION Fulfil -> Order strength 1.0;

      formula NetTotal { result Margin; expression total - discount_rate; }  // phantom operand
      rule BigOrder { kind DECISION; condition "unposted_balance > ceiling";  // phantom operands,
                      effect Fulfil; applies-to Order; authority Clerk; }     // unparsed string
      policy P { authority Clerk; rule BigOrder; default-conflict deny-overrides; }
      command Create { operation create; scope record; target Order; input one; output one;
                       idempotency conditional; atomicity atomic; authorization p.P; }
    }
    // assess -> valid: true, ready: true, requiredGaps: 0
    // Nothing in this model can be evaluated, and nothing says so.
impact: >
  Affects anyone using `ready: true` as the handoff gate, which the codegen prompt
  instructs. The cost is not a wrong verdict — it is correct by its own definition — but a
  *misleading* one at the moment it matters most. We shipped a verified, drift-proof,
  721/721-accounted application with zero business logic and no signal that anything was
  missing until we compared it against a hand-built system from the same source.
suggestedChange: >
  Add behavioural obligations, and a readiness axis that reports them separately rather
  than folding them into `ready`:

    coverage.rule.condition-evaluable      every RULE has a condition that parses
    coverage.expression.operands-resolved  every MATH/RULE operand resolves to a
                                           declared attribute, measure or parameter
    coverage.action.procedure-or-delegation every `invoke` action has a procedure, or an
                                           explicit delegation with pre/post-conditions
    coverage.measure.calculation           every MEASURE has a calculation or is marked
                                           externally sourced

  Then surface a `behaviourallyComplete` flag beside the existing `domainComplete`, so
  `ready` can keep meaning "structurally buildable" while the report says plainly whether
  the behaviour is there. Level them `recommended` first: made `required` immediately,
  every existing model with prose rules stops being ready, which is too abrupt.
  Two of these depend on other reports landing — `condition-evaluable` needs
  `rule-conditions-opaque-strings-20260729-11`, and `procedure-or-delegation` needs
  `no-procedure-surface-for-actions-20260729-14`. `operands-resolved` needs only
  `math-operands-not-resolved-20260729-10`, which is analyzer-only, so it can ship first.
workaround: >
  We computed the missing signal by hand from the realization manifest, after the fact —
  see `realization-ratio-not-reported-20260729-13`, which proposes surfacing it in the
  verifier. Nothing in the toolchain produces it today.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Third of five related reports. Unlike the others this one changes no contract — it is
obligations plus a report field — so it is deliverable independently, and it is the
cheapest way to stop the mistake this batch documents from recurring. Even with the
obligations at `recommended`, the gap would have been visible on day one instead of after
a full build.

## Triage result — ACCEPTED, fixed (honest axis; no coverage-contract change)

Confirmed: every coverage obligation is structural, so `ready: true` was reachable with every
rule condition an unparsed string, every MATH operand phantom, and every `invoke` action without
a procedure — the gate could not tell an application from a scaffold. Rather than add gated
coverage obligations that would always fail until RFC-13/RFC-14 land (and would force a
coverage-contract change + fixtures), the fix adds an honest, **separate** readiness axis to
`assess`: **`behaviourallyComplete`** — the mirror of `domainComplete: not-proven`. It reports,
per model, how many rules have a parsed condition, how many `invoke` actions carry a procedure,
how many expression operands are unresolved (reusing report `-10`), and an overall status
(`realizable` / `not-proven` / `not-applicable`). It is reported **beside** `ready` (which keeps
meaning "structurally buildable"), never folded into it — so the behavioural gap is visible on
day one instead of after a full build. `assess-report-v1` schema updated (additive). Verified +
regression-pinned. The two follow-on obligations the report proposes depend on RFC-13
(condition-evaluable) and RFC-14 (procedure) and are noted there; `operands-resolved` shipped now
as report `-10`.
