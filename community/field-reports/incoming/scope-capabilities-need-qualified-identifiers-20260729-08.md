# Field report — a declared `capability` never matches the same name in a scope, because matching is exact against the namespace-qualified form

```yaml
<!-- kcf-field-report:v1 -->
id: scope-capabilities-need-qualified-identifiers-20260729-08
kcfVersion: 1.11.0
commit: 549b566
phase: assess
area: tooling
construct: kcf completeness (declaredScope axis / _covers)
severity: medium
title: A scope's includedCapabilities must be namespace-qualified construct identities, so the same token written in the .kcf and the scope does not match and prose capabilities never can
observation: >
  `completeness` gates `closedWorldComplete` on a declared-scope axis: every string in
  `scope.includedCapabilities` must map to a model construct. Matching is
  `_covers(capability, terms, lowered)` = `capability in terms or capability.lower() in
  lowered` — exact, case-insensitive, no prefix or substring.

  `_model_capability_terms` collects concept identities and the contents of each
  concept's `traits`/`capabilities`/`skills`, so declaring a capability in the model
  looks like the intended path. It does not work as written. `capability procure_to_pay;`
  on an actor lands on the concept **namespace-qualified**:

      "capabilities": ["cap.procure_to_pay"]

  so the term collected is `cap.procure_to_pay`. A scope that names
  `procure_to_pay` — the identical token the author typed in the `.kcf` — is reported
  uncovered. Only the qualified form matches, and nothing in the scope schema or the
  authoring surface says so.

  Two consequences. First, the obvious authoring fails silently: same token in both
  files, still uncovered, no diagnostic naming the mismatch. Second, since matching is
  exact against identifiers, a scope written the way `scope-v1` reads — a governance
  artifact carrying `stakeholders`, `declaredBoundaries`, `openQuestions` — can never be
  covered if its capabilities are phrased for humans. "Procure to pay, end to end" is
  structurally unmatchable, and `capability-decl` cannot hold it either: it takes a
  `semantic-ref`, so `capability "procure-to-pay";` is a parse error.

  The axis therefore only passes when the scope is written in internal qualified
  identifiers — i.e. when it restates the model rather than declaring intent
  independently of it. That weakens what the axis is for: we had to rename four
  constructs and rewrite our scope to identifier form purely to make it meaningful.
  `ir["capabilities"]` also stays `[]` — the top-level collection appears unused, while
  the concept-level list is qualified.
evidence:
  commands:
    - kcf compile cap.kcf -o cap.json --validate
    - "python -c \"import json;print([c for c in json.load(open('cap.json'))['concepts'] if c['kind']=='ACTOR'][0]['capabilities'])\"   # -> ['cap.procure_to_pay']"
    - kcf completeness cap.json cap-scope.json
    - "python -c \"import json;print(json.load(open('cap.json'))['capabilities'])\"   # -> []"
  diagnostics:
    - "declaredScope.uncovered: ['procure_to_pay', 'Procure to pay, end to end', 'procure-to-pay']"
    - "blockers: [..., 'scope-capabilities-uncovered']"
    - "(no diagnostic explaining that only the namespace-qualified form matches)"
  snippet: |
    // cap.kcf
    kcf model Cap profile business-application {
      namespace cap;
      actor Clerk { capability procure_to_pay; }   // declared here
      entity Order { identity id: UUID generated; required total: Decimal; }
      // ... obligation-complete remainder omitted
    }

    // cap-scope.json
    {"scopeVersion":"1.0.0","model":"Cap",
     "includedCapabilities":["procure_to_pay",              // same token -> UNCOVERED
                             "Procure to pay, end to end",  // human phrasing -> UNCOVERED
                             "cap.procure_to_pay"]}         // qualified -> covered
    //
    // `capability "procure-to-pay";` is not an option: capability-decl takes a
    // semantic-ref, so a quoted string is a ParseError.
impact: >
  Affects anyone using the closed-world completeness gate, which is the only axis that
  asks whether the model covers what was promised. The failure is silent — an
  `uncovered` list with no hint that qualification is the issue — so the likely reactions
  are to conclude the axis is broken, or to paste construct identities into the scope,
  which makes the check tautological. Either way the governance value of a
  stakeholder-authored scope is lost.
suggestedChange: >
  Make `_covers` resolve a declared capability by its local name as well as its qualified
  form: index both `cap.procure_to_pay` and `procure_to_pay`, the way a trace resolver
  has to. That alone fixes the same-token case, which is the surprising one.
  For the human-phrasing case, either document plainly in `scope-v1.schema.json` that
  `includedCapabilities` are construct identities (and that a capability must be declared
  with `capability-decl` to be nameable), or give the scope an explicit mapping — e.g.
  `{"capability": "Procure to pay, end to end", "satisfiedBy": ["ProcurementCycle"]}` —
  so intent can be declared in the stakeholders' words and still be checkable.
  Whichever way it goes, `uncovered` would be far more useful if it said *why*: reporting
  the nearest available term would have turned an hour of guessing into a one-line fix.
workaround: >
  Write `includedCapabilities` as exact construct identities, and rename constructs where
  needed so the identities are the names you want to declare. We renamed four process
  constructs and rewrote the scope to match, then verified 18/18 covered.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. The two files in the snippet are the whole reproducer.

Found on a re-audit of a model that reaches `ready: true` with 0 required gaps: the
declared-scope axis was the last one still failing, and the reason turned out to be the
form of the identifier rather than anything about the model.

Sibling to the batch in `…-04` through `…-07`. Unlike those, this one is purely about the
matching rule and the schema's documentation of it — no grammar or IR change is implied by
the first suggestion.
