"""Semantic-automation triage and risk-based coverage.

The rule catalogue tags each rule with an `enforcement` (automated / partially-
automated / manual-review / profile-dependent), derived mechanically from the
analyzer. That answers "how many rules run automatically" - a rule *count*. It does
not answer the two questions that actually drive work:

  1. Of the rules still enforced by hand, which are *mechanically automatable* (a
     structural check over the IR), which *need external facts*, which need *human
     judgement*, and which are merely *advisory*? (Triage - so effort targets the
     automatable ones first.)
  2. What is automation coverage by *semantic risk* - not by rule count? Automating
     ten cosmetic naming rules matters less than automating one authorization rule.

This tool classifies every non-automated rule into a `manualClass`, assigns every
rule a `risk`, and reports automation coverage per risk bucket. Classification is by
transparent keyword heuristics over the rule text, overridable per rule via
``semantics/automation-triage-overrides.json``. Nothing here touches the analyzer or
the catalogue - it is a measurement layer, so it is gate-safe and domain-agnostic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = PROJECT_ROOT / "semantics" / "semantic-rules.json"
OVERRIDES = PROJECT_ROOT / "semantics" / "automation-triage-overrides.json"

MANUAL_ENFORCEMENTS = {"manual-review", "profile-dependent"}
# Manual-rule classes. The keyword heuristic only assigns the first four; the finer
# classes are assigned by per-rule review in automation-triage-overrides.json (each with
# a reason). "mechanically-automatable" means checkable against TODAY's IR - a rule that
# would need a new authoring/IR field is "needs-ir-extension", not automatable now.
MANUAL_CLASSES = (
    "mechanically-automatable",
    "needs-ir-extension",
    "needs-external-facts",
    "already-enforced",
    "enforced-elsewhere",
    "human-judgment",
    "advisory",
)
RISKS = ("high", "medium", "low")

# Keyword heuristics (checked against the rule's requirement + section, lowercased).
_HUMAN_JUDGEMENT = ("intent", "meaning", "appropriate", "business sense", "reasonable", "sensible",
                    "semantically correct", "domain expert", "judgement", "judgment", "makes sense",
                    "intended", "well-formed english", "clear ", "ambiguous")
_EXTERNAL_FACTS = ("external", "registry", "runtime", "deploy", "reachable", "credential",
                   "real system", "live ", "resolves", "network", "third-party", "provider")
_ADVISORY = ("should", "recommend", "prefer", "style", "naming", "convention", "readable",
             "descriptive", "document ", "documentation")

_HIGH_RISK = ("security", "authoriz", "access", "policy", "provenance", "lifecycle", "identity",
              "integrity", "conflict", "temporal", "permission", "audit", "boundary", "escalation",
              "prohibit", "supersession", "contradiction")
_LOW_RISK = ("naming", "style", "label", "description", "readable", "convention", "cosmetic")


def _text(rule: dict) -> str:
    return f"{rule.get('requirement', '')} {rule.get('section', '')}".lower()


def classify_manual(rule: dict) -> str:
    """The kind of effort a still-manual rule needs. Order is deliberate: a rule that
    needs judgement or external facts is NOT mechanically automatable even if it also
    reads structural, so those are matched first; advisory only for warnings; the
    remainder (structural checks expressible over the IR) is the automatable backlog."""
    text = _text(rule)
    if any(keyword in text for keyword in _HUMAN_JUDGEMENT):
        return "human-judgment"
    if any(keyword in text for keyword in _EXTERNAL_FACTS):
        return "needs-external-facts"
    if rule.get("severity") == "warning" and any(keyword in text for keyword in _ADVISORY):
        return "advisory"
    return "mechanically-automatable"


def classify_risk(rule: dict) -> str:
    text = _text(rule)
    rule_id = rule["id"].lower()
    if any(keyword in text or keyword in rule_id for keyword in _HIGH_RISK):
        return "high"
    if any(keyword in text or keyword in rule_id for keyword in _LOW_RISK):
        return "low"
    return "medium"


def load_overrides() -> dict:
    if OVERRIDES.exists():
        return json.loads(OVERRIDES.read_text(encoding="utf-8")).get("rules", {})
    return {}


def triage(catalogue: dict, overrides: dict | None = None) -> dict:
    overrides = overrides if overrides is not None else load_overrides()
    triaged = []
    for rule in catalogue["rules"]:
        override = overrides.get(rule["id"], {})
        automated = rule["enforcement"] == "automated"
        manual_class = None
        if rule["enforcement"] in MANUAL_ENFORCEMENTS:
            manual_class = override.get("manualClass") or classify_manual(rule)
        triaged.append({
            "id": rule["id"],
            "enforcement": rule["enforcement"],
            "automated": automated,
            "manualClass": manual_class,
            "risk": override.get("risk") or classify_risk(rule),
            "reclassified": bool(override.get("manualClass")),
            "reason": override.get("reason"),
        })
    return {"rules": triaged}


def report(catalogue: dict, overrides: dict | None = None) -> dict:
    triaged = triage(catalogue, overrides)["rules"]

    by_enforcement: dict[str, int] = {}
    manual_by_class = {name: 0 for name in MANUAL_CLASSES}
    by_risk = {name: {"total": 0, "automated": 0} for name in RISKS}
    backlog: list[str] = []
    untriaged: list[str] = []

    for rule in triaged:
        by_enforcement[rule["enforcement"]] = by_enforcement.get(rule["enforcement"], 0) + 1
        bucket = by_risk[rule["risk"]]
        bucket["total"] += 1
        if rule["automated"]:
            bucket["automated"] += 1
        if rule["enforcement"] in MANUAL_ENFORCEMENTS:
            if rule["manualClass"] in manual_by_class:
                manual_by_class[rule["manualClass"]] += 1
            else:
                untriaged.append(rule["id"])
            if rule["manualClass"] == "mechanically-automatable":
                backlog.append(rule["id"])

    for bucket in by_risk.values():
        bucket["automationRate"] = round(bucket["automated"] / bucket["total"], 3) if bucket["total"] else 0.0

    reclassifications = sorted(
        ({"id": rule["id"], "manualClass": rule["manualClass"], "reason": rule["reason"]}
         for rule in triaged if rule["reclassified"]),
        key=lambda entry: entry["id"],
    )

    return {
        "automationReportVersion": "1.0.0",
        "totalRules": len(triaged),
        "byEnforcement": by_enforcement,
        "manualByClass": manual_by_class,
        "byRisk": by_risk,
        "mechanicallyAutomatableBacklog": sorted(backlog),
        "reclassifications": reclassifications,
        "untriaged": sorted(untriaged),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage still-manual semantic rules and report automation coverage by semantic risk.")
    parser.add_argument("--catalogue", type=Path, default=CATALOGUE)
    parser.add_argument("--output", "-o", type=Path)
    args = parser.parse_args()

    catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
    result = report(catalogue)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 1 if result["untriaged"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
