from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler import compile_file  # noqa: E402
from confirm_synthetic import confirm as confirm_synthetic  # noqa: E402
from coverage_report import by_concept, load_coverage_model, report as coverage_report  # noqa: E402
from assess import assess as assess_model  # noqa: E402
from document_profile import check_document, emit_warnings, is_conformant, load_document_profiles  # noqa: E402
from import_mermaid import import_mermaid  # noqa: E402
from import_dbml import import_dbml  # noqa: E402
from ingest import ingest as ingest_model  # noqa: E402
from execution_plan import execution_plan  # noqa: E402
from init_project import init_project, PROFILES  # noqa: E402
from pattern_contracts import load_contracts, report as pattern_report, role_report  # noqa: E402
from review_queue import by_segment as review_by_segment, review_queue  # noqa: E402
from scaffold import build_scaffold  # noqa: E402
from source_coverage import is_complete as source_complete, source_coverage  # noqa: E402
from completeness import completeness as completeness_report  # noqa: E402
from meta_coverage import meta_coverage  # noqa: E402
from automation_report import report as automation_report  # noqa: E402
from verify_realization import verify as verify_realization  # noqa: E402
from merge_models import merge  # noqa: E402
from migrate_ir import migrate  # noqa: E402
from profile_resolver import resolve_profile  # noqa: E402
from semantic_analyzer import Analyzer  # noqa: E402




