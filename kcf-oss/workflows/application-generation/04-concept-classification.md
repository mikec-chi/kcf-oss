# 04 - Concept Classification

## Gate

Approve stable concept identities and primary kinds.

## Prompt

```text
Create the [DOMAIN] concept catalogue using the approved vocabulary, selected
KCF modules, and applicable EBNF grammars.

For every concept declare:

- stable qualified name;
- primary KCF kind;
- definition and requirement evidence;
- abstract or instantiable status;
- permitted traits;
- attributes or semantic properties;
- references;
- identity and uniqueness policy;
- provenance;
- temporal validity where applicable;
- invariants;
- unresolved classification concerns.

Use Entity only for managed subjects. Keep Information, Rule, Event, Work,
Intent, Measure, Actor, Resource, Lifecycle, Organization, Reasoning, Logic,
Math, Temporal, and Spatial concepts distinct.

Produce:

- [PROJECT_ROOT]/domain/03-concepts.json
- [PROJECT_ROOT]/domain/03-concepts.md

Check stable identity, primary-kind compatibility, abstract instantiation,
reference resolution, duplicate names, and module ownership.

The phase passes only when every concept has one justified primary kind and all
references resolve or are explicitly deferred.
```

