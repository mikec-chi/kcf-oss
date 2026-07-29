# Field report — `source-coverage` cannot see five IR collections, so constructs in them can never be traced

```yaml
<!-- kcf-field-report:v1 -->
id: source-coverage-blind-to-five-collections-20260729-04
kcfVersion: 1.11.0
commit: 549b566
phase: model
area: source-fidelity
construct: source_coverage.IDENTITY_COLLECTIONS
severity: medium
title: source-coverage reads 13 IR collections and ignores math/propositions/authorities/processes/profile sections, so constructs there are untraceable and uncountable
observation: >
  `source_coverage.construct_ids()` iterates `IDENTITY_COLLECTIONS`
  (source_coverage.py:29-33), which lists 13 collections: concepts, relationships,
  lifecycles, actions, collectionTransforms, organizations, information, rules,
  policies, reasoning, assertions, identityResolutions, knowledgeQueries.

  The IR carries more than that. `math`, `propositions`, `predicates`, `processes`,
  `authorities`, and the profile sections (`ir["integration"]["adapters"]` and its
  siblings) are all absent. A construct in one of those is really in the model — the
  compiler emitted it, `assess` counts it, a generator will see it — but citing it in a
  source trace makes it a `danglingConstruct`, and it can never contribute to
  `coveredSegments`.

  The effect is a silent ceiling on the faithfulness metric. In a model built from a
  structured source we ended up with 58 such constructs (33 authority grants from
  declared permissions, 9 value-domain propositions, 9 formulas, 4 integration
  adapters, 4 business processes). Their source segments are reported as
  `uncoveredSegments` — indistinguishable from prose nobody extracted — so
  `sourceComplete` cannot reach true no matter how faithful the extraction is.

  Worse for the tool's own purpose: the honest workaround is to drop those trace links,
  which shrinks the denominator and makes the loss *disappear* from the report rather
  than appear in it. That is the same failure shape as
  import-dbml-silent-noop-20260727-01 — a loss that looks like success.
evidence:
  commands:
    - "python -c \"import re,pathlib;s=pathlib.Path('kcf-oss/tools/source_coverage.py').read_text();print(re.search(r'IDENTITY_COLLECTIONS = \\((.*?)\\)',s,re.S).group(1))\""
    - kcf compile m.kcf -o ir.json --validate
    - "python -c \"import json;ir=json.load(open('ir.json'));print(len(ir['math']),len(ir['propositions']))\"   # -> constructs exist"
    - kcf source-coverage doc.json ir.json trace.json    # citing them -> danglingConstructs
  diagnostics:
    - "(no diagnostic — the constructs are simply absent from construct_ids(), so a trace citing them reports danglingConstructs and their segments report uncovered)"
  snippet: |
    kcf model M profile business-application {
      namespace m;
      entity Item { identity id: UUID; required name: String; }
      // Each of these compiles into a collection source-coverage does not read:
      proposition ItemStates { expression "state is one of new, done"; mode necessary; }
      formula ItemTotal { expression price - cost; }
      authority ItemGrant { mode may-perform; subject Clerk; target Item; when "read"; }
      actor Clerk { }
      // ...
    }
    // A trace citing ItemStates / ItemTotal / ItemGrant -> danglingConstructs.
    // Omitting them        -> their source segments count as uncoveredSegments.
    // Either way the model looks less faithful than it is.
impact: >
  Affects every model that uses the quantitative, logic, authority, process, or profile
  surfaces — i.e. anything beyond entities/actions/rules — and it affects the one axis
  that exists to prove nothing was dropped or invented. `sourceComplete` becomes
  unreachable for such models, which also blocks `closedWorldComplete` via the
  completeness tool's source axis, so a fully faithful extraction still reports as
  incomplete.
suggestedChange: >
  Extend `IDENTITY_COLLECTIONS` to every IR collection that carries identities:
  `math`, `propositions`, `predicates`, `processes`, `authorities`, `resources`,
  `routes`, `calendars`, `units`, `allocations`, `mutations`. Profile sections nest one
  level deeper (`ir[section][collection]`), so they need a small extra walk rather than
  a name in the tuple.
  Better still, derive the set from the IR schema instead of hard-coding it, so a new
  collection cannot be added to `model-ir-v1` and silently fall outside coverage. A
  cheap regression guard in the meantime: assert that every top-level array-of-objects
  in a golden IR is either in `IDENTITY_COLLECTIONS` or on an explicit exclusion list
  with a recorded reason — the same shape as the `coverage-meta` policy governance,
  which already prevents exactly this class of silent omission for coverage families.
workaround: >
  Our trace resolver classifies these separately: it resolves against the readable
  collections, detects names that exist only in an unreadable one, excludes them from
  the emitted trace (so integrity stays clean at 0 dangling) and then PRINTS the count
  and collection of every one. The loss stays visible in the build output instead of
  vanishing into a shrunken denominator, but it is still absent from the report the tool
  produces.
domainSanitized: true
```

## Notes for triage

Reproduced on `mikec-chi/kcf-oss@549b566`, grammar-stack 1.11.0, Python 3.12.10 on
Windows.

This was raised as a secondary note in the triage section of
`ordering-dimension-qualifier-catch-22-20260729-03`; filing it properly so it can be
triaged by `area`/`severity` on its own.

Also worth noting the interaction with `completeness`: the source axis reports
`evaluated-incomplete` purely because of this, so the model's `closedWorldComplete` flag
is held false by a tool limitation rather than by anything about the model.
