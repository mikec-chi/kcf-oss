# 11 - Runtime Capability and Emitter Contracts

> **Scope note.** kcf-oss stops at the semantic IR. Runtime manifests and
> deterministic emitters (and `runtime-manifest-v1`) are part of the commercial
> platform, not kcf-oss. On the open-source path you can skip to a `ready` IR and
> generate code with the LLM `codegen/` pack (which carries its own coverage
> self-audit). This step applies only if you are targeting that commercial
> runtime/emitter surface.

## Gate

Confirm that the selected runtime and emitters can preserve the validated model.

## Prompt

```text
Derive the [DOMAIN] runtime capability contract from the validated semantic IR
and `config/compatibility-matrix.json`.

Produce [PROJECT_ROOT]/domain/08-runtime-contract.json containing, for every
capability:

- stable identity and semantic version;
- source semantic identities;
- input and output semantic kinds and schemas;
- preconditions and postconditions;
- side effects and read/write sets;
- transaction, concurrency, idempotency, and retry requirements;
- authorization and data scope;
- audit and evidence requirements;
- failure modes, timeout, compensation, and reconciliation;
- environment and resource requirements;
- selected implementation binding;
- fallback binding and equivalence justification, when allowed.

Produce domain/08-emitter-support.md containing a matrix of every required
semantic element against each selected target. Use the target's declared support
and do not infer support merely from a target's name.

Produce [PROJECT_ROOT]/runtime/runtime-manifest.json conforming to
schemas/runtime-manifest-v1.schema.json. Its capabilities, bindings, and exact
module versions must agree with the detailed runtime contract and the current
module lock. Run runtime drift against the validated IR before approval.

Classify unsupported semantics as:

- error: generation must stop;
- warning: explicit approved degradation;
- preserve: retain in an extension envelope for another consumer.

Silent omission is forbidden.

The phase passes only when all required runtime semantics have compatible
bindings, the runtime manifest is schema-valid and drift-free, and every emitter
has an explicit support decision.
```
