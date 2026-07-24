from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def check() -> list[str]:
    errors = []
    manifest = json.loads((PROJECT_ROOT / "config" / "grammar-stack.json").read_text(encoding="utf-8"))
    matrix = json.loads((PROJECT_ROOT / "config" / "compatibility-matrix.json").read_text(encoding="utf-8"))
    lock = json.loads((PROJECT_ROOT / "config" / "module-lock.json").read_text(encoding="utf-8"))
    catalogue = json.loads((PROJECT_ROOT / "semantics" / "semantic-rules.json").read_text(encoding="utf-8"))
    if matrix["grammarStack"] != manifest["version"]: errors.append("compatibility matrix grammar stack version is stale")
    if manifest["irVersion"] not in matrix["supportedIrVersions"]: errors.append("manifest IR version is unsupported")
    if matrix["semanticCatalogueVersion"] != catalogue["version"]: errors.append("semantic catalogue version is incompatible")
    if lock["grammarStackVersion"] != manifest["version"]: errors.append("module lock grammar stack version is stale")
    for name, item in manifest["modules"].items():
        locked = lock["modules"].get(name)
        if not locked:
            errors.append(f"module {name} is not locked")
            continue
        digest = hashlib.sha256((PROJECT_ROOT / item["file"]).read_bytes()).hexdigest()
        if digest != locked["sha256"]: errors.append(f"module {name} hash differs from module lock")
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("\n".join(f"ERROR {item}" for item in errors))
        return 1
    count = len(json.loads((PROJECT_ROOT / "config" / "module-lock.json").read_text(encoding="utf-8"))["modules"])
    print(f"PASS compatibility matrix and {count} module locks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
