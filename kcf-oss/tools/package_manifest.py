"""Validate KCF package manifests so the three layers ship separately.

A package manifest declares a distributable unit and its kind:

- ``vocabulary`` - the grammar, IR schema, and engines (org- and domain-agnostic);
- ``pattern-library`` - reusable, type-level business patterns (cross-organization,
  no tenant data);
- ``organizational-knowledge`` - one organization's instance model (single-tenant,
  private).

For a pattern-library, this validator checks that everything the manifest claims
to ``provide`` actually exists in the loaded contracts and role vocabulary, and
that its declared ``contents`` are present. That makes the pattern-library <->
organizational-knowledge boundary an explicit, checkable interface rather than a
convention.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from pattern_contracts import declared_roles, load_contracts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = PROJECT_ROOT / "schemas" / "package-manifest-v1.schema.json"


def validate(manifest: dict, base_dir: Path, contracts: dict[str, dict]) -> list[str]:
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    errors = [f"schema: {error.message}" for error in Draft202012Validator(schema).iter_errors(manifest)]
    if errors:
        return errors

    provides = manifest.get("provides", {})
    if manifest["packageKind"] == "pattern-library":
        available_patterns = set(contracts)
        available_roles = set(declared_roles(contracts))
        for pattern_id in provides.get("patterns", []):
            if pattern_id not in available_patterns:
                errors.append(f"provides.patterns lists {pattern_id!r}, which has no loaded contract")
        for role in provides.get("roles", []):
            if role not in available_roles:
                errors.append(f"provides.roles lists {role!r}, which no loaded contract declares")

    for relative in manifest.get("contents", []):
        if not (base_dir / relative).exists():
            errors.append(f"contents entry does not exist: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a KCF package manifest.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--base-dir", type=Path, help="root the manifest's contents paths are relative to (default: manifest's parents[2])")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base_dir = args.base_dir or args.manifest.resolve().parents[2]
    errors = validate(manifest, base_dir, load_contracts())
    if errors:
        print("\n".join(f"ERROR {item}" for item in errors), file=sys.stderr)
        return 1
    print(f"PASS package manifest {manifest['name']} ({manifest['packageKind']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
