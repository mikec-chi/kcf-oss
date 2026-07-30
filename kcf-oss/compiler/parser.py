from __future__ import annotations

import json
import re
from typing import Any

from .ast import Declaration, Model, SourceSpan
from .lexer import Token, tokenize

# The set of keywords that may open a top-level declaration inside a model body. Used both as the
# "expected tokens" set at an unrecognized declaration and as the synchronization targets for bounded
# error recovery (parse_collect): after a parse error we skip to the next of these at brace-depth 0.
TOP_LEVEL_KEYWORDS = {
    "namespace", "use", "implements", "excludes", "organization", "information", "rule", "policy",
    "reasoning", "assertion", "identity-resolution", "knowledge-query", "skill", "capability", "unit",
    "authority", "process", "allocation", "calendar", "route", "proposition", "predicate",
    "formula", "function", "optimize", "distribution", "simulation", "relationship", "lifecycle",
    "command", "query", "transform", "collection",
}
_DIAG_MSG_RE = re.compile(r"^(?P<src>.*?):(?P<line>\d+):(?P<col>\d+):\s*(?P<msg>.*)$", re.S)


def all_top_level_keywords() -> set:
    """Every keyword that may open a top-level declaration - the fixed directives plus the concept
    kinds and profile-section keywords (resolved at call time since those tables are defined later)."""
    return TOP_LEVEL_KEYWORDS | set(CONCEPT_KINDS) | set(_PROFILE_SPEC)


def _nearest_keyword(word: str) -> str | None:
    """A cheap 'did you mean' suggestion: the closest top-level keyword within edit distance 2."""
    best, best_d = None, 3
    for candidate in all_top_level_keywords():
        d = _edit_distance(word, candidate, best_d)
        if d < best_d:
            best, best_d = candidate, d
    return best


def _edit_distance(a: str, b: str, ceiling: int) -> int:
    """Levenshtein distance, early-exiting once it provably exceeds ``ceiling``."""
    if abs(len(a) - len(b)) >= ceiling:
        return ceiling
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            val = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur.append(val)
            row_min = min(row_min, val)
        if row_min >= ceiling:
            return ceiling
        prev = cur
    return prev[-1]


CONCEPT_KINDS = {
    "entity": "ENTITY", "actor": "ACTOR", "work": "WORK", "event": "EVENT",
    "resource": "RESOURCE", "intent": "INTENT", "measure": "MEASURE",
    "temporal": "TEMPORAL", "spatial": "SPATIAL",
    "logic": "LOGIC", "math": "MATH",
}

# Reference-list fields a concept body may declare: an ACTOR's capabilities/skills,
# a WORK's required capabilities/skills, and an EVENT's subject/source/observer/
# trigger/affect-lifecycle/evidence. Each line is `<keyword> <ref>;` and appends to
# the mapped typed list (references resolved by the analyzer; the normalizer projects
# the EVENT lists into ir["events"]).
_CONCEPT_REF_FIELDS = {
    "capability": "capabilities",
    "skill": "skills",
    "requires-capability": "requiresCapability",
    "requires-skill": "requiresSkill",
    "subject": "subjects",
    "trigger": "triggers",
    "source": "sources",
    "observer": "observers",
    "affect-lifecycle": "affectsLifecycle",
    "evidence": "evidence",
    "role": "roles",
    "authority": "authorities",
    "responsible-for": "responsibleFor",
    "accountable-for": "accountableFor",
    "member-of": "memberOf",
    "performer": "performers",
    "input": "inputs",
    "output": "outputs",
    "outcome": "outcomes",
    "requires-resource": "requiresResource",
    "requires-tool": "requiresTool",
    "governed-by": "governedBy",
    "triggered-by": "triggeredBy",
    "emit": "emits",
    "compensate-with": "compensateWith",
    "temporal": "temporalRefs",
    "stakeholder": "stakeholders",
    "measure": "measures",
    "adjacent-to": "adjacentTo",
    "jurisdiction": "jurisdictions",
    "route": "spatialRoutes",
}


# ENTITY-dimension cardinality vocabulary (ergonomic bare-ident form; the numeric
# ranges of the dimension grammar, e.g. 0..1 / 1..*, are not lexable so they map to
# these keywords). Used on attributes, compositions, and named references.
_CARDINALITY = {"one", "many", "set", "zero-or-one", "one-or-many", "zero-or-many", "optional-one"}


# Profile-block element specs (operational + emitter profiles). Each profile is
# authored as a top-level block `<section> { <element> <id> { <field> <value>; } }`
# and projects into ir[<section>]. Per element: (ir-collection, {field-keyword:
# (ir-key, is-list)}). References inside a profile resolve by LOCAL id (matching the
# analyzer's within-section checks), so they are not namespace-qualified.
_PROFILE_SPEC = {
    "integration": {
        "adapter": ("adapters", {"protocol": ("protocol", False), "serialization": ("serialization", False), "authentication": ("authentication", False), "resource": ("resource", False)}),
        "endpoint": ("endpoints", {"adapter": ("adapter", False), "operation": ("operation", False), "address": ("address", False), "timeout": ("timeout", False), "retry": ("retry", False)}),
        "contract": ("contracts", {"action": ("action", False), "input": ("input", False), "output": ("output", False), "precondition": ("preconditions", True), "postcondition": ("postconditions", True), "failure-mode": ("failureModes", True)}),
        "route": ("routes", {"source": ("source", False), "target": ("target", False), "when": ("when", False)}),
        "retry-policy": ("retryPolicies", {"attempts": ("attempts", False), "backoff": ("backoff", False), "requires-idempotency": ("requiresIdempotency", False)}),
        "event-bridge": ("eventBridges", {"event": ("event", False), "endpoint": ("endpoint", False), "mapping": ("mapping", False)}),
    },
    "security": {
        "asset": ("assets", {"subject": ("subject", False), "classification": ("classification", False), "owner": ("owner", False)}),
        "threat": ("threats", {"vector": ("vector", False), "target": ("targets", True), "actor": ("actor", False)}),
        "risk": ("risks", {"threat": ("threat", False), "asset": ("asset", False), "likelihood": ("likelihood", False), "impact": ("impact", False), "level": ("level", False)}),
        "control": ("controls", {"rule": ("rule", False), "applies-to": ("appliesTo", True), "implementation": ("implementation", False), "evidence": ("evidence", False)}),
        "treatment": ("treatments", {"risk": ("risk", False), "mode": ("mode", False), "control": ("control", False), "owner": ("owner", False)}),
        "trust-boundary": ("trustBoundaries", {"contains": ("contains", True), "crossing-control": ("crossingControls", True)}),
    },
    "lineage": {
        "lineage": ("edges", {"source": ("source", False), "target": ("target", False), "transformation": ("transformation", False), "execution": ("execution", False)}),
        "binding": ("bindings", {"source": ("source", False), "target": ("target", False), "kind": ("kind", False), "condition": ("condition", False)}),
        "cost": ("costs", {"subject": ("subject", False), "amount": ("amount", False), "unit": ("unit", False), "period": ("period", False), "allocation": ("allocation", False)}),
    },
    "architecture": {
        "system": ("systems", {"capability": ("capabilities", True), "service": ("services", True)}),
        "service": ("services", {"realizes": ("realizes", False), "interface": ("interfaces", True), "runtime": ("runtime", False)}),
        "interface": ("interfaces", {"contract": ("contract", False), "protocol": ("protocol", False)}),
        "deployment": ("deployments", {"artifact": ("artifact", False), "target": ("target", False), "version": ("version", False)}),
        "boundary": ("boundaries", {"contains": ("contains", True), "control": ("controls", True)}),
    },
    "experience": {
        "app": ("apps", {"entry": ("entry", False), "view": ("views", True)}),
        # RFC-15: a view carries a KIND + per-kind bindings, most of which point at existing dimensions
        # (COMPOSITION→parent/tree, LIFECYCLE→column/kanban, MEASURE→series/chart, SPATIAL→geometry/map,
        # TEMPORAL→start/end + ORDERING→depends-on/gantt, view/measure→tile/dashboard, renderer→custom).
        # Additive + backward-compatible: a view with no `kind` keeps today's list/detail behaviour.
        "view": ("views", {"entity": ("entity", False), "component": ("components", True),
                           "action": ("actions", True), "kind": ("kind", False),
                           "parent": ("parent", False), "column": ("columns", True),
                           "swimlane": ("swimlane", False), "series": ("series", True),
                           "axis": ("axis", False), "chart-kind": ("chartKind", False),
                           "geometry": ("geometry", False), "start": ("start", False),
                           "end": ("end", False), "depends-on": ("dependsOn", False),
                           "tile": ("tiles", True), "renderer": ("renderer", False),
                           "section": ("sections", True)}),
        "component": ("components", {"property": ("properties", True), "slot": ("slots", True)}),
    },
    "design": {
        # RFC-16: optional per-region layout hint (priority/span/min-size/collapse) overrides the
        # automatic responsive layout; breakpoints are documented CONTAINER-relative (the view's region).
        "page": ("pages", {"view": ("view", False), "pattern": ("pattern", False),
                          "section": ("sections", True), "priority": ("priority", False),
                          "span": ("span", False), "min-size": ("minSize", False),
                          "collapse": ("collapse", False)}),
    },
    "analytics": {
        "dataset": ("datasets", {"source": ("source", False), "transform": ("transforms", True)}),
        "semantic-layer": ("semanticLayers", {"dimension": ("dimensions", True), "measure": ("measures", True)}),
    },
    "ai": {
        "dataset": ("datasets", {"information": ("information", False), "schema": ("schema", False)}),
        "model": ("models", {"input": ("input", False), "output": ("output", False), "method": ("method", False), "metric": ("metrics", True)}),
        "serving": ("serving", {"model": ("model", False), "runtime": ("runtime", False), "capacity": ("capacity", False)}),
        "governance": ("governance", {"policy": ("policies", True), "evidence": ("evidence", True), "explanation": ("explanations", True)}),
    },
}


