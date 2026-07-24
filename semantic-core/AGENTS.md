# Semantic Core Instructions

`semantic-core` owns only stack-neutral rules. Do not add KCF module names,
DBML grammar names, emitter-specific requirements, or target-technology syntax.

- Edit `semantics/stack-rules.md` or `semantics/action-rules.md`.
- Preserve stable dotted rule IDs.
- Regenerate with `python tools/build_rules.py`.
- Then regenerate both consumer catalogues:
  `dbml-stack/tools/build_semantic_rules.py` and
  `kcf-oss/tools/build_semantic_rules.py`.
- A consumer may specialize wording while retaining neutral ownership; it may
  not silently fork a neutral rule under a new identity.
