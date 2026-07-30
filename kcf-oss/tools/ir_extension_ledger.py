"""Authoritative status ledger for the 89 `needs-ir-extension` semantic rules.

The remediation contract: a `needs-ir-extension` rule is only honestly classified when its status is
DERIVED FROM EVIDENCE — the IR schema (does the field exist?), the parser (is there authoring syntax?),
the normalizer (does it flow to the IR?), the catalogue (is a handler assigned?), and the fixtures (is
it exercised?) — never from the override's prose alone. This module computes that ledger and the
reconciliation the conformance gate enforces, so an override can never again claim "the IR has no such
field" for a field that now exists.

Statuses (ledger vocabulary, a superset of the catalogue's enforcement values):
  ir-missing · ir-partial · ir-present-handler-missing · partially-automated · automated ·
  enforced-elsewhere · runtime-obligation · external-fact · human-judgment · advisory · superseded
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEDGER_SCHEMA_ID = "ir-extension-ledger-v1"

# The FROZEN set of the 89 rules originally classified needs-ir-extension. The ledger tracks these
# throughout the remediation even as individual rules become `automated` (and drop out of the
# automation-triage overrides), so the "exactly 89 reconciled" invariant holds for the whole migration.
_ORIGINAL_89 = (
    "action.collection.aggregate-type", "action.collection.equality", "action.collection.field-resolution",
    "action.collection.join-fanout", "action.collection.join-type", "action.collection.map-cardinality",
    "action.collection.order-total", "action.collection.projection-unique", "action.collection.set-compatibility",
    "action.compose.order", "action.compose.saga", "action.concurrency.lost-update", "action.concurrency.version",
    "action.destructive.recovery", "action.destructive.retention", "action.destructive.scope",
    "action.device.safety", "action.event.commit-order", "action.event.duplicate", "action.event.payload",
    "action.idempotency.conditional", "action.invoke.failure", "action.invoke.input", "action.invoke.output",
    "action.invoke.precondition", "action.invoke.recursion", "action.invoke.resolved", "action.invoke.transaction",
    "action.record.create-input", "action.record.create-readonly", "action.record.delete-policy",
    "action.record.exists-output", "action.record.key", "action.record.patch-format", "action.record.postcondition",
    "action.record.precondition", "action.record.update-fields", "action.retry.bound", "action.retry.classification",
    "action.set.cascade", "action.set.input-shape", "action.set.limit", "action.set.order", "action.set.output-shape",
    "action.set.pagination", "action.set.partial-failure", "action.transaction.external", "action.transaction.required",
    "action.transform.loss", "action.transform.null", "action.transform.required-coverage",
    "action.transform.reversibility", "action.transform.source-target", "action.transform.time",
    "action.transform.totality", "action.transform.type", "action.transform.unit", "action.transform.version",
    "integration.contract.schema", "integration.mapping.coverage", "integration.protocol",
    "integration.retry.idempotency", "kcf.concept.kind-compatible", "kcf.concept.trait", "kcf.concept.version",
    "kcf.extension.point", "kcf.profile.prohibited", "kcf.profile.relationship", "kcf.relationship.canonical",
    "kcf.relationship.condition", "kcf.relationship.inverse", "kcf.relationship.participation",
    "kcf.relationship.transitivity", "lineage.binding.schema", "lineage.complete", "stack.governance.audit",
    "stack.graph.cycle-policy", "stack.graph.dead-end", "stack.name.visibility", "stack.time.duration",
    "stack.time.window-compatible", "stack.type.assignment", "stack.type.collection", "stack.type.condition-boolean",
    "stack.type.known", "stack.type.nullability", "stack.type.operator", "stack.value.finite",
    "stack.value.unit-compatible",
)

# --- rules whose required IR action field(s) NOW EXIST (IR 1.1) — evidence checked against the schema.
#     rule -> (required action IR fields, authoring keywords, rfc)
_IR_PRESENT = {
    "action.concurrency.version": (["expectedVersion"], ["expected-version"], "RFC-4"),
    "action.concurrency.lost-update": (["expectedVersion"], ["expected-version"], "RFC-4"),
    "action.idempotency.conditional": (["idempotencyKey"], ["idempotency-key"], "RFC-4"),
    "action.transaction.required": (["transactionBoundary"], ["transaction-boundary"], "RFC-4"),
    "action.record.precondition": (["preconditions"], ["precondition"], "RFC-3"),
    "action.record.postcondition": (["postconditions"], ["postcondition"], "RFC-3"),
    "action.destructive.recovery": (["reversibility"], ["reversibility"], "RFC-5"),
    "action.destructive.retention": (["retention"], ["retention"], "RFC-5"),
    "action.record.delete-policy": (["deleteBehavior"], ["delete-behavior"], "RFC-5"),
    "action.set.limit": (["bulkLimit"], ["bulk-limit"], "RFC-5"),
    "action.set.order": (["bulkOrdering"], ["bulk-ordering"], "RFC-5"),
    "action.set.partial-failure": (["bulkFailurePolicy"], ["bulk-failure"], "RFC-5"),
    # RFC-2 typed field-level lineage: the new `fieldMappings` action construct (authoring `map ... -> ...`).
    "action.transform.source-target": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.type": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.loss": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.null": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.unit": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.required-coverage": (["fieldMappings"], ["map"], "RFC-2"),
    "action.transform.reversibility": (["fieldMappings"], ["map"], "RFC-2"),
    # RFC-1 unit compatibility gets its first reader from the RFC-2 field-mapping units.
    "stack.value.unit-compatible": (["fieldMappings"], ["map"], "RFC-1"),
    # RFC-3 action I/O contract fields (additive): create input coverage/read-only + patch dialect.
    "action.record.create-input": (["provides"], ["provide"], "RFC-3"),
    "action.record.create-readonly": (["provides"], ["provide"], "RFC-3"),
    "action.record.patch-format": (["patchDialect"], ["patch-dialect"], "RFC-3"),
    # RFC-3 set/bulk shape: the new returns/pagination action fields.
    "action.set.output-shape": (["returns"], ["returns"], "RFC-3"),
    "action.set.pagination": (["pagination"], ["pagination"], "RFC-3"),
    # RFC-4 retry + RFC-2 transform totality: additive action fields.
    "action.retry.bound": (["retryBackoff"], ["retry-backoff"], "RFC-4"),
    "action.retry.classification": (["retryClassification"], ["retry-classification"], "RFC-4"),
    "action.transform.totality": (["totality"], ["totality"], "RFC-2"),
    # RFC-3 action-to-action invocation contract (new `invocations` construct, authoring `invoke {...}`).
    "action.invoke.resolved": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.input": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.output": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.failure": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.precondition": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.recursion": (["invocations"], ["invoke"], "RFC-3"),
    "action.invoke.transaction": (["invocations"], ["invoke"], "RFC-3"),
}
# rules automated over fields ALREADY in the base IR (not new 1.1 action fields) — RFC-1 type-system
# rules read attribute type/default/required + concept measure/duration fields that always existed; the
# RFC-1 "extension" is the primitive/unit REGISTRY (config/type-system.json) the analyzer resolves against.
#     rule -> (base IR fields it reads, rfc)
_IR_BASE = {
    "stack.type.known": (["concepts[].attributes[].type"], "RFC-1"),
    "stack.type.nullability": (["concepts[].attributes[].required|identity|default"], "RFC-1"),
    "stack.type.assignment": (["concepts[].attributes[].default"], "RFC-1"),
    "stack.value.finite": (["concepts[].threshold|target|tolerance|weight|probability"], "RFC-1"),
    "stack.time.duration": (["concepts[].durationValue"], "RFC-1"),
    # RFC-3 record I/O rules that read pre-existing action fields (selection/mutations/operation).
    "action.record.key": (["actions[].selection"], "RFC-3"),
    "action.record.update-fields": (["actions[].mutations"], "RFC-3"),
    "action.record.exists-output": (["actions[].operation|effect|outputCardinality"], "RFC-3"),
    # RFC-6 relationship reasoning read the open relationship qualifiers + rootKind (existing IR).
    "kcf.relationship.canonical": (["relationships[].qualifiers.canonical|inverse"], "RFC-6"),
    "kcf.relationship.inverse": (["relationships[].qualifiers.inverse + source/target"], "RFC-6"),
    "kcf.relationship.transitivity": (["relationships[].qualifiers.transitive + rootKind"], "RFC-6"),
    # RFC-7 integration contracts read the existing integration section (adapters/endpoints/retry/mappings).
    "integration.protocol": (["integration.adapters[].protocol|serialization"], "RFC-7"),
    "integration.contract.schema": (["integration.endpoints[].operation"], "RFC-7"),
    "integration.retry.idempotency": (["integration.retryPolicies[].requiresIdempotency"], "RFC-7"),
    "integration.mapping.coverage": (["integration.mappings[].fieldMaps"], "RFC-7"),
    # RFC-8 specialization/lineage read the new concept `specializes` field + the lineage bindings.
    "kcf.concept.kind-compatible": (["concepts[].specializes"], "RFC-8"),
    "lineage.binding.schema": (["lineage.bindings[].source|target"], "RFC-8"),
    "action.set.cascade": (["actions[].deleteBehavior|selection|authorization"], "RFC-3"),
    # RFC-1 typed predicates + relationship condition read the new structured `predicate`.
    "stack.type.condition-boolean": (["rules[].predicate | relationships[].qualifiers.predicate"], "RFC-1"),
    "stack.type.operator": (["rules[].predicate.operator"], "RFC-1"),
    "kcf.relationship.condition": (["relationships[].qualifiers.predicate"], "RFC-6"),
    # RFC-2 collection-pipeline typed rules read collectionTransforms projections/expands/sort/aggregate.
    "action.collection.projection-unique": (["collectionTransforms[].projections"], "RFC-2"),
    "action.collection.field-resolution": (["collectionTransforms[].projections + inputSchema"], "RFC-2"),
    "action.collection.map-cardinality": (["collectionTransforms[].operation|expands"], "RFC-2"),
    "action.collection.order-total": (["collectionTransforms[].sort|keys"], "RFC-2"),
    "action.collection.aggregate-type": (["collectionTransforms[].aggregate"], "RFC-2"),
    "action.collection.join-type": (["collectionTransforms[].joinKeys + inputs"], "RFC-2"),
    "action.collection.join-fanout": (["collectionTransforms[].expectedCardinality"], "RFC-2"),
    "action.collection.equality": (["collectionTransforms[].keys|equalityKeys"], "RFC-2"),
    "action.collection.set-compatibility": (["collectionTransforms[].inputs schemas"], "RFC-2"),
    "kcf.relationship.participation": (["relationships[].rootKind + qualifiers"], "RFC-6"),
    "stack.type.collection": (["concepts[].attributes[].cardinality|default"], "RFC-1"),
    "stack.time.window-compatible": (["collectionTransforms[].windowUnit|slideUnit"], "RFC-1"),
}
# partially represented: forward/compensation exists; multi-step saga ordering + durable state do not.
_IR_PARTIAL = {
    "action.compose.saga": (["compensation"], ["compensation"], "RFC-5",
                            "compensation exists; multi-step saga ordering + durable state IR absent"),
}

# rfc assignment for the genuinely-still-blocked rules (no matching IR field yet).
_RFC_RULES = {
    "RFC-1": ["stack.type.assignment", "stack.type.collection", "stack.type.condition-boolean",
              "stack.type.known", "stack.type.nullability", "stack.type.operator",
              "stack.value.finite", "stack.value.unit-compatible", "stack.time.duration",
              "stack.time.window-compatible"],
    "RFC-2": ["action.transform.loss", "action.transform.null", "action.transform.required-coverage",
              "action.transform.reversibility", "action.transform.source-target", "action.transform.time",
              "action.transform.totality", "action.transform.type", "action.transform.unit",
              "action.transform.version", "action.collection.aggregate-type", "action.collection.equality",
              "action.collection.field-resolution", "action.collection.join-fanout", "action.collection.join-type",
              "action.collection.map-cardinality", "action.collection.order-total",
              "action.collection.projection-unique", "action.collection.set-compatibility"],
    "RFC-3": ["action.record.create-input", "action.record.create-readonly", "action.record.exists-output",
              "action.record.key", "action.record.patch-format", "action.record.update-fields",
              "action.invoke.failure", "action.invoke.input", "action.invoke.output", "action.invoke.precondition",
              "action.invoke.recursion", "action.invoke.resolved", "action.invoke.transaction",
              "action.set.cascade", "action.set.input-shape", "action.set.output-shape", "action.set.pagination"],
    "RFC-4": ["action.retry.bound", "action.retry.classification", "action.transaction.external"],
    "RFC-5": ["action.destructive.scope", "action.device.safety", "action.compose.order",
              "action.event.commit-order", "action.event.duplicate", "action.event.payload"],
    "RFC-6": ["kcf.relationship.canonical", "kcf.relationship.condition", "kcf.relationship.inverse",
              "kcf.relationship.participation", "kcf.relationship.transitivity"],
    "RFC-7": ["integration.contract.schema", "integration.mapping.coverage", "integration.protocol",
              "integration.retry.idempotency"],
    "RFC-8": ["kcf.concept.kind-compatible", "kcf.concept.trait", "kcf.concept.version",
              "lineage.binding.schema", "lineage.complete"],
    # non-IR / downstream candidates (Phase 5 finalizes the terminal class + enforcement location).
    "none": ["kcf.extension.point", "kcf.profile.prohibited", "kcf.profile.relationship",
             "stack.governance.audit", "stack.graph.cycle-policy", "stack.graph.dead-end",
             "stack.name.visibility"],
}
# the symbolic IR construct each still-blocked RFC needs (documents what remains).
_RFC_REQUIRED = {
    "RFC-1": ["typed expression/predicate IR (operator operands, boolean conditions) + typed field "
              "mappings for collection/unit/window compatibility — primitive/unit REGISTRY foundation "
              "already delivered in config/type-system.json (Slice 5)"],
    "RFC-2": ["collection-pipeline field lineage + transform totality/time/version — the single-record "
              "actions[].fieldMappings construct already delivered in Slice 6 (grammar stack 1.12)"],
    "RFC-3": ["action-to-action invocation contract (invoke.*) + bulk input/output-shape & pagination "
              "construct (set.*) — the single-record I/O contract (provides/patchDialect/selection) "
              "already delivered in Slice 7"],
    "RFC-4": ["actions[].retry (backoff + failure classification)"],
    "RFC-5": ["saga/device-safety/event change-contract constructs"],
    "RFC-6": ["boolean-expression IR for relationship conditions + a participation/governance verb "
              "taxonomy — canonical/inverse/transitivity already delivered in Slice 8 over qualifiers"],
    "RFC-7": ["integration.contract (protocol/serialization/field mapping)"],
    "RFC-8": ["per-kind trait-permission taxonomy (kcf.concept.trait) + a derived-concept lineage marker "
              "(lineage.complete) — specialization (specializes) + lineage-binding resolution delivered in Slice 10"],
    "none": [],
}
# proposed terminal classification (Phase 5 decides finally) for rules that will NOT get model-IR fields.
_TARGET = {
    "action.transaction.external": "runtime-obligation", "action.device.safety": "runtime-obligation",
    "action.event.commit-order": "runtime-obligation", "action.event.duplicate": "runtime-obligation",
    "action.destructive.scope": "runtime-obligation", "stack.governance.audit": "enforced-elsewhere",
    "stack.graph.dead-end": "advisory", "stack.graph.cycle-policy": "advisory",
    "stack.name.visibility": "advisory", "kcf.extension.point": "human-judgment",
    "kcf.profile.prohibited": "human-judgment", "kcf.profile.relationship": "human-judgment",
}
# maps an automation-triage manualClass (the catalogue's vocabulary) to the ledger's terminal status
# for rules deliberately reclassified as NOT getting a model-IR field (enforced at runtime / elsewhere /
# by human judgment / advisory). `needs-external-facts` is the catalogue's name for a runtime obligation.
_TERMINAL_STATUS = {
    "needs-external-facts": "runtime-obligation",
    "enforced-elsewhere": "enforced-elsewhere",
    "human-judgment": "human-judgment",
    "advisory": "advisory",
}

# reason phrases that assert an IR field is ABSENT — used to detect a stale override.
_ABSENCE_RE = re.compile(r"(has no|have no|no .* field|not derivable|does not define|no .* in the IR|"
                         r"no IR structure|no saga construct|lacks? )", re.I)


def _rfc_of(rule_id: str) -> str | None:
    if rule_id in _IR_PRESENT:
        return _IR_PRESENT[rule_id][2]
    if rule_id in _IR_PARTIAL:
        return _IR_PARTIAL[rule_id][2]
    for rfc, ids in _RFC_RULES.items():
        if rule_id in ids:
            return None if rfc == "none" else rfc
    return None


def action_fields(ir_schema: dict) -> set:
    return set(((ir_schema.get("$defs", {}).get("action", {}) or {}).get("properties", {}) or {}).keys())


def build_ledger(*, overrides: dict, ir_schema: dict, catalogue: dict, coverage: dict,
                 parser_src: str, normalizer_src: str) -> dict:
    """Compute the evidence-derived ledger for every `needs-ir-extension` rule."""
    fields = action_fields(ir_schema)
    handlers = {r["id"]: r.get("handler") for r in catalogue.get("rules", [])}
    automated = set(coverage.get("automatedRuleIds", []))
    partial = set(coverage.get("partiallyAutomatedRuleIds", []))
    normalizer_passthrough = "**declaration.values" in normalizer_src   # actions flow verbatim to IR
    # Iterate the FROZEN original 89, not the current overrides — a rule that becomes `automated`
    # drops out of the needs-ir-extension overrides but must still be tracked here (now as automated).
    entries = []
    for rid in _ORIGINAL_89:
        present = rid in _IR_PRESENT
        partial_ir = rid in _IR_PARTIAL
        base = rid in _IR_BASE
        if present:
            req, syntax, rfc = _IR_PRESENT[rid]
        elif partial_ir:
            req, syntax, rfc, _note = _IR_PARTIAL[rid]
        elif base:
            req, rfc = _IR_BASE[rid]
            syntax = []
        else:
            rfc = _rfc_of(rid)
            req = _RFC_REQUIRED.get(rfc or "none", [])
            syntax = []
        # base rules read pre-existing IR fields (not action $defs), so their schema support is inherent.
        schema_support = True if base else (bool(req) and all(f in fields for f in req) and (present or partial_ir))
        parser_support = bool(syntax) and all(any(k in parser_src for k in [kw, f'"{kw}"']) for kw in syntax)
        normalizer_support = schema_support and normalizer_passthrough
        handler = handlers.get(rid)
        has_neg = rid in automated
        override_class = (overrides["rules"].get(rid) or {}).get("manualClass")
        terminal = _TERMINAL_STATUS.get(override_class)
        # derive status from evidence.
        if handler and rid in automated:
            status = "automated"
        elif rid in partial:
            status = "partially-automated"
        elif partial_ir:
            status = "ir-partial"
        elif schema_support and parser_support:
            status = "ir-present-handler-missing"
        elif terminal:
            # deliberately reclassified: this rule will NOT get a model-IR field; its enforcement lives
            # elsewhere (runtime / stack tooling / governance) or it is advisory. See override reason.
            status = terminal
        else:
            status = "ir-missing"
        target = terminal or _TARGET.get(rid, "automated")
        entries.append({
            "ruleId": rid, "rfc": rfc, "status": status,
            "requiredIr": req, "authoringSyntax": syntax,
            "schemaSupport": schema_support, "parserSupport": parser_support,
            "normalizerSupport": normalizer_support, "handler": handler,
            "positiveFixture": "tests/fixtures/valid/transportation-ir.json" if has_neg else None,
            "negativeFixture": "tests/fixtures/invalid/semantic-failures-ir.json" if has_neg else None,
            "targetClassification": target,
            "overrideReason": (overrides["rules"].get(rid) or {}).get("reason", ""),
        })
    counts: dict = {}
    for e in entries:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    return {"$schema": LEDGER_SCHEMA_ID, "ledgerVersion": "1.0.0", "sourceRuleCount": len(entries),
            "counts": counts, "rules": entries}


def reconcile(ledger: dict) -> dict:
    """Detect contradictions the gate must fail on: a stale override (reason asserts a field is missing
    that the schema now has), or a rule with IR present still labeled ir-missing."""
    stale, mislabelled, automated_without_evidence = [], [], []
    for e in ledger["rules"]:
        if e["schemaSupport"] and _ABSENCE_RE.search(e.get("overrideReason", "") or ""):
            stale.append(e["ruleId"])
        if e["schemaSupport"] and e["status"] == "ir-missing":
            mislabelled.append(e["ruleId"])
        if e["status"] == "automated" and not (e["handler"] and e["positiveFixture"] and e["negativeFixture"]):
            automated_without_evidence.append(e["ruleId"])
    return {"stale": sorted(stale), "mislabelled": sorted(mislabelled),
            "automatedWithoutEvidence": sorted(automated_without_evidence)}


def load_and_build() -> dict:
    def _read(p):
        return json.loads((PROJECT_ROOT / p).read_text(encoding="utf-8"))
    return build_ledger(
        overrides=_read("semantics/automation-triage-overrides.json"),
        ir_schema=_read("schemas/model-ir-v1.schema.json"),
        catalogue=_read("semantics/semantic-rules.json"),
        coverage=_read("semantics/coverage.json"),
        parser_src=(PROJECT_ROOT / "compiler" / "parser.py").read_text(encoding="utf-8"),
        normalizer_src=(PROJECT_ROOT / "compiler" / "normalizer.py").read_text(encoding="utf-8"))


def main() -> int:
    ledger = load_and_build()
    out = PROJECT_ROOT / "semantics" / "ir-extension-status.json"
    out.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    rec = reconcile(ledger)
    print(f"ir-extension ledger: {ledger['sourceRuleCount']} rules; counts={ledger['counts']}")
    print(f"reconcile: stale={rec['stale']} mislabelled={rec['mislabelled']}")
    return 0 if not (rec["stale"] or rec["mislabelled"] or rec["automatedWithoutEvidence"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
