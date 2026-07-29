# Field report — `verify-realization` checks that delegation is *explained*, never how much is delegated, so a fully-delegated manifest passes

```yaml
<!-- kcf-field-report:v1 -->
id: realization-ratio-not-reported-20260729-13
kcfVersion: 1.11.0
commit: 2071c8d
phase: codegen
area: tooling
construct: kcf verify-realization (report summary)
severity: medium
title: The realization report gives a flat byDisposition count with no per-construct-class ratio, so a manifest that delegates every action and rule reports ok=true at the highest evidence level
observation: >
  `verify-realization` is careful about the right things: every identity must be
  accounted for, and every `delegated`/`out-of-tier`/`deferred`/`unsupported` disposition
  must carry a `note`. That is a real improvement over a prose `dropped: []` claim.

  What it does not do is weigh the dispositions. Our backend manifest reported:

      ok: true
      evidenceLevel: test-present          (the highest level)
      summary: {identityCount: 721, accountedFor: 721, missing: 0,
                byDisposition: {realized: 496, delegated: 225}}

  Every delegated entry had an honest note. Nothing was hidden. And yet the same report
  shape would be produced by a manifest that delegated **721 of 721** identities with a
  note on each — `ok: true`, `test-present`, nothing missing. "Accounted for" and
  "realized" are different claims, and only the first is checked.

  The signal that was missing is trivially derivable from data already in the manifest.
  Grouping the same dispositions by construct class:

      ACTION (crud/bulk)   246/246 realized
      ACTION.invoke          0/14  realized
      RULE                   0/51  realized

  The first line is reassuring. The second and third say "this is a scaffold, not an
  application" — and they would have said it on the first run rather than after a
  side-by-side comparison against a hand-built system.
evidence:
  commands:
    - kcf verify-realization model-ir.json realization-manifest.json --repo .
    - "python -c \"import json;r=json.load(open('realization-report.json'));print(r['ok'],r['evidenceLevel'],r['summary'])\""
    - "python -c \"import json;m=json.load(open('realization-manifest.json'));ir=json.load(open('model-ir.json'));d={x['semanticId']:x['disposition'] for x in m['dispositions']};inv=[a['id'] for a in ir['actions'] if a['operation']=='invoke'];print('ACTION.invoke realized:',sum(1 for i in inv if d.get(i)=='realized'),'/',len(inv))\""
  diagnostics:
    - "ok: true | evidenceLevel: test-present | byDisposition: {realized: 496, delegated: 225}"
    - "(no per-class breakdown; no signal that 0 of 14 invoke actions and 0 of 51 rules were realized)"
  snippet: |
    // A minimal manifest that passes verify-realization while realizing nothing:
    {
      "realizationManifestVersion": "1.0.0",
      "model": "M",
      "stack": "any",
      "tier": "backend",
      "dispositions": [
        {"semanticId": "m.Order",       "disposition": "delegated",
         "note": "not implemented in this tier"},
        {"semanticId": "CreateOrder",   "disposition": "delegated",
         "note": "not implemented in this tier"}
        // ... one honest note per identity, nothing realized
      ]
    }
    // -> ok: true, missing: 0. Accounted for is not the same as realized.
impact: >
  Affects anyone using the manifest as the handoff gate — which is its stated purpose
  ("so lossless handoff is checked, not merely asserted"). The check is sound for
  *accounting* and silent about *substance*, so a generation that produced structure and
  skipped behaviour passes at the highest evidence level. Ours did, twice, in both tiers,
  and the report gave us no reason to look closer.
suggestedChange: >
  Add a per-construct-class breakdown to the report summary. No new input is needed — the
  manifest already carries every disposition and the IR already carries every construct's
  kind:

      byClass: {
        "concept.ENTITY":  {realized: 64,  delegated: 0},
        "action.create":   {realized: 51,  delegated: 0},
        "action.invoke":   {realized: 0,   delegated: 14},
        "rule":            {realized: 0,   delegated: 51},
        "lifecycle":       {realized: 18,  delegated: 0}
      }

  Consider also a non-fatal `notice` when a whole class is 0 % realized, since that is
  almost always worth a human look, and it is the exact shape of the thing we missed.
  Deliberately not proposing a threshold that fails the build: a legitimately
  frontend-only tier delegates all persistence, so a hard rule would produce false
  failures. Reporting is enough — the number is the intervention.
workaround: >
  Compute it after the fact with a few lines over the manifest and the IR, as in the
  third command above. Every project that cares will write the same snippet.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@2071c8d`, grammar-stack 1.11.0, Python 3.12.10 on
Windows, against a 721-identity model with manifests for two tiers.

Fourth of five related reports, and the cheapest of the set — pure reporting over data the
tool already has, no contract change and no new check. It pairs with
`no-behavioural-coverage-obligations-20260729-12`: that one would have warned before
generation, this one would have warned immediately after.

## Triage result — ACCEPTED, fixed

Confirmed: `verify-realization` checked that every identity was *accounted for* and every
non-realized disposition carried a note, but never *how much* was realized — so a manifest
delegating 721/721 with a note on each reported `ok: true` at the highest evidence level. Fixed
in `tools/verify_realization.py`: the report summary now carries a **`byClass`** ratio
(realized/total per construct class, with `actions` split by `operation` so `action.invoke` is
visible separately from CRUD), and a top-level **`notices`** list raises a non-fatal note for
every class that is 0% realized. No new input — the manifest already carries every disposition
and the IR every construct's kind; deliberately non-fatal (a frontend-only tier legitimately
delegates persistence — the number is the intervention, not a hard gate). Schema updated
(`realization-report-v1`, additive). Verified + regression-pinned in `run_conformance.py`.
