# Field report — codegen's default principal is the RBAC superuser, so omitting auth bypasses every policy

```yaml
<!-- kcf-field-report:v1 -->
id: codegen-security-default-superuser-20260727-04
kcfVersion: 1.11.0
commit: c031be6
phase: codegen
area: codegen
construct: security
severity: high
title: Generated backend defaults an absent/blank principal to the superuser role, defeating the realized RBAC policies
observation: >
  The security profile's policies are realized correctly — a request carrying a role
  that lacks authority is denied (403). But the request principal is derived from a
  role header that DEFAULTS to the RBAC superuser ("Administrator") when the header is
  absent or blank. So an unauthenticated caller is treated as the superuser and passes
  every policy gate.
evidence:
  commands:
    - "DELETE /actions/DeleteEntity/{id}            # NO auth header -> 204 (deleted)"
    - "DELETE /actions/DeleteEntity/{id}  X-Role: Guest   # -> 403 (correctly denied)"
  diagnostics:
    - "current_principal(x_role: str|None = Header(default=\"Administrator\")) -> Principal(role=x_role or \"Administrator\")"
  snippet: |
    security {
      policy AccessControl { authority Administrator; ... }
    }
    # Codegen -> current_principal defaults role to the superuser when the header is
    # missing/blank, so "no identity" == "highest privilege".
impact: >
  Any generated backend from a model with a security profile: the policy layer looks
  enforced (wrong roles are denied) but is trivially bypassed by sending no identity at
  all. This is the inverse of fail-safe — absence of auth grants maximum privilege.
suggestedChange: >
  Default an absent/blank principal to an UNPRIVILEGED role (or reject with 401), never
  to the authority/superuser. Codegen guidance should state the fail-closed default and
  show it in the security EXAMPLE. The superuser should require an explicit, verifiable
  identity.
workaround: >
  In the generated app, change the default role to a least-privilege value and return
  401 on a blank/absent principal.
domainSanitized: true
```