def write_json(value: dict, output: Path | None) -> None:
    text = json.dumps(value, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> int:
    parser = argparse.ArgumentParser(prog="kcf", description="KCF compiler, validator, profile, and migration CLI. OSS stops at the semantic IR; code generation is LLM-based (see codegen/).")
    commands = parser.add_subparsers(dest="command", required=True)

    compile_command = commands.add_parser("compile")
    compile_command.add_argument("source", type=Path)
    compile_command.add_argument("--output", "-o", type=Path)
    compile_command.add_argument("--validate", action="store_true")

    validate_command = commands.add_parser("validate")
    validate_command.add_argument("model", type=Path)
    validate_command.add_argument("--output", "-o", type=Path)

    profile_command = commands.add_parser("profile")
    profile_command.add_argument("preset")
    profile_command.add_argument("--output", "-o", type=Path)


    migrate_command = commands.add_parser("migrate")
    migrate_command.add_argument("source", type=Path)
    migrate_command.add_argument("output", type=Path)
    migrate_command.add_argument("--report", type=Path)

    merge_command = commands.add_parser("merge")
    merge_command.add_argument("models", type=Path, nargs="+")
    merge_command.add_argument("--id", required=True)
    merge_command.add_argument("--namespace", required=True)
    merge_command.add_argument("--output", "-o", type=Path)
    merge_command.add_argument("--identity-map", type=Path)

    coverage_command = commands.add_parser("coverage-report")
    coverage_command.add_argument("model", type=Path)
    coverage_command.add_argument("--output", "-o", type=Path)
    coverage_command.add_argument("--strict", action="store_true")
    coverage_command.add_argument("--by-concept", action="store_true")

    pattern_command = commands.add_parser("pattern-check")
    pattern_command.add_argument("model", type=Path)
    pattern_command.add_argument("--patterns")
    pattern_command.add_argument("--output", "-o", type=Path)

    roles_command = commands.add_parser("roles-check")
    roles_command.add_argument("model", type=Path)
    roles_command.add_argument("--output", "-o", type=Path)


    scaffold_command = commands.add_parser("scaffold")
    scaffold_command.add_argument("--profile")
    scaffold_command.add_argument("--patterns")
    scaffold_command.add_argument("--output", "-o", type=Path)

    assess_command = commands.add_parser("assess")
    assess_command.add_argument("model", type=Path)
    assess_command.add_argument("--output", "-o", type=Path)

    execplan_command = commands.add_parser("execution-plan")
    execplan_command.add_argument("model", type=Path)
    execplan_command.add_argument("--output", "-o", type=Path)

    review_command = commands.add_parser("review-queue")
    review_command.add_argument("model", type=Path)
    review_command.add_argument("--high-confidence", type=float, default=0.8)
    review_command.add_argument("--by-segment", type=Path)
    review_command.add_argument("--output", "-o", type=Path)

    source_command = commands.add_parser("source-coverage")
    source_command.add_argument("document", type=Path)
    source_command.add_argument("model", type=Path)
    source_command.add_argument("trace", type=Path)
    source_command.add_argument("--output", "-o", type=Path)

    ingest_command = commands.add_parser("ingest")
    ingest_command.add_argument("model", type=Path)
    ingest_command.add_argument("document", type=Path)
    ingest_command.add_argument("trace", type=Path)
    ingest_command.add_argument("--output", "-o", type=Path)

    verify_command = commands.add_parser("verify-realization", help="verify a codegen realization manifest against the IR (and optionally the generated repo)")
    verify_command.add_argument("model", type=Path)
    verify_command.add_argument("manifest", type=Path)
    verify_command.add_argument("--repo", type=Path)
    verify_command.add_argument("--output", "-o", type=Path)

    completeness_command = commands.add_parser("completeness", help="multi-axis, closed-world completeness against a declared scope")
    completeness_command.add_argument("model", type=Path)
    completeness_command.add_argument("scope", type=Path)
    completeness_command.add_argument("--document", type=Path)
    completeness_command.add_argument("--trace", type=Path)
    completeness_command.add_argument("--output", "-o", type=Path)

    metacov_command = commands.add_parser("coverage-meta", help="report which grammar construct families have a coverage policy (coverage of the coverage system)")
    metacov_command.add_argument("--strict", action="store_true", help="exit non-zero if any construct family has no coverage policy")
    metacov_command.add_argument("--output", "-o", type=Path)

    autoreport_command = commands.add_parser("automation-report", help="triage still-manual semantic rules and report automation coverage by semantic risk")
    autoreport_command.add_argument("--output", "-o", type=Path)

    doccheck_command = commands.add_parser("document-check")
    doccheck_command.add_argument("document", type=Path)
    doccheck_command.add_argument("--output", "-o", type=Path)

    mermaid_command = commands.add_parser("import-mermaid")
    mermaid_command.add_argument("source", type=Path)
    mermaid_command.add_argument("--id", required=True)
    mermaid_command.add_argument("--namespace", required=True)
    mermaid_command.add_argument("--output", "-o", type=Path)
    mermaid_command.add_argument("--source-doc", type=Path)
    mermaid_command.add_argument("--trace", type=Path)

    dbml_command = commands.add_parser("import-dbml")
    dbml_command.add_argument("source", type=Path)
    dbml_command.add_argument("--id", required=True)
    dbml_command.add_argument("--namespace", required=True)
    dbml_command.add_argument("--profile", default="business-application")
    dbml_command.add_argument("--output", "-o", type=Path)
    dbml_command.add_argument("--source-doc", type=Path)
    dbml_command.add_argument("--trace", type=Path)

    confirm_command = commands.add_parser("confirm")
    confirm_command.add_argument("model", type=Path)
    confirm_command.add_argument("--reviewer", required=True)
    confirm_command.add_argument("--as-of", required=True)
    confirm_command.add_argument("--decisions", type=Path)
    confirm_command.add_argument("--confirm", action="append")
    confirm_command.add_argument("--reject", action="append")
    confirm_command.add_argument("--output", "-o", type=Path, required=True)

    commands.add_parser("coverage")
    commands.add_parser("check")

    init_command = commands.add_parser("init", help="seed a KCF knowledge application (model as source of truth)")
    init_command.add_argument("directory", type=Path, help="target project directory")
    init_command.add_argument("--name", help="model name (default: the directory name)")
    init_command.add_argument("--profile", default="business-application", choices=PROFILES)

    args = parser.parse_args()

    if args.command == "init":
        name = args.name or "".join(w.capitalize() for w in args.directory.name.replace("-", " ").replace("_", " ").split()) or "App"
        try:
            created = init_project(args.directory, name, args.profile)
        except ValueError as exc:
            print(f"kcf init: {exc}", file=sys.stderr)
            return 1
        print(f"Seeded knowledge application '{name}' ({args.profile}) at {args.directory}:")
        for path in created:
            print(f"  + {path}")
        print("\nNext: point your coding agent at AGENTS.md, then model your domain in "
              f"model/{name}.kcf and keep code in sync with it (see .kcf/MODEL_SYNC.md).")
        return 0

    if args.command == "compile":
        model = compile_file(args.source)
        write_json(model, args.output)
        if args.validate:
            diagnostics = Analyzer(model).run()
            if diagnostics: print(json.dumps({"diagnostics": diagnostics}, indent=2), file=sys.stderr)
            return 1 if any(item["severity"] == "error" for item in diagnostics) else 0
        return 0
    if args.command == "validate":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        diagnostics = Analyzer(model).run()
        result = {"model": str(args.model), "valid": not any(item["severity"] == "error" for item in diagnostics), "diagnostics": diagnostics}
        write_json(result, args.output)
        return 0 if result["valid"] else 1
    if args.command == "profile":
        write_json(resolve_profile(args.preset), args.output)
        return 0
    if args.command == "migrate":
        model = json.loads(args.source.read_text(encoding="utf-8"))
        migrated, changes = migrate(model)
        write_json(migrated, args.output)
        report = {"source": str(args.source), "targetVersion": migrated["irVersion"], "changes": changes}
        if args.report: write_json(report, args.report)
        else: write_json(report, None)
        return 0
    if args.command == "merge":
        models = [json.loads(path.read_text(encoding="utf-8")) for path in args.models]
        extra_alias = json.loads(args.identity_map.read_text(encoding="utf-8")) if args.identity_map else None
        unified, conflicts = merge(models, args.id, args.namespace, extra_alias)
        write_json(unified, args.output)
        analyzer_diagnostics = Analyzer(unified).run()
        if conflicts or analyzer_diagnostics:
            report = {"conflicts": conflicts, "analyzerDiagnostics": analyzer_diagnostics}
            print(json.dumps(report, indent=2), file=sys.stderr)
        return 1 if conflicts or any(item["severity"] == "error" for item in analyzer_diagnostics) else 0
    if args.command == "coverage-report":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        result = coverage_report(model, load_coverage_model())
        write_json(by_concept(result) if args.by_concept else result, args.output)
        if result["summary"]["required"]:
            return 1
        return 1 if args.strict and result["summary"]["recommended"] else 0
    if args.command == "pattern-check":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        pattern_ids = [item for item in args.patterns.split(",") if item] if args.patterns else None
        result = pattern_report(model, load_contracts(), pattern_ids)
        write_json(result, args.output)
        summary = result["summary"]
        return 1 if (summary["claimedButUnproven"] or summary["requiredButAbsent"] or summary["requiredWithoutContract"]) else 0
    if args.command == "roles-check":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        result = role_report(model, load_contracts())
        write_json(result, args.output)
        return 1 if result["unknownTraits"] else 0
        return 0 if draft["roles"] else 1
    if args.command == "scaffold":
        if not args.profile and not args.patterns:
            print("provide --profile and/or --patterns", file=sys.stderr)
            return 2
        extra = [item for item in args.patterns.split(",") if item] if args.patterns else []
        write_json(build_scaffold(args.profile, extra, load_contracts()), args.output)
        return 0
    if args.command == "assess":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        result = assess_model(model)
        write_json(result, args.output)
        return 0 if result["ready"] else 1
    if args.command == "execution-plan":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        write_json(execution_plan(model), args.output)
        return 0
    if args.command == "review-queue":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        if args.by_segment:
            trace = json.loads(args.by_segment.read_text(encoding="utf-8"))
            write_json(review_by_segment(model, trace, args.high_confidence), args.output)
        else:
            write_json(review_queue(model, args.high_confidence), args.output)
        return 0
    if args.command == "source-coverage":
        report = source_coverage(
            json.loads(args.document.read_text(encoding="utf-8")),
            json.loads(args.model.read_text(encoding="utf-8")),
            json.loads(args.trace.read_text(encoding="utf-8")),
        )
        write_json(report, args.output)
        return 0 if source_complete(report) else 1
    if args.command == "ingest":
        report = ingest_model(
            json.loads(args.model.read_text(encoding="utf-8")),
            json.loads(args.document.read_text(encoding="utf-8")),
            json.loads(args.trace.read_text(encoding="utf-8")),
        )
        write_json(report, args.output)
        return 0 if (report["ready"] and report["sourceComplete"]) else 1
    if args.command == "verify-realization":
        report = verify_realization(
            json.loads(args.model.read_text(encoding="utf-8")),
            json.loads(args.manifest.read_text(encoding="utf-8")),
            args.repo,
        )
        write_json(report, args.output)
        return 0 if report["ok"] else 1
    if args.command == "completeness":
        document = json.loads(args.document.read_text(encoding="utf-8")) if args.document else None
        trace = json.loads(args.trace.read_text(encoding="utf-8")) if args.trace else None
        report = completeness_report(
            json.loads(args.model.read_text(encoding="utf-8")),
            json.loads(args.scope.read_text(encoding="utf-8")),
            document,
            trace,
        )
        write_json(report, args.output)
        return 0 if report["closedWorldComplete"] else 1
    if args.command == "coverage-meta":
        report = meta_coverage(load_coverage_model(), verify_fixtures=True, root=PROJECT_ROOT)
        write_json(report, args.output)
        return 1 if (args.strict and report["withoutPolicy"]) else 0
    if args.command == "automation-report":
        report = automation_report(json.loads((PROJECT_ROOT / "semantics" / "semantic-rules.json").read_text(encoding="utf-8")))
        write_json(report, args.output)
        return 1 if report["untriaged"] else 0
    if args.command == "document-check":
        document = json.loads(args.document.read_text(encoding="utf-8"))
        report = check_document(document, load_document_profiles())
        write_json(report, args.output)
        emit_warnings(report)
        return 0 if is_conformant(report) else 1
    if args.command == "import-mermaid":
        result = import_mermaid(args.source.read_text(encoding="utf-8"), args.id, args.namespace)
        write_json(result["model"], args.output)
        if args.source_doc:
            write_json(result["document"], args.source_doc)
        if args.trace:
            write_json(result["trace"], args.trace)
        return 0
    if args.command == "import-dbml":
        result = import_dbml(args.source.read_text(encoding="utf-8"), args.id, args.namespace, args.profile)
        # Fail loudly rather than silently emitting an empty model: 0 tables almost always
        # means the source isn't the supported dbml.org `Table { ... }` subset (e.g. a
        # different DBML dialect). Domain-agnostic — only the table count is inspected.
        if not result["model"]["concepts"]:
            print(f"import-dbml: parsed {args.source} but found 0 tables - no model was "
                  f"produced. This importer accepts the dbml.org subset (`Table name {{ ... }}` "
                  f"with `[pk]`, `[ref: OP other.col]`); check the source is that dialect.",
                  file=sys.stderr)
            return 2
        write_json(result["model"], args.output)
        if args.source_doc:
            write_json(result["document"], args.source_doc)
        if args.trace:
            write_json(result["trace"], args.trace)
        return 0
    if args.command == "confirm":
        model = json.loads(args.model.read_text(encoding="utf-8"))
        confirm_ids, reject_ids = [], []
        if args.decisions:
            payload = json.loads(args.decisions.read_text(encoding="utf-8"))
            confirm_ids += payload.get("confirm", [])
            reject_ids += payload.get("reject", [])
        if args.confirm:
            confirm_ids += [item for chunk in args.confirm for item in chunk.split(",") if item]
        if args.reject:
            reject_ids += [item for chunk in args.reject for item in chunk.split(",") if item]
        updated, summary = confirm_synthetic(model, confirm_ids, reject_ids, args.reviewer, args.as_of)
        write_json(updated, args.output)
        print(json.dumps(summary, indent=2), file=sys.stderr)
        return 1 if summary["notFound"] else 0
    if args.command == "coverage":
        print((PROJECT_ROOT / "semantics" / "coverage.json").read_text(encoding="utf-8"), end="")
        return 0
    if args.command == "check":
        if not (PROJECT_ROOT.parent / "semantic-core").exists():
            print(
                "kcf check runs the full conformance gate and needs the semantic-core\n"
                "catalogue, which ships only in a source checkout (kcf-oss/ and\n"
                "semantic-core/ as siblings) - not in the installed wheel. Clone the\n"
                "repository to run the gate: https://github.com/OWNER/kcf",
                file=sys.stderr,
            )
            return 2
        return subprocess.run([sys.executable, str(TOOLS_ROOT / "run_conformance.py")], cwd=PROJECT_ROOT).returncode
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
