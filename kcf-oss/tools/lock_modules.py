from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "config" / "grammar-stack.json"
OUTPUT = PROJECT_ROOT / "config" / "module-lock.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    modules = {}
    for name, item in manifest["modules"].items():
        path = PROJECT_ROOT / item["file"]
        modules[name] = {
            "version": "1.0.0",
            "file": item["file"],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    output = {"lockVersion": "1.0.0", "grammarStackVersion": manifest["version"], "modules": modules}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Locked {len(modules)} KCF modules")


if __name__ == "__main__":
    main()
