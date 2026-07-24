from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "config" / "grammar-stack.json"
PRESETS_ROOT = PROJECT_ROOT / "profiles" / "presets"
PRESET_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "profile-preset-v1.schema.json"


def preset_roots() -> list[Path]:
    """Ordered preset search path. Directories named in the KCF_PRESET_PATH
    environment variable are searched before this stack's own presets, so a
    proprietary overlay stack can add presets that inherit OSS presets."""
    roots: list[Path] = []
    for entry in os.environ.get("KCF_PRESET_PATH", "").split(os.pathsep):
        entry = entry.strip()
        if entry:
            roots.append(Path(entry))
    roots.append(PRESETS_ROOT)
    return roots


def find_preset_file(profile: str) -> Path | None:
    for root in preset_roots():
        candidate = root / f"{profile}.json"
        if candidate.exists():
            return candidate
    return None


def known_presets() -> list[str]:
    names: set[str] = set()
    for root in preset_roots():
        if root.exists():
            names.update(item.stem for item in root.glob("*.json"))
    return sorted(names)
LIST_FIELDS = (
    "requestedModules", "requiredRuntimeCapabilities", "defaultEmitters",
    "requiredPatterns", "recommendedPatterns", "prohibitedPatterns",
)


class ProfileError(ValueError):
    pass


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_preset(profile: str) -> dict:
    path = find_preset_file(profile)
    if path is None:
        known = ", ".join(known_presets())
        raise ProfileError(f"Unknown profile {profile!r}; expected one of: {known}")
    preset = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(PRESET_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(preset), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<preset>"
        raise ProfileError(f"Invalid profile {profile!r} at {location}: {errors[0].message}")
    if preset["id"] != profile:
        raise ProfileError(f"Profile file {profile!r} declares mismatched id {preset['id']!r}")
    return preset


def compose_preset(profile: str, ancestry: tuple[str, ...] = ()) -> dict:
    if profile in ancestry:
        chain = " -> ".join((*ancestry, profile))
        raise ProfileError(f"Profile inheritance cycle: {chain}")
    preset = load_preset(profile)
    result = {
        "id": profile,
        "version": preset.get("version", "1.0.0"),
        "description": preset["description"],
        "extends": list(preset.get("extends", [])),
        "presetChain": [],
        **{field: [] for field in LIST_FIELDS},
    }
    for parent in preset.get("extends", []):
        inherited = compose_preset(parent, (*ancestry, profile))
        for field in LIST_FIELDS:
            result[field].extend(inherited.get(field, []))
        result["presetChain"].extend(inherited["presetChain"])
    for field in LIST_FIELDS:
        result[field].extend(preset.get(field, []))
        result[field] = list(dict.fromkeys(result[field]))
    result["presetChain"] = list(dict.fromkeys([*result["presetChain"], profile]))
    overlap = set(result["requiredPatterns"]) & set(result["prohibitedPatterns"])
    if overlap:
        raise ProfileError(f"Profile {profile!r} both requires and prohibits: {', '.join(sorted(overlap))}")
    return result


def resolve_modules(requested: list[str], manifest: dict | None = None) -> list[str]:
    manifest = manifest or load_manifest()
    modules = manifest["modules"]
    unknown = sorted(set(requested) - set(modules))
    if unknown:
        raise ProfileError(f"Unknown KCF modules: {', '.join(unknown)}")
    selected: set[str] = set()
    pending = list(requested)
    while pending:
        module = pending.pop()
        if module in selected:
            continue
        selected.add(module)
        item = modules[module]
        pending.extend(item.get("imports", []))
        pending.extend(item.get("semanticImports", []))
    selected.add(manifest["rootModule"])
    return [name for name in modules if name in selected]


def resolve_profile(profile: str) -> dict:
    manifest = load_manifest()
    preset = compose_preset(profile)
    return {
        "profile": preset["id"],
        "profileVersion": preset["version"],
        "description": preset["description"],
        "extends": preset["extends"],
        "presetChain": preset["presetChain"],
        "modules": resolve_modules(preset["requestedModules"], manifest),
        "runtimeRequirements": preset["requiredRuntimeCapabilities"],
        "emitters": preset["defaultEmitters"],
        "requiredPatterns": preset["requiredPatterns"],
        "recommendedPatterns": preset["recommendedPatterns"],
        "prohibitedPatterns": preset["prohibitedPatterns"],
        "grammarStackVersion": manifest["version"],
        "irVersion": manifest["irVersion"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a KCF profile preset and its complete dependency closure.")
    parser.add_argument("profile")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(resolve_profile(args.profile), indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
