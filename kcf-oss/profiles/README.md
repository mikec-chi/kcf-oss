# KCF Profile Presets

Presets select a deterministic module closure, runtime capabilities, and
business-pattern obligations. Presets may inherit from one or more
foundational presets through `extends`; the resolver deduplicates inherited
lists, rejects cycles, and rejects any pattern that becomes both required and
prohibited.

Foundational presets:

| Preset | Primary use |
| --- | --- |
| `business-application` | Governed transactional applications |
| `event-driven-system` | Event-oriented processes and integrations |
| `operational-system` | Work, scheduling, resources, and operations |
| `analytics-platform` | Governed transformation and measures |
| `ai-application` | Governed features, models, serving, and monitoring |
| `organizational-knowledge` | Policies, assertions, reasoning, provenance, and graph publication |

Business-pattern presets:

| Preset | Pattern family |
| --- | --- |
| `customer-relationship-management` | Customer 360, consent, interactions, opportunities |
| `order-to-cash` | Quote through collection and returns |
| `procure-to-pay` | Requisition through supplier payment |
| `case-management` | Intake, assignment, evidence, decision, SLA, escalation |
| `subscription-billing` | Entitlements, usage, recurring billing, renewal |
| `project-delivery` | Work breakdown, milestones, resources, risks, changes |
| `workforce-management` | Workers, positions, skills, capacity, delegation |
| `asset-maintenance` | Assets, inspections, maintenance, parts, downtime |
| `compliance-risk-management` | Obligations, risks, controls, audits, remediation |
| `master-data-management` | Canonical identity, matching, stewardship, synchronization |
| `knowledge-management` | Taxonomy, content, expertise, search, recommendation |

Resolve a preset:

```powershell
python tools/kcf.py profile customer-relationship-management
```

Textual models select one primary preset and may compose additional presets with
`use <preset>;`. They declare `implements <pattern>;` for required patterns and
may declare `excludes <pattern>;` for deliberately omitted recommendations.
The compiler carries all obligations and claims into normalized IR, where the
semantic analyzer enforces them.
