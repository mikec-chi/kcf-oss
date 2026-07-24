# 05 - Relationship Model

## Gate

Approve how concepts are connected before behavior is generated.

## Prompt

```text
Create the [DOMAIN] relationship model from the approved concept catalogue.

For every relationship specify:

- stable identity;
- reusable relationship definition or definition reference;
- exactly one root relationship kind;
- source and target;
- forward and inverse meanings;
- endpoint-kind and trait constraints;
- source and target cardinalities;
- qualifiers;
- directionality;
- symmetry and transitivity policy;
- mode, roles, polarity, and strength where applicable;
- conditions;
- effective and runtime temporal validity;
- provenance;
- validation, reasoning, and runtime implications.

Use only these roots:

CLASSIFICATION, COMPOSITION, ASSOCIATION, IDENTITY, PARTICIPATION,
DEPENDENCY, TRANSFORMATION, CAUSATION, ORDERING, GOVERNANCE.

Use the most precise root. Do not infer causation from dependency, authority
from participation, or identity from classification. Store one canonical
orientation and derive inverse traversal.

Produce:

- [PROJECT_ROOT]/domain/04-relationships.json
- [PROJECT_ROOT]/domain/04-relationship-review.md

The phase passes only when endpoints resolve, roots are precise, cardinalities
are coherent, and duplicate or contradictory facts have been addressed.
```

