---
description: Model a domain with KCF, then generate code (uses the kcf MCP server)
argument-hint: [domain description]
---

Use the `kcf` MCP server's tools to model the domain below and then generate an
application from the model — so the code is built from a complete, machine-checked
specification, not guessed from prose.

Domain: $ARGUMENTS

Follow this loop, showing me the model and the readiness verdict at each step:

1. Call `authoring_reference` (once) for the `.kcf` syntax. Draft a `.kcf` model
   capturing the entities, actors, events, lifecycles, relationships, and
   command/query action contracts the domain implies. Do not invent fields,
   statuses, or rules I didn't state — ask me when unsure.
2. `compile` the draft; fix any syntax/analyzer errors.
3. `assess` it. Fix every **required** gap (e.g. a missing identity). Realize the
   sensible **recommended** gaps (CRUD, lifecycle, set/bulk, transformation); mark
   reference/immutable entities read-only with `mutability "read-only";`. The model
   only needs to be **valid**, not fully `ready` — use `coverage` for a to-do list.
4. Ask me which **tech stack** to target (`list_stacks` shows the options).
5. Call `codegen_prompt(source, stack)` and run the returned system + user prompts
   to generate the app; finish with its coverage self-audit.
