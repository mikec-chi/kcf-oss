# 02b - Pattern-Seeded Comprehensive Synthesis

## Gate

Optional accelerator, used when the human states an intent as a broad, named
pattern ("I want a procure-to-pay process") rather than detailed requirements.
It flips the human's role from author to curator: the LLM drafts a comprehensive
model from general domain knowledge, structured by the grammar's dimensions and
measured against the pattern's contracts, and the human validates it in step 10c.
This step never commits knowledge; it produces reviewable proposals only.

## Prompt

```text
The stakeholder named a pattern: [PATTERN] (a profile/preset id).

1. Resolve the scaffold. Run:

   python tools/kcf.py profile [PATTERN]   # OSS foundational profiles
   # or, for a business pattern in an overlay stack:
   python <overlay>/tools/<cli>.py profile [PATTERN]

   Record its requiredPatterns, recommendedPatterns, prohibitedPatterns, and the
   resolved module closure. The modules tell you which of the 16 dimensions are
   in play; the required patterns are the obligations you must model; the
   prohibited patterns are anti-patterns you must NOT introduce.

2. Read the pattern contracts for each required (and recommended) pattern id.
   Each contract lists obligations that reference roles by TRAIT (e.g.
   "purchase-order", "supplier"), never by literal name. These traits are your
   synthesis target: every concept you propose to fulfil a role must carry the
   corresponding trait.

3. Synthesize comprehensively, dimension by dimension. For each concept you
   introduce, walk the in-scope dimensions and propose what the concept needs in
   each: identity and attributes (ENTITY); states and transitions (LIFECYCLE);
   the actions that change it, with authorization (ACTION); how it relates to
   other concepts via the typed algebra (RELATIONSHIP); governing rules and
   policies (RULE); who acts (ACTOR/ORGANIZATION); events, timing, measures, and
   resources as applicable. Do not introduce any prohibited pattern.

4. Tag every proposal as governed synthetic knowledge: extraction-method llm,
   extraction-model "[MODEL_ID]", a calibrated confidence, status inferred for
   assertions. Record pattern origin so template and tenant data stay separable:
   put the fulfilling role trait on each concept, and record the seeding pattern
   id in the concept's metadata (metadata.seededFrom = "[PATTERN_ID]"). This
   keeps the pattern (type-level, cross-organization) distinguishable from the
   organization's own customizations (instance-level) throughout the model. At
   each org-specific decision point (approval thresholds, terms, ownership)
   present the typical value AND flag it for the SME to set.

5. Compile the draft to [PROJECT_ROOT]/domain/synthetic-model-ir.json and
   self-check it - "comprehensive" must be measurable, not asserted:

   python tools/kcf.py validate [PROJECT_ROOT]/domain/synthetic-model-ir.json
   python tools/kcf.py pattern-check [PROJECT_ROOT]/domain/synthetic-model-ir.json
   python tools/kcf.py coverage-report [PROJECT_ROOT]/domain/synthetic-model-ir.json --by-concept

   Iterate until requiredButAbsent and claimedButUnproven are empty and every
   required coverage gap is filled or recorded as a justified exclusion.

Write the draft and a per-concept, dimension-by-dimension rationale to
domain/synthetic-proposals.md, then hand off to step 10c for SME confirmation.
Nothing synthesized here becomes fact until the SME confirms it.
```
