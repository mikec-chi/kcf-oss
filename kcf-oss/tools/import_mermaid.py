"""Deterministic importer: a mermaid flowchart -> KCF model + source document + trace.

When the source is machine-readable (here, mermaid flowchart syntax) the
structural skeleton can be imported deterministically instead of guessed by an
LLM - eliminating the segmentation-fidelity risk for the diagram's structure.
Each node becomes an identity-bearing WORK concept and each edge an
identity-bearing ORDERING relationship, so every node *and* every arrow is
independently traceable (a dropped arrow shows up as an uncovered segment or an
unsourced construct, which a single coarse lifecycle could not surface).

Emits the (model, source-document, source-trace) triple the ingestion pipeline
consumes; by construction it is self-consistent and source-complete. Supports the
common flowchart subset: `flowchart`/`graph` headers, node shapes
`X[..]` / `X{..}` / `X(..)`, and edges `A --> B` / `A -->|label| B` / `A --- B`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ARROW = re.compile(r"(-\.->|-->|==>|---|--)(?:\|([^|]*)\|)?")
NODE_REF = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$")
SHAPED = re.compile(r'^[\[({]+\s*"?(.*?)"?\s*[\])}]+$')


def _parse_node(text: str):
    text = text.strip()
    match = NODE_REF.match(text)
    if not match:
        return None
    node_id = match.group(1)
    rest = match.group(2).strip()
    label, shape = None, "node"
    if rest:
        inner = SHAPED.match(rest)
        if inner:
            label = inner.group(1).strip()
        shape = "decision" if rest[0] == "{" else "node"
    return node_id, label, shape


def parse_mermaid(text: str):
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def register(parsed):
        node_id, label, shape = parsed
        existing = nodes.setdefault(node_id, {"label": None, "shape": "node"})
        if label:
            existing["label"] = label
        if shape == "decision":
            existing["shape"] = "decision"

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        if re.match(r"^(flowchart|graph)\b", line):
            continue
        arrow = ARROW.search(line)
        if arrow:
            left = _parse_node(line[: arrow.start()])
            right = _parse_node(line[arrow.end():])
            if not left or not right:
                continue
            register(left)
            register(right)
            edges.append({"from": left[0], "to": right[0], "label": (arrow.group(2) or "").strip() or None})
        else:
            parsed = _parse_node(line)
            if parsed:
                register(parsed)
    return nodes, edges


def import_mermaid(text: str, model_id: str, namespace: str) -> dict:
    nodes, edges = parse_mermaid(text)

    concepts = []
    for node_id in nodes:
        node = nodes[node_id]
        concept = {"id": node_id, "qualifiedName": f"{namespace}.{node_id}", "kind": "WORK"}
        metadata = {key: value for key, value in (("label", node["label"]), ("shape", node["shape"])) if value}
        if metadata:
            concept["metadata"] = metadata
        concepts.append(concept)

    relationships = []
    seen: dict[str, int] = {}
    edge_ids: list[str] = []
    for edge in edges:
        base = f"{edge['from']}-to-{edge['to']}"
        seen[base] = seen.get(base, 0) + 1
        edge_id = base if seen[base] == 1 else f"{base}-{seen[base]}"
        edge_ids.append(edge_id)
        # A flowchart arrow is a workflow-ordering edge; declare the ordering dimension
        # so the ORDERING relationship is meaningful (and satisfies kcf.relationship.ordering).
        qualifiers = {"dimension": "workflow"}
        if edge["label"]:
            qualifiers["condition"] = edge["label"]
        relationship = {"id": edge_id, "rootKind": "ORDERING", "source": f"{namespace}.{edge['from']}", "target": f"{namespace}.{edge['to']}", "qualifiers": qualifiers}
        relationships.append(relationship)

    model = {
        "$schema": "../schemas/model-ir-v1.schema.json",
        "irVersion": "1.0.0",
        "id": model_id,
        "module": "KCF",
        "namespace": namespace,
        "concepts": concepts,
        "relationships": relationships,
    }

    segments = []
    links = []
    for node_id in nodes:
        segment_id = f"node:{node_id}"
        segments.append({"segmentId": segment_id, "text": nodes[node_id]["label"] or node_id, "kind": "decision" if nodes[node_id]["shape"] == "decision" else "node"})
        links.append({"segmentId": segment_id, "constructs": [f"{namespace}.{node_id}"]})
    for edge, edge_id in zip(edges, edge_ids):
        segment_id = f"edge:{edge_id}"
        text = f"{edge['from']} --> {edge['to']}" + (f" [{edge['label']}]" if edge["label"] else "")
        segments.append({"segmentId": segment_id, "text": text, "kind": "edge"})
        links.append({"segmentId": segment_id, "constructs": [edge_id]})

    document = {"sourceDocumentVersion": "1.0.0", "documentId": model_id, "documentKind": "flowchart", "segments": segments}
    trace = {"sourceTraceVersion": "1.0.0", "documentId": model_id, "model": model_id, "links": links}
    return {"model": model, "document": document, "trace": trace}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a mermaid flowchart into a KCF model + source document + trace.")
    parser.add_argument("source", type=Path, help="a .mmd / mermaid flowchart file")
    parser.add_argument("--id", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output", "-o", type=Path, help="write the model IR here")
    parser.add_argument("--source-doc", type=Path, help="write the source document here")
    parser.add_argument("--trace", type=Path, help="write the source trace here")
    args = parser.parse_args()

    result = import_mermaid(args.source.read_text(encoding="utf-8"), args.id, args.namespace)
    for value, path, default_stdout in (
        (result["model"], args.output, True),
        (result["document"], args.source_doc, False),
        (result["trace"], args.trace, False),
    ):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        elif default_stdout:
            print(json.dumps(value, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
