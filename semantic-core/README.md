# Shared Semantic Core

This package owns stack-neutral semantic rules used by KCF and any other
grammar stack. It contains no KCF-, DBML-, or emitter-specific constructs.

- `semantics/stack-rules.md` owns general module, name, type, reference, graph,
  time, security, governance, and observability rules.
- `semantics/action-rules.md` owns technology-neutral record, set, collection,
  transformation, invocation, transaction, retry, and destructive-action rules.
- `semantics/semantic-rules.json` is the generated machine-readable catalogue.

Run `python tools/build_rules.py` to regenerate the catalogue. Consumers merge
these rules with their stack-local catalogue and may override wording without
changing rule ownership.
