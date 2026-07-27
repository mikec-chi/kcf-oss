"""Deterministic importer: a DBML schema -> KCF model + source document + trace.

Removes the hand-translation error class for relational sources. Translating DBML to a
semantic model by hand silently drops columns, relationship cardinality, `on_delete`,
and the table `category`; a deterministic importer captures all of them **by
construction**. Each `Table` -> an ENTITY concept, each column -> a typed attribute,
each `Ref` (and inline `[ref: ...]`) -> a typed relationship carrying `cardinality` and
`on-delete`, and a DBML `category` (a `[category: ...]` table setting or a
`Note: 'category: X'`) -> advisory `metadata.category`.

Emits the (model, source-document, source-trace) triple `source_coverage` consumes -
source-complete by construction, so a subsequent hand edit that drops a table or a
relationship shows up as an uncovered segment.

Supported DBML subset: `Table name [settings] { ... }` blocks; column lines
`name type [pk|primary key, not null, unique, ref: OP other.col, delete: POLICY, ...]`;
table `Note:` and `[category: ...]`; and top-level `Ref[ name]: A.col OP B.col [delete: POLICY]`
where OP is `>` (many-to-one), `<` (one-to-many), `-` (one-to-one), `<>` (many-to-many).
`indexes { }` blocks and `Enum`/`Project` blocks are skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# DBML type token -> KCF type.
_TYPE_MAP = {
    "int": "Integer", "integer": "Integer", "bigint": "Integer", "smallint": "Integer",
    "serial": "Integer", "bigserial": "Integer",
    "decimal": "Decimal", "numeric": "Decimal", "float": "Decimal", "double": "Decimal",
    "real": "Decimal", "money": "Decimal",
    "varchar": "String", "char": "String", "text": "String", "string": "String",
    "citext": "String",
    "bool": "Boolean", "boolean": "Boolean",
    "timestamp": "DateTime", "timestamptz": "DateTime", "datetime": "DateTime",
    "date": "Date", "time": "Time",
    "uuid": "UUID", "json": "Json", "jsonb": "Json",
}
# DBML ref operator -> (relationship cardinality, source-is-many?)
_CARD = {">": "many-to-one", "<": "one-to-many", "-": "one-to-one", "<>": "many-to-many"}


def _map_type(dbml_type: str) -> str:
    base = re.split(r"[(\[]", dbml_type.strip(), 1)[0].strip().lower()
    return _TYPE_MAP.get(base, "String")


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(re.sub(r"//.*$", "", line) for line in text.splitlines())


def _settings(raw: str) -> dict:
    """Parse a `[k: v, flag, k2: v2]` settings blob into a dict (flags -> True)."""
    out: dict = {}
    if not raw:
        return out
    inner = raw.strip().lstrip("[").rstrip("]")
    # split on commas not inside quotes/parens
    parts = re.split(r",(?![^(']*[)'])", inner)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, _, val = part.partition(":")
            out[key.strip().lower()] = val.strip().strip("'\"")
        else:
            out[part.strip().lower()] = True
    return out


_TABLE = re.compile(r'Table\s+"?([\w.]+)"?(?:\s+as\s+"?\w+"?)?\s*(\[[^\]]*\])?\s*\{', re.IGNORECASE)
_REF_LINE = re.compile(
    r'Ref\s*[\w"]*\s*:\s*"?([\w.]+)"?\s*(<>|[<>-])\s*"?([\w.]+)"?\s*(\[[^\]]*\])?', re.IGNORECASE)
_INLINE_REF = re.compile(r'ref\s*:\s*(<>|[<>-])\s*"?([\w.]+)"?', re.IGNORECASE)


def _block_body(text: str, open_idx: int):
    """Return (body, end_index) for a `{...}` block starting at the brace at open_idx."""
    depth, i = 0, open_idx
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i
        i += 1
    return text[open_idx + 1:], len(text)


def parse_dbml(text: str):
    text = _strip_comments(text)
    tables: dict[str, dict] = {}
    refs: list[dict] = []
    _ref_seen: set = set()

    def add_ref(src_tab, src_col, op, tgt_tab, tgt_col, settings):
        # dedup the same FK declared both inline (`[ref: ...]`) and as a top-level `Ref:`
        key = (src_tab, src_col, tgt_tab, tgt_col)
        if key in _ref_seen:
            return
        _ref_seen.add(key)
        refs.append({"from": src_tab, "fromCol": src_col, "op": op,
                     "to": tgt_tab, "toCol": tgt_col, "onDelete": settings.get("delete")})

    pos = 0
    for m in _TABLE.finditer(text):
        name = m.group(1).split(".")[-1]
        tset = _settings(m.group(2) or "")
        body, _ = _block_body(text, m.end() - 1)
        columns = []
        note_category = None
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.lower().startswith(("indexes", "note")) and "{" in line:
                continue
            note_m = re.match(r"Note\s*:\s*'([^']*)'", line, re.IGNORECASE)
            if note_m:
                cat = re.search(r"category\s*[:=]\s*(\w+)", note_m.group(1), re.IGNORECASE)
                if cat:
                    note_category = cat.group(1).lower()
                continue
            col_m = re.match(r'"?(\w+)"?\s+([\w()\[\]]+)\s*(\[[^\]]*\])?', line)
            if not col_m or line.lower().startswith(("table", "ref", "enum", "indexes")):
                continue
            col_name, col_type, col_set_raw = col_m.group(1), col_m.group(2), col_m.group(3) or ""
            cset = _settings(col_set_raw)
            columns.append({"name": col_name, "type": col_type, "settings": cset})
            inline = _INLINE_REF.search(col_set_raw)
            if inline:
                tgt = inline.group(2).split(".")
                add_ref(name, col_name, inline.group(1),
                        tgt[0], tgt[1] if len(tgt) > 1 else None, cset)
        category = tset.get("category") or note_category
        tables[name] = {"columns": columns, "category": category}

    for m in _REF_LINE.finditer(text):
        src = m.group(1).split("."); tgt = m.group(3).split(".")
        add_ref(src[0], src[1] if len(src) > 1 else None, m.group(2),
                tgt[0], tgt[1] if len(tgt) > 1 else None, _settings(m.group(4) or ""))
    return tables, refs


def import_dbml(text: str, model_id: str, namespace: str, profile: str = "business-application") -> dict:
    tables, refs = parse_dbml(text)
    qn = lambda name: f"{namespace}.{name}"

    concepts, segments, links = [], [], []
    for tname, table in tables.items():
        attributes = []
        pk_seen = False
        for col in table["columns"]:
            s = col["settings"]
            is_pk = bool(s.get("pk") or s.get("primary key") or s.get("primary"))
            pk_seen = pk_seen or is_pk
            attributes.append({
                "name": col["name"], "type": _map_type(col["type"]),
                "identity": is_pk,
                "required": bool(is_pk or s.get("not null") or s.get("not_null")),
            })
            seg = f"col:{tname}.{col['name']}"
            segments.append({"segmentId": seg, "text": f"{tname}.{col['name']} {col['type']}", "kind": "field"})
            links.append({"segmentId": seg, "constructs": [qn(tname)]})
        concept = {"id": tname, "qualifiedName": qn(tname), "kind": "ENTITY", "attributes": attributes}
        if table["category"]:
            concept["metadata"] = {"category": table["category"]}
        concepts.append(concept)
        seg = f"table:{tname}"
        segments.append({"segmentId": seg, "text": f"Table {tname}", "kind": "section"})
        links.append({"segmentId": seg, "constructs": [qn(tname)]})

    relationships = []
    seen: dict[str, int] = {}
    for ref in refs:
        if ref["from"] not in tables or ref["to"] not in tables:
            continue
        base = f"{ref['from']}-to-{ref['to']}"
        seen[base] = seen.get(base, 0) + 1
        rid = base if seen[base] == 1 else f"{base}-{seen[base]}"
        cardinality = _CARD.get(ref["op"], "many-to-one")
        on_delete = (ref["onDelete"] or "").lower() or None
        quals = {"cardinality": cardinality, "source-role": ref["from"], "target-role": ref["to"]}
        if on_delete:
            quals["on-delete"] = on_delete
        rel = {
            "id": rid,
            # cascade delete => the target owns the source (composition); else association
            "rootKind": "COMPOSITION" if on_delete == "cascade" else "ASSOCIATION",
            "source": qn(ref["from"]), "target": qn(ref["to"]),
            "strength": 1.0, "qualifiers": quals,
        }
        relationships.append(rel)
        seg = f"ref:{rid}"
        segments.append({"segmentId": seg, "text": f"Ref {ref['from']} {ref['op']} {ref['to']}", "kind": "edge"})
        links.append({"segmentId": seg, "constructs": [rid]})

    model = {
        "$schema": "../schemas/model-ir-v1.schema.json",
        "irVersion": "1.0.0", "id": model_id, "module": "KCF",
        "namespace": namespace, "profile": profile,
        "concepts": concepts, "relationships": relationships,
    }
    document = {"sourceDocumentVersion": "1.0.0", "documentId": model_id,
                "documentKind": "dbml", "segments": segments}
    trace = {"sourceTraceVersion": "1.0.0", "documentId": model_id, "model": model_id, "links": links}
    return {"model": model, "document": document, "trace": trace}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a DBML schema into a KCF model + source document + trace.")
    parser.add_argument("source", type=Path, help="a .dbml file")
    parser.add_argument("--id", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--profile", default="business-application")
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--source-doc", type=Path)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    result = import_dbml(args.source.read_text(encoding="utf-8"), args.id, args.namespace, args.profile)
    # Fail loudly instead of silently emitting an empty model: parsing a source that
    # yields no tables almost always means the input is not the supported dbml.org
    # `Table { ... }` subset (e.g. a different DBML dialect). Domain-agnostic — this
    # only inspects the table count, nothing about the schema's meaning.
    if not result["model"]["concepts"]:
        print(f"import-dbml: parsed {args.source} but found 0 tables - no model was "
              f"produced. This importer accepts the dbml.org subset (`Table name {{ ... }}` "
              f"with `[pk]`, `[ref: OP other.col]`, etc.); check the source is that dialect.",
              file=sys.stderr)
        return 2
    for value, path, to_stdout in (
        (result["model"], args.output, True),
        (result["document"], args.source_doc, False),
        (result["trace"], args.trace, False),
    ):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        elif to_stdout:
            print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
