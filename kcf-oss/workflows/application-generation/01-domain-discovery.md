# 01 - Domain Discovery

## Gate

Confirm domain scope and evidence before classifying concepts.

## Prompt

```text
Analyze all requirements under [REQUIREMENTS_PATH] for [DOMAIN].

Produce [PROJECT_ROOT]/domain/00-domain-brief.md containing:

- domain purpose and boundaries;
- stakeholders and actors;
- managed subjects;
- work performed;
- events and observations;
- lifecycle and state concerns;
- policies, decisions, obligations, and prohibitions;
- information created, consumed, or exchanged;
- resources and capacity constraints;
- temporal and spatial concerns;
- desired outcomes and measures;
- external systems and integrations;
- security, privacy, safety, and regulatory constraints;
- domain exclusions;
- contradictions and unresolved ambiguity;
- questions that materially affect the model.

For every material statement identify its requirement source or label it as an
assumption. Do not propose databases, APIs, classes, services, or screens yet.

The phase passes only when the scope, evidence, exclusions, assumptions, and
material open questions are explicit.
```

