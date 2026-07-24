from __future__ import annotations

import json
from typing import Any

from .ast import Declaration, Model, SourceSpan
from .lexer import Token, tokenize


CONCEPT_KINDS = {
    "entity": "ENTITY", "actor": "ACTOR", "work": "WORK", "event": "EVENT",
    "resource": "RESOURCE", "intent": "INTENT", "measure": "MEASURE",
    "temporal": "TEMPORAL", "spatial": "SPATIAL",
    "logic": "LOGIC", "math": "MATH",
}


class ParseError(ValueError):
    pass


class Parser:
    def __init__(self, text: str, source: str = "<memory>"):
        self.tokens = tokenize(text)
        self.index = 0
        self.source = source

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def accept(self, value: str) -> Token | None:
        if self.current.value == value:
            return self.advance()
        return None

    def expect(self, value: str) -> Token:
        token = self.current
        if token.value != value:
            raise ParseError(f"{self.source}:{token.line}:{token.column}: expected {value!r}, found {token.value!r}")
        return self.advance()

    def expect_ident(self) -> Token:
        token = self.current
        if token.kind != "IDENT":
            raise ParseError(f"{self.source}:{token.line}:{token.column}: expected identifier, found {token.value!r}")
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
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unclosed model")
            keyword = self.current.value
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
                raise ParseError(f"{self.source}:{token.line}:{token.column}: unsupported declaration {keyword!r}")
        end = self.expect("}")
        if self.current.kind != "EOF":
            token = self.current
            raise ParseError(f"{self.source}:{token.line}:{token.column}: unexpected trailing input {token.value!r}")
        model.span = self.span(start, end)
        return model

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
                self.expect(";")
                values["attributes"].append(attribute)
            elif keyword == "ref":
                self.advance(); values["references"].append(self.expect_ident().value); self.expect(";")
            elif keyword == "trait":
                self.advance(); values["traits"].append(self.expect_ident().value); self.expect(";")
            elif keyword == "abstract":
                self.advance(); values["abstract"] = True; self.expect(";")
            else:
                key = self.expect_ident().value
                values["metadata"][key] = self.scalar()
                self.expect(";")
        end = self.expect("}")
        return Declaration("concept", name, values, self.span(start, end))

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
                   "confidentiality": "confidentiality", "freshness": "freshness", "completeness": "completeness"}
        while self.current.value != "}":
            key = self.current.value
            if self.parse_knowledge_metadata(values):
                continue
            if key in list_keys:
                self.advance(); values[list_keys[key]].append(self.scalar()); self.expect(";")
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
        while self.current.value != ";":
            key = self.expect_ident().value
            values[key] = self.scalar()
        end = self.expect(";")
        return Declaration("relationship", name, values, self.span(start, end))

    def parse_lifecycle(self) -> Declaration:
        start = self.expect("lifecycle")
        name = self.expect_ident().value
        subject = None
        if self.accept("for"):
            subject = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"subject": subject, "states": [], "initial": [], "terminal": [], "transitions": []}
        while self.current.value != "}":
            keyword = self.expect_ident().value
            if keyword in {"state", "initial", "terminal"}:
                state = self.expect_ident().value
                if state not in values["states"]:
                    values["states"].append(state)
                if keyword == "initial": values["initial"].append(state)
                if keyword == "terminal": values["terminal"].append(state)
                self.expect(";")
            elif keyword == "transition":
                source = self.expect_ident().value; self.expect("->"); target = self.expect_ident().value
                transition = {"from": source, "to": target}
                if self.accept("using"): transition["action"] = self.expect_ident().value
                values["transitions"].append(transition); self.expect(";")
            else:
                raise ParseError(f"{self.source}:{self.current.line}:{self.current.column}: unsupported lifecycle member {keyword!r}")
        end = self.expect("}")
        return Declaration("lifecycle", name, values, self.span(start, end))

    def parse_action(self) -> Declaration:
        start = self.advance()
        effect = start.value
        name = self.expect_ident().value
        self.expect("{")
        values: dict[str, Any] = {"effect": effect, "mutations": []}
        cardinality_keys = {"input": "inputCardinality", "output": "outputCardinality"}
        while self.current.value != "}":
            key = self.expect_ident().value
            value = self.scalar()
            if key == "mutate": values["mutations"].append(value)
            elif key in cardinality_keys: values[cardinality_keys[key]] = value
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
            else: values[key] = value
            self.expect(";")
        end = self.expect("}")
        return Declaration("collection", name, values, self.span(start, end))


def parse(text: str, source: str = "<memory>") -> Model:
    return Parser(text, source).parse()
