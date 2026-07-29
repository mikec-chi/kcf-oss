# Field report — an action can declare a full contract but never a procedure, so specified algorithms have nowhere to go

> **Routing note:** `area: grammar-gap`. Per [`README.md`](../README.md) this routes to a
> **[Grammar RFC](../../../kcf-oss/docs/EXTENDING.md)** plus a
> [`VERSIONING`](../../../kcf-oss/docs/VERSIONING.md) decision. It is the largest of the
> five reports in this batch and the one most likely to be declined on scope grounds; it
> is filed because the evidence is unusually concrete.

```yaml
<!-- kcf-field-report:v1 -->
id: no-procedure-surface-for-actions-20260729-14
kcfVersion: 1.11.0
commit: 2071c8d
phase: model
area: grammar-gap
construct: action-decl (ACTION dimension) / WORK process
severity: medium
title: ACTION carries idempotency/atomicity/concurrency/authorization but no procedure, so a source that specifies algorithm steps has no construct to compile them into
observation: >
  `action-decl` is rich about the *contract* of an operation — `operation`, `scope`,
  `selection`, `input`/`output` cardinality, `mutate`, `idempotency`, `atomicity`,
  `concurrency`, `authorization`, pre/post-conditions, `failure-mode`. It says nothing
  about what the operation does.

  For CRUD that is exactly right: the procedure is implied by `operation` + `target`, and
  KCF generated 246 of our 246 CRUD/bulk actions cleanly from the contract alone. For a
  domain operation it is the whole difficulty. Our source specified all 11 of its
  algorithms as ordered steps:

      steps: { 1: action(lock_series, [document_type: document_type])
               2: if (series_missing) then { action(create_series, [next_number: 1]) }
               3: transform(next_number -> zero_padded_sequence) using: zfill_from_format
               4: transform(zero_padded_sequence -> document_number) using: apply_series_format
               5: action(increment_series)
               6: emit(Report: document_number) }

  There is no construct to compile that into. `process` (WORK) is BPMN choreography over
  work items, not a procedure over data; `math` holds an expression but not a sequence
  with side effects. So all 11 algorithms were dropped at the transcoding step and the 14
  corresponding actions became `delegated` — a contract-checked endpoint with a body that
  returns "not specified by the model".

  Note what the existing contract already provides. An `invoke` action with
  `atomicity=atomic`, `idempotency=conditional`, `concurrency=optimistic` and
  `authorization` tells a generator precisely how to *wrap* a body: transaction boundary,
  no-op detection, version guard, policy gate. All of that was generated correctly. The
  only missing thing is the body.

  We measured what that costs. A hand-built application from the same source implements
  the same 14 operations in roughly 990 lines of domain service — first-in-first-out costing,
  straight-line accrual, document numbering, approval routing. That is the entire
  behavioural gap between a KCF-generated application and a working one, and none of it
  is expressible today.
evidence:
  commands:
    - "grep -n 'action-decl' -A14 kcf-oss/grammars/authoring/KCF-AUTHORING-v1.2.ebnf   # no procedure member"
    - kcf compile model.kcf -o ir.json --validate
    - "python -c \"import json;a=[x for x in json.load(open('ir.json'))['actions'] if x['operation']=='invoke'][0];print(sorted(a))\"   # contract keys only"
    - kcf verify-realization ir.json realization-manifest.json --repo .   # 14 invoke actions -> delegated
  diagnostics:
    - "(none — an action without a procedure is well-formed; there is no procedure to omit)"
  snippet: |
    kcf model Probe profile operational-system {
      namespace p;
      entity Series { identity id: UUID generated; required next_number: Integer; }
      actor Clerk { }
      work Assign { kind TASK; }
      relationship pa: PARTICIPATION Clerk -> Assign strength 1.0;
      relationship tr: TRANSFORMATION Assign -> Series strength 1.0;

      // Everything about HOW to allocate a number is expressible except the steps.
      command NextDocumentNumber {
        operation invoke;
        scope record;
        target Series;
        input one; output one;
        idempotency conditional;      // the generator knows to make it a no-op-safe call
        atomicity atomic;             // ... and to wrap it in one transaction
        concurrency optimistic;       // ... and to guard on version
        authorization p.SeriesPolicy;
        // steps: lock the series row, format, increment   <- nowhere to put this
      }
      // ... obligation-complete remainder omitted
    }
impact: >
  Affects any model whose source specifies procedures — which is most real
  specifications, and certainly any regulated one. The generated application gets a
  correct, authorized, transactional endpoint per operation and an empty body, so the
  behavioural half must be hand-written with nothing verifying it against the spec. In our
  build that was 14 of 260 actions by count and approximately all of the domain value.
suggestedChange: >
  None proposed in detail; this needs an RFC and a versioning decision. Two shapes seem
  worth weighing, and they differ a lot in ambition:

  (a) **A checkable delegation.** Keep procedures out of KCF, but let an action declare
      `delegates-to <handler-name>` with its pre/post-conditions, so the handoff is a
      named, verifiable contract instead of an absence. `verify-realization` could then
      require an artifact for the named handler, and a missing implementation would fail
      rather than pass as `delegated`. Small, additive, and it preserves the "OSS stops at
      the IR" boundary — arguably the boundary is honoured better by naming the seam than
      by leaving it implicit.

  (b) **An ordered step list.** A typed sequence of steps over declared constructs —
      lock/read/write/transform/emit, with a guard expression per step — reusing the
      expression AST from `math` and the operand resolution proposed in
      `math-operands-not-resolved-20260729-10`. Considerably larger, and it invites the
      objection that KCF would become a programming language. The counter-argument from
      this build is that the source needed only 6 step kinds and never a loop.

  (a) is worth doing regardless of whether (b) is ever attempted; it is cheap and it
  converts a silent gap into a checked one.
workaround: >
  Exposed each of the 14 as a contract-checked endpoint returning `status: delegated`
  with a note, dispositioned them `delegated` in the manifest, and documented the
  procedures separately. The endpoints are authorized, transactional and correct in
  everything except what they do.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

Last of five related reports, and the one I would deprioritise if the set is triaged
together: options (a) and (b) both need a design decision, whereas
`math-operands-not-resolved-…-10`, `no-behavioural-coverage-obligations-…-12` and
`realization-ratio-not-reported-…-13` are all deliverable without one and would together
have made this gap visible before we generated anything.

Stated plainly because it is the honest framing: KCF's boundary is presented as
"stops at the IR", but in practice it falls between *structure* and *behaviour*. The
structural side was excellent — 64 entities, 260 actions, 18 lifecycles, 111 foreign keys,
a full OpenAPI contract and a typed client, all generated, reproducible and verified at
721/721. Whether the behavioural side belongs inside that boundary is a project decision,
not a defect. What is a defect is that nothing tells you which side of the line your model
falls on, and that is what the other four reports address.

## Triage result — ACCEPTED — routed to a Grammar RFC (contract change)

Confirmed: `action-decl` carries a full operation *contract* but no *procedure*, so a source that
specifies an algorithm as ordered steps has no construct to compile it into (`process` is BPMN
choreography, `math` an expression, not a sequence with side effects). CRUD is unaffected (procedure
implied by operation+target), but `invoke` domain actions become contract-checked endpoints with an
empty body — the measured behavioural gap between a generated app and a working one. Adding a
procedure surface changes `action-decl` and `model-ir-v1`, so it routes to a **Grammar RFC +
VERSIONING** decision. Registered as **RFC-14** in `docs/IR-ROADMAP.md` (largest of the batch and
explicitly flagged as possibly out-of-scope — whether procedural behaviour belongs inside KCF's
boundary is a project decision, not a defect; the report proposes no production). The *visibility*
of the gap is fixed independently: `assess.behaviourallyComplete` reports
`invokeActions.withProcedure: 0/N` (report `-12`) and `verify-realization` byClass shows
`action.invoke` 0% realized (report `-13`). No grammar/IR change was made here.
