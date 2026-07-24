from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    source: str
    line: int
    column: int
    end_line: int
    end_column: int

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "line": self.line,
            "column": self.column,
            "endLine": self.end_line,
            "endColumn": self.end_column,
        }


@dataclass
class Declaration:
    kind: str
    name: str
    values: dict[str, Any] = field(default_factory=dict)
    span: SourceSpan | None = None


@dataclass
class Model:
    name: str
    profile: str
    namespace: str | None = None
    extra_profiles: list[str] = field(default_factory=list)
    implemented_patterns: list[str] = field(default_factory=list)
    excluded_patterns: list[str] = field(default_factory=list)
    declarations: list[Declaration] = field(default_factory=list)
    span: SourceSpan | None = None
