<!--
Elicitation pack — copy to <pack-name>/guide.md and edit.
Header (for the sibling README.md):
  Title:   e.g. "SaaS multi-tenant"
  Author:  <you>
  Use when: <the kind of domain this fits — e.g. any multi-tenant B2B SaaS>
  Assumes: <what it presumes — e.g. per-org tenancy, RBAC>
-->

# House elicitation conventions — <pack name>

Guide the questions and defaults while modelling. Never invent facts the user did
not state — ask.

## Always ask about

- **Tenancy** — is data scoped per organization/tenant? If yes, every entity
  carries a tenant reference and every query is tenant-filtered.
- **Audit** — who did what, when? Default to an audit event on every command unless
  the user opts out.
- **Lifecycle** — for any "record"/"case"/"order"/"request", ask its statuses and
  the allowed transitions.

## Standard actors & entities (confirm, don't assume)

- Propose at least `admin` and `member` roles; ask which actions each may perform
  and encode it as `authorization`.
- Propose `Organization`/`User` when tenancy or auth comes up.

## Naming

- Singular PascalCase concepts; verbs for commands (`ApproveInvoice`), nouns for
  queries (`OverdueInvoices`).

## Stop rules

- Never fabricate compliance, retention, or pricing rules — flag them as open
  questions instead of guessing.
