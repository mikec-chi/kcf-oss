from __future__ import annotations

import io
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

from compiler import compile_file, compile_text
from check_compatibility import check as check_compatibility
from confirm_synthetic import confirm as confirm_synthetic
from coverage_report import load_coverage_model, report as coverage_report
from merge_models import merge
from migrate_ir import migrate
from assess import assess as assess_model
from execution_plan import execution_plan
from document_profile import check_document, emit_warnings, is_conformant as document_conformant, load_document_profiles
from import_mermaid import import_mermaid
from import_dbml import import_dbml
from ingest import ingest as ingest_model
from pattern_contracts import contract_role_errors, load_contracts as load_pattern_contracts, report as pattern_report, role_report
from review_queue import by_segment as review_by_segment, review_queue
from scaffold import build_scaffold
from source_coverage import is_complete as source_complete, source_coverage
from verify_realization import ir_identities, verify as verify_realization
from ir_identity import model_semantic_ids, unclassified_ir_sections
from completeness import completeness
from meta_coverage import construct_families, meta_coverage
from automation_report import report as automation_report
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

    # --- P4: semantic-automation triage + risk-based coverage ---
    # Every still-manual rule is triaged by the kind of effort it needs, and automation
    # coverage is reported by semantic RISK, not rule count - so effort targets the
    # mechanically-automatable, high-risk rules first. A measurement layer only (it does
    # not touch the analyzer or catalogue), so it is gate-safe.
    automation = automation_report(catalogue)
    validate(automation, "automation-report-v1.schema.json")
    check(not automation["untriaged"], f"still-manual rules were not triaged: {automation['untriaged']}")
    check(automation["totalRules"] == coverage["totalRules"], "automation report rule count disagrees with coverage")
    check(sum(bucket["total"] for bucket in automation["byRisk"].values()) == automation["totalRules"], "risk buckets do not sum to the total rule count")
    manual_total = coverage["counts"].get("manual-review", 0) + coverage["counts"].get("profile-dependent", 0)
    check(sum(automation["manualByClass"].values()) == manual_total, "triage classes do not account for every manual/profile rule")
    # The mechanically-automatable backlog has been driven to zero: every still-manual
    # rule is either automated or reclassified (needs-ir-extension / already-enforced /
    # enforced-elsewhere / needs-external-facts / human-judgment / advisory) with a
    # reason in automation-triage-overrides.json. Guard that it stays honestly empty and
    # fully triaged, and that any reclassification carries a reason.
    check(automation["mechanicallyAutomatableBacklog"] == [], f"a mechanically-automatable rule reappeared without a handler: {automation['mechanicallyAutomatableBacklog']}")
    check(automation["manualByClass"].get("needs-ir-extension", 0) >= 1, "needs-ir-extension class unexpectedly empty (overrides not loaded?)")
    check(all(entry.get("reason") for entry in automation["reclassifications"]), "a reclassification is missing its reason")
    check(0.0 <= automation["byRisk"]["high"]["automationRate"] <= 1.0, "high-risk automation rate is out of range")
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
        "kcf.relationship.ordering", "action.record.upsert-key",
        "action.destructive.authorization", "action.record.create-output",
        "action.set.concurrency", "action.transform.field-lineage",
        "action.record.replace-complete", "action.collection.sample", "action.collection.window",
        "action.transform.classification", "action.transform.identity",
        "action.set.query-pure", "action.record.target",
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

    # P1: a schema-valid but empty application is NOT ready. The substantive-content
    # obligation is model-level, so - unlike the per-element identity/authorization
    # obligations - it is not vacuously satisfied when the model has no elements.
    empty_app = json.loads((coverage_root / "empty-application.json").read_text())
    validate(empty_app, "model-ir-v1.schema.json")
    empty_assessment = assess_model(empty_app)
    validate(empty_assessment, "assess-report-v1.schema.json")
    check(not empty_assessment["ready"], "an empty application was assessed ready")
    check("coverage.model.substantive-content" in empty_assessment["checks"]["coverage"]["requiredGapIds"],
          f"empty application did not surface the substantive-content required gap: {empty_assessment['checks']['coverage']}")
    check(empty_assessment["coverageStatus"] == "no-substantive-content",
          f"empty application coverageStatus should be no-substantive-content: {empty_assessment['coverageStatus']}")
    check("codegen-handoff" not in empty_assessment["readyFor"], "an empty application was declared ready for codegen-handoff")

    # P1: an intentionally-sparse vocabulary package opts out of the substantive-
    # content and profile-anchor obligations (packageKind 'vocabulary') and is judged
    # only on per-element obligations - so an honest term library is ready.
    vocab = json.loads((coverage_root / "vocabulary-package.json").read_text())
    validate(vocab, "model-ir-v1.schema.json")
    vocab_report = coverage_report(vocab, coverage_model)
    check(vocab_report["summary"]["required"] == 0, f"vocabulary package reported required gaps: {vocab_report['gaps']}")
    vocab_assessment = assess_model(vocab)
    check(vocab_assessment["ready"], f"vocabulary package was not assessed ready: {vocab_assessment}")

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

    # --- P5: source fidelity - source-complete (linkage) vs source-confirmed (encodings reviewed) ---
    # Linkage-only traceability proves nothing was dropped/invented; it does NOT prove
    # the encoding faithfully means the source. That is the encoding-review lifecycle.
    check(clean_coverage["sourceComplete"] and not clean_coverage["sourceConfirmed"],
          "a linkage-only trace must be source-complete but not yet source-confirmed")
    trace_confirmed = json.loads((source_root / "trace-confirmed.json").read_text())
    validate(trace_confirmed, "source-trace-v1.schema.json")
    confirmed_report = source_coverage(source_doc, source_model, trace_confirmed)
    validate(confirmed_report, "source-coverage-report-v1.schema.json")
    check(confirmed_report["sourceComplete"] and confirmed_report["sourceConfirmed"],
          f"a fully-reviewed extraction was not source-confirmed: {confirmed_report['unconfirmedConstructs']}/{confirmed_report['disputedConstructs']}")
    check(confirmed_report["counts"]["confirmedConstructs"] == confirmed_report["counts"]["sourcedConstructs"],
          "not every sourced construct was counted as confirmed")
    check(not confirmed_report["ungovernedConfirmations"], f"a properly-governed trace reported governance failures: {confirmed_report['ungovernedConfirmations']}")

    # R3: a confirmation is only counted when GOVERNED - a record that claims
    # 'semantically-confirmed' but names no reviewer/time/disposition and whose excerpt
    # hash does not match the source segment is surfaced, never silently accepted.
    trace_ungoverned = json.loads((source_root / "trace-ungoverned.json").read_text())
    validate(trace_ungoverned, "source-trace-v1.schema.json")
    ungoverned_report = source_coverage(source_doc, source_model, trace_ungoverned)
    validate(ungoverned_report, "source-coverage-report-v1.schema.json")
    check(not ungoverned_report["sourceConfirmed"], "an ungoverned confirmation was accepted as source-confirmed")
    check("shop.Customer" not in set(ungoverned_report["reviewStates"]) or ungoverned_report["counts"]["confirmedConstructs"] == 0,
          "an ungoverned confirmation was counted as confirmed")
    flagged = {entry["identity"] for entry in ungoverned_report["ungovernedConfirmations"]}
    check("shop.Customer" in flagged, "an ungoverned confirmation claim was not surfaced")
    issues = {issue for entry in ungoverned_report["ungovernedConfirmations"] for issue in entry["issues"]}
    check({"excerpt-hash-mismatch", "missing-reviewer", "disposition-not-accept"} <= issues,
          f"governance did not detect the expected failures: {sorted(issues)}")
    trace_disputed = json.loads((source_root / "trace-disputed.json").read_text())
    validate(trace_disputed, "source-trace-v1.schema.json")
    disputed_report = source_coverage(source_doc, source_model, trace_disputed)
    validate(disputed_report, "source-coverage-report-v1.schema.json")
    check(disputed_report["sourceComplete"] and not disputed_report["sourceConfirmed"],
          "a disputed extraction is source-complete but must NOT be source-confirmed")
    check("shop.Product" in disputed_report["disputedConstructs"], "source fidelity did not flag the disputed construct")
    check("order-contains-product" in disputed_report["unconfirmedConstructs"], "source fidelity did not flag the un-reviewed construct")

    ingest_report = ingest_model(source_model, source_doc, trace_clean)
    validate(ingest_report, "ingest-report-v1.schema.json")
    check(ingest_report["ready"] and ingest_report["sourceComplete"], f"clean ingestion was not ready+complete: {ingest_report['valid']}/{ingest_report['ready']}/{ingest_report['sourceComplete']}")
    check(not ingest_model(source_model, source_doc, trace_lossy)["sourceComplete"], "lossy ingestion was reported source-complete")

    # --- P6: executable codegen evidence (realization manifest verifier) ---
    # The prose "dropped: []" self-audit becomes machine-checkable: every IR identity
    # must have a disposition, realized ones must carry artifact evidence, and gaps
    # must be explicitly noted. A complete manifest verifies; an incomplete one names
    # exactly what was dropped / unbacked / unknown.
    realization_root = FIXTURES_ROOT / "realization"
    realization_model = json.loads((realization_root / "model.json").read_text())
    validate(realization_model, "model-ir-v1.schema.json")
    check(ir_identities(realization_model) == {"shop.Order": "concepts", "CreateOrder": "actions"},
          f"IR identity enumeration drifted: {ir_identities(realization_model)}")
    manifest_ok = json.loads((realization_root / "manifest-complete.json").read_text())
    validate(manifest_ok, "realization-manifest-v1.schema.json")
    ok_report = verify_realization(realization_model, manifest_ok)
    validate(ok_report, "realization-report-v1.schema.json")
    check(ok_report["ok"] and ok_report["summary"]["missing"] == 0, f"complete realization manifest failed verification: {ok_report['errors']}")
    # R5: a green report WITHOUT --repo is only 'accounted' - it must not imply the
    # artifacts exist. With a repo whose files+symbols+tests are present it climbs the
    # evidence ladder to 'test-present'.
    check(ok_report["evidenceLevel"] == "accounted", f"unchecked realization should be 'accounted', got {ok_report['evidenceLevel']}")
    repo_report = verify_realization(realization_model, manifest_ok, realization_root / "repo")
    validate(repo_report, "realization-report-v1.schema.json")
    check(repo_report["ok"] and repo_report["evidenceLevel"] == "test-present",
          f"repo-checked realization did not reach test-present: {repo_report['evidenceLevel']} / {repo_report['errors']}")
    manifest_bad = json.loads((realization_root / "manifest-incomplete.json").read_text())
    validate(manifest_bad, "realization-manifest-v1.schema.json")
    bad_report = verify_realization(realization_model, manifest_bad)
    validate(bad_report, "realization-report-v1.schema.json")
    bad_codes = {error["code"] for error in bad_report["errors"]}
    check(not bad_report["ok"] and bad_report["evidenceLevel"] == "none", "an incomplete realization manifest passed verification")
    check({"missing-disposition", "realized-without-evidence", "unknown-identity"} <= bad_codes,
          f"realization verifier missed expected error classes: {sorted(bad_codes)}")

    # R4: the identity inventory is EXHAUSTIVE - it reuses the one authoritative
    # ir_identity.model_semantic_ids, so profile/tail sections cannot be silently
    # unverified. The profiles reference model exercises all eight profile sections.
    profiles_ir = compile_file(DOMAINS_ROOT / "profiles.kcf")
    profile_ids = ir_identities(profiles_ir)
    inventoried_sections = set(profile_ids.values())
    check({"integration", "security", "lineage", "architecture", "experience", "design", "analytics", "ai"} <= set(profile_ids),
          f"authoritative identity inventory omits profile sections: {sorted(inventoried_sections)}")

    # V6: schema-to-identity-inventory conformance. Every top-level property of the IR
    # schema must be classified in ir_identity (a list/string/singleton identity source
    # or explicitly EXCLUDED with a reason). A new identity-bearing IR section then fails
    # this gate until registered - keeping "every semantic identity" honest as the IR
    # grows. Also cross-check that sections the reference models actually PRODUCE are
    # classified (not silently excluded).
    ir_schema = json.loads((SCHEMAS_ROOT / "model-ir-v1.schema.json").read_text(encoding="utf-8"))
    unclassified = unclassified_ir_sections(ir_schema)
    check(not unclassified, f"IR schema has unclassified top-level section(s) - register in ir_identity.py: {unclassified}")
    # W6: an extension package is a semantic identity, so a realization must account for it
    # (D-005 at the package level) - arbitrary content cannot hide in an unaccounted bag.
    ext_ids = model_semantic_ids({"concepts": [], "extensions": {"acme.audit": {"x": 1}}})
    check(ext_ids.get("extensions.acme.audit") == "extensions", f"extension package was not accounted as a semantic identity: {ext_ids}")
    from ir_identity import EXCLUDED_SECTIONS as _EXCLUDED
    for name in sorted((PROJECT_ROOT / "tests" / "domains").glob("*.kcf")):
        produced = {key for key, value in compile_file(name).items() if isinstance(value, (list, dict)) and value}
        wrongly_excluded = {k for k in produced if k in _EXCLUDED and k not in ("profiles", "modules", "moduleVersions", "requiredPatterns", "recommendedPatterns", "prohibitedPatterns", "implementedPatterns", "excludedPatterns", "sourceMap", "extensions")}
        check(not wrongly_excluded, f"{name.name} produces section(s) marked non-identity in ir_identity: {sorted(wrongly_excluded)}")

    # --- P2: closed-world completeness against a declared scope ---
    # Completeness is reported along separate axes and is explicit that "complete"
    # means complete AGAINST THE DECLARED SCOPE - every included capability maps to a
    # construct, with no open questions - not against an unbounded open world.
    scope_root = FIXTURES_ROOT / "scope"
    scope_model = json.loads((FIXTURES_ROOT / "walkthrough" / "support-ticket-ready.json").read_text())
    scope_complete = json.loads((scope_root / "scope-complete.json").read_text())
    validate(scope_complete, "scope-v1.schema.json")
    comp = completeness(scope_model, scope_complete)
    validate(comp, "completeness-report-v1.schema.json")
    check(comp["closedWorldComplete"] and not comp["blockers"], f"a model covering its declared scope was not closed-world complete: {comp['blockers']}")
    check(comp["axes"]["source"]["status"] == "not-applicable", "a scope with no declared sources should make the source axis not-applicable")
    check(not comp["axes"]["declaredScope"]["uncovered"], f"declared-scope axis reported spurious uncovered capabilities: {comp['axes']['declaredScope']}")
    check(comp["axes"]["declaredScope"]["covered"] == scope_complete["includedCapabilities"], "declared-scope axis did not map every included capability to a construct")
    scope_incomplete = json.loads((scope_root / "scope-incomplete.json").read_text())
    validate(scope_incomplete, "scope-v1.schema.json")
    comp_bad = completeness(scope_model, scope_incomplete)
    validate(comp_bad, "completeness-report-v1.schema.json")
    check(not comp_bad["closedWorldComplete"], "a model with uncovered scope + open questions was reported complete")
    check({"scope-capabilities-uncovered", "open-questions"} <= set(comp_bad["blockers"]), f"completeness blockers missed scope/open-question reasons: {comp_bad['blockers']}")
    check({"support.Refund", "EscalateTicket"} <= set(comp_bad["axes"]["declaredScope"]["uncovered"]),
          f"declared-scope axis did not flag uncovered capabilities: {comp_bad['axes']['declaredScope']['uncovered']}")
    check(comp_bad["axes"]["openQuestions"], "completeness did not surface declared open questions")

    # R1: a scope that NAMES its sources must have them evaluated before it is complete.
    scope_sourced = json.loads((scope_root / "scope-sourced.json").read_text())
    validate(scope_sourced, "scope-v1.schema.json")
    unevaluated = completeness(source_model, scope_sourced)
    validate(unevaluated, "completeness-report-v1.schema.json")
    check(not unevaluated["closedWorldComplete"] and "sources-declared-not-evaluated" in unevaluated["blockers"],
          f"declared-but-unevaluated sources did not block completeness: {unevaluated['blockers']}")
    check(unevaluated["axes"]["source"]["status"] == "declared-not-evaluated", "source axis status wrong for unevaluated declared sources")
    evaluated = completeness(source_model, scope_sourced, source_doc, trace_clean)
    validate(evaluated, "completeness-report-v1.schema.json")
    check(evaluated["closedWorldComplete"] and evaluated["axes"]["source"]["status"] == "evaluated-complete",
          f"a sourced scope evaluated complete was not closed-world complete: {evaluated['blockers']}")

    # R2: a closed-world scope must declare at least one capability unless it declares a package/vocabulary kind.
    empty_scope = {"scopeVersion": "1.0.0", "includedCapabilities": []}
    validate(empty_scope, "scope-v1.schema.json")
    empty_comp = completeness(scope_model, empty_scope)
    check(not empty_comp["closedWorldComplete"] and "empty-scope" in empty_comp["blockers"], "an empty scope was reported closed-world complete")
    vocab_scope = {"scopeVersion": "1.0.0", "packageKind": "vocabulary", "includedCapabilities": []}
    validate(vocab_scope, "scope-v1.schema.json")
    vocab_comp = completeness(scope_model, vocab_scope)
    check("empty-scope" not in vocab_comp["blockers"], "an explicit vocabulary scope was wrongly blocked for emptiness")

    # --- P3: coverage of the coverage system (meta-coverage) ---
    # Every grammar construct family either has a coverage policy or is reported as
    # coverage-policy-missing - a construct is never silently treated as complete for
    # lack of a policy. Every obligation's dimension must be a real family (no orphans),
    # and every obligation must resolve to a registered evaluator.
    meta = meta_coverage(coverage_model, verify_fixtures=True, root=PROJECT_ROOT)
    validate(meta, "coverage-meta-report-v1.schema.json")
    check(not meta["orphanObligations"], f"coverage obligations reference unknown construct families: {meta['orphanObligations']}")
    check(all(row["hasEvaluator"] for row in meta["families"]), "a coverage obligation has no registered evaluator")
    covered_families = {row["family"] for row in meta["families"] if row["status"] == "covered"}
    check({"ENTITY", "ACTION", "RULE", "EVENT", "ACTOR", "RELATIONSHIP"} <= covered_families,
          f"a core construct family lost its coverage policy: {sorted(covered_families)}")
    check(meta["withPolicy"] + len(meta["withoutPolicy"]) == meta["totalFamilies"], "meta-coverage family accounting is inconsistent")
    # V4: every construct family now has an EXPLICIT policy - obligations, or a
    # familyPolicies decision (conditional / intentionally-none). No family is left as
    # an undecided blind spot, and every declared decision carries a reason.
    check(meta["withoutPolicy"] == [], f"a construct family has neither obligations nor a familyPolicies decision: {meta['withoutPolicy']}")
    check(all(row.get("policyReason") for row in meta["families"] if row["status"] in ("conditional", "intentionally-none")),
          "a declared family policy (conditional/intentionally-none) is missing its reason")
    check({"SECURITY", "INTEGRATION"} <= covered_families, f"SECURITY/INTEGRATION must have completeness obligations: {sorted(covered_families)}")
    # The blind-spot mechanism still works: a synthetic family with no obligation/policy is reported missing.
    probe = meta_coverage(coverage_model, families=[*construct_families(), "ZZZ_PROBE_FAMILY"])
    check("ZZZ_PROBE_FAMILY" in probe["withoutPolicy"], "meta-coverage no longer detects an undecided family")

    # R6/V5: every obligation that declares fixtures must have them VERIFIED - the
    # positive fixture produces no gap and the negative fixture produces one - so a
    # declared fixture reference is demonstrated coverage-governance, not a dangling
    # pointer. And EVERY REQUIRED obligation must be regression-gated: if a required
    # coverage evaluator regresses, its negative fixture stops producing the gap and
    # this gate fails - so no required obligation can silently lose protection.
    governance = meta["fixtureGovernance"]
    check(governance["verified"] and governance["fixtureDeclared"] >= 6, f"too few obligations declare fixtures: {governance['fixtureDeclared']}")
    check(governance["positiveVerified"] == governance["fixtureDeclared"], "a positive obligation fixture produced an unexpected gap")
    check(governance["negativeVerified"] == governance["fixtureDeclared"], "a negative obligation fixture failed to produce a gap")
    required_obligations = {obligation["id"] for obligation in coverage_model["obligations"] if obligation["level"] == "required"}
    gated = set(governance["regressionGateIncluded"])
    ungated_required = sorted(required_obligations - gated)
    check(not ungated_required, f"required coverage obligation(s) lack verified positive+negative fixtures: {ungated_required}")
    # W4: every coverage obligation (required AND recommended) is now regression-gated -
    # every executable evaluator has verified positive+negative fixtures (inline or in
    # config/coverage-fixtures.json), so no coverage evaluator can silently regress.
    all_obligations = {obligation["id"] for obligation in coverage_model["obligations"]}
    ungated_all = sorted(all_obligations - gated)
    check(not ungated_all, f"coverage obligation(s) not regression-gated: {ungated_all}")

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
    # document-check warnings: a missing/unprofiled modality is a non-fatal warning (not a
    # hard fail) and MUST be surfaced by emit_warnings on every entry point (report
    # document-check-warnings-not-surfaced-by-cli-20260729-02); declaring is never worse
    # than omitting, so both stay conformant.
    prose_seg = {"segmentId": "p1", "kind": "statement", "text": "Every item carries a unique tag."}
    profiled = check_document({"documentId": "d", "documentKind": "prose", "segments": [prose_seg]}, document_profiles)
    check(profiled["hasProfile"] and document_conformant(profiled) and profiled["warnings"] == [], "profiled prose document should be conformant with no warnings")
    no_kind = check_document({"documentId": "d", "segments": [prose_seg]}, document_profiles)
    check(document_conformant(no_kind) and len(no_kind["warnings"]) == 1, "a document with no documentKind should be conformant but warn")
    unprofiled = check_document({"documentId": "d", "documentKind": "spreadsheet", "segments": [prose_seg]}, document_profiles)
    check(document_conformant(unprofiled) and len(unprofiled["warnings"]) == 1, "a declared-but-unprofiled kind should be conformant but warn (never worse than omitting)")
    _buf = io.StringIO(); emit_warnings(no_kind, _buf)
    check(_buf.getvalue().startswith("warning: ") and "documentKind" in _buf.getvalue(), "emit_warnings did not write the warning to the given stream")

    # --- 2026-07-29 field-report batch (#03-#08): authoring/analysis fidelity guards ---
    # #03 (ordering-dimension-qualifier-catch-22): `dimension` is required on ORDERING by
    # kcf.relationship.ordering, so it MUST be a recognized qualifier — else every valid
    # ORDERING edge trips the "not recognized" advisory. Guard the class of bug generally.
    from semantic_analyzer import KNOWN_RELATIONSHIP_QUALIFIERS
    check("dimension" in KNOWN_RELATIONSHIP_QUALIFIERS, "ORDERING's required `dimension` qualifier is missing from KNOWN_RELATIONSHIP_QUALIFIERS")
    # #04 (source-coverage-blind-to-five-collections): construct_ids must see id-bearing
    # constructs in every domain collection incl. profile sections, and must NOT count
    # infrastructure collections (emitters), so faithfulness is reachable and honest.
    from source_coverage import construct_ids as _construct_ids
    _cov_ids = _construct_ids({"propositions": [{"id": "m.P"}], "authorities": [{"id": "m.A"}],
                               "math": [{"id": "m.F"}], "processes": [{"id": "m.Proc"}],
                               "integration": {"adapters": [{"id": "m.Adapter"}]},
                               "emitters": [{"id": "m.Emitter"}]})
    check({"m.P", "m.A", "m.F", "m.Proc", "m.Adapter"} <= _cov_ids, "source-coverage construct_ids is blind to a domain/profile collection")
    check("m.Emitter" not in _cov_ids, "source-coverage must not demand a source for infrastructure (emitters)")
    # #05 (entity-immutable-declaration-dropped): `immutable;` on a non-EVENT concept must
    # project as read-only mutability, not vanish.
    _imm_ir = compile_text("kcf model M profile operational-system { namespace m; "
                           "entity Ledger { identity id: UUID generated; required amount: Decimal; "
                           "category transactional; immutable; } }")
    _ledger = next(c for c in _imm_ir["concepts"] if c["id"] == "Ledger")
    check((_ledger.get("metadata") or {}).get("mutability") == "read-only", "`immutable;` on an entity did not project to metadata.mutability read-only")
    # #06 (lifecycle-obligation-ignores-exempt): a read-only transactional entity is exempt
    # from the lifecycle obligation; a mutable one still attracts it.
    from coverage_report import ev_concept_kind_has_lifecycle as _ev_lifecycle
    _obl = {"id": "coverage.entity.lifecycle", "level": "recommended", "obligation": "has-lifecycle", "conceptKind": "ENTITY"}
    _ro = {"concepts": [{"id": "L", "qualifiedName": "m.L", "kind": "ENTITY", "metadata": {"category": "transactional", "mutability": "read-only"}}], "lifecycles": []}
    _mu = {"concepts": [{"id": "M", "qualifiedName": "m.M", "kind": "ENTITY", "metadata": {"category": "transactional"}}], "lifecycles": []}
    check(_ev_lifecycle(_ro, _obl) == [], "read-only transactional entity should be exempt from the lifecycle obligation")
    check(len(_ev_lifecycle(_mu, _obl)) == 1, "a mutable transactional entity should still attract a lifecycle recommendation")
    # #08 (scope-capabilities-need-qualified-identifiers): a capability declared as
    # `capability procure_to_pay;` lands qualified (cap.procure_to_pay); a scope naming
    # either the bare or the qualified token must match.
    from completeness import _model_capability_terms as _cap_terms, _covers as _cap_covers
    _cterms = _cap_terms({"concepts": [{"id": "Clerk", "qualifiedName": "cap.Clerk", "kind": "ACTOR", "capabilities": ["cap.procure_to_pay"]}]})
    _clow = {t.lower() for t in _cterms}
    check(_cap_covers("procure_to_pay", _cterms, _clow) and _cap_covers("cap.procure_to_pay", _cterms, _clow), "scope capability must match by bare local name and by namespace-qualified form")

    # --- The canonical six-stage journey (evidence -> generated app) ---
    # Smoke-test the orchestration end to end so the guided scaffold + status/stage
    # detection + review packet + approve (governed IR + review envelope) + verify-project
    # cannot silently regress. (generate-plan is exercised separately - it pulls the mcp
    # prompt-assembly, out of scope for the core gate.)
    import tempfile as _tempfile, shutil as _shutil
    from init_project import init_project as _init_project
    import journey as _journey
    _JOURNEY_KCF = (
        "kcf model JourneyDemo profile business-application {\n"
        "  namespace journeydemo;\n"
        "  entity Order { identity id: UUID; required title: String; required status: String; }\n"
        "  actor Clerk { }\n  work ManageOrderWork { }\n"
        "  rule OrderAccess { kind CONSTRAINT; condition \"the clerk is assigned\"; effect ManageOrderWork; applies-to Order; authority Clerk; }\n"
        "  policy OrderPolicy { authority Clerk; rule OrderAccess; default-conflict deny-overrides; }\n"
        "  command CreateOrder { operation create; scope record; target Order; input one; output one; idempotency conditional; idempotency-key rid; atomicity atomic; authorization journeydemo.OrderPolicy; }\n"
        "  query GetOrder { operation read; scope record; target Order; selection identity; input one; output one; }\n"
        "  lifecycle OrderLifecycle for Order { initial Open; terminal Resolved; transition Open -> Resolved; }\n}\n")
    _jtmp = Path(_tempfile.mkdtemp(prefix="kcf-journey-"))
    try:
        _proj = _jtmp / "demo"
        _init_project(_proj, "JourneyDemo", "business-application", guided=True)
        check((_proj / "START_HERE.md").is_file() and (_proj / "inputs").is_dir()
              and (_proj / "kcf.project.json").is_file(), "guided init did not produce the evidence-first scaffold")
        (_proj / "model" / "JourneyDemo.kcf").write_text(_JOURNEY_KCF, encoding="utf-8")
        (_proj / "inputs" / "requirements" / "r.md").write_text("An Order has a title and a status.\n", encoding="utf-8")
        _added = _journey.add_sources(_proj, _proj / "inputs" / "requirements" / "r.md")
        check(len(_added) == 1 and _added[0]["kind"] == "prose", "sources add did not register the prose evidence")
        _st = _journey.status(_proj)
        check(_st["modelValid"] and _st["stage"] == "review" and _st["next"], f"journey status wrong: stage={_st['stage']} valid={_st['modelValid']}")
        _md, _meta = _journey.review_packet(_proj)
        check(_meta["valid"] and "## Approval buckets" in _md and "stateDiagram" in _md, "review packet missing expected sections")
        _summary = _journey.approve(_proj, "tester", as_of="2026-07-29T00:00:00Z")
        check(_summary["envelopeValid"] and (_proj / _summary["governedIr"]).is_file()
              and (_proj / _summary["envelope"]).is_file(), "approve did not emit a valid envelope + governed IR")
        _result = _journey.verify_project(_proj)
        check(_result["ok"] and _result["checks"]["requiredGaps"] == 0
              and _result["checks"]["driftFromApproved"] in (0, None), f"verify-project not ok: {_result.get('checks')}")
        # Drift: an approved model that then changes must fail verification.
        (_proj / "model" / "JourneyDemo.kcf").write_text(
            _JOURNEY_KCF.replace("actor Clerk { }", "actor Clerk { }\n  entity Note { identity id: UUID; required body: String; }"),
            encoding="utf-8")
        check(not _journey.verify_project(_proj)["ok"], "verify-project did not detect model/code drift after an approved model changed")
    finally:
        _shutil.rmtree(_jtmp, ignore_errors=True)

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
