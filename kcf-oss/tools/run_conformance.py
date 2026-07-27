from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

TOOLS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler import compile_file
from check_compatibility import check as check_compatibility
from confirm_synthetic import confirm as confirm_synthetic
from coverage_report import load_coverage_model, report as coverage_report
from merge_models import merge
from migrate_ir import migrate
from assess import assess as assess_model
from execution_plan import execution_plan
from document_profile import check_document, is_conformant as document_conformant, load_document_profiles
from import_mermaid import import_mermaid
from import_dbml import import_dbml
from ingest import ingest as ingest_model
from pattern_contracts import contract_role_errors, load_contracts as load_pattern_contracts, report as pattern_report, role_report
from review_queue import by_segment as review_by_segment, review_queue
from scaffold import build_scaffold
from source_coverage import is_complete as source_complete, source_coverage
from profile_resolver import resolve_profile
from resolve_stack import load, resolve
from semantic_analyzer import Analyzer
from semantic_delta import compare


FIXTURES_ROOT = PROJECT_ROOT / "tests" / "fixtures"
SEMANTICS_ROOT = PROJECT_ROOT / "semantics"
SCHEMAS_ROOT = PROJECT_ROOT / "schemas"
DOMAINS_ROOT = PROJECT_ROOT / "tests" / "domains"
CORE_ROOT = PROJECT_ROOT.parent / "semantic-core"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def validate(document, schema_name):
    schema = json.loads((SCHEMAS_ROOT / schema_name).read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(document))
    check(not errors, f"{schema_name} validation failed: {[error.message for error in errors[:3]]}")


