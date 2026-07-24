# Whitepaper-to-Grammar Concept Map

## Part I: concepts, dimensions, and meaning

Part I establishes the universal concept metatype, distinct concept kinds,
dimension grammar responsibilities, lexical mapping, semantic parsing, four
semantic layers, and runtime meaning. These map to:

- `KCF`: concept kinds, constructs, traits, references, expressions,
  profiles, lexical bindings, assertions, runtime instances, provenance;
- the sixteen dimension grammar modules;
- capability contracts and bindings;
- the grammar/domain/runtime/emission separation documented in `README.md`.

## Part II: root relationship algebra

Part II defines ten root relationship families and their metadata. These map to
`RELATIONSHIP`, including endpoint constraints, verbs, inverse meaning,
directionality, cardinality, symmetry, transitivity, mode, roles, polarity,
strength, conditions, temporal semantics, validation, reasoning, execution,
provenance, and versioning.

Relationship definitions live in `RELATIONSHIP`; domain assertions and runtime
instances live in `KCF`. This preserves the whitepaper's three-way
distinction.

## Part III: grammar design and compilation

Part III defines the semantic metagrammar, individual dimension grammar shapes,
profiles, semantic analysis, semantic IR, capability contracts, emitters,
validation/reasoning/execution plans, registry behavior, packages, and extension
governance. These map to:

- `KCF` for metagrammar, profiles, extensions, and capability contracts;
- `ACTION` for record/set effects and collection transformation contracts;
- each named dimension module for its foundational constructs;
- `COMPILATION` for normalized IR and executable semantic plans;
- `AUTHORING` for ergonomic textual declarations that desugar into the canonical
  KCF and ACTION constructs;
- AUTHORING v1.2 and the organizational-knowledge IR collections for
  organizations, governed information, policies, reasoning, epistemic
  assertions, identity reconciliation, bitemporal history, ingestion
  provenance, access policy, and explicit query assumptions;
- `INTEGRATION`, `SECURITY`, and `LINEAGE` for reusable cross-dimensional
  operational profiles;
- `ARCHITECTURE`, `EXPERIENCE`, `DESIGN`, `ANALYTICS`, and `AI` for
  semantic-preserving dimension profiles;
- the manifest and integrity lock; versioned JSON Schemas; textual compiler;
  profile resolver; validator, linter, analyzer, and conformance fixtures;
  semantic-delta, migration, and compatibility tools; and the LLM code-generation
  pack (`codegen/`) that turns a `ready` IR into an application for any stack.
  (A separate commercial platform builds on the same IR.)

The PDFs call the series Parts I-III of V. This implementation covers only the
three supplied documents and leaves extension points for later execution-focused
parts without inventing their missing requirements.
