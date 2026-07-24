from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_SCHEMA = PROJECT_ROOT / "schemas" / "model-ir-v1.schema.json"


KINDS = {
    "ENTITY", "ACTOR", "WORK", "EVENT", "LIFECYCLE", "RULE", "INFORMATION",
    "RESOURCE", "TEMPORAL", "SPATIAL", "ORGANIZATIONAL", "INTENT",
    "REASONING", "MEASURE", "LOGIC", "MATH",
}
ROOT_RELATIONSHIPS = {
    "CLASSIFICATION", "COMPOSITION", "ASSOCIATION", "IDENTITY", "PARTICIPATION",
    "DEPENDENCY", "TRANSFORMATION", "CAUSATION", "ORDERING", "GOVERNANCE",
}
COMMANDS = {
    "create", "replace", "update", "patch", "delete", "upsert", "bulk-create",
    "bulk-update", "bulk-patch", "bulk-delete", "bulk-upsert", "synchronize",
    "invoke", "emit", "allocate", "release",
}
SET_MUTATIONS = {"bulk-update", "bulk-patch", "bulk-delete", "bulk-upsert", "synchronize"}
COLLECTION_OPERATIONS = {
    "select", "project", "filter", "map", "flat-map", "distinct", "sort",
    "group", "aggregate", "join", "union", "intersect", "except", "window",
    "sample", "partition", "deduplicate",
}
ORGANIZATION_KINDS = {"ORGANIZATION", "UNIT", "DEPARTMENT", "TEAM", "POSITION"}
INFORMATION_KINDS = {"DOCUMENT", "MESSAGE", "RECORD", "MODEL", "EVIDENCE", "INSTRUCTION", "REPORT", "SEMANTIC_PACKET"}
RULE_KINDS = {"CONSTRAINT", "PERMISSION", "PROHIBITION", "OBLIGATION", "ELIGIBILITY", "CLASSIFICATION", "DERIVATION", "DECISION", "EXCEPTION"}
REASONING_KINDS = {"CLAIM", "FACT", "HYPOTHESIS", "ASSUMPTION", "INFERENCE", "EXPLANATION", "RECOMMENDATION", "CONTRADICTION"}
EPISTEMIC_STATUSES = {"asserted", "inferred", "disputed", "superseded", "retracted", "unknown"}


