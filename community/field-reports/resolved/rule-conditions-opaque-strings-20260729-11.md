# Field report — rule conditions stay opaque strings although KCF already has an expression AST

> **Routing note:** `area: grammar-gap`. Per [`README.md`](../README.md) this routes to a
> **[Grammar RFC](../../../kcf-oss/docs/EXTENDING.md)** plus a
> **[VERSIONING](../../../kcf-oss/docs/VERSIONING.md)** decision, since it changes both
> the authoring surface and the `model-ir-v1` shape of `rules[].condition`.

```yaml
<!-- kcf-field-report:v1 -->
id: rule-conditions-opaque-strings-20260729-11
kcfVersion: 1.11.0
commit: 2071c8d
phase: model
area: grammar-gap
construct: rule-decl condition (RULE dimension)
severity: high
title: A rule's condition compiles to a bare string while a formula's expression compiles to an AST, so the entire RULE dimension is unreachable by code generation
observation: >
  Two dimensions state comparable things, and only one is parsed.

      formula:  expression = (cost - residual) / (life_years * 12);
      -> ir["math"][0]["expression"] == {"op":"/","left":{"op":"-", ...}}      (a tree)

      rule:     condition "order_amount > escalation_threshold";
      -> ir["rules"][0]["condition"] == "order_amount > escalation_threshold"   (a str)

  `rule-decl` types the condition as a `scalar`, so it is text by construction. In a real
  model of 51 rules, **0 of 51 conditions compiled to a tree**, though every one of them
  is a mechanically-implementable predicate: `approver_id == submitter_id`,
  `balance >= 0`, `invited_party_count < 3`, `party_barred == true`,
  `request_state != certified_or_approved`.

  The result is that the dimension carrying a system's business rules cannot be generated
  from. A code generator receives 51 sentences and can do nothing with them but paste them
  into a comment or a docstring, which is what ours did. The rules were then written by
  hand, with no tool able to confirm the hand-written form matches the declared condition.

  What makes this worth an RFC rather than a shrug is that **the machinery already
  exists**. The MATH parser produces exactly the tree shape a rule condition needs; it is
  simply not pointed at `condition`. `ruleKind` even names the intended use — `CONSTRAINT`
  maps to an invariant/validator, `DECISION` to a branch, `DERIVATION` to a computed
  value — so the semantics of a parsed condition are already decided.
evidence:
  commands:
    - kcf compile probe.kcf -o ir.json --validate
    - "python -c \"import json;ir=json.load(open('ir.json'));print(type(ir['math'][0]['expression']).__name__, type(ir['rules'][0]['condition']).__name__)\"   # -> dict str"
    - "python -c \"import json;ir=json.load(open('ir.json'));print(sum(1 for r in ir['rules'] if isinstance(r['condition'],dict)),'/',len(ir['rules']),'conditions parsed')\"   # -> 0 / 51"
    - "grep -n 'rule-decl' kcf-oss/grammars/authoring/KCF-AUTHORING-v1.2.ebnf   # condition is a scalar"
  diagnostics:
    - "(none — a condition is a well-formed scalar, so there is nothing to diagnose)"
  snippet: |
    kcf model Probe profile business-application {
      namespace p;
      entity Order { identity id: UUID generated; required total: Decimal; }
      actor Clerk { }
      work Fulfil { kind TASK; }
      relationship pa: PARTICIPATION Clerk -> Fulfil strength 1.0;
      relationship tr: TRANSFORMATION Fulfil -> Order strength 1.0;

      rule BigOrder {
        kind DECISION;
        condition "total > 100000";     // a predicate over a DECLARED attribute
        effect Fulfil;
        applies-to Order;
        authority Clerk;
      }
      // ... obligation-complete remainder omitted
    }
    // ir["rules"][0]["condition"] == "total > 100000"   — a string, not {"op":">",...}
    // The identical arithmetic inside a `formula` compiles to a tree.
impact: >
  Affects every model with business rules, i.e. the reason most people would reach for
  KCF. It is the single largest reason a KCF-generated application comes out as a
  structural scaffold: in our build 51 of 51 rules were dispositioned `delegated` in both
  realization manifests, and the resulting app enforced no approval threshold, no
  segregation of duties, and no balance guard, while `kcf assess` reported `ready: true`.
  A hand-built application from the same specification enforced all of them.
suggestedChange: >
  None proposed in detail — this is an RFC-shaped decision touching `rule-decl`, the
  `model-ir-v1` shape of `rules[].condition`, the analyzer, and codegen guidance. The
  evidence above is the input.
  Three things worth settling in that RFC, from this build:
  (1) whether a parsed condition replaces the string or sits beside it (`conditionAst`
      alongside `condition` would be additive and non-breaking, and would let existing
      models migrate lazily);
  (2) operand resolution, which is the same problem as
      `math-operands-not-resolved-20260729-10` and should be solved once for both — an
      unresolvable operand makes a parsed condition no more useful than a string;
  (3) how far the expression language should go. Our 51 conditions needed only
      comparison, equality, boolean and membership. Nothing needed quantifiers or
      function calls, so the existing math grammar plus comparison operators would have
      covered 100 % of a real government-system rule set.
workaround: >
  We surfaced each condition in the OpenAPI description of the affected operations so it
  is at least visible to an implementer, marked all 51 rules `delegated` with a note, and
  hand-wrote nothing — the rules remain unenforced in the generated application.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Second of five related reports. The set describes one coherent problem: KCF models the
*contract* of behaviour but not behaviour, and no gate notices. See
`math-operands-not-resolved-…-10` (the same operand problem in the dimension that *does*
have an AST), `no-behavioural-coverage-obligations-…-12` (why `ready: true` did not warn
us), `realization-ratio-not-reported-…-13` (why the manifest did not either), and
`no-procedure-surface-for-actions-…-14`.

If only one of the five is actioned, `…-10` is cheaper; this one has more leverage.

## Triage result — ACCEPTED — routed to a Grammar RFC (contract change)

Confirmed: a `formula` expression compiles to an AST while a `rule` `condition` compiles to a bare
string (`rule-decl` types it as a scalar), so the RULE dimension — a system's business rules — is
unreachable by code generation (0/51 conditions parsed in a real model; all delegated; the app
enforced no approval/SoD/balance rules while `assess` said `ready`). Changing `rule-decl`, the
`model-ir-v1` shape of `rules[].condition`, the analyzer, and codegen is a contract change, so per
the field-report routing and the one rule for core changes it goes through a **Grammar RFC +
VERSIONING** decision, never a silent change. Registered as **RFC-13** in `docs/IR-ROADMAP.md`,
carrying the report's three design questions (AST beside vs replacing the string; shared operand
resolution with report `-10`, already fixed for MATH; expression-language scope). Meanwhile the
gap is now **visible** rather than silent: `assess.behaviourallyComplete` (report `-12`) reports
`withParsedCondition: 0/N`. No grammar/IR change was made here.