class ParseError(ValueError):
    pass


class Parser:
    def __init__(self, text: str, source: str = "<memory>"):
        self.tokens = tokenize(text)
        self.index = 0
        self.source = source
        self.depth = 0  # brace nesting depth, maintained by advance() (used only by error recovery)

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        # Track brace nesting so bounded recovery knows when it is back at the model-body level. `{`/`}`
        # only ever appear as their own punctuation tokens, so a value check is exact.
        if token.value == "{":
            self.depth += 1
        elif token.value == "}":
            self.depth -= 1
        return token

    def accept(self, value: str) -> Token | None:
        if self.current.value == value:
            return self.advance()
        return None

    def _perr(self, code: str, token: Token, message: str, *, expected=None,
              found=None, suggestion=None) -> "ParseError":
        """Build a ParseError that ALSO carries machine-readable fields (code, line, column, found,
        expected tokens, repair suggestion) so a recovering caller can emit a structured diagnostic
        instead of a bare string. The string message is unchanged for back-compatibility."""
        err = ParseError(f"{self.source}:{token.line}:{token.column}: {message}")
        err.code = code
        err.line = token.line
        err.column = token.column
        err.found = token.value if found is None else found
        err.expected = list(expected or [])
        err.suggestion = suggestion
        return err

    def expect(self, value: str) -> Token:
        token = self.current
        if token.value != value:
            raise self._perr("parse.expected-token", token,
                             f"expected {value!r}, found {token.value!r}", expected=[value])
        return self.advance()

    def expect_ident(self) -> Token:
        token = self.current
        if token.kind != "IDENT":
            raise self._perr("parse.expected-identifier", token,
                             f"expected identifier, found {token.value!r}", expected=["<identifier>"])
        return self.advance()

    def scalar(self) -> Any:
        token = self.current
        if token.kind == "STRING":
            self.advance()
            return json.loads(token.value)
        if token.kind == "NUMBER":
            self.advance()
            return float(token.value) if "." in token.value else int(token.value)
        if token.value in {"true", "false"}:
            self.advance()
            return token.value == "true"
        return self.expect_ident().value

    def span(self, start: Token, end: Token) -> SourceSpan:
        return SourceSpan(self.source, start.line, start.column, end.end_line, end.end_column)

    def parse(self) -> Model:
        start = self.current
        self.accept("kcf")
        self.expect("model")
        name = self.expect_ident().value
        profile = "business-application"
        if self.accept("profile"):
            profile = self.expect_ident().value
        self.expect("{")
        model = Model(name=name, profile=profile)
        while self.current.value != "}":
            if self.current.kind == "EOF":
                raise self._perr("parse.unclosed-model", self.current, "unclosed model", expected=["}"])
            self._parse_top_level_item(model)
        end = self.expect("}")
        if self.current.kind != "EOF":
            token = self.current
            raise self._perr("parse.trailing-input", token,
                             f"unexpected trailing input {token.value!r}")
        model.span = self.span(start, end)
        return model

    def _parse_header(self) -> tuple[Token, Model]:
        """Parse `[kcf] model <name> [profile <p>] {` and return (start_token, model)."""
        start = self.current
        self.accept("kcf")
        self.expect("model")
        name = self.expect_ident().value
        profile = "business-application"
        if self.accept("profile"):
            profile = self.expect_ident().value
        self.expect("{")
        return start, Model(name=name, profile=profile)

    def _parse_top_level_item(self, model: Model) -> None:
        """Parse ONE top-level declaration/directive into ``model``. Raises ParseError on failure
        (enriched via _perr for the unrecognized-declaration case). Shared by parse() and
        parse_collect() so the recovery variant reuses the exact same dispatch."""
        keyword = self.current.value
        if True:
            if keyword == "namespace":
                self.advance(); model.namespace = self.expect_ident().value; self.expect(";")
            elif keyword == "use":
                self.advance(); model.extra_profiles.append(self.expect_ident().value); self.expect(";")
            elif keyword == "implements":
                self.advance(); model.implemented_patterns.append(self.expect_ident().value); self.expect(";")
            elif keyword == "excludes":
                self.advance(); model.excluded_patterns.append(self.expect_ident().value); self.expect(";")
            elif keyword == "organization":
                model.declarations.append(self.parse_organization())
            elif keyword == "information":
                model.declarations.append(self.parse_information())
            elif keyword == "rule":
                model.declarations.append(self.parse_rule())
            elif keyword == "policy":
                model.declarations.append(self.parse_policy())
            elif keyword == "reasoning":
                model.declarations.append(self.parse_reasoning())
            elif keyword == "assertion":
                model.declarations.append(self.parse_assertion())
            elif keyword == "identity-resolution":
                model.declarations.append(self.parse_identity_resolution())
            elif keyword == "knowledge-query":
                model.declarations.append(self.parse_knowledge_query())
            elif keyword == "skill":
                model.declarations.append(self.parse_skill())
            elif keyword == "capability":
                model.declarations.append(self.parse_capability())
            elif keyword == "unit":
                model.declarations.append(self.parse_unit())
            elif keyword == "authority":
                model.declarations.append(self.parse_authority())
            elif keyword == "process":
                model.declarations.append(self.parse_process())
            elif keyword in _PROFILE_SPEC:
                model.declarations.append(self.parse_profile(keyword))
            elif keyword == "allocation":
                model.declarations.append(self.parse_allocation())
            elif keyword == "calendar":
                model.declarations.append(self.parse_calendar())
            elif keyword == "route":
                model.declarations.append(self.parse_route())
            elif keyword == "proposition":
                model.declarations.append(self.parse_proposition())
            elif keyword == "predicate":
                model.declarations.append(self.parse_predicate())
            elif keyword in {"formula", "function", "optimize", "distribution", "simulation"}:
                model.declarations.append(self.parse_math())
            elif keyword in CONCEPT_KINDS:
                model.declarations.append(self.parse_concept())
            elif keyword == "relationship":
                model.declarations.append(self.parse_relationship())
            elif keyword == "lifecycle":
                model.declarations.append(self.parse_lifecycle())
            elif keyword in {"command", "query", "transform"}:
                model.declarations.append(self.parse_action())
            elif keyword == "collection":
                model.declarations.append(self.parse_collection())
            else:
                token = self.current
                nearest = _nearest_keyword(keyword)
                raise self._perr("parse.unsupported-declaration", token,
                                 f"unsupported declaration {keyword!r}",
                                 expected=sorted(all_top_level_keywords()),
                                 suggestion=(f"did you mean {nearest!r}?" if nearest else None))

    # --- bounded error recovery -------------------------------------------------
    def _structured(self, err: "ParseError") -> dict:
        """Turn a ParseError into a machine-readable diagnostic. Enriched errors (via _perr) carry the
        fields directly; plain string errors are parsed back into line/column/message."""
        if getattr(err, "code", None):
            diag = {"code": err.code, "line": err.line, "column": err.column, "message": str(err),
                    "found": err.found, "expected": err.expected}
            if err.suggestion:
                diag["suggestion"] = err.suggestion
            return diag
        match = _DIAG_MSG_RE.match(str(err))
        if match:
            return {"code": "parse.error", "line": int(match["line"]), "column": int(match["col"]),
                    "message": str(err), "found": None, "expected": []}
        return {"code": "parse.error", "line": None, "column": None, "message": str(err),
                "found": None, "expected": []}

    def _synchronize(self, min_index: int) -> None:
        """Skip to the next top-level declaration boundary so parsing can resume after an error: a
        top-level keyword (or the model's closing brace) encountered back at the model-body depth of 1.
        Uses the advance()-maintained ``self.depth`` so an error raised deep inside a nested block
        correctly skips out of that block first. Guarantees forward progress past ``min_index``."""
        keywords = all_top_level_keywords()
        while self.index < min_index and self.current.kind != "EOF":
            self.advance()
        while self.current.kind != "EOF":
            if self.depth <= 1 and (self.current.value in keywords or self.current.value == "}"):
                return
            self.advance()

    def parse_collect(self) -> tuple[Model, list[dict]]:
        """Like parse() but RECOVERS at top-level declaration boundaries, collecting every diagnostic
        instead of aborting on the first. Returns (partial_model, diagnostics). A caller compiles the
        model only when diagnostics is empty; otherwise it reports all diagnostics at once - far fewer
        LLM/author repair round-trips than one-error-at-a-time.

        Recovery is bounded to top-level boundaries: an error inside a block is reported once and the
        rest of that block is skipped, so a second independent error in the SAME block may not be
        surfaced until the first is fixed. Errors in DISTINCT top-level declarations are all collected."""
        diagnostics: list[dict] = []
        try:
            start, model = self._parse_header()  # consumes the model's `{` -> self.depth == 1
        except ParseError as err:
            # header failure is unrecoverable (we don't know where the body begins)
            return Model(name="<unparsed>", profile="business-application"), [self._structured(err)]
        while self.current.kind != "EOF":
            if self.depth == 1 and self.current.value == "}":
                end = self.advance()
                model.span = self.span(start, end)
                return model, diagnostics
            item_start = self.index
            try:
                self._parse_top_level_item(model)
            except ParseError as err:
                diagnostics.append(self._structured(err))
                self._synchronize(item_start + 1)
        diagnostics.append(self._structured(
            self._perr("parse.unclosed-model", self.current, "unclosed model", expected=["}"])))
        return model, diagnostics

    def parse_concept(self) -> Declaration:
        start = self.advance()
        kind = CONCEPT_KINDS[start.value]
        name = self.expect_ident().value
        values: dict[str, Any] = {"kind": kind, "attributes": [], "references": [], "traits": [], "metadata": {}}
        if start.value == "event" and self.accept("immutable"):
            values["immutable"] = True
            end = self.expect(";")
            return Declaration("concept", name, values, self.span(start, end))
        self.expect("{")
        while self.current.value != "}":
            keyword = self.current.value
            if keyword in {"identity", "required", "optional", "field"}:
                modifier = self.advance().value
                field_name = self.expect_ident().value
                self.expect(":")
                type_name = self.expect_ident().value
                attribute = {"name": field_name, "type": type_name}
                if modifier == "identity":
                    attribute.update({"identity": True, "required": True})
                elif modifier == "required":
                    attribute["required"] = True
                elif modifier == "optional":
                    attribute["required"] = False
                if self.accept("="):
                    attribute["default"] = self.scalar()
                # Trailing ergonomic modifiers (ENTITY dimension attribute-def):
                # a cardinality keyword, a `generated` flag, and free-form qualifiers.
                qualifiers: list[str] = []
                while self.current.kind == "IDENT" and self.current.value != "}":
                    token = self.advance().value
                    if token == "generated":
                        attribute["generated"] = True
                    elif token in _CARDINALITY:
                        attribute["cardinality"] = token
                    else:
                        qualifiers.append(token)
                if qualifiers:
                    attribute["qualifiers"] = qualifiers
                self.expect(";")
                values["attributes"].append(attribute)
            elif keyword == "compose":
                self.advance()
                comp = {"name": self.expect_ident().value}
                self.expect(":"); comp["target"] = self.expect_ident().value
                comp["cardinality"] = self.expect_ident().value
                if self.accept("orphan"):
                    comp["orphan"] = self.expect_ident().value
                self.expect(";"); values.setdefault("compositions", []).append(comp)
            elif keyword == "reference":
                self.advance()
                ref = {"name": self.expect_ident().value}
                self.expect(":"); ref["target"] = self.expect_ident().value
                ref["cardinality"] = self.expect_ident().value
                if self.accept("inverse"):
                    ref["inverse"] = self.expect_ident().value
                self.expect(";"); values.setdefault("namedReferences", []).append(ref)
            elif keyword == "collection":
                self.advance()
                cname = self.expect_ident().value
                if self.accept("of"):
                    coll = {"name": cname, "of": self.expect_ident().value}
                    self.expect("{")
                    while self.current.value != "}":
                        ck = self.current.value
                        if ck == "identity":
                            self.advance(); coll["identity"] = self.expect_ident().value; self.expect(";")
                        elif ck == "order-by":
                            self.advance(); coll["orderBy"] = self.expect_ident().value; self.expect(";")
                        elif ck == "constraint":
                            self.advance(); coll.setdefault("constraints", []).append(self.expect_ident().value); self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported collection member {ck!r}")
                    self.expect("}"); values.setdefault("collections", []).append(coll)
                else:
                    self.expect(":"); coll = {"name": cname, "of": self.expect_ident().value}; self.expect(";")
                    values.setdefault("collections", []).append(coll)
            elif keyword == "lifecycle":
                self.advance(); values["lifecycleRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "constraint":
                self.advance(); values.setdefault("constraints", []).append(self.expect_ident().value); self.expect(";")
            elif keyword == "mutation":
                values.setdefault("mutations", []).append(self.parse_entity_mutation())
            elif keyword == "ref":
                self.advance(); values["references"].append(self.expect_ident().value); self.expect(";")
            elif keyword == "trait":
                self.advance(); values["traits"].append(self.expect_ident().value); self.expect(";")
            elif keyword == "abstract":
                self.advance(); values["abstract"] = True; self.expect(";")
            elif keyword == "immutable":
                self.advance(); values["immutable"] = True; self.expect(";")
            elif keyword in _CONCEPT_REF_FIELDS:
                self.advance()
                values.setdefault(_CONCEPT_REF_FIELDS[keyword], []).append(self.expect_ident().value)
                self.expect(";")
            # Dimension `kind` classifier (event-kind, actor-kind, resource-kind, ...);
            # promoted to a first-class field so the analyzer can enforce the enum.
            elif keyword == "kind":
                self.advance(); values["conceptKind"] = self.expect_ident().value.upper(); self.expect(";")
            # EVENT single-value fields (occurrence/detection are attribute or temporal
            # names, carried verbatim; correlation-key is a free-form key list).
            elif keyword in ("occurrence-time", "detection-time"):
                field = "occurrenceTime" if keyword == "occurrence-time" else "detectionTime"
                self.advance(); values[field] = self.expect_ident().value; self.expect(";")
            elif keyword == "correlation-key":
                self.advance(); values.setdefault("correlationKeys", []).append(self.expect_ident().value); self.expect(";")
            elif keyword == "severity":
                self.advance(); values["severity"] = self.scalar(); self.expect(";")
            elif keyword == "expectedness":
                self.advance(); values["expectedness"] = self.expect_ident().value; self.expect(";")
            elif keyword == "match":
                self.advance(); values["matchCondition"] = self.scalar(); self.expect(";")
            # MEASURE single-value fields (unit/calculation/period are refs;
            # scale/aggregation are enums; threshold/target/tolerance are numbers).
            elif keyword == "unit":
                self.advance(); values["unitRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "scale":
                self.advance(); values["scale"] = self.expect_ident().value; self.expect(";")
            elif keyword == "calculation":
                # Shared by MEASURE (a ref/expression) and TEMPORAL (an expression);
                # stored verbatim as a string/ident so both kinds work.
                self.advance(); values["calculation"] = self.scalar(); self.expect(";")
            elif keyword == "aggregation":
                self.advance(); values["aggregation"] = self.expect_ident().value; self.expect(";")
            elif keyword == "period":
                self.advance(); values["periodRef"] = self.expect_ident().value; self.expect(";")
            elif keyword in ("threshold", "target", "tolerance"):
                key = self.advance().value; values[key] = self.scalar(); self.expect(";")
            # ACTOR single-value members.
            elif keyword == "availability":
                self.advance(); values["availability"] = self.scalar(); self.expect(";")
            elif keyword == "communication":
                self.advance(); values["communicationRef"] = self.expect_ident().value; self.expect(";")
            # WORK condition members (multi-valued condition strings).
            elif keyword in ("precondition", "postcondition", "completion", "failure"):
                key = {"precondition": "preconditions", "postcondition": "postconditions",
                       "completion": "completions", "failure": "failures"}[keyword]
                self.advance(); values.setdefault(key, []).append(self.scalar()); self.expect(";")
            # INTENT single-value members.
            elif keyword == "desired-state":
                self.advance(); values["desiredState"] = self.scalar(); self.expect(";")
            elif keyword == "success":
                self.advance(); values.setdefault("successes", []).append(self.scalar()); self.expect(";")
            elif keyword == "priority":
                self.advance(); values["priority"] = self.scalar(); self.expect(";")
            elif keyword == "time-horizon":
                self.advance(); values["timeHorizon"] = self.expect_ident().value; self.expect(";")
            elif keyword == "tradeoff":
                self.advance(); left = self.expect_ident().value; self.expect("against"); right = self.expect_ident().value
                tradeoff = {"item": left, "against": right}
                if self.accept("weight"): tradeoff["weight"] = self.scalar()
                self.expect(";"); values.setdefault("tradeoffs", []).append(tradeoff)
            # TEMPORAL single-value members.
            elif keyword in ("start", "end"):
                key = "startValue" if keyword == "start" else "endValue"
                self.advance(); values[key] = self.scalar(); self.expect(";")
            elif keyword == "duration":
                self.advance(); amount = self.scalar(); unit = self.expect_ident().value
                values["durationValue"] = {"value": amount, "unit": unit}; self.expect(";")
            elif keyword == "recurrence":
                self.advance(); values["recurrence"] = self.scalar(); self.expect(";")
            elif keyword == "calendar":
                self.advance(); values["calendarRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "timezone":
                self.advance(); values["timezone"] = self.scalar(); self.expect(";")
            # SPATIAL single-value members.
            elif keyword == "contained-in":
                self.advance(); values["containedIn"] = self.expect_ident().value; self.expect(";")
            # RFC-8 specialization: `specializes <concept>;` — the parent this concept refines.
            elif keyword == "specializes":
                self.advance(); values["specializes"] = self.expect_ident().value; self.expect(";")
            elif keyword == "geometry":
                self.advance(); gkind = self.expect_ident().value; self.expect("[")
                coords = []
                while self.current.value != "]":
                    point = [self.scalar(), self.scalar()]
                    if self.current.kind == "NUMBER": point.append(self.scalar())
                    coords.append(point)
                    self.accept(",")
                self.expect("]"); self.expect(";")
                values["geometry"] = {"geometryKind": gkind, "coordinates": coords}
            # RESOURCE numeric capacity (+unit) vs SPATIAL capacity reference(s),
            # disambiguated by whether the value is a number or a semantic-ref.
            elif keyword == "capacity":
                self.advance()
                if self.current.kind == "NUMBER":
                    values["capacity"] = self.scalar()
                    if self.current.kind == "IDENT": values["capacityUnit"] = self.advance().value
                else:
                    values.setdefault("spatialCapacities", []).append(self.expect_ident().value)
                self.expect(";")
            elif keyword == "consumption":
                self.advance(); values["consumption"] = self.expect_ident().value; self.expect(";")
            elif keyword == "location":
                self.advance(); values["locationRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "owner":
                self.advance(); values["ownerRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "allocation-policy":
                self.advance(); values["allocationPolicy"] = self.expect_ident().value; self.expect(";")
            elif keyword == "reservation-policy":
                self.advance(); values["reservationPolicy"] = self.expect_ident().value; self.expect(";")
            elif keyword == "replenishment":
                self.advance(); values["replenishmentRef"] = self.expect_ident().value; self.expect(";")
            elif keyword == "cost":
                self.advance(); values["costRef"] = self.expect_ident().value; self.expect(";")
            else:
                key = self.expect_ident().value
                values["metadata"][key] = self.scalar()
                self.expect(";")
        end = self.expect("}")
        return Declaration("concept", name, values, self.span(start, end))

    def parse_process(self) -> Declaration:
        """A top-level WORK-dimension process-def (BPMN choreography): start/end/
        intermediate events, steps, gateways, calls, flows, boundary events, lanes."""
        start = self.expect("process")
        name = self.expect_ident().value
        values: dict[str, Any] = {"nodes": [], "flows": [], "boundaries": [], "lanes": []}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "start":
                self.advance(); node = {"type": "start", "id": self.expect_ident().value}
                if self.accept("triggered-by"): node["triggeredBy"] = self.expect_ident().value
                self.expect(";"); values["nodes"].append(node)
            elif k == "end":
                self.advance(); node = {"type": "end", "id": self.expect_ident().value}
                if self.accept("outcome"): node["outcome"] = self.expect_ident().value
                self.expect(";"); values["nodes"].append(node)
            elif k == "event":
                self.advance(); nid = self.expect_ident().value; self.expect("uses")
                node = {"type": "intermediate", "id": nid, "uses": self.expect_ident().value}
                self.expect(";"); values["nodes"].append(node)
            elif k == "step":
                self.advance(); nid = self.expect_ident().value; self.expect(":")
                node = {"type": "step", "id": nid, "activity": self.expect_ident().value}
                if self.accept("in"): node["lane"] = self.expect_ident().value
                self.expect(";"); values["nodes"].append(node)
            elif k == "gateway":
                self.advance(); nid = self.expect_ident().value; self.expect(":")
                node = {"type": "gateway", "id": nid, "gatewayKind": self.expect_ident().value}
                self.expect(";"); values["nodes"].append(node)
            elif k == "call":
                self.advance(); nid = self.expect_ident().value; self.expect(":")
                node = {"type": "call", "id": nid, "activity": self.expect_ident().value}
                self.expect(";"); values["nodes"].append(node)
            elif k == "flow":
                self.advance(); source = self.expect_ident().value; self.expect("->")
                flow = {"from": source, "to": self.expect_ident().value}
                if self.accept("when"): flow["when"] = self.scalar()
                if self.accept("priority"): flow["priority"] = self.scalar()
                self.expect(";"); values["flows"].append(flow)
            elif k == "boundary":
                self.advance(); nid = self.expect_ident().value; self.expect("on")
                on = self.expect_ident().value; self.expect("uses")
                boundary = {"id": nid, "on": on, "uses": self.expect_ident().value}
                self.expect(";"); values["boundaries"].append(boundary)
            elif k == "lane":
                self.advance(); lid = self.expect_ident().value
                lane = {"id": lid, "contains": []}
                self.expect("{")
                while self.current.value != "}":
                    lk = self.current.value
                    if lk == "performer":
                        self.advance(); lane["performer"] = self.expect_ident().value; self.expect(";")
                    elif lk == "contains":
                        self.advance(); lane["contains"].append(self.expect_ident().value); self.expect(";")
                    else:
                        raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported lane member {lk!r}")
                self.expect("}"); values["lanes"].append(lane)
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported process member {k!r}")
        end = self.expect("}")
        return Declaration("process", name, values, self.span(start, end))

    def parse_profile(self, section: str) -> Declaration:
        """A top-level operational/emitter profile block (integration/security/lineage/
        architecture/experience/design/analytics/ai). Elements project into
        ir[<section>][<collection>]; references resolve by local id."""
        start = self.expect(section)
        spec = _PROFILE_SPEC[section]
        collections: dict[str, list] = {}
        self.expect("{")
        while self.current.value != "}":
            elem = self.current.value
            special = self._parse_profile_special(section, elem)
            if special is not None:
                coll, item = special
                collections.setdefault(coll, []).append(item)
                continue
            if elem not in spec:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported {section} element {elem!r}")
            collection, fields = spec[elem]
            self.advance()
            item: dict[str, Any] = {"id": self.expect_ident().value}
            self.expect("{")
            while self.current.value != "}":
                fk = self.current.value
                if fk in fields:
                    ir_key, is_list = fields[fk]
                    self.advance(); value = self.scalar()
                    if is_list:
                        item.setdefault(ir_key, []).append(value)
                    else:
                        item[ir_key] = value
                    self.expect(";")
                elif self.parse_knowledge_metadata(item):
                    continue
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported {section}.{elem} member {fk!r}")
            self.expect("}")
            collections.setdefault(collection, []).append(item)
        end = self.expect("}")
        return Declaration("profile", section, {"section": section, "collections": collections}, self.span(start, end))

    def _parse_profile_special(self, section: str, elem: str):
        """Nested / arrow profile elements the flat spec can't express. Returns
        (collection, item) or None. Mirrors the profile grammars' sub-structures."""
        if section == "integration" and elem == "mapping":
            self.advance(); item = {"id": self.expect_ident().value, "fieldMaps": []}
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k in ("from", "to"):
                    self.advance(); item[k] = self.expect_ident().value; self.expect(";")
                elif k == "map":
                    self.advance(); fm = {"from": self.expect_ident().value}
                    self.expect("->"); fm["to"] = self.expect_ident().value
                    if self.accept("using"): fm["using"] = self.expect_ident().value
                    self.expect(";"); item["fieldMaps"].append(fm)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported mapping member {k!r}")
            self.expect("}"); return ("mappings", item)
        if section == "integration" and elem == "error-policy":
            self.advance(); item = {"id": self.expect_ident().value, "handlers": []}
            self.expect("{")
            while self.current.value != "}":
                if self.current.value == "on":
                    self.advance(); handler = {"on": self.expect_ident().value}
                    self.expect("->"); handler["target"] = self.expect_ident().value; self.expect(";")
                    item["handlers"].append(handler)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported error-policy member {self.current.value!r}")
            self.expect("}"); return ("errorPolicies", item)
        if section == "architecture" and elem == "topology":
            self.advance(); item = {"id": self.expect_ident().value, "nodes": [], "edges": []}
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k == "node":
                    self.advance(); node = {"id": self.expect_ident().value, "hosts": []}
                    self.expect("{")
                    while self.current.value != "}":
                        nk = self.current.value
                        if nk == "hosts":
                            self.advance(); node["hosts"].append(self.expect_ident().value); self.expect(";")
                        elif nk == "environment":
                            self.advance(); node["environment"] = self.expect_ident().value; self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported node member {nk!r}")
                    self.expect("}"); item["nodes"].append(node)
                elif k == "connect":
                    self.advance(); edge = {"from": self.expect_ident().value}
                    self.expect("->"); edge["to"] = self.expect_ident().value
                    if self.accept("via"): edge["via"] = self.expect_ident().value
                    self.expect(";"); item["edges"].append(edge)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported topology member {k!r}")
            self.expect("}"); return ("topologies", item)
        if section == "experience" and elem == "flow":
            self.advance(); item = {"id": self.expect_ident().value, "nodes": [], "edges": []}
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k == "entry":
                    self.advance(); item["entry"] = self.expect_ident().value; self.expect(";")
                elif k == "node":
                    self.advance(); nid = self.expect_ident().value; self.expect(":")
                    item["nodes"].append({"id": nid, "ref": self.expect_ident().value}); self.expect(";")
                elif k == "transition":
                    self.advance(); edge = {"from": self.expect_ident().value}
                    self.expect("->"); edge["to"] = self.expect_ident().value
                    if self.accept("when"): edge["when"] = self.scalar()
                    self.expect(";"); item["edges"].append(edge)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported flow member {k!r}")
            self.expect("}"); return ("flows", item)
        if section == "experience" and elem == "bind":
            self.advance(); item = {"source": self.expect_ident().value}
            self.expect("to"); item["target"] = self.expect_ident().value
            if self.accept("mode"): item["mode"] = self.expect_ident().value
            self.expect(";"); return ("bindings", item)
        if section == "design" and elem == "design-system":
            self.advance(); item = {"id": self.expect_ident().value, "tokens": [], "breakpoints": [], "patterns": []}
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k == "token":
                    self.advance(); tid = self.expect_ident().value; self.expect(":")
                    tkind = self.expect_ident().value; self.expect("=")
                    item["tokens"].append({"id": tid, "tokenKind": tkind, "value": self.scalar()}); self.expect(";")
                elif k == "breakpoint":
                    self.advance(); bid = self.expect_ident().value; self.expect(":")
                    bp = {"id": bid, "value": self.scalar()}
                    if self.current.kind == "IDENT": bp["unit"] = self.advance().value
                    self.expect(";"); item["breakpoints"].append(bp)
                elif k == "pattern":
                    self.advance(); pattern = {"id": self.expect_ident().value, "constraints": []}
                    self.expect("{")
                    while self.current.value != "}":
                        if self.current.value == "constraint":
                            self.advance(); pattern["constraints"].append(self.expect_ident().value); self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported pattern member {self.current.value!r}")
                    self.expect("}"); item["patterns"].append(pattern)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported design-system member {k!r}")
            self.expect("}"); return ("systems", item)
        if section == "analytics" and elem in ("report", "dashboard"):
            self.advance(); item = {"id": self.expect_ident().value, "visuals": []}
            if elem == "dashboard": item["filters"] = []; item["actions"] = []
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k in ("layer", "output"):
                    self.advance(); item[k] = self.expect_ident().value; self.expect(";")
                elif k == "filter":
                    self.advance(); item["filters"].append(self.expect_ident().value); self.expect(";")
                elif k == "action":
                    self.advance(); item["actions"].append(self.expect_ident().value); self.expect(";")
                elif k == "visual":
                    self.advance(); vis = {"id": self.expect_ident().value, "fields": []}
                    self.expect("{")
                    while self.current.value != "}":
                        vk = self.current.value
                        if vk == "kind":
                            self.advance(); vis["kind"] = self.scalar(); self.expect(";")
                        elif vk == "field":
                            self.advance(); vis["fields"].append(self.expect_ident().value); self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported visual member {vk!r}")
                    self.expect("}"); item["visuals"].append(vis)
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported {elem} member {k!r}")
            self.expect("}"); return ("reports" if elem == "report" else "dashboards", item)
        if section == "ai" and elem == "features":
            self.advance(); item = {"id": self.expect_ident().value, "features": []}
            self.expect("{")
            while self.current.value != "}":
                k = self.current.value
                if k == "feature":
                    self.advance(); fid = self.expect_ident().value; self.expect(":")
                    feat = {"id": fid, "ref": self.expect_ident().value}
                    if self.accept("lineage"): feat["lineage"] = self.expect_ident().value
                    self.expect(";"); item["features"].append(feat)
                elif k == "target":
                    self.advance(); item["target"] = self.expect_ident().value; self.expect(";")
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported features member {k!r}")
            self.expect("}"); return ("featureSchemas", item)
        if section == "ai" and elem == "pipeline":
            self.advance(); item = {"id": self.expect_ident().value, "steps": []}
            self.expect("{")
            while self.current.value != "}":
                if self.current.value == "step":
                    self.advance(); idx = self.scalar(); self.expect(":")
                    item["steps"].append({"index": idx, "ref": self.expect_ident().value}); self.expect(";")
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported pipeline member {self.current.value!r}")
            self.expect("}"); return ("pipelines", item)
        if section == "security" and elem == "security-map":
            self.advance(); item = {"source": self.expect_ident().value}
            self.expect("->"); item["target"] = self.expect_ident().value
            if self.accept("coverage"): item["coverage"] = self.scalar()
            self.expect(";"); return ("securityMappings", item)
        if section == "lineage" and elem == "field-lineage":
            self.advance(); item = {"from": self.expect_ident().value}
            self.expect("->"); item["to"] = self.expect_ident().value
            if self.accept("using"): item["using"] = self.expect_ident().value
            self.expect(";"); return ("fieldLineage", item)
        return None

    def parse_allocation(self) -> Declaration:
        """A top-level RESOURCE-dimension allocation-def."""
        start = self.expect("allocation")
        name = self.expect_ident().value
        values: dict[str, Any] = {}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k in ("resource", "consumer", "reservation"):
                self.advance(); values[k] = self.expect_ident().value; self.expect(";")
            elif k == "quantity":
                self.advance(); values["quantity"] = self.scalar(); self.expect(";")
            elif self.parse_knowledge_metadata(values):  # temporal-validity (valid-from/to)
                continue
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported allocation member {k!r}")
        end = self.expect("}")
        return Declaration("allocation", name, values, self.span(start, end))

    def parse_calendar(self) -> Declaration:
        """A top-level TEMPORAL-dimension calendar-def."""
        start = self.expect("calendar")
        name = self.expect_ident().value
        values: dict[str, Any] = {"workingDays": [], "holidays": []}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "timezone":
                self.advance(); values["timezone"] = self.scalar(); self.expect(";")
            elif k == "working-day":
                self.advance(); values["workingDays"].append(self.expect_ident().value); self.expect(";")
            elif k == "holiday":
                self.advance(); values["holidays"].append(self.scalar()); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported calendar member {k!r}")
        end = self.expect("}")
        return Declaration("calendar", name, values, self.span(start, end))

    def parse_route(self) -> Declaration:
        """A top-level SPATIAL-dimension route-def."""
        start = self.expect("route")
        name = self.expect_ident().value
        values: dict[str, Any] = {"via": [], "constraints": []}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k in ("from", "to"):
                self.advance(); values[k] = self.expect_ident().value; self.expect(";")
            elif k == "via":
                self.advance(); values["via"].append(self.expect_ident().value); self.expect(";")
            elif k == "distance":
                self.advance(); amount = self.scalar(); unit = self.expect_ident().value
                values["distance"] = {"value": amount, "unit": unit}; self.expect(";")
            elif k == "constraint":
                self.advance(); values["constraints"].append(self.expect_ident().value); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported route member {k!r}")
        end = self.expect("}")
        return Declaration("route", name, values, self.span(start, end))

    def parse_proposition(self) -> Declaration:
        """A top-level LOGIC-dimension proposition-def."""
        start = self.expect("proposition")
        name = self.expect_ident().value
        values: dict[str, Any] = {}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "expression":
                self.advance(); values["expression"] = self.scalar(); self.expect(";")
            elif k == "mode":
                self.advance(); values["mode"] = self.expect_ident().value; self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported proposition member {k!r}")
        end = self.expect("}")
        return Declaration("proposition", name, values, self.span(start, end))

    def parse_predicate(self) -> Declaration:
        """A top-level LOGIC-dimension predicate-def. Params may be given as a
        parenthesised list `predicate P (x: T) { ... }` or via `param` body lines."""
        start = self.expect("predicate")
        name = self.expect_ident().value
        values: dict[str, Any] = {"parameters": self._maybe_paren_params()}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "param":
                self.advance(); pname = self.expect_ident().value; self.expect(":")
                values["parameters"].append({"name": pname, "type": self.expect_ident().value}); self.expect(";")
            elif k == "expression":
                self.advance(); values["expression"] = self.scalar(); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported predicate member {k!r}")
        end = self.expect("}")
        return Declaration("predicate", name, values, self.span(start, end))

    def _maybe_paren_params(self) -> list:
        """Optional parenthesised parameter list `( name: type, ... )` (LOGIC/MATH)."""
        params: list = []
        if self.accept("("):
            while self.current.value != ")":
                pname = self.expect_ident().value; self.expect(":")
                params.append({"name": pname, "type": self.expect_ident().value})
                if not self.accept(","):
                    break
            self.expect(")")
        return params

    def _math_value(self):
        """A quoted string stays a string; anything else parses into a math-expression
        AST (additive/multiplicative/power/unary/primary)."""
        if self.current.kind == "STRING":
            return self.scalar()
        return self._math_additive()

    def _math_additive(self):
        node = self._math_multiplicative()
        while self.current.value in ("+", "-"):
            op = self.advance().value
            node = {"op": op, "left": node, "right": self._math_multiplicative()}
        return node

    def _math_multiplicative(self):
        node = self._math_power()
        while self.current.value in ("*", "/"):
            op = self.advance().value
            node = {"op": op, "left": node, "right": self._math_power()}
        return node

    def _math_power(self):
        node = self._math_unary()
        if self.current.value == "^":
            self.advance()
            node = {"op": "^", "left": node, "right": self._math_power()}
        return node

    def _math_unary(self):
        if self.current.value in ("+", "-"):
            op = self.advance().value
            return {"op": "u" + op, "operand": self._math_primary()}
        return self._math_primary()

    def _math_primary(self):
        if self.accept("("):
            node = self._math_additive(); self.expect(")"); return node
        token = self.current
        if token.kind == "NUMBER":
            self.advance()
            return {"num": float(token.value) if "." in token.value else int(token.value)}
        return {"ref": self.expect_ident().value}

    def parse_math(self) -> Declaration:
        """A top-level MATH-dimension def (formula/function/optimize/distribution/
        simulation). Expressions parse into an AST (or stay a string when quoted);
        params use either a parenthesised list or a `param` body form."""
        start = self.advance()
        values: dict[str, Any] = {"mathKind": start.value}
        name = self.expect_ident().value
        params = self._maybe_paren_params()
        if params:
            values["parameters"] = params
        if self.accept("->"):  # function return type
            values["returns"] = self.expect_ident().value
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k in ("result", "returns", "family", "model"):
                self.advance(); values[k] = self.expect_ident().value; self.expect(";")
            elif k == "expression":
                self.advance(); values["expression"] = self._math_value(); self.expect(";")
            elif k == "param":
                self.advance(); pname = self.expect_ident().value; self.expect(":")
                values.setdefault("parameters", []).append({"name": pname, "type": self.expect_ident().value}); self.expect(";")
            elif k == "objective":
                self.advance(); direction = self.expect_ident().value
                values["objective"] = {"direction": direction, "expression": self._math_value()}; self.expect(";")
            elif k == "variable":
                self.advance(); values.setdefault("variables", []).append(self.expect_ident().value); self.expect(";")
            elif k == "constraint":
                self.advance(); values.setdefault("constraints", []).append(self.scalar()); self.expect(";")
            elif k in ("trials", "seed"):
                self.advance(); values[k] = self.scalar(); self.expect(";")
            else:
                key = self.expect_ident().value; values.setdefault("qualifiers", {})[key] = self.scalar(); self.expect(";")
        end = self.expect("}")
        return Declaration("math", name, values, self.span(start, end))

    def parse_authority(self) -> Declaration:
        """A top-level ACTOR-dimension authority-def (an authority grant)."""
        start = self.expect("authority")
        name = self.expect_ident().value
        values: dict[str, Any] = {"when": []}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "mode":
                self.advance(); values["mode"] = self.expect_ident().value; self.expect(";")
            elif k == "subject":
                self.advance(); values["subject"] = self.expect_ident().value; self.expect(";")
            elif k == "target":
                self.advance(); values["target"] = self.expect_ident().value; self.expect(";")
            elif k == "when":
                self.advance(); values["when"].append(self.scalar()); self.expect(";")
            elif self.parse_knowledge_metadata(values):  # temporal-validity (valid-from/valid-to)
                continue
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported authority member {k!r}")
        end = self.expect("}")
        return Declaration("authority", name, values, self.span(start, end))

    def parse_unit(self) -> Declaration:
        """A top-level MEASURE-dimension unit-def."""
        start = self.expect("unit")
        name = self.expect_ident().value
        values: dict[str, Any] = {}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "dimension":
                self.advance(); values["dimension"] = self.expect_ident().value; self.expect(";")
            elif k == "symbol":
                self.advance(); values["symbol"] = self.scalar(); self.expect(";")
            elif k == "base":
                self.advance(); values["base"] = self.expect_ident().value; self.expect(";")
            elif k == "factor":
                self.advance(); values["factor"] = self.scalar(); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported unit member {k!r}")
        end = self.expect("}")
        return Declaration("unit", name, values, self.span(start, end))

    def parse_entity_mutation(self) -> dict:
        """An entity-embedded mutation (ENTITY dimension mutation-def). The subject is
        the enclosing entity; the normalizer projects it into ir["mutations"]."""
        self.expect("mutation")
        m: dict[str, Any] = {"name": self.expect_ident().value, "changes": [], "mutates": [],
                             "preconditions": [], "postconditions": [], "emits": []}
        self.expect("{")
        while self.current.value != "}":
            k = self.current.value
            if k == "operation":
                self.advance(); m["operation"] = self.expect_ident().value; self.expect(";")
            elif k == "scope":
                self.advance(); m["scope"] = self.expect_ident().value; self.expect(";")
            elif k == "selection":
                self.advance(); m["selection"] = self.expect_ident().value; self.expect(";")
            elif k == "change":
                self.advance(); field = self.expect_ident().value
                change = {"kind": "change", "target": field}
                if self.accept("from"):
                    change["from"] = self.scalar(); self.expect("to"); change["to"] = self.scalar()
                self.expect(";"); m["changes"].append(change); m["mutates"].append(field)
            elif k in ("add-member", "remove-member"):
                self.advance(); field = self.expect_ident().value; self.expect(";")
                m["changes"].append({"kind": k, "target": field}); m["mutates"].append(field)
            elif k == "archive":
                self.advance()
                target = self.expect_ident().value if self.current.kind == "IDENT" else None
                self.expect(";"); m["changes"].append({"kind": "archive", **({"target": target} if target else {})})
            elif k == "precondition":
                self.advance(); m["preconditions"].append(self.scalar()); self.expect(";")
            elif k == "postcondition":
                self.advance(); m["postconditions"].append(self.scalar()); self.expect(";")
            elif k == "emit":
                self.advance(); m["emits"].append(self.expect_ident().value); self.expect(";")
            elif k == "atomicity":
                self.advance(); m["atomicity"] = self.expect_ident().value; self.expect(";")
            elif k == "concurrency":
                self.advance(); m["concurrency"] = self.expect_ident().value; self.expect(";")
            elif k == "version-field":
                self.advance(); m["versionField"] = self.expect_ident().value; self.expect(";")
            elif k == "idempotency":
                self.advance(); m["idempotency"] = self.expect_ident().value; self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported mutation member {k!r}")
        self.expect("}")
        return m

    def parse_skill(self) -> Declaration:
        start = self.expect("skill")
        name = self.expect_ident().value
        values: dict[str, Any] = {}
        self.expect("{")
        while self.current.value != "}":
            key = self.current.value
            if key == "requires":
                self.advance(); values.setdefault("requires", []).append(self.expect_ident().value); self.expect(";")
            elif key == "level":
                self.advance(); values["level"] = self.scalar(); self.expect(";")
            elif key == "constraint":
                self.advance(); values.setdefault("constraints", []).append(self.expect_ident().value); self.expect(";")
            else:
                k = self.expect_ident().value; values[k] = self.scalar(); self.expect(";")
        end = self.expect("}")
        return Declaration("skill", name, values, self.span(start, end))

    def parse_capability(self) -> Declaration:
        start = self.expect("capability")
        name = self.expect_ident().value
        values: dict[str, Any] = {}
        self.expect("{")
        while self.current.value != "}":
            key = self.current.value
            if key == "requires-skill":
                self.advance(); values.setdefault("requiresSkill", []).append(self.expect_ident().value); self.expect(";")
            elif key == "outcome":
                self.advance(); values.setdefault("outcome", []).append(self.expect_ident().value); self.expect(";")
            elif key == "implemented-by":
                self.advance(); values["implementedBy"] = self.expect_ident().value; self.expect(";")
            else:
                k = self.expect_ident().value; values[k] = self.scalar(); self.expect(";")
        end = self.expect("}")
        return Declaration("capability", name, values, self.span(start, end))

    def parse_knowledge_metadata(self, values: dict[str, Any]) -> bool:
        key_map = {
            "valid-from": "validFrom", "valid-to": "validTo",
            "recorded-at": "recordedAt", "source-document": "sourceDocument",
            "source-location": "sourceLocation", "extraction-method": "extractionMethod",
            "extraction-model": "extractionModel", "reviewed-by": "reviewedBy",
            "classification": "classification", "access-policy": "accessPolicy",
        }
        key = self.current.value
        if key == "evidence":
            self.advance(); values.setdefault("evidence", []).append(self.scalar()); self.expect(";")
            return True
        if key == "confidence":
            self.advance(); values["confidence"] = self.scalar(); self.expect(";")
            return True
        if key in key_map:
            self.advance(); values[key_map[key]] = self.scalar(); self.expect(";")
            return True
        return False

    def parse_organization(self) -> Declaration:
        start = self.expect("organization")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {
            "members": [], "roles": [], "authorityDomains": [], "owns": [],
            "accountableFor": [], "reporting": [], "escalations": [], "evidence": [],
        }
        list_keys = {
            "member": "members", "role": "roles", "authority-domain": "authorityDomains",
            "owns": "owns", "accountable-for": "accountableFor",
        }
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            if key == "kind":
                self.advance(); values["organizationKind"] = self.expect_ident().value.upper(); self.expect(";")
            elif key == "parent":
                self.advance(); values["parent"] = self.expect_ident().value; self.expect(";")
            elif key in list_keys:
                self.advance(); values[list_keys[key]].append(self.expect_ident().value); self.expect(";")
            elif key == "reports":
                self.advance()
                item = {"source": self.expect_ident().value}
                self.expect("to"); item["target"] = self.expect_ident().value
                if self.accept("valid-from"):
                    item["validFrom"] = self.scalar()
                    if self.accept("valid-to"): item["validTo"] = self.scalar()
                self.expect(";"); values["reporting"].append(item)
            elif key == "escalation":
                self.advance(); self.expect("[")
                path = [self.expect_ident().value]
                while self.accept("->"): path.append(self.expect_ident().value)
                self.expect("]"); self.expect(";"); values["escalations"].append(path)
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported organization member {key!r}")
        end = self.expect("}")
        return Declaration("organization", name, values, self.span(start, end))

    def parse_information(self) -> Declaration:
        start = self.expect("information")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"subjects": [], "authors": [], "sources": [], "audiences": [], "evidence": []}
        list_keys = {"subject": "subjects", "author": "authors", "source": "sources", "audience": "audiences"}
        key_map = {"kind": "informationKind", "schema": "schema", "representation": "representation",
                   "confidentiality": "confidentiality", "freshness": "freshness", "completeness": "completeness",
                   "trust": "trust"}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            if key in list_keys:
                self.advance(); values[list_keys[key]].append(self.scalar()); self.expect(";")
            elif key == "field":
                # Nested schema field-def: `field <name>: <type> [cardinality];`
                self.advance(); fname = self.expect_ident().value; self.expect(":")
                field = {"name": fname, "type": self.expect_ident().value}
                if self.current.kind == "IDENT" and self.current.value != ";":
                    field["cardinality"] = self.advance().value
                self.expect(";"); values.setdefault("schemaFields", []).append(field)
            elif key in key_map:
                self.advance(); values[key_map[key]] = self.scalar(); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported information member {key!r}")
        end = self.expect("}")
        if "informationKind" in values: values["informationKind"] = str(values["informationKind"]).upper()
        return Declaration("information", name, values, self.span(start, end))

    def parse_rule(self) -> Declaration:
        start = self.expect("rule")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"appliesTo": [], "effects": [], "exceptions": [], "evidence": []}
        list_keys = {"applies-to": "appliesTo", "effect": "effects", "exception": "exceptions", "evidence": "evidence"}
        key_map = {"kind": "ruleKind", "condition": "condition", "mode": "mode", "priority": "priority",
                   "conflict": "conflict", "authority": "authority"}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            if key in list_keys:
                self.advance(); values[list_keys[key]].append(self.scalar()); self.expect(";")
            elif key == "predicate":
                # RFC-1 typed predicate: `predicate <field>;` (boolean field) OR
                # `predicate <left> <op> <right>;` (typed comparison/logical). Projects onto `predicate`.
                self.advance()
                toks = []
                while self.current.value != ";":
                    toks.append(self.scalar())
                if len(toks) == 1:
                    values["predicate"] = {"field": toks[0]}
                elif len(toks) == 3:
                    values["predicate"] = {"left": toks[0], "operator": toks[1], "right": toks[2]}
                else:
                    raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: "
                                     f"predicate must be `<field>` or `<left> <op> <right>`")
                self.expect(";")
            elif key in key_map:
                self.advance(); values[key_map[key]] = self.scalar(); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported rule member {key!r}")
        end = self.expect("}")
        if "ruleKind" in values: values["ruleKind"] = str(values["ruleKind"]).upper()
        if "mode" in values: values["mode"] = str(values["mode"]).upper()
        return Declaration("rule", name, values, self.span(start, end))

    def parse_policy(self) -> Declaration:
        start = self.expect("policy")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"rules": [], "evidence": []}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            self.advance()
            value = self.scalar()
            if key == "rule": values["rules"].append(value)
            elif key == "authority": values["authority"] = value
            elif key == "default-conflict": values["defaultConflict"] = value
            else: raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported policy member {key!r}")
            self.expect(";")
        end = self.expect("}")
        return Declaration("policy", name, values, self.span(start, end))

    def parse_reasoning(self) -> Declaration:
        start = self.expect("reasoning")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"premises": [], "evidence": [], "assumptions": [], "contradictions": [], "alternatives": []}
        list_keys = {"premise": "premises", "evidence": "evidence", "assumption": "assumptions",
                     "contradiction": "contradictions", "alternative": "alternatives"}
        key_map = {"kind": "reasoningKind", "proposition": "proposition", "conclusion": "conclusion",
                   "method": "method", "confidence": "confidence"}
        while self.current.value != "}":
            key = self.current.value
            if key not in {"confidence", "evidence"} and self.parse_knowledge_metadata(values):
                continue
            self.advance(); value = self.scalar()
            if key in list_keys: values[list_keys[key]].append(value)
            elif key in key_map: values[key_map[key]] = value
            else: raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported reasoning member {key!r}")
            self.expect(";")
        end = self.expect("}")
        if "reasoningKind" in values: values["reasoningKind"] = str(values["reasoningKind"]).upper()
        if "method" in values: values["method"] = str(values["method"]).upper()
        return Declaration("reasoning", name, values, self.span(start, end))

    def parse_assertion(self) -> Declaration:
        start = self.expect("assertion")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"evidence": [], "contradicts": []}
        key_map = {"subject": "subject", "predicate": "predicate", "object": "object", "object-ref": "object", "status": "status",
                   "supersedes": "supersedes", "derived-by": "derivedBy"}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            self.advance(); value = self.scalar()
            if key == "contradicts": values["contradicts"].append(value)
            elif key in key_map:
                values[key_map[key]] = value
                if key == "object-ref": values["objectIsReference"] = True
            else: raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported assertion member {key!r}")
            self.expect(";")
        end = self.expect("}")
        return Declaration("assertion", name, values, self.span(start, end))

    def parse_identity_resolution(self) -> Declaration:
        start = self.expect("identity-resolution")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {
            "aliases": [], "externalIds": [], "sameAs": [], "mergeSources": [],
            "splitTargets": [], "evidence": [],
        }
        list_keys = {"alias": "aliases", "external-id": "externalIds", "same-as": "sameAs",
                     "merge-source": "mergeSources", "split-target": "splitTargets"}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            self.advance(); value = self.scalar()
            if key in list_keys: values[list_keys[key]].append(value)
            elif key in {"canonical", "status"}: values[key] = value
            else: raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported identity member {key!r}")
            self.expect(";")
        end = self.expect("}")
        return Declaration("identity-resolution", name, values, self.span(start, end))

    def parse_knowledge_query(self) -> Declaration:
        start = self.expect("knowledge-query")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {}
        while self.current.value != "}":
            key = self.expect_ident().value
            value = self.scalar()
            values[{"select": "selectKind", "where": "where", "world": "world",
                    "negation": "negation", "inference": "inference",
                    "temporal": "temporal", "as-of": "asOf"}.get(key, key)] = value
            self.expect(";")
        end = self.expect("}")
        return Declaration("knowledge-query", name, values, self.span(start, end))

    def parse_relationship(self) -> Declaration:
        start = self.expect("relationship")
        name = self.expect_ident().value
        self.expect(":")
        root_kind = self.expect_ident().value.upper()
        source = self.expect_ident().value
        self.expect("->")
        target = self.expect_ident().value
        values: dict[str, Any] = {"rootKind": root_kind, "source": source, "target": target}
        # strength/allow-self/validity are first-class; every other RELATIONSHIP-algebra
        # qualifier (forward/inverse/directionality/cardinality/polarity/infer/validate/
        # execute/condition/version/...) lives under the open `qualifiers` object.
        multi = {"validate": "validations", "infer": "inferences", "execute": "executions",
                 "condition": "conditions"}
        qualifiers: dict[str, Any] = {}
        while self.current.value != ";":
            key = self.expect_ident().value
            if key == "strength":
                values["strength"] = self.scalar()
            elif key in ("valid-from", "valid-to"):
                values["validFrom" if key == "valid-from" else "validTo"] = self.scalar()
            elif key in ("allow-self", "allowSelf"):
                values["allowSelf"] = self.scalar()
            elif key == "cardinality":
                first = self.expect_ident().value
                qualifiers["cardinality"] = f"{first}-to-{self.expect_ident().value}" if self.accept("to") else first
            elif key in multi:
                qualifiers.setdefault(multi[key], []).append(self.scalar())
            elif key == "predicate":
                # RFC-1 typed relationship predicate: `predicate <field>` | `predicate <l> <op> <r>`.
                # Peek for an operator to disambiguate (qualifiers are space-separated, not ;-terminated).
                left = self.scalar()
                if self.current.value in {"gt", "lt", "ge", "le", "eq", "ne", "and", "or"}:
                    op = self.expect_ident().value
                    qualifiers["predicate"] = {"left": left, "operator": op, "right": self.scalar()}
                else:
                    qualifiers["predicate"] = {"field": left}
            else:
                qualifiers[key] = self.scalar()
        if qualifiers:
            values["qualifiers"] = qualifiers
        end = self.expect(";")
        return Declaration("relationship", name, values, self.span(start, end))

    def parse_lifecycle(self) -> Declaration:
        start = self.expect("lifecycle")
        name = self.expect_ident().value
        subject = None
        if self.accept("for"):
            subject = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"subject": subject, "states": [], "initial": [], "terminal": [],
                                  "transitions": [], "governsKind": [], "invariants": [],
                                  "temporalRefs": [], "stateBodies": {}}
        while self.current.value != "}":
            keyword = self.expect_ident().value
            if keyword == "state":
                sname = self.expect_ident().value
                if sname not in values["states"]:
                    values["states"].append(sname)
                if self.accept("{"):
                    body: dict[str, Any] = {"entry": [], "exit": [], "invariant": []}
                    while self.current.value != "}":
                        bk = self.current.value
                        if bk in ("entry", "exit"):
                            self.advance(); body[bk].append(self.expect_ident().value); self.expect(";")
                        elif bk == "invariant":
                            self.advance(); body["invariant"].append(self.scalar()); self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported state member {bk!r}")
                    self.expect("}")
                    values["stateBodies"][sname] = {k: v for k, v in body.items() if v}
                else:
                    self.expect(";")
            elif keyword in {"initial", "terminal"}:
                state = self.expect_ident().value
                if state not in values["states"]:
                    values["states"].append(state)
                values[keyword].append(state)
                self.expect(";")
            elif keyword == "transition":
                source = self.expect_ident().value; self.expect("->"); target = self.expect_ident().value
                transition: dict[str, Any] = {"from": source, "to": target}
                if self.accept("using"): transition["action"] = self.expect_ident().value
                if self.accept("{"):
                    while self.current.value != "}":
                        tk = self.current.value
                        if tk in ("trigger", "requires-work", "effect"):
                            key = {"trigger": "trigger", "requires-work": "requiresWork", "effect": "effect"}[tk]
                            self.advance(); transition.setdefault(key, []).append(self.expect_ident().value); self.expect(";")
                        elif tk == "guard":
                            self.advance(); transition.setdefault("guard", []).append(self.scalar()); self.expect(";")
                        else:
                            raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported transition member {tk!r}")
                    self.expect("}")
                else:
                    self.expect(";")
                values["transitions"].append(transition)
            elif keyword == "governs-kind":
                values["governsKind"].append(self.expect_ident().value.upper()); self.expect(";")
            elif keyword == "invariant":
                values["invariants"].append(self.scalar()); self.expect(";")
            elif keyword == "temporal":
                values["temporalRefs"].append(self.expect_ident().value); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported lifecycle member {keyword!r}")
        # Drop empty accumulators so unchanged lifecycles keep their prior IR shape.
        for key in ("governsKind", "invariants", "temporalRefs", "stateBodies"):
            if not values[key]:
                del values[key]
        end = self.expect("}")
        return Declaration("lifecycle", name, values, self.span(start, end))

    def parse_action(self) -> Declaration:
        start = self.advance()
        effect = start.value
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"effect": effect, "mutations": []}
        cardinality_keys = {"input": "inputCardinality", "output": "outputCardinality"}
        # ACTION-contract conditions are multi-valued (a contract may state several
        # pre/post-conditions or failure modes).
        condition_keys = {"precondition": "preconditions", "postcondition": "postconditions",
                          "failure-mode": "failureModes"}
        # IR 1.1 executable-contract scalar fields: hyphenated authoring keyword -> camelCase IR key.
        # (Each is a single `key: value;` line, so it flows through the scalar path below.)
        contract_keys = {"expected-version": "expectedVersion", "idempotency-key": "idempotencyKey",
                         "transaction-boundary": "transactionBoundary", "compensation": "compensation",
                         "reversibility": "reversibility", "delete-behavior": "deleteBehavior",
                         "retention": "retention", "bulk-limit": "bulkLimit",
                         "bulk-ordering": "bulkOrdering", "bulk-failure": "bulkFailurePolicy",
                         "patch-dialect": "patchDialect",  # RFC-3 action I/O contract (scalar)
                         "returns": "returns", "pagination": "pagination",  # RFC-3 set/bulk shape
                         "retry-classification": "retryClassification",  # RFC-4 retry
                         "retry-backoff": "retryBackoff", "totality": "totality"}  # RFC-4 / RFC-2
        while self.current.value != "}":
            key = self.expect_ident().value
            # transaction-policy pair: `transaction <mode>, <atomicity>;`
            if key == "transaction":
                values["transactionMode"] = self.expect_ident().value
                self.expect(","); values["atomicity"] = self.expect_ident().value; self.expect(";"); continue
            # multiple input/output schema references (input/output keywords are the
            # cardinality shorthands, so refs use consumes/produces).
            if key in ("consumes", "produces"):
                dst = "inputs" if key == "consumes" else "outputs"
                values.setdefault(dst, []).append(self.expect_ident().value); self.expect(";"); continue
            # RFC-3 action I/O: `provide <field>;` accumulates the client-supplied input fields.
            if key == "provide":
                values.setdefault("provides", []).append(self.expect_ident().value); self.expect(";"); continue
            # RFC-3 action-to-action invocation: `invoke <target> { arg <f>; handles <mode>;
            # establishes <pre>; expects <shape>; bounded; }`. Projects onto `invocations`.
            if key == "invoke":
                inv: dict[str, Any] = {"target": self.expect_ident().value, "args": [], "handles": [], "establishes": []}
                self.expect("{")
                while self.current.value != "}":
                    ik = self.expect_ident().value
                    if ik == "arg":
                        inv["args"].append(self.expect_ident().value); self.expect(";")
                    elif ik == "handles":
                        inv["handles"].append(self.scalar()); self.expect(";")
                    elif ik == "establishes":
                        inv["establishes"].append(self.scalar()); self.expect(";")
                    elif ik == "expects":
                        inv["expects"] = self.scalar(); self.expect(";")
                    elif ik == "bounded":
                        inv["bounded"] = True; self.expect(";")
                    else:
                        raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unknown invoke member {ik!r}")
                self.expect("}")
                values.setdefault("invocations", []).append(inv); continue
            # RFC-2 typed field lineage: `map <source> -> <target> [via <fn>] [null <behavior>]
            # [unit <src> -> <tgt>] [lossy];` — the source/target are dotted field paths (Entity.field).
            if key == "map":
                mapping: dict[str, Any] = {"source": self.expect_ident().value}
                self.expect("->")
                mapping["target"] = self.expect_ident().value
                while self.current.value != ";":
                    clause = self.expect_ident().value
                    if clause == "via":
                        mapping["function"] = self.scalar()
                    elif clause == "null":
                        mapping["nullBehavior"] = self.expect_ident().value
                    elif clause == "unit":
                        mapping["sourceUnit"] = self.expect_ident().value
                        self.expect("->"); mapping["targetUnit"] = self.expect_ident().value
                    elif clause == "lossy":
                        mapping["lossy"] = True
                    else:
                        raise self._perr("parse.unexpected-token", self.tokens[self.index - 1],
                                         f"unknown field-mapping clause {clause!r}",
                                         expected=["via", "null", "unit", "lossy", ";"])
                values.setdefault("fieldMappings", []).append(mapping)
                self.expect(";"); continue
            value = self.scalar()
            if key == "mutate": values["mutations"].append(value)
            elif key in cardinality_keys: values[cardinality_keys[key]] = value
            elif key in condition_keys: values.setdefault(condition_keys[key], []).append(value)
            elif key in contract_keys: values[contract_keys[key]] = value
            else: values[key] = value
            self.expect(";")
        end = self.expect("}")
        return Declaration("action", name, values, self.span(start, end))

    def parse_collection(self) -> Declaration:
        start = self.expect("collection")
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"keys": [], "inputs": []}
        while self.current.value != "}":
            key = self.expect_ident().value
            value = self.scalar()
            if key == "key": values["keys"].append(value)
            elif key == "input": values["inputs"].append(value)
            elif key == "project": values.setdefault("projections", []).append(value)  # RFC-2 collection projection
            elif key == "join-key": values.setdefault("joinKeys", []).append(value)     # RFC-2 join key(s)
            elif key == "equality-key": values.setdefault("equalityKeys", []).append(value)
            else: values[key] = value
            self.expect(";")
        end = self.expect("}")
        return Declaration("collection", name, values, self.span(start, end))


def parse(text: str, source: str = "<memory>") -> Model:
    return Parser(text, source).parse()


def parse_collect(text: str, source: str = "<memory>") -> tuple[Model, list[dict]]:
    """Parse with bounded recovery, returning (partial_model, structured_diagnostics)."""
    return Parser(text, source).parse_collect()
