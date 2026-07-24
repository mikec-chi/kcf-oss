# 09 - Normalized Semantic IR

## Gate

Create the single semantic source of truth used by validation and generation.

## Prompt

```text
Author [PROJECT_ROOT]/domain/model.kcf from the approved [DOMAIN] artifacts,
then compile it into normalized KCF semantic IR at
[PROJECT_ROOT]/domain/model-ir.json.

Run:

python tools/kcf.py compile [PROJECT_ROOT]/domain/model.kcf `
  --output [PROJECT_ROOT]/domain/model-ir.json --validate

Use kcf-oss/docs/AUTHORING.md and the four source/golden pairs under
kcf-oss/tests/domains/ as authoring examples. Select [PROFILE_PRESET] and
add explicit `use` clauses only when the preset closure does not cover an
approved module. Do not write JSON IR by hand.
Add `implements <pattern>;` for every required profile pattern only after its
semantic constructs have been authored. Add `excludes <pattern>;` for an
approved omission of a recommended pattern. Never exclude a required pattern
or implement a prohibited pattern.

The IR must:

- use stable qualified identities;
- contain no duplicated declaration ownership;
- resolve every internal reference exactly once;
- preserve source and derivation provenance;
- preserve concept, relationship, action, lifecycle, process, rule,
  information, resource, temporal, spatial, intent, measure, and reasoning
  semantics;
- preserve organizations, governed information, policies, reasoning,
  assertions, identity resolutions, and query policies as dedicated IR
  collections when organizational knowledge is selected;
- activate integration, security, lineage, architecture, experience, design,
  analytics, and AI semantics through the selected profile closure;
- express every supported domain declaration in textual KCF; record semantics
  not expressible by AUTHORING v1.2 as explicit compiler gaps rather than
  injecting untraceable JSON;
- distinguish grammar definitions, domain assertions, runtime instances, and
  emitted artifacts;
- contain no application implementation code;
- carry inherited required, recommended, and prohibited patterns plus explicit
  implementation/exclusion claims into normalized IR;
- list unresolved external dependencies and unavailable checks explicitly.

Confirm that the generated IR `sourceMap` maps every compiled declaration to a
source span. Create a traceability appendix for requirement evidence not carried
by the compiler.

The phase passes only when recompilation is deterministic, the generated IR is
internally referentially closed, and every unavailable authoring construct is
visible for human disposition.
```
