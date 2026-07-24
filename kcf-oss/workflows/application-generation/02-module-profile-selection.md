# 02 - Module and Profile Selection

## Gate

Approve which KCF semantics apply before authoring the model.

## Prompt

```text
Read the approved domain/00-domain-brief.md and
kcf-oss/config/grammar-stack.json. Evaluate the presets under
kcf-oss/profiles/presets/ before selecting individual modules.

Begin with [PROFILE_PRESET]. Run `python tools/kcf.py profile <preset>` for it
and every serious alternative, compare the returned module closure and runtime
requirements, and use the calculated dependency closure rather than manually
reconstructing imports.
For each alternative, also compare `requiredPatterns`, `recommendedPatterns`,
and `prohibitedPatterns`. Prefer the narrowest business-pattern preset whose
required semantic spine matches the approved domain.

Determine which KCF modules apply to [DOMAIN]. Produce
[PROJECT_ROOT]/domain/01-model-profile.md containing:

- required core dimension grammars;
- required operational profiles;
- required emitter profiles;
- requested conformance level [CONFORMANCE_LEVEL];
- constructs required from every selected module;
- prohibited or out-of-scope constructs;
- grammar imports and semantic dependencies;
- external registries or runtime facts required for validation;
- validations that will be unavailable without those facts;
- rationale for every selected or rejected module.
- selected preset, explicit `use` additions, and emitter targets.
- every required pattern and the model constructs that will satisfy it;
- accepted or excluded recommendations, with rationale;
- prohibited patterns and the controls that prevent them.

KCF and RELATIONSHIP normally apply to every domain model. Select other
modules because their semantic responsibilities are present, not because their
names merely resemble requirement vocabulary.

The phase passes only when every selected module has an evidence-backed purpose,
module ownership does not overlap, and every inherited pattern obligation has
an explicit disposition.
```