def main():
    valid_path = FIXTURES_ROOT / "valid" / "transportation-ir.json"
    invalid_paths = sorted((FIXTURES_ROOT / "invalid").glob("*.json"))
    delta_path = FIXTURES_ROOT / "delta" / "transportation-v2-ir.json"
    valid = json.loads(valid_path.read_text())
    changed = json.loads(delta_path.read_text())
    catalogue = json.loads((SEMANTICS_ROOT / "semantic-rules.json").read_text())
    coverage = json.loads((SEMANTICS_ROOT / "coverage.json").read_text())
    fixture_index = json.loads((FIXTURES_ROOT / "rules" / "fixture-index.json").read_text())
    ownership = json.loads((SEMANTICS_ROOT / "legacy-rule-ownership.json").read_text())
    validate(valid, "model-ir-v1.schema.json")
    validate(changed, "model-ir-v1.schema.json")
    semantic_schema = json.loads((SEMANTICS_ROOT / "semantic-rules.schema.json").read_text())
    check(not list(Draft202012Validator(semantic_schema).iter_errors(catalogue)), "semantic catalogue failed its schema")
    core_catalogue = json.loads((CORE_ROOT / "semantics" / "semantic-rules.json").read_text(encoding="utf-8"))
    core_schema = json.loads((CORE_ROOT / "semantics" / "semantic-rules.schema.json").read_text(encoding="utf-8"))
    check(not list(Draft202012Validator(core_schema).iter_errors(core_catalogue)), "semantic-core catalogue failed its schema")
    check("dbml-stack" not in (TOOLS_ROOT / "build_semantic_rules.py").read_text(encoding="utf-8"), "KCF rule build still depends on DBML")
    catalogue_ids = [rule["id"] for rule in catalogue["rules"]]
    check(len(catalogue_ids) == len(set(catalogue_ids)), "semantic rule catalogue contains duplicate IDs")
    check(all(re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", rule_id) for rule_id in catalogue_ids), "semantic rule catalogue contains an invalid ID")
    check(not coverage["unclassified"], "semantic rule coverage contains unclassified rules")
    check(coverage["totalRules"] == len(catalogue_ids), "semantic rule coverage count is stale")
    check(fixture_index["automatedRuleIds"] == coverage["automatedRuleIds"], "per-rule fixture index is stale")
    check(len(ownership["rules"]) == 550, "legacy semantic ownership audit is incomplete")
    check(all(item["owner"] in {"semantic-core", "kcf", "dbml"} for item in ownership["rules"]), "legacy rule has no valid owner")
    valid_diagnostics = Analyzer(valid).run()
    check(not any(d["severity"] == "error" for d in valid_diagnostics), f"valid fixture failed: {valid_diagnostics}")
    invalid_diagnostics = [
        diagnostic
        for path in invalid_paths
        for diagnostic in Analyzer(json.loads(path.read_text())).run()
    ]
    ids = {d["rule_id"] for d in invalid_diagnostics}
    check(ids <= set(catalogue_ids), f"analyzer emitted uncatalogued rule IDs: {sorted(ids - set(catalogue_ids))}")
    required = {
        "stack.name.unique", "kcf.concept.primary-kind", "kcf.concept.reference",
        "kcf.relationship.root-kind", "lifecycle.single-initial",
        "action.set.explicit-scope", "action.retry.side-effects",
        "kcf.event.immutable", "kcf.resource.capacity",
        "stack.order.unique", "kcf.emitter.unsupported",
        "action.collection.boundedness", "process.single-initial",
        "integration.endpoint", "stack.security.authorization",
        "security.risk.references", "security.risk.level", "security.risk.mitigation",
        "stack.security.boundary", "lineage.cycle", "lineage.binding.unique",
        "lineage.cost.nonnegative",
        "architecture.reference.kind", "architecture.deployment.complete", "experience.app.reference",
        "experience.action.invoke", "experience.flow.entry", "design.design-system.unique",
        "design.scale.order", "design.page.binding", "analytics.binding.kind",
        "ai.feature.keys", "ai.feature.target", "ai.pipeline.order",
        "ai.serving.model", "ai.serving.capacity",
        "organization.kind", "organization.parent.reference",
        "organization.hierarchy.acyclic", "organization.member.reference",
        "organization.reporting.reference", "organization.reporting.temporal",
        "organization.escalation.path", "information.kind",
        "information.reference", "information.temporal", "information.provenance",
        "knowledge.ingestion.trace", "knowledge.access.policy",
        "rule.complete", "rule.reference", "rule.policy.authority",
        "rule.policy.members", "rule.conflict.strategy", "reasoning.complete",
        "reasoning.reference", "reasoning.confidence", "reasoning.contradiction",
        "knowledge.assertion.subject", "knowledge.assertion.status",
        "knowledge.assertion.provenance", "knowledge.assertion.temporal",
        "knowledge.assertion.inference", "knowledge.assertion.supersession",
        "knowledge.assertion.contradiction", "knowledge.identity.canonical",
        "knowledge.identity.ambiguity", "knowledge.identity.transition",
        "knowledge.query.policy", "knowledge.query.negation",
        "knowledge.query.temporal", "knowledge.bitemporal.recorded",
        "kcf.profile.pattern-required", "kcf.profile.pattern-prohibited",
        "kcf.profile.pattern-exclusion",
    }
    check(required <= ids, f"invalid fixture missed diagnostics: {sorted(required - ids)}")
    check(set(coverage["automatedRuleIds"]) <= ids, "an automated semantic rule lacks an invalid regression fixture")
    manifest, _ = load()
    for module in manifest["modules"]:
        check(resolve(module).strip(), f"resolver emitted no grammar for {module}")
    check(not compare(valid, valid), "identical model produced semantic delta")
    delta = compare(valid, changed)
    check(any(change["classification"] == "breaking" for change in delta), "breaking semantic delta was not classified")
    delta_result = {"deltaVersion": "1.0.0", "recommendedVersionChange": "major", "changes": delta}
    validate(delta_result, "semantic-delta-v1.schema.json")

    merge_root = FIXTURES_ROOT / "merge"
    merge_a = json.loads((merge_root / "customer-orders-a.json").read_text())
    merge_b = json.loads((merge_root / "customer-orders-b.json").read_text())
    unified, merge_conflicts = merge([merge_a, merge_b], "CustomerCommerce", "shop")
    check(not merge_conflicts, f"compatible merge reported conflicts: {merge_conflicts}")
    validate(unified, "model-ir-v1.schema.json")
    check(not any(item["severity"] == "error" for item in Analyzer(unified).run()), "merged model failed the semantic analyzer")
    merge_golden = json.loads((merge_root / "unified.golden.json").read_text())
    check(unified == merge_golden, "merge golden snapshot is stale")
    customer = next(c for c in unified["concepts"] if c["qualifiedName"] == "shop.Customer")
    check([a["name"] for a in customer["attributes"]] == ["customerId", "name", "email"], "merge did not union attributes losslessly")
    alias_model = json.loads((merge_root / "crm-alias.json").read_text())
    aliased, _ = merge([merge_a, alias_model], "CustomerCommerce", "shop")
    aliased_keys = {c["qualifiedName"] for c in aliased["concepts"]}
    check("shop.Customer" in aliased_keys and "crm.Client" not in aliased_keys, "identity resolution did not unify the cross-namespace concept")
    aliased_customer = next(c for c in aliased["concepts"] if c["qualifiedName"] == "shop.Customer")
    check("clientId" in {a["name"] for a in aliased_customer["attributes"]}, "aliased concept attributes were not folded into the canonical identity")
    conflict_a = json.loads((merge_root / "conflict-a.json").read_text())
    conflict_b = json.loads((merge_root / "conflict-b.json").read_text())
    _, conflicts = merge([conflict_a, conflict_b], "Conflicted", "shop")
    conflict_ids = {item["ruleId"] for item in conflicts}
    check({"merge.concept.conflict", "merge.attribute.conflict"} <= conflict_ids, f"merge did not report expected conflicts: {sorted(conflict_ids)}")

    coverage_root = FIXTURES_ROOT / "coverage"
    coverage_model = load_coverage_model()
    validate(coverage_model, "coverage-model-v1.schema.json")
    incomplete = json.loads((coverage_root / "coverage-incomplete.json").read_text())
    validate(incomplete, "model-ir-v1.schema.json")
    gap_report = coverage_report(incomplete, coverage_model)
    validate(gap_report, "coverage-report-v1.schema.json")
    check(gap_report["summary"]["required"] >= 1, "coverage report found no required gaps in the incomplete model")
    gap_ids = {item["gapId"] for item in gap_report["gaps"]}
    check({"coverage.entity.identity", "coverage.entity.lifecycle", "coverage.action.authorization", "coverage.actor.present"} <= gap_ids,
          f"coverage report missed expected gaps: {sorted(gap_ids)}")
    check("coverage.measure.present" not in gap_ids, "analytics-only obligation wrongly applied to a business-application model")
    complete = json.loads((coverage_root / "coverage-complete.json").read_text())
    validate(complete, "model-ir-v1.schema.json")
    complete_report = coverage_report(complete, coverage_model)
    check(complete_report["summary"]["totalGaps"] == 0, f"complete model reported gaps: {complete_report['gaps']}")

    synthetic = json.loads((coverage_root / "synthetic-model.json").read_text())
    decisions = json.loads((coverage_root / "decisions.json").read_text())
    confirmed_model, confirm_summary = confirm_synthetic(synthetic, decisions["confirm"], decisions["reject"], "sme:test", "2026-07-23T00:00:00Z")
    validate(confirmed_model, "model-ir-v1.schema.json")
    check(not confirm_summary["notFound"], f"confirmation referenced unknown identities: {confirm_summary['notFound']}")
    check("fin.SynthRule" not in {item.get("qualifiedName") or item["id"] for item in confirmed_model.get("rules", [])}, "rejected synthetic rule was not removed")
    confirmed_claim = next(item for item in confirmed_model["assertions"] if (item.get("qualifiedName") or item["id"]) == "fin.SynthClaim")
    check(confirmed_claim["status"] == "asserted" and confirmed_claim.get("reviewedBy") == "sme:test", "confirmed synthetic assertion was not promoted to reviewed fact")
    human_claim = next(item for item in confirmed_model["assertions"] if (item.get("qualifiedName") or item["id"]) == "fin.HumanClaim")
    check(human_claim.get("reviewedBy") == "sme:jane", "confirmation altered a record it was not asked to change")

    pattern_contracts = load_pattern_contracts()
    contract_schema = json.loads((SCHEMAS_ROOT / "pattern-contract-v1.schema.json").read_text(encoding="utf-8"))
    for contract in pattern_contracts.values():
        check(not list(Draft202012Validator(contract_schema).iter_errors(contract)), f"pattern contract {contract['patternId']} failed its schema")
    patterns_root = FIXTURES_ROOT / "patterns"
    satisfied = json.loads((patterns_root / "pattern-satisfied.json").read_text())
    validate(satisfied, "model-ir-v1.schema.json")
    satisfied_report = pattern_report(satisfied, pattern_contracts)
    validate(satisfied_report, "pattern-report-v1.schema.json")
    check(satisfied_report["summary"]["satisfied"] >= 1, "a satisfied pattern was not proven satisfied")
    check(not satisfied_report["summary"]["claimedButUnproven"], f"a satisfied model reported unproven claims: {satisfied_report['summary']['claimedButUnproven']}")
    unproven = json.loads((patterns_root / "pattern-unproven.json").read_text())
    validate(unproven, "model-ir-v1.schema.json")
    unproven_report = pattern_report(unproven, pattern_contracts)
    validate(unproven_report, "pattern-report-v1.schema.json")
    check("core.auditable-entity" in unproven_report["summary"]["claimedButUnproven"], "an unbacked pattern claim was not flagged as claimed-but-unproven")

    # Relationship-shape obligation (trait-linked-to-trait): links, not just presence
    linked_ok = json.loads((patterns_root / "linked-satisfied.json").read_text())
    validate(linked_ok, "model-ir-v1.schema.json")
    check(pattern_report(linked_ok, pattern_contracts)["summary"]["satisfied"] >= 1, "a linked model did not satisfy the relationship-shape pattern")
    linked_missing = json.loads((patterns_root / "linked-missing.json").read_text())
    validate(linked_missing, "model-ir-v1.schema.json")
    missing_report = pattern_report(linked_missing, pattern_contracts)
    check("core.related-entities" in missing_report["summary"]["claimedButUnproven"], "an unlinked model was not flagged for the missing relationship")
    missing_gaps = {gap["gapId"] for entry in missing_report["results"] for gap in entry["gaps"]}
    check("core.related-entities.link" in missing_gaps, "the relationship-shape obligation did not fire on a missing link")

    # Role vocabulary is the explicit interface between pattern libraries and
    # organizational-knowledge instances: contracts must declare every role they
    # use, and an instance's traits must resolve to a declared role.
    for contract in pattern_contracts.values():
        role_errors = contract_role_errors(contract)
        check(not role_errors, f"pattern contract role self-consistency failed: {role_errors}")
    satisfied_roles = role_report(satisfied, pattern_contracts)
    validate(satisfied_roles, "role-report-v1.schema.json")
    check(not satisfied_roles["unknownTraits"], f"a model using declared roles reported unknown traits: {satisfied_roles['unknownTraits']}")
    unknown_trait_model = json.loads((patterns_root / "unknown-trait.json").read_text())
    validate(unknown_trait_model, "model-ir-v1.schema.json")
    unknown_roles = role_report(unknown_trait_model, pattern_contracts)
    check("widget" in unknown_roles["unknownTraits"], "an undeclared instance trait was not flagged")

    # --- Authoring simplifiers: scaffold, assess, review-queue ---
    scaffold = build_scaffold(None, ["core.auditable-entity"], pattern_contracts)
    validate(scaffold, "scaffold-v1.schema.json")
    check("auditable" in {role["trait"] for role in scaffold["roles"]}, "scaffold did not surface the pattern's roles")
    check(any(entry["patternId"] == "core.auditable-entity" and entry["items"] for entry in scaffold["obligations"]), "scaffold did not surface the pattern's obligations")

    ready_report = assess_model(satisfied)
    validate(ready_report, "assess-report-v1.schema.json")
    check(ready_report["ready"], f"a satisfied model was assessed not-ready: {ready_report['checks']}")
    not_ready = assess_model(unproven)
    check(not not_ready["ready"], "an unproven model was assessed ready")

    review = json.loads((coverage_root / "review-source.json").read_text())
    validate(review, "model-ir-v1.schema.json")
    queue = review_queue(review)
    validate(queue, "review-queue-v1.schema.json")
    check(queue["counts"]["review"] >= 1 and queue["counts"]["bulk"] >= 1, f"review queue did not tier synthetic items: {queue['counts']}")
    check("fin.HumanFact" not in {entry["id"] for entry in queue["decisions"]}, "review queue included non-synthetic human knowledge")
    low = next(entry for entry in queue["decisions"] if entry["id"] == "fin.ThresholdClaim")
    check(low["tier"] == "review", "a low-confidence synthetic item was not placed in the review tier")

    # --- Natural-language ingestion: source-relative coverage + front door ---
    source_root = FIXTURES_ROOT / "source"
    source_doc = json.loads((source_root / "source-doc.json").read_text())
    validate(source_doc, "source-document-v1.schema.json")
    source_model = json.loads((source_root / "model.json").read_text())
    validate(source_model, "model-ir-v1.schema.json")
    trace_clean = json.loads((source_root / "trace-clean.json").read_text())
    validate(trace_clean, "source-trace-v1.schema.json")
    clean_coverage = source_coverage(source_doc, source_model, trace_clean)
    validate(clean_coverage, "source-coverage-report-v1.schema.json")
    check(source_complete(clean_coverage), f"faithful extraction reported source-coverage gaps: {clean_coverage}")
    trace_lossy = json.loads((source_root / "trace-lossy.json").read_text())
    lossy_coverage = source_coverage(source_doc, source_model, trace_lossy)
    check("s2" in lossy_coverage["uncoveredSegments"], "source coverage did not flag prose that produced no construct")
    check("shop.Product" in lossy_coverage["unsourcedConstructs"], "source coverage did not flag an ungrounded construct")
    dangling = source_coverage(source_doc, source_model, {"links": [{"segmentId": "s9", "constructs": ["shop.Ghost"]}]})
    check(dangling["danglingSegments"] == ["s9"] and dangling["danglingConstructs"] == ["shop.Ghost"], "source coverage did not flag dangling trace links")

    ingest_report = ingest_model(source_model, source_doc, trace_clean)
    validate(ingest_report, "ingest-report-v1.schema.json")
    check(ingest_report["ready"] and ingest_report["sourceComplete"], f"clean ingestion was not ready+complete: {ingest_report['valid']}/{ingest_report['ready']}/{ingest_report['sourceComplete']}")
    check(not ingest_model(source_model, source_doc, trace_lossy)["sourceComplete"], "lossy ingestion was reported source-complete")

    by_seg = review_by_segment(review, {"links": [
        {"segmentId": "p1", "constructs": ["fin.Invoice"]},
        {"segmentId": "p2", "constructs": ["fin.MatchRule", "fin.ThresholdClaim"]},
    ]})
    grouped = {row["segmentId"] for row in by_seg["bySegment"]}
    check({"p1", "p2"} <= grouped, f"by-segment review did not group decisions by originating segment: {grouped}")

    # --- Document ingestion: profiles + deterministic mermaid importer ---
    document_profiles = load_document_profiles()
    profile_schema = json.loads((SCHEMAS_ROOT / "document-profile-v1.schema.json").read_text(encoding="utf-8"))
    check(document_profiles, "no document profiles loaded")
    for profile in document_profiles.values():
        check(not list(Draft202012Validator(profile_schema).iter_errors(profile)), f"document profile {profile['documentKind']} failed its schema")
    imported = import_mermaid((source_root / "order-process.mmd").read_text(encoding="utf-8"), "OrderProcess", "proc")
    validate(imported["model"], "model-ir-v1.schema.json")
    validate(imported["document"], "source-document-v1.schema.json")
    validate(imported["trace"], "source-trace-v1.schema.json")
    check(not any(item["severity"] == "error" for item in Analyzer(imported["model"]).run()), "mermaid-imported model failed the analyzer")
    check(len(imported["model"]["relationships"]) == 5 and len(imported["model"]["concepts"]) == 5, "mermaid import lost nodes or edges")
    import_coverage = source_coverage(imported["document"], imported["model"], imported["trace"])
    check(source_complete(import_coverage), f"deterministic import was not source-complete: {import_coverage}")

    # Deterministic DBML importer: complete-by-construction, carries category + cardinality + on_delete.
    dbml_out = import_dbml((source_root / "crm.dbml").read_text(encoding="utf-8"), "Crm", "crm")
    validate(dbml_out["model"], "model-ir-v1.schema.json")
    validate(dbml_out["document"], "source-document-v1.schema.json")
    validate(dbml_out["trace"], "source-trace-v1.schema.json")
    check(not any(d["severity"] == "error" for d in Analyzer(dbml_out["model"]).run()), "DBML-imported model failed the analyzer")
    _by_id = {c["id"]: c for c in dbml_out["model"]["concepts"]}
    check(len(_by_id) == 3 and _by_id["accounts"]["metadata"]["category"] == "master"
          and _by_id["opportunities"]["metadata"]["category"] == "transactional",
          "DBML import lost tables or the category tag")
    _rels = dbml_out["model"]["relationships"]
    check(len(_rels) == 2 and all(r["qualifiers"].get("cardinality") for r in _rels)
          and any(r["qualifiers"].get("on-delete") == "cascade" for r in _rels),
          "DBML import lost relationship cardinality / on_delete")
    check(source_complete(source_coverage(dbml_out["document"], dbml_out["model"], dbml_out["trace"])),
          "DBML import was not source-complete")
    doc_check = check_document(imported["document"], document_profiles)
    check(document_conformant(doc_check) and doc_check["documentKind"] == "flowchart", f"imported flowchart failed document-check: {doc_check}")
    drifted_doc = dict(imported["document"], segments=[*imported["document"]["segments"], {"segmentId": "x", "text": "?", "kind": "field"}])
    check(not document_conformant(check_document(drifted_doc, document_profiles)), "document-check did not flag a segment kind foreign to the flowchart profile")

    # --- Walkthrough: the documented model -> coverage -> handoff loop (docs/WALKTHROUGH.md) ---
    walkthrough_root = FIXTURES_ROOT / "walkthrough"
    draft = json.loads((walkthrough_root / "support-ticket-draft.json").read_text())
    validate(draft, "model-ir-v1.schema.json")
    draft_assessment = assess_model(draft)
    check(not draft_assessment["ready"], "walkthrough draft was unexpectedly ready")
    check("coverage.entity.identity" in draft_assessment["checks"]["coverage"]["requiredGapIds"], "walkthrough draft did not surface the expected required identity gap")
    ready = json.loads((walkthrough_root / "support-ticket-ready.json").read_text())
    validate(ready, "model-ir-v1.schema.json")
    ready_assessment = assess_model(ready)
    check(ready_assessment["ready"], f"walkthrough ready model was not ready: {ready_assessment['checks']}")
    check(ready_assessment["checks"]["coverage"]["requiredGaps"] == 0, "walkthrough ready model has required coverage gaps")

    # --- Execution plan: deterministic emit vs code-gen artifact vs runtime LLM ---
    exec_model = json.loads((FIXTURES_ROOT / "execution" / "discount-rules.json").read_text())
    validate(exec_model, "model-ir-v1.schema.json")
    plan = execution_plan(exec_model)
    validate(plan, "execution-plan-v1.schema.json")
    disposition = {entry["id"].split(".")[-1]: (entry["disposition"], entry["overridden"]) for entry in plan["elements"]}
    check(disposition["DiscountCap"] == ("deterministic", False), "a structured condition was not classified deterministic")
    check(disposition["ApprovalPolicy"] == ("codegen", False), "a free-text predicate was not classified for code-gen")
    check(disposition["MarginRationale"] == ("runtime-llm", False), "a reasoning proposition was not classified runtime-llm")
    check(disposition["ManualReviewRule"] == ("runtime-llm", True), "an explicit executionMode override was not honored")
    check(plan["summary"] == {"deterministic": 2, "codegen": 1, "runtimeLlm": 2}, f"execution-plan summary drifted: {plan['summary']}")

    for profile_path in sorted((PROJECT_ROOT / "profiles" / "presets").glob("*.json")):
        validate(json.loads(profile_path.read_text(encoding="utf-8")), "profile-preset-v1.schema.json")
        resolved = resolve_profile(profile_path.stem)
        check("KCF" in resolved["modules"], f"profile {profile_path.stem} omitted the root module")
        check(resolved["modules"], f"profile {profile_path.stem} has no module closure")
        check(resolved["presetChain"][-1] == profile_path.stem, f"profile {profile_path.stem} has an invalid inheritance chain")
        check(not (set(resolved["requiredPatterns"]) & set(resolved["prohibitedPatterns"])), f"profile {profile_path.stem} has conflicting pattern obligations")

    for source in sorted(DOMAINS_ROOT.glob("*.kcf")):
        compiled = compile_file(source)
        golden_path = source.with_suffix(".golden.json")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        check(compiled == golden, f"compiler golden snapshot is stale for {source.name}")
        validate(compiled, "model-ir-v1.schema.json")
        diagnostics = Analyzer(compiled).run()
        check(not any(item["severity"] == "error" for item in diagnostics), f"domain trial {source.name} failed: {diagnostics}")

    # Entity `category` metadata is reconciled against the derived shape (advisory,
    # warning-only). Lock that behavior: the mis-tagged Lead is flagged; the correctly
    # tagged Account/AuditEntry are not.
    cat_diags = Analyzer(compile_file(DOMAINS_ROOT / "entity-category.kcf")).run()
    cat_shape = [d for d in cat_diags if d["rule_id"] == "kcf.entity.category-shape"]
    check(len(cat_shape) == 1 and cat_shape[0]["subject"] == "crm.Lead",
          f"category-shape reconciliation regressed: {cat_shape}")

    # Containment (DDD aggregate root/part) is derived from COMPOSITION and reconciled
    # against an advisory tag: the mis-tagged pure part is flagged, roots are not.
    con = Analyzer(compile_file(DOMAINS_ROOT / "entity-containment.kcf"))
    con_diags = con.run()
    con_shape = [d for d in con_diags if d["rule_id"] == "kcf.entity.containment-shape"]
    pure_parts, _ = con.derive_containment()
    check(len(con_shape) == 1 and con_shape[0]["subject"] == "shop.StatusChange",
          f"containment-shape reconciliation regressed: {con_shape}")
    check(pure_parts == {"shop.StatusChange", "shop.AuditEntry"},
          f"containment derivation regressed: {sorted(pure_parts)}")

    legacy = dict(valid)
    legacy.pop("$schema")
    legacy.pop("irVersion")
    migrated, migration_changes = migrate(legacy)
    check(migration_changes, "legacy IR migration made no changes")
    validate(migrated, "model-ir-v1.schema.json")
    compatibility_errors = check_compatibility()
    check(not compatibility_errors, f"compatibility or module-lock failure: {compatibility_errors}")
    subprocess.run([sys.executable, str(TOOLS_ROOT / "validate_stack.py")], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(TOOLS_ROOT / "lint_stack.py")], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(TOOLS_ROOT / "property_tests.py")], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(TOOLS_ROOT / "check_codegen_coverage.py")], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(TOOLS_ROOT / "check_doc_examples.py")], check=True, cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL)
    print(
        f"PASS valid fixture; PASS invalid fixture ({len(invalid_diagnostics)} diagnostics); "
        f"PASS semantic delta ({len(delta)} changes); "
        f"PASS {len(manifest['modules'])} resolved modules; PASS schemas, profiles, compiler goldens, migration, locks, codegen coverage, doc examples"
    )


if __name__ == "__main__":
    main()
