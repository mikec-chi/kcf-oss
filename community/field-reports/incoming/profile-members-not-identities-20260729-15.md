# Field report — profile-section members are not semantic identities, so a manifest that builds none of the declared screens passes while one that admits it fails

```yaml
<!-- kcf-field-report:v1 -->
id: profile-members-not-identities-20260729-15
kcfVersion: 1.11.0
commit: 2071c8d
phase: codegen
area: tooling
construct: ir_identity.model_semantic_ids / profile sections (experience, design, security, …)
severity: high
title: Members of a profile section carry no semantic identity, so declared views/tokens/controls cannot be accounted for — omitting them reports ok=true and dispositioning one reports unknown-identity
observation: >
  A profile section is one identity; everything inside it is invisible to accounting.

  In a model declaring 5 views:

      declared views in the IR:                 5
      counted as semantic identities:           0
      is the section 'experience' an identity:   True
      total identities:                         15

  Two consequences, and together they invert the incentive the manifest exists to create.

  **Omission passes.** A frontend manifest that builds *none* of the 5 declared screens,
  dispositioning only the section with a one-line note, verifies clean:

      ok: true   identityCount: 15   accountedFor: 15   missing: 0   errors: 0

  **Admission fails.** Adding an honest per-screen entry —
  `{"semanticId": "ApprovalQueue", "disposition": "delegated",
     "note": "declared in the model but not built"}` — is rejected:

      ok: false
      unknown-identity — manifest references 'ApprovalQueue', which is not a semantic
      identity in the IR

  So there is no way to record that a specific declared screen is missing. The only
  accepted description of "we built 2 of 17 views" is a single `delegated` line on
  `experience`, which reads identically to "the frontend tier does not apply here".

  This is the same anti-pattern as `document-profile-missing-prose-image-20260729-01`
  (already resolved): the check rewarded declaring *less* than you knew. There it was a
  `documentKind` you were better off deleting; here it is a per-artifact disposition you
  are forced to delete.

  It is not limited to presentation. The same holds for every profile section —
  `security` (controls, threats, treatments), `lineage`, `architecture`, `integration`,
  `analytics`, `ai`. A declared security control cannot be individually accounted for
  either, which matters more than a screen.

  Worth noting how this interacts with policy. `coverage-meta` records EXPERIENCE and
  DESIGN as `intentionally-none`:

      EXPERIENCE (UI/flows) is emitter-tier; frontend generation derives from
      ENTITY/ACTION, so no required experience completeness obligation is imposed.

  That is defensible for a generated CRUD UI, where screens genuinely do derive from
  ENTITY/ACTION. It stops holding when a source declares its own view set: the model
  then contains named screens that no obligation checks *and* no identity accounts for,
  so both gates are silent at once.
evidence:
  commands:
    - kcf compile probe.kcf -o ir.json --validate
    - "python -c \"import importlib.util,json,sys;s=importlib.util.spec_from_file_location('i','kcf-oss/tools/ir_identity.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);ir=json.load(open('ir.json'));ids=set(m.model_semantic_ids(ir));v=[x['id'] for x in ir['experience']['views']];print(len(v),'views,',sum(1 for x in v if x in ids),'are identities,','experience' in ids)\"   # -> 5 views, 0 are identities, True"
    - kcf verify-realization ir.json manifest-omitting-views.json    # -> ok: true, missing: 0
    - kcf verify-realization ir.json manifest-naming-a-view.json     # -> ok: false, unknown-identity
  diagnostics:
    - "ok: true | identityCount: 15 | accountedFor: 15 | missing: 0 | errors: 0   (zero of five declared screens built)"
    - "unknown-identity — manifest references 'ApprovalQueue', which is not a semantic identity in the IR"
  snippet: |
    kcf model Probe profile business-application {
      namespace p;
      entity Order { identity id: UUID generated; required total: Decimal; }
      actor Clerk { }
      work Fulfil { kind TASK; }
      relationship pa: PARTICIPATION Clerk -> Fulfil strength 1.0;
      relationship tr: TRANSFORMATION Fulfil -> Order strength 1.0;

      experience {
        app Shop { entry OrderList; }
        view OrderList { entity Order; }
        view OrderDetail { entity Order; }
        view ApprovalQueue { entity Order; }   // none of these five
        view Dashboard { entity Order; }       // can be individually
        view AuditTrail { entity Order; }      // dispositioned
      }
      // ... obligation-complete remainder omitted
    }
impact: >
  Affects any model that declares its own presentation, security, lineage, architecture,
  integration or analytics artifacts — i.e. any model transcoded from a specification
  that covers more than the data layer. The manifest's stated purpose is that "lossless
  handoff is checked, not merely asserted", and for these sections it cannot be: the
  granularity to express the loss does not exist.
  In our build 17 views and a full design system were declared and 2 views were realized.
  Both tiers still reported `ok: true`, `test-present`, 723/723 with zero errors. Nothing
  in the toolchain indicated the shortfall — it was noticed only when a human looked at
  the screen and said the UI was not at par.
  Filed `high` rather than `medium` on three grounds: the failure is silent, honesty is
  actively rejected, and it spans eight sections including `security`.
suggestedChange: >
  Register profile-section members in `ir_identity.model_semantic_ids` using a qualified
  form, e.g. `experience.views.ApprovalQueue`, `design.systems.MyDS`,
  `security.controls.AccessControl`. `ir_identity` already documents itself as the single
  source of truth for "every semantic identity", and its docstring lists these very
  sections as the ones a previous subset-enumeration bug had left unverified — so this
  looks like the same fix, one level deeper.
  That change alone would have surfaced `experience.views: 2/17 realized` in the
  per-class breakdown proposed in `realization-ratio-not-reported-20260729-13`, and it
  would remove the `unknown-identity` rejection that currently blocks an honest entry. It
  is additive to the report and the manifest schema — existing manifests that disposition
  only the section would begin reporting the members as missing, so it wants the same
  staged rollout suggested elsewhere in this batch (warn first, then require).
  Separately worth revisiting whether `intentionally-none` is still right for EXPERIENCE
  when the model declares explicit views; a `recommended` obligation such as "every
  declared view is realized or dispositioned" would cost little and close the second gate.
workaround: >
  None that is honest within the manifest. We dispositioned the section `delegated` with
  a prose note naming which screens were not built, which a human can read and no tool
  can check, and recorded the shortfall in the project's own mapping notes instead.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows. The snippet plus two small manifests are the whole reproducer; the second
manifest differs from the first by one appended disposition and flips `ok` from true to
false.

Sixth report in the 2026-07-29 batch, and a distinct mechanism from the other five.
Those concern *behaviour* the model cannot express (`rule-conditions-opaque-strings-…-11`,
`no-procedure-surface-for-actions-…-14`) or gates that do not examine it
(`no-behavioural-coverage-obligations-…-12`, `realization-ratio-not-reported-…-13`). This
one concerns **granularity**: the model does hold the declaration, and the accounting
layer has no unit small enough to refer to it.

It also limits the fix proposed in `…-13`: a per-construct-class ratio cannot report
`experience.views 2/17` while those views are not identities, so that report and this one
are best actioned together.

Related: `source-coverage-blind-to-five-collections-20260729-04` (in
[#17](https://github.com/mikec-chi/kcf-oss/pull/17), merged) noted that profile sections
are unreadable by `source_coverage`. That was about *traceability*; this is about
*accountability* — the same structural cause with a different and sharper consequence.
