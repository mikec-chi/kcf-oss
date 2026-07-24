from __future__ import annotations

from .ast import Declaration


def record_source(source_map: dict, subject: str, declaration: Declaration) -> None:
    if declaration.span:
        source_map[subject] = declaration.span.as_dict()