class Analyzer:
    def __init__(self, model: dict, validate_schema: bool = True):
        self.model = model
        self.diagnostics = []
        self.symbols = {}
        if validate_schema:
            self.check_schema()

    def check_schema(self):
        schema = json.loads(MODEL_SCHEMA.read_text(encoding="utf-8"))
        for error in sorted(Draft202012Validator(schema).iter_errors(self.model), key=lambda item: list(item.path)):
            subject = ".".join(str(part) for part in error.absolute_path) or "<model>"
            self.report("error", "stack.schema.valid", subject, error.message)

    def report(self, severity, rule_id, subject, message, related=None, correction=None):
        source_location = self.model.get("sourceMap", {}).get(subject)
        if source_location is None:
            source_location = {"format": "semantic-ir", "subject": subject}
        self.diagnostics.append({
            "severity": severity,
            "rule_id": rule_id,
            "module": self.model.get("module", "KCF"),
            "model": self.model.get("id", "<anonymous>"),
            "sourceLocation": source_location,
            "subject": subject,
            "message": message,
            "related": related or [],
            "correction": correction or f"Correct {subject!r} so it satisfies {rule_id}.",
        })

    def build_symbols(self):
        for concept in self.model.get("concepts", []):
            name = concept.get("qualifiedName") or concept.get("id")
            if not name:
                self.report("error", "kcf.concept.identity", "<concept>", "Concept has no identity.")
                continue
            if name in self.symbols:
                self.report("error", "stack.name.unique", name, "Duplicate concept identity.")
            self.symbols[name] = concept
            kind = concept.get("kind")
            if kind not in KINDS:
                self.report("error", "kcf.concept.primary-kind", name, f"Unknown or missing primary kind {kind!r}.")
            if concept.get("abstract") and concept.get("instances"):
                self.report("error", "kcf.concept.abstract", name, "Abstract concept has runtime instances.")

    def check_refs(self):
        for concept in self.model.get("concepts", []):
            name = concept.get("qualifiedName") or concept.get("id", "<concept>")
            for ref in concept.get("references", []):
                target = ref.get("target") if isinstance(ref, dict) else ref
                if target not in self.symbols:
                    self.report("error", "kcf.concept.reference", name, f"Unresolved reference {target!r}.")

    def reference_exists(self, value):
        if not isinstance(value, str):
            return False
        if value in self.symbols:
            return True
        namespace = self.model.get("namespace")
        candidates = {value, value.rsplit(".", 1)[-1]}
        if namespace and "." not in value:
            candidates.add(f"{namespace}.{value}")
        collections = (
            "actions", "lifecycles", "organizations", "information", "rules",
            "policies", "reasoning", "assertions", "identityResolutions",
        )
        for collection in collections:
            for item in self.model.get(collection, []):
                identities = {item.get("id"), item.get("qualifiedName")}
                if namespace and item.get("id"):
                    identities.add(f"{namespace}.{item['id']}")
                if candidates & identities:
                    return True
        return False

    def check_temporal_range(self, item, rule_id, subject):
        valid_from, valid_to = item.get("validFrom"), item.get("validTo")
        if valid_from and valid_to and valid_from > valid_to:
            self.report("error", rule_id, subject, "validFrom is after validTo.")

    def check_access_policy(self, item, subject):
        if (item.get("classification") or item.get("confidentiality")) and not item.get("accessPolicy"):
            self.report("error", "knowledge.access.policy", subject, "Classified or confidential knowledge has no access policy.")
        if item.get("accessPolicy") and not self.reference_exists(item["accessPolicy"]):
            self.report("error", "knowledge.access.policy", subject, "Knowledge access policy does not resolve.")

    def check_relationships(self):
        seen = set()
        for rel in self.model.get("relationships", []):
            rid = rel.get("id", "<relationship>")
            source, target = rel.get("source"), rel.get("target")
            if source not in self.symbols or target not in self.symbols:
                self.report("error", "kcf.relationship.endpoint", rid, "Relationship endpoint does not resolve.")
            root = rel.get("rootKind")
            if root not in ROOT_RELATIONSHIPS:
                self.report("error", "kcf.relationship.root-kind", rid, f"Invalid root relationship kind {root!r}.")
            key = (rel.get("definition"), source, target, tuple(sorted(rel.get("qualifiers", {}).items())))
            if key in seen:
                self.report("warning", "stack.graph.edge-unique", rid, "Duplicate equivalent relationship.")
            seen.add(key)
            if source == target and not rel.get("allowSelf"):
                self.report("error", "stack.graph.no-self-edge", rid, "Self relationship is not permitted.")
            strength = rel.get("strength")
            if strength is not None and not 0 <= strength <= 1:
                self.report("error", "kcf.relationship.strength", rid, "Strength must be in [0,1].")
            valid_from, valid_to = rel.get("validFrom"), rel.get("validTo")
            if valid_from and valid_to and valid_from > valid_to:
                self.report("error", "kcf.relationship.temporal", rid, "validFrom is after validTo.")

    def check_lifecycles(self):
        for lifecycle in self.model.get("lifecycles", []):
            lid = lifecycle.get("id", "<lifecycle>")
            states = set(lifecycle.get("states", []))
            initials = lifecycle.get("initial", [])
            terminals = set(lifecycle.get("terminal", []))
            if isinstance(initials, str):
                initials = [initials]
            if len(initials) != 1:
                self.report("error", "lifecycle.single-initial", lid, "Lifecycle requires exactly one initial state.")
            if not terminals:
                self.report("error", "lifecycle.final", lid, "Lifecycle requires at least one terminal state.")
            graph = defaultdict(set)
            for transition in lifecycle.get("transitions", []):
                source, target = transition.get("from"), transition.get("to")
                if source not in states or target not in states:
                    self.report("error", "process.transition-endpoints", lid, f"Invalid transition {source!r} -> {target!r}.")
                graph[source].add(target)
            if initials:
                reached = self.reachable(graph, initials[0])
                for state in states - reached:
                    self.report("warning", "process.reachability", f"{lid}.{state}", "State is unreachable.")
                if terminals and not (terminals & reached):
                    self.report("error", "stack.graph.reachability", lid, "No terminal state is reachable.")

    @staticmethod
    def reachable(graph, start):
        seen, queue = set(), deque([start])
        while queue:
            node = queue.popleft()
            if node in seen:
                continue
            seen.add(node)
            queue.extend(graph[node] - seen)
        return seen

    @staticmethod
    def has_cycle(graph):
        # Iterative depth-first search so deep dependency graphs cannot exceed
        # the Python recursion limit. `on_stack` is the set of nodes on the
        # current DFS path; reaching one again is a back edge, i.e. a cycle.
        visited = set()
        for root in list(graph):
            if root in visited:
                continue
            stack = [(root, iter(graph[root]))]
            on_stack = {root}
            while stack:
                node, targets = stack[-1]
                for target in targets:
                    if target in on_stack:
                        return True
                    if target not in visited:
                        stack.append((target, iter(graph[target])))
                        on_stack.add(target)
                        break
                else:
                    on_stack.discard(node)
                    visited.add(node)
                    stack.pop()
        return False

    def check_actions(self):
        for action in self.model.get("actions", []):
            aid = action.get("id", "<action>")
            required = ["effect", "operation", "scope", "target", "inputCardinality", "outputCardinality"]
            missing = [field for field in required if field not in action]
            if missing:
                self.report("error", "action.contract.incomplete", aid, "Missing: " + ", ".join(missing))
            operation = action.get("operation")
            effect = action.get("effect")
            scope = action.get("scope")
            if operation in COMMANDS and effect != "command":
                self.report("error", "action.invoke.effect-context", aid, "Mutation/invocation operation must be a command.")
            if operation in SET_MUTATIONS and scope not in {"set", "batch", "stream", "window"}:
                self.report("error", "action.set.explicit-scope", aid, "Bulk operation requires collection scope.")
            if operation in SET_MUTATIONS and not action.get("selection"):
                self.report("error", "action.set.selection-required", aid, "Set mutation requires an explicit selection.")
            if action.get("selection") == "all" and operation in SET_MUTATIONS:
                self.report("warning", "action.set.unbounded-warning", aid, "Destructive/mutating selection targets all records.")
            if effect == "command" and not action.get("idempotency"):
                self.report("error", "action.contract.incomplete", aid, "Command requires idempotency classification.")
            if action.get("retry", 0) and action.get("idempotency") == "non-idempotent":
                self.report("error", "action.retry.side-effects", aid, "Non-idempotent command cannot be retried without protection.")
            if scope in {"set", "batch", "stream", "window"} and effect == "command" and not action.get("atomicity"):
                self.report("error", "action.set.atomicity", aid, "Set command requires atomicity semantics.")
            if effect == "command" and not (action.get("authorization") or action.get("authorizationExemption")):
                self.report("error", "stack.security.authorization", aid, "Executable command has no authorization rule or explicit exemption.")

    def check_collection_transforms(self):
        for transform in self.model.get("collectionTransforms", []):
            tid = transform.get("id", "<collection-transform>")
            operation = transform.get("operation")
            if operation not in COLLECTION_OPERATIONS:
                self.report("error", "action.collection.input-schema", tid, f"Unknown collection operation {operation!r}.")
            if not transform.get("inputSchema"):
                self.report("error", "action.collection.input-schema", tid, "Collection transformation requires an input schema.")
            if not transform.get("outputSchema"):
                self.report("error", "action.collection.output-schema", tid, "Collection transformation requires an output schema.")
            if operation == "filter" and not transform.get("predicate"):
                self.report("error", "action.collection.filter-boolean", tid, "Filter requires a boolean predicate.")
            if operation in {"sort", "distinct", "group", "aggregate"} and transform.get("bounded") is False and not transform.get("window"):
                self.report("error", "action.collection.boundedness", tid, "Materializing operation on an unbounded input requires a window.")
            if operation == "group" and not transform.get("keys"):
                self.report("error", "action.collection.group-key", tid, "Group requires at least one key.")
            if operation == "aggregate" and not transform.get("grain"):
                self.report("error", "action.collection.aggregate-grain", tid, "Aggregate requires an output grain.")
            if operation == "join" and len(transform.get("inputs", [])) != 2:
                self.report("error", "action.collection.join-inputs", tid, "Join requires exactly two declared inputs.")
            if operation == "partition" and not transform.get("keys"):
                self.report("error", "action.collection.partition", tid, "Partition requires a key or explicit policy.")
            if operation == "deduplicate" and not transform.get("survivorPolicy"):
                self.report("error", "action.collection.dedup-survivor", tid, "Deduplication requires a survivor policy.")

    def check_processes(self):
        for process in self.model.get("processes", []):
            pid = process.get("id", "<process>")
            nodes = process.get("nodes", [])
            names = [node.get("id") for node in nodes]
            if len(names) != len(set(names)):
                self.report("error", "process.state-unique", pid, "Process node identities are not unique.")
            starts = [node.get("id") for node in nodes if node.get("type") == "start"]
            ends = {node.get("id") for node in nodes if node.get("type") == "end"}
            if len(starts) != 1:
                self.report("error", "process.single-initial", pid, "Process requires exactly one start node.")
            if not ends:
                self.report("error", "process.final", pid, "Process requires at least one end node.")
            known = set(names)
            graph = defaultdict(set)
            for flow in process.get("flows", []):
                source, target = flow.get("from"), flow.get("to")
                if source not in known or target not in known:
                    self.report("error", "process.transition-endpoints", pid, f"Invalid process flow {source!r} -> {target!r}.")
                graph[source].add(target)
            if starts:
                reached = self.reachable(graph, starts[0])
                for node in known - reached:
                    self.report("warning", "process.reachability", f"{pid}.{node}", "Process node is unreachable.")
                if ends and not (ends & reached):
                    self.report("error", "stack.graph.reachability", pid, "No process end node is reachable.")

    def check_integration(self):
        integration = self.model.get("integration", {})
        adapters = {item.get("id") for item in integration.get("adapters", [])}
        endpoints = {item.get("id") for item in integration.get("endpoints", [])}
        for endpoint in integration.get("endpoints", []):
            if endpoint.get("adapter") not in adapters:
                self.report("error", "integration.endpoint", endpoint.get("id", "<endpoint>"), "Endpoint adapter does not resolve locally.")
        for route in integration.get("routes", []):
            if route.get("source") not in endpoints or route.get("target") not in endpoints:
                self.report("error", "integration.endpoint", route.get("id", "<route>"), "Route endpoint does not resolve locally.")
        for policy in integration.get("retryPolicies", []):
            attempts = policy.get("attempts")
            if not isinstance(attempts, int) or attempts < 0:
                self.report("error", "stack.value.range", policy.get("id", "<retry-policy>"), "Retry attempts must be a nonnegative integer.")
            if attempts and not policy.get("requiresIdempotency"):
                self.report("error", "action.retry.side-effects", policy.get("id", "<retry-policy>"), "Retry policy must require idempotency or duplicate protection.")

    def check_security(self):
        security = self.model.get("security", {})
        assets = {item.get("id") for item in security.get("assets", [])}
        threats = {item.get("id") for item in security.get("threats", [])}
        treatments = security.get("treatments", [])
        treatments_by_risk = defaultdict(list)
        for treatment in treatments:
            treatments_by_risk[treatment.get("risk")].append(treatment)
        for risk in security.get("risks", []):
            rid = risk.get("id", "<risk>")
            if risk.get("asset") not in assets or risk.get("threat") not in threats:
                self.report("error", "security.risk.references", rid, "Risk threat or asset does not resolve locally.")
            likelihood, impact, level = risk.get("likelihood"), risk.get("impact"), risk.get("level")
            values = (likelihood, impact, level)
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
                self.report("error", "stack.value.range", rid, "Risk likelihood, impact, and level must be finite and nonnegative.")
            elif not risk.get("levelOverride") and not math.isclose(level, likelihood * impact, rel_tol=1e-9, abs_tol=1e-9):
                self.report("error", "security.risk.level", rid, "Risk level does not equal likelihood multiplied by impact.")
            if isinstance(level, (int, float)) and level >= security.get("highRiskThreshold", 0.5):
                candidates = treatments_by_risk.get(risk.get("id"), [])
                valid = any(
                    treatment.get("mode") in {"mitigate", "transfer", "avoid"}
                    or (treatment.get("mode") == "accept" and treatment.get("owner") and treatment.get("expires"))
                    for treatment in candidates
                )
                if not valid:
                    self.report("error", "security.risk.mitigation", rid, "High risk lacks a valid treatment or governed acceptance.")
        controls = {item.get("id") for item in security.get("controls", [])}
        for boundary in security.get("trustBoundaries", []):
            if boundary.get("crossings") and not (set(boundary.get("crossingControls", [])) & controls):
                self.report("error", "stack.security.boundary", boundary.get("id", "<trust-boundary>"), "Trust-boundary crossing has no applicable control.")

    def check_lineage_and_cost(self):
        lineage = self.model.get("lineage", {})
        graph = defaultdict(set)
        for edge in lineage.get("edges", []):
            graph[edge.get("source")].add(edge.get("target"))
        if self.has_cycle(graph) and not lineage.get("iterativeComputation"):
            self.report("error", "lineage.cycle", "lineage", "Lineage graph contains a cycle without an iterative-computation declaration.")
        binding_targets = defaultdict(list)
        for binding in lineage.get("bindings", []):
            binding_targets[binding.get("target")].append(binding.get("source"))
        for target, sources in binding_targets.items():
            if target and len(set(sources)) > 1:
                self.report("error", "lineage.binding.unique", target, "Single-source binding target has conflicting sources.")
        for cost in lineage.get("costs", []):
            amount = cost.get("amount")
            if not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
                self.report("error", "lineage.cost.nonnegative", cost.get("id", "<cost>"), "Cost must be finite and nonnegative.")

    def check_architecture(self):
        architecture = self.model.get("architecture", {})
        interfaces = {item.get("id") for item in architecture.get("interfaces", [])}
        nodes = {item.get("id") for topology in architecture.get("topologies", []) for item in topology.get("nodes", [])}
        for service in architecture.get("services", []):
            for interface in service.get("interfaces", []):
                if interface not in interfaces:
                    self.report("error", "architecture.reference.kind", service.get("id", "<service>"), f"Interface {interface!r} does not resolve.")
        for topology in architecture.get("topologies", []):
            local_nodes = {item.get("id") for item in topology.get("nodes", [])}
            for edge in topology.get("edges", []):
                if edge.get("from") not in local_nodes or edge.get("to") not in local_nodes:
                    self.report("error", "architecture.reference.kind", topology.get("id", "<topology>"), "Topology edge endpoint does not resolve locally.")
        for deployment in architecture.get("deployments", []):
            if deployment.get("target") not in nodes:
                self.report("error", "architecture.deployment.complete", deployment.get("id", "<deployment>"), "Deployment target does not resolve to a topology node.")

    def check_experience(self):
        experience = self.model.get("experience", {})
        views = {item.get("id") for item in experience.get("views", [])}
        actions = {item.get("id") for item in self.model.get("actions", [])}
        for app in experience.get("apps", []):
            if app.get("entry") not in views or any(view not in views for view in app.get("views", [])):
                self.report("error", "experience.app.reference", app.get("id", "<app>"), "Application entry or view does not resolve.")
        for view in experience.get("views", []):
            for action in view.get("actions", []):
                if action not in actions:
                    self.report("error", "experience.action.invoke", view.get("id", "<view>"), f"Invoked action {action!r} does not resolve.")
        for flow in experience.get("flows", []):
            nodes = {item.get("id") for item in flow.get("nodes", [])}
            if flow.get("entry") not in nodes:
                self.report("error", "experience.flow.entry", flow.get("id", "<flow>"), "Flow entry does not resolve.")
            graph = defaultdict(set)
            for edge in flow.get("edges", []):
                source, target = edge.get("from"), edge.get("to")
                if source not in nodes or target not in nodes:
                    self.report("error", "experience.flow.transition", flow.get("id", "<flow>"), "Flow transition endpoint does not resolve.")
                graph[source].add(target)
            if flow.get("entry") in nodes:
                for node in nodes - self.reachable(graph, flow.get("entry")):
                    self.report("warning", "experience.flow.reachability", f"{flow.get('id')}.{node}", "Experience-flow node is unreachable.")

    def check_design(self):
        design = self.model.get("design", {})
        for system in design.get("systems", []):
            groups = [system.get("tokens", []), system.get("breakpoints", []), system.get("patterns", [])]
            names = [item.get("id") for group in groups for item in group]
            if len(names) != len(set(names)):
                self.report("error", "design.design-system.unique", system.get("id", "<design-system>"), "Design-system names are not unique.")
            values = [item.get("value") for item in system.get("breakpoints", [])]
            if any(not isinstance(value, (int, float)) or value < 0 for value in values) or values != sorted(set(values)):
                self.report("error", "design.scale.order", system.get("id", "<design-system>"), "Breakpoints must be finite, nonnegative, unique, and strictly ordered.")
        known_views = {item.get("id") for item in self.model.get("experience", {}).get("views", [])}
        for page in design.get("pages", []):
            if page.get("view") not in known_views:
                self.report("error", "design.page.binding", page.get("id", "<page>"), "Page view binding does not resolve.")

    def check_analytics(self):
        analytics = self.model.get("analytics", {})
        layers = {item.get("id") for item in analytics.get("semanticLayers", [])}
        actions = {item.get("id") for item in self.model.get("actions", [])}
        for item in analytics.get("reports", []) + analytics.get("dashboards", []):
            if item.get("layer") not in layers:
                self.report("error", "analytics.binding.kind", item.get("id", "<analytic-output>"), "Semantic-layer binding does not resolve.")
        for dashboard in analytics.get("dashboards", []):
            for action in dashboard.get("actions", []):
                if action not in actions:
                    self.report("error", "analytics.binding.kind", dashboard.get("id", "<dashboard>"), f"Dashboard action {action!r} does not resolve.")

    def check_ai(self):
        ai = self.model.get("ai", {})
        feature_schemas = {item.get("id"): item for item in ai.get("featureSchemas", [])}
        for schema_id, schema in feature_schemas.items():
            features = [item.get("id") for item in schema.get("features", [])]
            if len(features) != len(set(features)):
                self.report("error", "ai.feature.keys", schema_id, "Feature identities are not unique.")
            if schema.get("target") and schema.get("target") not in features:
                self.report("error", "ai.feature.target", schema_id, "Target does not name a declared feature.")
        models = {item.get("id") for item in ai.get("models", [])}
        for pipeline in ai.get("pipelines", []):
            indexes = [step.get("index") for step in pipeline.get("steps", [])]
            if indexes != sorted(set(indexes)):
                self.report("error", "ai.pipeline.order", pipeline.get("id", "<pipeline>"), "Pipeline indexes must be unique and ordered.")
        for serving in ai.get("serving", []):
            if serving.get("model") not in models:
                self.report("error", "ai.serving.model", serving.get("id", "<serving>"), "Served model does not resolve.")
            capacity = serving.get("capacity")
            if capacity is not None and (not isinstance(capacity, (int, float)) or capacity <= 0):
                self.report("error", "ai.serving.capacity", serving.get("id", "<serving>"), "Serving capacity must be positive.")

    def check_organizational_knowledge(self):
        namespace = self.model.get("namespace", "")
        organizations = self.model.get("organizations", [])
        organization_ids = {f"{namespace}.{item['id']}" if namespace else item["id"] for item in organizations}
        hierarchy = defaultdict(set)
        for item in organizations:
            oid = item.get("id", "<organization>")
            qualified = f"{namespace}.{oid}" if namespace else oid
            if item.get("organizationKind") not in ORGANIZATION_KINDS:
                self.report("error", "organization.kind", oid, "Unsupported organization kind.")
            parent = item.get("parent")
            if parent:
                if parent not in organization_ids:
                    self.report("error", "organization.parent.reference", oid, "Organization parent does not resolve to an organization.")
                hierarchy[qualified].add(parent)
            for value in [
                *item.get("members", []), *item.get("roles", []), *item.get("authorityDomains", []),
                *item.get("owns", []), *item.get("accountableFor", []),
            ]:
                if not self.reference_exists(value):
                    self.report("error", "organization.member.reference", oid, f"Organizational reference {value!r} does not resolve.")
            for report in item.get("reporting", []):
                source, target = report.get("source"), report.get("target")
                resolved = [self.symbols.get(value) for value in (source, target)]
                if any(value is None or value.get("kind") not in {"ACTOR", "ORGANIZATIONAL"} for value in resolved):
                    self.report("error", "organization.reporting.reference", oid, "Reporting endpoints must resolve to Actor or Organizational concepts.")
                self.check_temporal_range(report, "organization.reporting.temporal", oid)
            for path in item.get("escalations", []):
                if len(path) < 2 or len(path) != len(set(path)) or any(not self.reference_exists(value) for value in path):
                    self.report("error", "organization.escalation.path", oid, "Escalation path is too short, repeats an endpoint, or has an unresolved endpoint.")
            self.check_access_policy(item, oid)
        if self.has_cycle(hierarchy):
            self.report("error", "organization.hierarchy.acyclic", "organizations", "Organizational parent hierarchy contains a cycle.")

        information = self.model.get("information", [])
        for item in information:
            iid = item.get("id", "<information>")
            if item.get("informationKind") not in INFORMATION_KINDS:
                self.report("error", "information.kind", iid, "Unsupported information kind.")
            references = [
                *item.get("subjects", []), *item.get("authors", []), *item.get("sources", []),
                *item.get("audiences", []), *item.get("evidence", []),
                *(item.get(key) for key in ("schema", "freshness", "reviewedBy") if item.get(key)),
            ]
            if any(not self.reference_exists(value) for value in references):
                self.report("error", "information.reference", iid, "One or more information references do not resolve.")
            self.check_temporal_range(item, "information.temporal", iid)
            if not (item.get("sources") or item.get("evidence") or item.get("sourceDocument")) or not item.get("recordedAt"):
                self.report("error", "information.provenance", iid, "Governed information requires a source/evidence/document and recording time.")
            if not item.get("recordedAt"):
                self.report("error", "knowledge.bitemporal.recorded", iid, "Governed information does not distinguish recording time from valid time.")
            extraction = any(item.get(key) is not None for key in ("extractionMethod", "extractionModel", "sourceLocation"))
            required_trace = ("sourceDocument", "sourceLocation", "extractionMethod", "extractionModel", "confidence", "recordedAt", "reviewedBy")
            if extraction and any(item.get(key) is None for key in required_trace):
                self.report("error", "knowledge.ingestion.trace", iid, "Extracted knowledge is missing complete document, location, method, model, confidence, recording, or review provenance.")
            self.check_access_policy(item, iid)

        rules = self.model.get("rules", [])
        for item in rules:
            rid = item.get("id", "<rule>")
            if item.get("ruleKind") not in RULE_KINDS or not item.get("condition") or not item.get("effects"):
                self.report("error", "rule.complete", rid, "Rule kind, condition, and effects are required.")
            references = [
                *item.get("appliesTo", []), *item.get("effects", []), *item.get("exceptions", []),
                *item.get("evidence", []), *(item.get(key) for key in ("authority", "reviewedBy") if item.get(key)),
            ]
            if any(not self.reference_exists(value) for value in references):
                self.report("error", "rule.reference", rid, "One or more rule references do not resolve.")
            self.check_access_policy(item, rid)
        by_target = defaultdict(list)
        for item in rules:
            for target in item.get("appliesTo", []):
                by_target[target].append(item)
        for target, candidates in by_target.items():
            modes = {item.get("mode") for item in candidates}
            if "PERMISSION" in modes and "PROHIBITION" in modes and any(not item.get("conflict") for item in candidates):
                self.report("error", "rule.conflict.strategy", target, "Conflicting permission/prohibition rules lack a deterministic conflict strategy.")

        for item in self.model.get("policies", []):
            pid = item.get("id", "<policy>")
            authority = self.symbols.get(item.get("authority"))
            if not authority or authority.get("kind") not in {"ACTOR", "ORGANIZATIONAL"}:
                self.report("error", "rule.policy.authority", pid, "Policy authority must resolve to an Actor or Organizational concept.")
            for rule in item.get("rules", []):
                concept = self.symbols.get(rule)
                if not concept or concept.get("kind") != "RULE":
                    self.report("error", "rule.policy.members", pid, f"Policy rule {rule!r} does not resolve to a Rule concept.")
            self.check_access_policy(item, pid)

        assertions = self.model.get("assertions", [])
        assertion_ids = {
            identity for item in assertions
            for identity in (item.get("id"), item.get("qualifiedName"), f"{namespace}.{item.get('id')}" if namespace else None)
            if identity
        }
        reasoning_ids = {
            identity for item in self.model.get("reasoning", [])
            for identity in (item.get("id"), f"{namespace}.{item.get('id')}" if namespace else None)
            if identity
        }
        for item in assertions:
            aid = item.get("qualifiedName") or item.get("id", "<assertion>")
            if not self.reference_exists(item.get("subject")):
                self.report("error", "knowledge.assertion.subject", aid, "Assertion subject does not resolve.")
            if item.get("objectIsReference") and not self.reference_exists(item.get("object")):
                self.report("error", "knowledge.assertion.subject", aid, "Assertion object reference does not resolve.")
            if item.get("status") not in EPISTEMIC_STATUSES:
                self.report("error", "knowledge.assertion.status", aid, "Assertion has no valid epistemic status.")
            if item.get("status") in {"asserted", "inferred", "disputed"}:
                if not (item.get("evidence") or item.get("sourceDocument")) or not item.get("recordedAt"):
                    self.report("error", "knowledge.assertion.provenance", aid, "Active assertion lacks evidence/source and recording time.")
                if item.get("extractionMethod") and not item.get("reviewedBy"):
                    self.report("error", "knowledge.assertion.provenance", aid, "Automatically extracted assertion lacks human review.")
            if not item.get("recordedAt"):
                self.report("error", "knowledge.bitemporal.recorded", aid, "Assertion does not distinguish recording time from valid time.")
            self.check_temporal_range(item, "knowledge.assertion.temporal", aid)
            if item.get("status") == "inferred" and item.get("derivedBy") not in reasoning_ids:
                self.report("error", "knowledge.assertion.inference", aid, "Inferred assertion has no resolvable reasoning derivation.")
            if item.get("supersedes") and (item["supersedes"] not in assertion_ids or item["supersedes"] == aid):
                self.report("error", "knowledge.assertion.supersession", aid, "Superseded assertion is missing or self-referential.")
            for target in item.get("contradicts", []):
                if target not in assertion_ids or target == aid:
                    self.report("error", "knowledge.assertion.contradiction", aid, "Contradiction target is missing or self-referential.")
            self.check_access_policy(item, aid)

        for item in self.model.get("reasoning", []):
            rid = item.get("id", "<reasoning>")
            if item.get("reasoningKind") not in REASONING_KINDS or not item.get("proposition") or not item.get("method"):
                self.report("error", "reasoning.complete", rid, "Reasoning kind, proposition, and method are required.")
            if item.get("reasoningKind") in {"FACT", "INFERENCE"} and not (item.get("premises") or item.get("evidence")):
                self.report("error", "reasoning.complete", rid, "Facts and inferences require premises or evidence.")
            references = [*item.get("premises", []), *item.get("evidence", []), *item.get("alternatives", [])]
            if any(not self.reference_exists(value) for value in references):
                self.report("error", "reasoning.reference", rid, "One or more reasoning references do not resolve.")
            confidence = item.get("confidence")
            if confidence is not None and (not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
                self.report("error", "reasoning.confidence", rid, "Reasoning confidence must be in [0,1].")
            for target in item.get("contradictions", []):
                if target not in reasoning_ids | assertion_ids or target in {rid, f"{namespace}.{rid}" if namespace else rid}:
                    self.report("error", "reasoning.contradiction", rid, "Reasoning contradiction target is missing or self-referential.")
            self.check_access_policy(item, rid)

        aliases = defaultdict(set)
        for item in self.model.get("identityResolutions", []):
            iid = item.get("id", "<identity-resolution>")
            canonical = item.get("canonical")
            if not self.reference_exists(canonical):
                self.report("error", "knowledge.identity.canonical", iid, "Canonical identity does not resolve.")
            for token in [*item.get("aliases", []), *item.get("externalIds", [])]:
                aliases[str(token)].add(canonical)
            references = [*item.get("sameAs", []), *item.get("mergeSources", []), *item.get("splitTargets", [])]
            if any(not self.reference_exists(value) for value in references):
                self.report("error", "knowledge.identity.transition", iid, "Identity transition reference does not resolve.")
            if item.get("status") == "merged" and not item.get("mergeSources"):
                self.report("error", "knowledge.identity.transition", iid, "Merged identity has no merge sources.")
            if item.get("status") == "split" and not item.get("splitTargets"):
                self.report("error", "knowledge.identity.transition", iid, "Split identity has no split targets.")
        for token, canonicals in aliases.items():
            if len(canonicals) > 1:
                self.report("error", "knowledge.identity.ambiguity", token, "Alias or external identity maps to multiple canonical concepts.")

        for item in self.model.get("knowledgeQueries", []):
            qid = item.get("id", "<knowledge-query>")
            if any(not item.get(key) for key in ("selectKind", "where", "world", "negation", "inference", "temporal")):
                self.report("error", "knowledge.query.policy", qid, "Knowledge query lacks an explicit semantic policy.")
            if item.get("negation") == "failure" and item.get("world") != "closed":
                self.report("error", "knowledge.query.negation", qid, "Negation-as-failure requires a closed-world assumption.")
            if item.get("temporal") == "as-of" and not item.get("asOf"):
                self.report("error", "knowledge.query.temporal", qid, "As-of query lacks an effective timestamp.")

    def check_events_resources_plans(self):
        for event in self.model.get("events", []):
            if event.get("mutable"):
                self.report("error", "kcf.event.immutable", event.get("id", "<event>"), "Historical event facts must be immutable.")
        capacities = {r.get("id"): r.get("capacity") for r in self.model.get("resources", [])}
        used = defaultdict(float)
        for allocation in self.model.get("allocations", []):
            resource = allocation.get("resource")
            quantity = allocation.get("quantity", 0)
            if quantity < 0:
                self.report("error", "stack.value.range", allocation.get("id", "<allocation>"), "Allocation cannot be negative.")
            used[resource] += quantity
        for resource, quantity in used.items():
            if resource in capacities and capacities[resource] is not None and quantity > capacities[resource]:
                self.report("error", "kcf.resource.capacity", resource, "Allocations exceed capacity.")
        for plan in self.model.get("plans", []):
            indexes = [step.get("index") for step in plan.get("steps", [])]
            if len(indexes) != len(set(indexes)):
                self.report("error", "stack.order.unique", plan.get("id", "<plan>"), "Plan step indexes are not unique.")
        required = set(self.model.get("runtimeRequirements", []))
        for emitter in self.model.get("emitters", []):
            missing = required - set(emitter.get("supports", []))
            if missing and emitter.get("unsupportedPolicy") == "error":
                self.report("error", "kcf.emitter.unsupported", emitter.get("id", "<emitter>"), "Unsupported semantics: " + ", ".join(sorted(missing)))

    def check_profile_patterns(self):
        required = set(self.model.get("requiredPatterns", []))
        recommended = set(self.model.get("recommendedPatterns", []))
        prohibited = set(self.model.get("prohibitedPatterns", []))
        implemented = set(self.model.get("implementedPatterns", []))
        excluded = set(self.model.get("excludedPatterns", []))
        for pattern in sorted(required - implemented):
            self.report(
                "error", "kcf.profile.pattern-required", pattern,
                f"Selected profiles require business pattern {pattern!r}, but the model does not declare it implemented.",
                correction=f"Add 'implements {pattern};' and model its obligations, or select a different profile.",
            )
        for pattern in sorted(prohibited & implemented):
            self.report(
                "error", "kcf.profile.pattern-prohibited", pattern,
                f"Selected profiles prohibit business pattern {pattern!r}, but the model declares it implemented.",
                correction=f"Remove 'implements {pattern};' or select a compatible profile.",
            )
        for pattern in sorted(required & excluded):
            self.report(
                "error", "kcf.profile.pattern-exclusion", pattern,
                f"Required business pattern {pattern!r} cannot be excluded.",
                correction=f"Remove 'excludes {pattern};' or select a profile that does not require it.",
            )
        for pattern in sorted((excluded - recommended) - prohibited):
            self.report(
                "warning", "kcf.profile.pattern-exclusion", pattern,
                f"Pattern {pattern!r} is excluded without being recommended or prohibited by a selected profile.",
                correction="Remove the exclusion or document it in a custom profile.",
            )

    def run(self):
        self.build_symbols()
        self.check_refs()
        self.check_relationships()
        self.check_lifecycles()
        self.check_actions()
        self.check_collection_transforms()
        self.check_processes()
        self.check_integration()
        self.check_security()
        self.check_lineage_and_cost()
        self.check_architecture()
        self.check_experience()
        self.check_design()
        self.check_analytics()
        self.check_ai()
        self.check_organizational_knowledge()
        self.check_events_resources_plans()
        self.check_profile_patterns()
        return self.diagnostics


def main():
    parser = argparse.ArgumentParser(description="Validate a KCF semantic IR JSON model.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    diagnostics = Analyzer(json.loads(args.model.read_text(encoding="utf-8"))).run()
    result = {"model": str(args.model), "valid": not any(d["severity"] == "error" for d in diagnostics), "diagnostics": diagnostics}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
