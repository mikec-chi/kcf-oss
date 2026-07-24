"""Console-script entry point for the installed ``kcf`` command.

Resolves the reference toolchain in either layout and delegates to
``kcf-oss/tools/kcf.py``'s ``main()``, so ``kcf <command>`` behaves exactly like
``python kcf-oss/tools/kcf.py <command>``:

* **Source checkout** — this module sits at the repo root beside ``kcf-oss/`` and
  ``semantic-core/`` (the sibling layout the extraction script produces). Full
  functionality, including ``kcf check``.
* **Installed wheel** — the toolchain ships as the ``kcf_oss`` package; the
  adopter commands (``compile`` / ``assess`` / ``coverage-report`` / …) resolve
  their data by path from inside the package. ``kcf check`` needs ``semantic-core`` and a
  build step, so it is a contributor command run from a source checkout.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _find_toolchain() -> tuple[Path, Path]:
    """Return (oss_root, tools_dir) for whichever layout we are running in."""
    here = Path(__file__).resolve().parent

    # 1. Source checkout: kcf-oss/ is a sibling of this launcher.
    checkout = here / "kcf-oss"
    if (checkout / "tools" / "kcf.py").exists():
        return checkout, checkout / "tools"

    # 2. Installed wheel: the toolchain is the importable `kcf_oss` package.
    spec = importlib.util.find_spec("kcf_oss")
    if spec and spec.submodule_search_locations:
        root = Path(next(iter(spec.submodule_search_locations)))
        if (root / "tools" / "kcf.py").exists():
            return root, root / "tools"

    raise SystemExit(
        "kcf: could not locate the toolchain. Install with `pip install kcf-oss`, "
        "or run from a checkout that keeps kcf-oss/ and semantic-core/ as siblings."
    )


def main() -> int:
    oss_root, tools = _find_toolchain()
    # kcf.py inserts its own PROJECT_ROOT (the kcf-oss root) before its imports,
    # so only the tools directory must be importable for the flat sibling imports.
    for entry in (str(tools), str(oss_root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    spec = importlib.util.spec_from_file_location("kcf_main", tools / "kcf.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
