# KCF Versioning and Compatibility

KCF versions three contracts independently:

- grammar-stack version;
- normalized semantic IR version;
- semantic-rule catalogue version.

`config/compatibility-matrix.json` declares supported combinations.
`config/module-lock.json` records each grammar module version and SHA-256 digest.
Run `python tools/lock_modules.py` only when an intentional grammar change has
been reviewed, and then run the complete conformance suite.

Semantic changes follow these rules:

- removing a concept, changing its primary kind, narrowing a required contract,
  or adding a runtime requirement is breaking;
- adding an optional concept or attribute is compatible;
- documentation-only changes are patch-level;
- deprecated diagnostic IDs remain aliases for at least one major release.

Use `tools/semantic_delta.py` before release and `tools/migrate_ir.py` when an
older or unversioned IR document must be brought to the current schema.
Recompile current `.kcf` source whenever possible; migration is for persisted IR
without a current source representation. Run compatibility checks before
publishing.
