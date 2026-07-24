# KCF Grammar Sources

- `core/` owns the shared metagrammar, root relationship algebra, and Action
  contracts.
- `authoring/` owns the ergonomic textual language that compiles into canonical
  semantic IR; it does not redefine the core constructs.
- `dimensions/` contains the sixteen primary semantic dimensions.
- `compilation/` defines semantic IR, plans, emitters, packages, and registry
  constructs.
- `profiles/operational/` composes integration, security, lineage, binding, and
  cost concerns.
- `profiles/emitters/` defines architecture, experience, design, analytics, and
  AI technology-facing profiles.

File paths and start productions are normative in
`../config/grammar-stack.json`.
