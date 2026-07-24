# House elicitation conventions — example

Copy this to `elicitation.md`, edit it to your team's standards, and point the
MCP server at it so the guided `model_domain` flow follows your house rules when
it interviews the user and drafts the `.kcf` model. It **tunes how** the domain is
elicited; it never lets the assistant invent facts the user didn't state.

**Where it plugs in:**

- **MCP host config** — set the env var once:
  ```jsonc
  { "mcpServers": { "kcf": { "command": "kcf-mcp",
      "env": { "KCF_ELICITATION_GUIDE": "/abs/path/mcp/elicitation.md" } } } }
  ```
  The `model_domain` prompt then injects it as *House elicitation conventions*.
- **Per invocation** — pass it inline: the prompt takes a `conventions` argument
  (`/kcf` in Claude, or the connector's Prompts UI), merged with the env file.

Contract: these guide the **questions asked** and **defaults proposed**. The
assistant must still ask before inventing fields, statuses, or rules, and the
model must reach **valid** before code generation. Keep it short and imperative.
Everything below is an example — replace it.

---

## Always ask about

- **Tenancy** — is data scoped per organization/tenant? If yes, every entity
  carries a tenant reference and every query is tenant-filtered.
- **Audit** — who did what, when? Default to an `audit-log` event on every
  command unless the user opts out.
- **Soft delete vs hard delete** — default to soft delete (`deleted_at`) for
  business entities; confirm before modeling a hard delete.
- **Lifecycle** — for any entity the user calls a "record", "case", "order", or
  "request", ask for its statuses and the allowed transitions.

## Standard actors

- Assume at least `admin` and `member` roles unless told otherwise; ask which
  actions each may perform and encode it as `authorization`.

## Standard entities to propose (confirm, don't assume)

- `User` / `Organization` when tenancy or auth comes up.
- A reference/lookup entity (marked `mutability "read-only";`) for any fixed code
  list the user mentions (statuses, categories, countries…).

## Naming

- Singular PascalCase concept names; verbs for commands (`ApproveInvoice`), nouns
  for queries (`OverdueInvoices`).

## Stop rules

- Never fabricate compliance, retention, or pricing rules — flag them as open
  questions for the user instead of guessing.
