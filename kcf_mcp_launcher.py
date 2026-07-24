"""Console-script entry point for the ``kcf-mcp`` command (the KCF MCP server).

Resolves ``kcf-oss/mcp/server.py`` in either layout — a source checkout (this
launcher sits beside ``kcf-oss/``) or an installed wheel (the toolchain ships as
the ``kcf_oss`` package) — and runs its ``main()``. Equivalent to
``python kcf-oss/mcp/server.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _find_server() -> Path:
    here = Path(__file__).resolve().parent
    checkout = here / "kcf-oss" / "mcp" / "server.py"
    if checkout.exists():
        return checkout
    spec = importlib.util.find_spec("kcf_oss")
    if spec and spec.submodule_search_locations:
        candidate = Path(next(iter(spec.submodule_search_locations))) / "mcp" / "server.py"
        if candidate.exists():
            return candidate
    raise SystemExit(
        "kcf-mcp: could not locate the MCP server. Install with "
        "`pip install \"kcf-oss[mcp]\"`, or run from a checkout."
    )


def main() -> None:
    server = _find_server()
    sys.path.insert(0, str(server.parent))
    spec = importlib.util.spec_from_file_location("kcf_mcp_server", server)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.main()


if __name__ == "__main__":
    main()
