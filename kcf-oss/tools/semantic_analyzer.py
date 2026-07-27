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
# Advisory data-management classification carried as entity metadata (not a primitive).
# Reconciled against the derived semantic shape; see check_category_consistency.
ENTITY_CATEGORIES = {"master", "transactional", "reference", "config"}
# Metadata keys the grammar/normalizer legitimately place on a concept (advisory tags +
# normalized kind discriminators). Anything else fell through the concept-body catch-all
# (`<ident> <scalar>;` -> metadata) — most likely a typo or an unsupported field silently
# captured as free metadata, a real footgun (a mistyped/misversioned field only errors
# once a later grammar types that slot). See check_concept_metadata (advisory warning).
KNOWN_CONCEPT_METADATA = {
    "category", "mutability", "readOnly", "capacity", "policy", "containment",
    "informationKind", "organizationKind", "reasoningKind", "ruleKind",
}
# Advisory DDD-aggregate role: `root` (aggregate root -> top-level nav) vs `part` (pure
# part -> subtab on its parent's detail). Derivable from COMPOSITION edges; reconciled
# like `category`. Not a primitive.
CONTAINMENT_ROLES = {"root", "part"}
# Recognized relationship qualifiers (ride the relationship-decl `{ identifier scalar }`
# catch-all). cardinality + roles + on-delete drive UI generation (grid/tab vs panel,
# tab label, cascade/restrict). Advisory-checked, like concept metadata.
KNOWN_RELATIONSHIP_QUALIFIERS = {
    "cardinality", "source-role", "target-role", "on-delete", "inverse",
    "validations", "inferences", "min", "max",
}
ON_DELETE_POLICIES = {"cascade", "restrict", "detach", "archive", "set-null", "no-action"}
ACTION_OPERATIONS = {
    "create", "read", "replace", "update", "patch", "delete", "upsert", "exists",
    "query", "count", "bulk-create", "bulk-update", "bulk-patch", "bulk-delete",
    "bulk-upsert", "synchronize", "invoke", "emit", "allocate", "release",
}
ACTION_SCOPES = {"record", "set", "batch", "stream", "window"}
ACTION_CARDINALITIES = {"zero", "one", "optional-one", "many", "stream"}
SELECTION_KINDS = {"identity", "predicate", "keys", "relation", "partition", "window", "all"}
ATOMICITY_MODES = {"atomic", "per-record", "best-effort"}
CONCURRENCY_MODES = {"none", "optimistic", "pessimistic", "serialized"}
DIRECTIONALITIES = {"directed", "bidirectional", "symmetric"}
POLARITIES = {"affirm", "deny", "support", "oppose", "permit", "prohibit"}
INFERENCE_SEMANTICS = {"none", "inverse", "transitive", "inherit", "qualify", "causal"}
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
            "skills", "capabilities", "units", "collectionTransforms", "authorities",
            "calendars", "routes", "propositions", "predicates", "math", "resources",
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
            qualifier_key = tuple(sorted(
                (k, tuple(v) if isinstance(v, list) else v)
                for k, v in (rel.get("qualifiers", {}) or {}).items()
            ))
            key = (rel.get("definition"), source, target, qualifier_key)
            if key in seen:
                self.report("warning", "stack.graph.edge-unique", rid, "Duplicate equivalent relationship.")
            seen.add(key)
            if source == target and not rel.get("allowSelf"):
                self.report("error", "stack.graph.no-self-edge", rid, "Self relationship is not permitted.")
            strength = rel.get("strength")
            if strength is not None and not 0 <= strength <= 1:
                self.report("error", "kcf.relationship.strength", rid, "Strength must be in [0,1].")
            # Enum membership for the relationship qualifiers that define one
            # (qualifiers live under the open `qualifiers` object).
            quals = rel.get("qualifiers", {}) or {}
            if quals.get("directionality") is not None and quals["directionality"] not in DIRECTIONALITIES:
                self.report("error", "kcf.relationship.directionality", rid, f"Unknown directionality {quals['directionality']!r}.")
            if quals.get("polarity") is not None and quals["polarity"] not in POLARITIES:
                self.report("error", "kcf.relationship.polarity", rid, f"Unknown polarity {quals['polarity']!r}.")
            for inference in quals.get("inferences", []):
                if inference not in INFERENCE_SEMANTICS:
                    self.report("error", "kcf.relationship.infer", rid, f"Unknown inference semantics {inference!r}.")
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
            # Enum membership for the contract fields (catches typos the semantic
            # constraints below would otherwise silently accept).
            if operation is not None and operation not in ACTION_OPERATIONS:
                self.report("error", "action.operation.unknown", aid, f"Unknown operation {operation!r}.")
            if scope is not None and scope not in ACTION_SCOPES:
                self.report("error", "action.scope.unknown", aid, f"Unknown scope {scope!r}.")
            if action.get("selection") is not None and action["selection"] not in SELECTION_KINDS:
                self.report("error", "action.selection.unknown", aid, f"Unknown selection {action['selection']!r}.")
            for card_field in ("inputCardinality", "outputCardinality"):
                if action.get(card_field) is not None and action[card_field] not in ACTION_CARDINALITIES:
                    self.report("error", "action.cardinality.unknown", aid, f"Unknown {card_field} {action[card_field]!r}.")
            if action.get("atomicity") is not None and action["atomicity"] not in ATOMICITY_MODES:
                self.report("error", "action.atomicity.unknown", aid, f"Unknown atomicity {action['atomicity']!r}.")
            if action.get("concurrency") is not None and action["concurrency"] not in CONCURRENCY_MODES:
                self.report("error", "action.concurrency.unknown", aid, f"Unknown concurrency {action['concurrency']!r}.")
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
        # Key on qualifiedName (what allocations reference) with a bare-id fallback,
        # so the capacity check actually matches namespace-qualified allocation refs.
        capacities = {(r.get("qualifiedName") or r.get("id")): r.get("capacity") for r in self.model.get("resources", [])}
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

    def check_capabilities_skills(self):
        """Every declared concept reference-list must resolve: an ACTOR's
        capabilities/skills, a WORK's required capabilities/skills, an EVENT's
        subject(s)/trigger(s), a capability's requires-skill/implemented-by, and a
        skill's requires."""
        for concept in self.model.get("concepts", []):
            name = concept.get("qualifiedName") or concept.get("id", "<concept>")
            for field, rule in (("capabilities", "kcf.actor.capability"), ("skills", "kcf.actor.skill"),
                                ("requiresCapability", "kcf.work.requires-capability"),
                                ("requiresSkill", "kcf.work.requires-skill"),
                                ("subjects", "kcf.event.subject"), ("triggers", "kcf.event.trigger"),
                                ("sources", "kcf.event.source"), ("observers", "kcf.event.observer"),
                                ("affectsLifecycle", "kcf.event.affect-lifecycle"),
                                ("evidence", "kcf.event.evidence"),
                                ("roles", "kcf.actor.role"), ("authorities", "kcf.actor.authority"),
                                ("responsibleFor", "kcf.actor.responsible-for"),
                                ("accountableFor", "kcf.actor.accountable-for"),
                                ("memberOf", "kcf.actor.member-of"),
                                ("performers", "kcf.work.performer"), ("inputs", "kcf.work.input"),
                                ("outputs", "kcf.work.output"), ("outcomes", "kcf.work.outcome"),
                                ("requiresResource", "kcf.work.requires-resource"),
                                ("requiresTool", "kcf.work.requires-tool"),
                                ("governedBy", "kcf.work.governed-by"),
                                ("triggeredBy", "kcf.work.triggered-by"),
                                ("emits", "kcf.work.emit"),
                                ("compensateWith", "kcf.work.compensate-with"),
                                ("temporalRefs", "kcf.work.temporal"),
                                ("stakeholders", "kcf.intent.stakeholder"),
                                ("measures", "kcf.intent.measure"),
                                ("adjacentTo", "kcf.spatial.adjacent-to"),
                                ("jurisdictions", "kcf.spatial.jurisdiction"),
                                ("spatialRoutes", "kcf.spatial.route"),
                                ("spatialCapacities", "kcf.spatial.capacity")):
                for ref in concept.get(field, []):
                    if not self.reference_exists(ref):
                        self.report("error", rule, name, f"Unresolved {field} reference {ref!r}.")
        for capability in self.model.get("capabilities", []):
            cid = capability.get("qualifiedName") or capability.get("id", "<capability>")
            for ref in capability.get("requiresSkill", []):
                if not self.reference_exists(ref):
                    self.report("error", "kcf.capability.requires-skill", cid, f"Unresolved skill reference {ref!r}.")
            if capability.get("implementedBy") and not self.reference_exists(capability["implementedBy"]):
                self.report("error", "kcf.capability.implemented-by", cid, f"Unresolved implementation {capability['implementedBy']!r}.")
        for skill in self.model.get("skills", []):
            sid = skill.get("qualifiedName") or skill.get("id", "<skill>")
            for ref in skill.get("requires", []):
                if not self.reference_exists(ref):
                    self.report("error", "kcf.skill.requires", sid, f"Unresolved skill prerequisite {ref!r}.")

    EVENT_KINDS = {"OCCURRENCE", "SIGNAL", "OBSERVATION", "NORMAL", "EXCEPTION",
                   "THRESHOLD", "SCHEDULED", "EXTERNAL", "DERIVED", "CORRECTION"}
    EXPECTEDNESS = {"expected", "unexpected", "unknown"}

    def check_events(self):
        """EVENT dimension enums: an event's kind (if declared) must be a defined
        event-kind, and expectedness (if declared) must be a defined level."""
        for concept in self.model.get("concepts", []):
            if concept.get("kind") != "EVENT":
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<event>")
            kind = concept.get("conceptKind")
            if kind is not None and kind not in self.EVENT_KINDS:
                self.report("error", "kcf.event.kind", name,
                            f"Unknown event kind {kind!r}; expected one of {sorted(self.EVENT_KINDS)}.")
            expectedness = concept.get("expectedness")
            if expectedness is not None and expectedness not in self.EXPECTEDNESS:
                self.report("error", "kcf.event.expectedness", name,
                            f"Unknown expectedness {expectedness!r}; expected one of {sorted(self.EXPECTEDNESS)}.")

    CARDINALITIES = {"one", "many", "set", "zero-or-one", "one-or-many", "zero-or-many", "optional-one"}
    ORPHAN_POLICIES = {"restrict", "cascade", "detach", "archive"}
    MUTATION_OPERATIONS = {"create", "replace", "update", "patch", "delete", "upsert",
                           "archive", "assign-reference", "add-member", "remove-member", "synchronize"}
    MUTATION_SCOPES = {"record", "set", "batch", "stream"}
    ATOMICITIES = {"atomic", "per-record", "best-effort"}
    CONCURRENCY_POLICIES = {"none", "optimistic", "pessimistic", "serialized"}
    SELECTIONS = {"identity", "predicate", "keys", "partition", "all"}

    def check_entities(self):
        """ENTITY dimension: resolve compositions/named-references/embedded-collection
        targets, inline lifecycle binding, and inline constraint-uses; enforce
        cardinality/orphan enums; and validate entity-embedded mutations (subject,
        operation/scope/atomicity/concurrency/selection enums, emitted events)."""
        for concept in self.model.get("concepts", []):
            name = concept.get("qualifiedName") or concept.get("id", "<concept>")
            for comp in concept.get("compositions", []):
                if not self.reference_exists(comp.get("target")):
                    self.report("error", "kcf.entity.composition", name, f"Unresolved composition target {comp.get('target')!r}.")
                if comp.get("cardinality") and comp["cardinality"] not in self.CARDINALITIES:
                    self.report("error", "kcf.entity.cardinality", name, f"Unknown cardinality {comp['cardinality']!r}.")
                if comp.get("orphan") and comp["orphan"] not in self.ORPHAN_POLICIES:
                    self.report("error", "kcf.entity.orphan", name, f"Unknown orphan policy {comp['orphan']!r}.")
            for ref in concept.get("namedReferences", []):
                if not self.reference_exists(ref.get("target")):
                    self.report("error", "kcf.entity.reference", name, f"Unresolved reference target {ref.get('target')!r}.")
                if ref.get("cardinality") and ref["cardinality"] not in self.CARDINALITIES:
                    self.report("error", "kcf.entity.cardinality", name, f"Unknown cardinality {ref['cardinality']!r}.")
            for coll in concept.get("collections", []):
                if not self.reference_exists(coll.get("of")):
                    self.report("error", "kcf.entity.collection", name, f"Unresolved collection element type {coll.get('of')!r}.")
            if concept.get("lifecycleRef") and not self.reference_exists(concept["lifecycleRef"]):
                self.report("error", "kcf.entity.lifecycle", name, f"Unresolved lifecycle {concept['lifecycleRef']!r}.")
            for ref in concept.get("constraints", []):
                if not self.reference_exists(ref):
                    self.report("error", "kcf.entity.constraint", name, f"Unresolved constraint {ref!r}.")
        for mutation in self.model.get("mutations", []):
            mid = mutation.get("qualifiedName") or mutation.get("id", "<mutation>")
            if not self.reference_exists(mutation.get("subject")):
                self.report("error", "kcf.mutation.subject", mid, f"Unresolved mutation subject {mutation.get('subject')!r}.")
            for field, allowed, rule in (("operation", self.MUTATION_OPERATIONS, "kcf.mutation.operation"),
                                         ("scope", self.MUTATION_SCOPES, "kcf.mutation.scope"),
                                         ("atomicity", self.ATOMICITIES, "kcf.mutation.atomicity"),
                                         ("concurrency", self.CONCURRENCY_POLICIES, "kcf.mutation.concurrency"),
                                         ("selection", self.SELECTIONS, "kcf.mutation.selection")):
                value = mutation.get(field)
                if value is not None and value not in allowed:
                    self.report("error", rule, mid, f"Unknown {field} {value!r}; expected one of {sorted(allowed)}.")
            for emitted in mutation.get("emits", []):
                if not self.reference_exists(emitted):
                    self.report("error", "kcf.mutation.emit", mid, f"Unresolved emitted event {emitted!r}.")

    MEASURE_KINDS = {"QUANTITY", "METRIC", "KPI", "THRESHOLD", "SCORE"}
    SCALE_KINDS = {"nominal", "ordinal", "interval", "ratio"}
    AGGREGATION_KINDS = {"sum", "average", "minimum", "maximum", "count", "distinct-count", "none"}

    def check_measures(self):
        """MEASURE dimension: measure kind/scale/aggregation enums and unit/
        calculation/period references (all optional in the ergonomic surface), plus
        unit `base` references."""
        for concept in self.model.get("concepts", []):
            if concept.get("kind") != "MEASURE":
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<measure>")
            kind = concept.get("conceptKind")
            if kind is not None and kind not in self.MEASURE_KINDS:
                self.report("error", "kcf.measure.kind", name, f"Unknown measure kind {kind!r}; expected one of {sorted(self.MEASURE_KINDS)}.")
            if concept.get("scale") is not None and concept["scale"] not in self.SCALE_KINDS:
                self.report("error", "kcf.measure.scale", name, f"Unknown scale {concept['scale']!r}; expected one of {sorted(self.SCALE_KINDS)}.")
            if concept.get("aggregation") is not None and concept["aggregation"] not in self.AGGREGATION_KINDS:
                self.report("error", "kcf.measure.aggregation", name, f"Unknown aggregation {concept['aggregation']!r}; expected one of {sorted(self.AGGREGATION_KINDS)}.")
            for field, rule in (("unitRef", "kcf.measure.unit"), ("periodRef", "kcf.measure.period")):
                if concept.get(field) and not self.reference_exists(concept[field]):
                    self.report("error", rule, name, f"Unresolved {field} reference {concept[field]!r}.")
        for unit in self.model.get("units", []):
            uid = unit.get("qualifiedName") or unit.get("id", "<unit>")
            if unit.get("base") and not self.reference_exists(unit["base"]):
                self.report("error", "kcf.unit.base", uid, f"Unresolved base unit {unit['base']!r}.")

    ACTOR_KINDS = {"PERSON", "ROLE", "TEAM", "ORGANIZATION", "SYSTEM", "AI_AGENT", "MACHINE", "EXTERNAL_PARTY"}
    AUTHORITY_MODES = {"may-perform", "may-approve", "may-delegate", "may-escalate", "must-not-perform"}

    def check_actors(self):
        """ACTOR dimension: actor-kind enum, communication reference, and top-level
        authority grants (mode enum + subject/target references)."""
        for concept in self.model.get("concepts", []):
            if concept.get("kind") != "ACTOR":
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<actor>")
            kind = concept.get("conceptKind")
            if kind is not None and kind not in self.ACTOR_KINDS:
                self.report("error", "kcf.actor.kind", name, f"Unknown actor kind {kind!r}; expected one of {sorted(self.ACTOR_KINDS)}.")
            if concept.get("communicationRef") and not self.reference_exists(concept["communicationRef"]):
                self.report("error", "kcf.actor.communication", name, f"Unresolved communication reference {concept['communicationRef']!r}.")
        for authority in self.model.get("authorities", []):
            aid = authority.get("qualifiedName") or authority.get("id", "<authority>")
            mode = authority.get("mode")
            if mode is not None and mode not in self.AUTHORITY_MODES:
                self.report("error", "kcf.authority.mode", aid, f"Unknown authority mode {mode!r}; expected one of {sorted(self.AUTHORITY_MODES)}.")
            for field in ("subject", "target"):
                if authority.get(field) and not self.reference_exists(authority[field]):
                    self.report("error", f"kcf.authority.{field}", aid, f"Unresolved authority {field} {authority[field]!r}.")

    WORK_KINDS = {"ACTION", "DECISION", "TASK", "ACTIVITY", "PROCESS"}
    GATEWAY_KINDS = {"exclusive", "inclusive", "parallel", "event-based"}

    def check_work(self):
        """WORK dimension: work-kind enum, and process choreography (gateway-kind
        enum; step/call/event/boundary/lane semantic refs; flow endpoints referencing
        process-local node ids)."""
        for concept in self.model.get("concepts", []):
            if concept.get("kind") != "WORK":
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<work>")
            kind = concept.get("conceptKind")
            if kind is not None and kind not in self.WORK_KINDS:
                self.report("error", "kcf.work.kind", name, f"Unknown work kind {kind!r}; expected one of {sorted(self.WORK_KINDS)}.")
        for process in self.model.get("processes", []):
            pid = process.get("qualifiedName") or process.get("id", "<process>")
            node_ids = {node["id"] for node in process.get("nodes", [])}
            # Structural checks (unique ids, single start, >=1 end, flow endpoints,
            # reachability) are owned by check_processes; here we add the WORK-dimension
            # semantics: gateway enum + semantic-ref resolution + boundary/lane wiring.
            for node in process.get("nodes", []):
                if node.get("type") == "gateway" and node.get("gatewayKind") not in self.GATEWAY_KINDS:
                    self.report("error", "kcf.process.gateway", pid, f"Unknown gateway kind {node.get('gatewayKind')!r}.")
                for ref_key in ("activity", "uses", "triggeredBy", "outcome"):
                    if node.get(ref_key) and not self.reference_exists(node[ref_key]):
                        self.report("error", "kcf.process.node", pid, f"Unresolved {ref_key} {node[ref_key]!r} in node {node.get('id')!r}.")
            for boundary in process.get("boundaries", []):
                if boundary.get("on") not in node_ids:
                    self.report("error", "kcf.process.boundary", pid, f"Boundary attached to unknown node {boundary.get('on')!r}.")
                if boundary.get("uses") and not self.reference_exists(boundary["uses"]):
                    self.report("error", "kcf.process.boundary", pid, f"Unresolved boundary event {boundary['uses']!r}.")
            for lane in process.get("lanes", []):
                if lane.get("performer") and not self.reference_exists(lane["performer"]):
                    self.report("error", "kcf.process.lane", pid, f"Unresolved lane performer {lane['performer']!r}.")
                for contained in lane.get("contains", []):
                    if contained not in node_ids:
                        self.report("error", "kcf.process.lane", pid, f"Lane contains unknown node {contained!r}.")

    # A lifecycle may govern any declared concept kind (the full metagrammar set),
    # not just the ergonomic parse_concept kinds.
    CONCEPT_KIND_NAMES = KINDS

    def check_lifecycle_refs(self):
        """LIFECYCLE dimension enrichments: governs-kind enum, state entry/exit actions,
        transition trigger/requires-work/effect, and temporal references."""
        for lifecycle in self.model.get("lifecycles", []):
            lid = lifecycle.get("qualifiedName") or lifecycle.get("id", "<lifecycle>")
            for governed in lifecycle.get("governsKind", []):
                if governed not in self.CONCEPT_KIND_NAMES:
                    self.report("error", "kcf.lifecycle.governs-kind", lid, f"Unknown governed concept kind {governed!r}.")
            for state, body in (lifecycle.get("stateBodies") or {}).items():
                for ref_key in ("entry", "exit"):
                    for ref in body.get(ref_key, []):
                        if not self.reference_exists(ref):
                            self.report("error", f"kcf.lifecycle.state.{ref_key}", lid, f"Unresolved {ref_key} {ref!r} in state {state!r}.")
            for transition in lifecycle.get("transitions", []):
                for ref_key in ("trigger", "requiresWork", "effect"):
                    for ref in transition.get(ref_key, []):
                        if not self.reference_exists(ref):
                            self.report("error", f"kcf.lifecycle.transition", lid, f"Unresolved {ref_key} {ref!r}.")
            for ref in lifecycle.get("temporalRefs", []):
                if not self.reference_exists(ref):
                    self.report("error", "kcf.lifecycle.temporal", lid, f"Unresolved temporal reference {ref!r}.")

    INTENT_KINDS = {"GOAL", "OBJECTIVE", "OUTCOME", "REQUEST", "PREFERENCE", "PRIORITY", "SUCCESS_CONDITION", "FAILURE_CONDITION"}
    TEMPORAL_KINDS = {"INSTANT", "INTERVAL", "DURATION", "DEADLINE", "SCHEDULE", "RECURRENCE", "EFFECTIVE_PERIOD"}
    DURATION_UNITS = {"millisecond", "second", "minute", "hour", "day", "week", "month", "year"}
    SPATIAL_KINDS = {"LOCATION", "REGION", "ZONE", "PATH", "COORDINATE", "JURISDICTION"}
    GEOMETRY_KINDS = {"point", "line", "polygon", "volume"}
    MODAL_OPERATORS = {"necessary", "possible", "permitted", "obligatory", "known", "believed"}

    def check_quantitative(self):
        """INTENT/TEMPORAL/SPATIAL/LOGIC/MATH enums + single-reference resolution."""
        kind_rules = {"INTENT": ("kcf.intent.kind", self.INTENT_KINDS),
                      "TEMPORAL": ("kcf.temporal.kind", self.TEMPORAL_KINDS),
                      "SPATIAL": ("kcf.spatial.kind", self.SPATIAL_KINDS)}
        for concept in self.model.get("concepts", []):
            kind = concept.get("kind")
            if kind not in kind_rules:
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<concept>")
            rule, allowed = kind_rules[kind]
            classifier = concept.get("conceptKind")
            if classifier is not None and classifier not in allowed:
                self.report("error", rule, name, f"Unknown {kind.lower()} kind {classifier!r}; expected one of {sorted(allowed)}.")
            for field, frule in (("containedIn", "kcf.spatial.contained-in"),
                                 ("calendarRef", "kcf.temporal.calendar"),
                                 ("timeHorizon", "kcf.intent.time-horizon")):
                if concept.get(field) and not self.reference_exists(concept[field]):
                    self.report("error", frule, name, f"Unresolved {field} {concept[field]!r}.")
            geometry = concept.get("geometry")
            if geometry and geometry.get("geometryKind") not in self.GEOMETRY_KINDS:
                self.report("error", "kcf.spatial.geometry", name, f"Unknown geometry kind {geometry.get('geometryKind')!r}.")
            duration = concept.get("durationValue")
            if duration and duration.get("unit") not in self.DURATION_UNITS:
                self.report("error", "kcf.temporal.duration", name, f"Unknown duration unit {duration.get('unit')!r}.")
        for proposition in self.model.get("propositions", []):
            pid = proposition.get("qualifiedName") or proposition.get("id", "<proposition>")
            if proposition.get("mode") is not None and proposition["mode"] not in self.MODAL_OPERATORS:
                self.report("error", "kcf.logic.mode", pid, f"Unknown modal operator {proposition['mode']!r}.")
        for formula in self.model.get("math", []):
            mid = formula.get("qualifiedName") or formula.get("id", "<math>")
            for field in ("result", "model"):
                if formula.get(field) and not self.reference_exists(formula[field]):
                    self.report("error", "kcf.math.reference", mid, f"Unresolved {field} {formula[field]!r}.")
        for route in self.model.get("routes", []):
            rid = route.get("qualifiedName") or route.get("id", "<route>")
            for field in ("from", "to"):
                if route.get(field) and not self.reference_exists(route[field]):
                    self.report("error", "kcf.spatial.route", rid, f"Unresolved route {field} {route[field]!r}.")
            for waypoint in route.get("via", []):
                if not self.reference_exists(waypoint):
                    self.report("error", "kcf.spatial.route", rid, f"Unresolved route via {waypoint!r}.")
            for constraint in route.get("constraints", []):
                if not self.reference_exists(constraint):
                    self.report("error", "kcf.spatial.route", rid, f"Unresolved route constraint {constraint!r}.")

    RESOURCE_KINDS = {"CONSUMABLE", "RENEWABLE", "CAPACITY", "TOOL", "FACILITY", "COMPUTE", "FINANCIAL"}
    CONSUMPTION_MODES = {"consume", "reserve", "borrow", "share"}

    def check_resources(self):
        """RESOURCE dimension: resource-kind + consumption enums, resource reference
        fields, and allocation references."""
        for resource in self.model.get("resources", []):
            rid = resource.get("qualifiedName") or resource.get("id", "<resource>")
            if resource.get("resourceKind") is not None and resource["resourceKind"] not in self.RESOURCE_KINDS:
                self.report("error", "kcf.resource.kind", rid, f"Unknown resource kind {resource['resourceKind']!r}; expected one of {sorted(self.RESOURCE_KINDS)}.")
            if resource.get("consumption") is not None and resource["consumption"] not in self.CONSUMPTION_MODES:
                self.report("error", "kcf.resource.consumption", rid, f"Unknown consumption mode {resource['consumption']!r}.")
            for field in ("capacityUnit", "location", "owner", "allocationPolicy", "reservationPolicy", "replenishment", "cost"):
                if resource.get(field) and not self.reference_exists(resource[field]):
                    self.report("error", "kcf.resource.reference", rid, f"Unresolved {field} {resource[field]!r}.")
        for allocation in self.model.get("allocations", []):
            aid = allocation.get("qualifiedName") or allocation.get("id", "<allocation>")
            for field in ("resource", "consumer", "reservation"):
                if allocation.get(field) and not self.reference_exists(allocation[field]):
                    self.report("error", "kcf.allocation.reference", aid, f"Unresolved {field} {allocation[field]!r}.")

    def derive_containment(self):
        """Return (pure_parts, parent_of) derived purely from COMPOSITION edges — no
        domain knowledge. A **pure part** (DDD aggregate part → subtab-only UI) is a
        COMPOSITION target that is (a) not itself a COMPOSITION parent and (b) has no
        independent (non-composition) inbound reference. Everything else is an aggregate
        **root** (top-level nav). `parent_of[e]` is the COMPOSITION source that owns a
        pure part `e`."""
        rels = self.model.get("relationships", [])
        entities = {c.get("qualifiedName") or c.get("id")
                    for c in self.model.get("concepts", []) if c.get("kind") == "ENTITY"}
        comp_targets = {r.get("target") for r in rels if r.get("rootKind") == "COMPOSITION"}
        comp_sources = {r.get("source") for r in rels if r.get("rootKind") == "COMPOSITION"}
        indep_inbound: dict = {}
        for rel in rels:
            if rel.get("rootKind") != "COMPOSITION":
                indep_inbound[rel.get("target")] = indep_inbound.get(rel.get("target"), 0) + 1
        for concept in self.model.get("concepts", []):
            for ref in concept.get("references", []):
                target = ref.get("target") if isinstance(ref, dict) else ref
                indep_inbound[target] = indep_inbound.get(target, 0) + 1
        pure_parts, parent_of = set(), {}
        for entity in entities:
            if (entity in comp_targets and entity not in comp_sources
                    and indep_inbound.get(entity, 0) == 0):
                pure_parts.add(entity)
                parents = [r.get("source") for r in rels
                           if r.get("rootKind") == "COMPOSITION" and r.get("target") == entity]
                if parents:
                    parent_of[entity] = parents[0]
        return pure_parts, parent_of

    def check_containment_consistency(self):
        """Advisory — warnings only. An entity's containment role (aggregate `root` →
        top-level nav vs pure `part` → a subtab on its parent) is derivable from
        COMPOSITION structure; reconcile an advisory `containment` tag against it."""
        pure_parts, _ = self.derive_containment()
        for concept in self.model.get("concepts", []):
            if concept.get("kind") != "ENTITY":
                continue
            name = concept.get("qualifiedName") or concept.get("id", "<entity>")
            stated = (concept.get("metadata") or {}).get("containment")
            if stated is None:
                continue
            if stated not in CONTAINMENT_ROLES:
                self.report("warning", "kcf.entity.containment-vocab", name,
                            f"Unknown containment {stated!r}; expected 'root' or 'part'.")
                continue
            derived_part = name in pure_parts
            if stated == "part" and not derived_part:
                self.report(
                    "warning", "kcf.entity.containment-shape", name,
                    "Marked containment 'part' but the structure is not a pure part "
                    "(it is a composition parent, is independently referenced, or is not "
                    "composed) — likely an aggregate 'root'.")
            elif stated == "root" and derived_part:
                self.report(
                    "warning", "kcf.entity.containment-shape", name,
                    "Marked containment 'root' but the structure is a pure part (a "
                    "COMPOSITION target with no children and no independent inbound "
                    "reference) — likely a 'part' (a subtab on its parent).")

    def check_relationship_qualifiers(self):
        """Advisory — warnings only. Relationship qualifiers (cardinality / source-role /
        target-role / on-delete) ride the relationship-decl catch-all and drive UI
        generation (master-detail grid vs single panel, tab label, cascade/restrict).
        Flag an unrecognized qualifier key (typo) and an out-of-vocabulary `on-delete`."""
        for rel in self.model.get("relationships", []):
            rid = rel.get("id", "<relationship>")
            for key, value in (rel.get("qualifiers") or {}).items():
                if key not in KNOWN_RELATIONSHIP_QUALIFIERS:
                    self.report(
                        "warning", "kcf.relationship.unknown-qualifier", rid,
                        f"Relationship qualifier {key!r} is not recognized — verify it is "
                        f"not a typo.")
                elif key == "on-delete" and isinstance(value, str) and value not in ON_DELETE_POLICIES:
                    self.report(
                        "warning", "kcf.relationship.on-delete-vocab", rid,
                        f"on-delete {value!r} is not a known policy "
                        f"({', '.join(sorted(ON_DELETE_POLICIES))}).")

    def check_concept_metadata(self):
        """Advisory — warnings only. The concept-body grammar has a catch-all that turns
        an unrecognized ``field value;`` line into free ``metadata`` (this is how advisory
        tags like ``mutability``/``category`` ride in). That same catch-all silently
        swallows typos and unsupported fields — which then surface only as a hard error
        once a later grammar version types that slot. Flag concept metadata keys outside
        the known-legitimate set so the author can catch a typo at authoring time."""
        for concept in self.model.get("concepts", []):
            name = concept.get("qualifiedName") or concept.get("id", "<concept>")
            for key in (concept.get("metadata") or {}):
                if key not in KNOWN_CONCEPT_METADATA:
                    self.report(
                        "warning", "kcf.concept.unknown-field", name,
                        f"Field {key!r} on {name!r} was captured as free metadata "
                        f"(unrecognized concept field) — verify it is not a typo or an "
                        f"unsupported field.",
                        correction=f"Correct or remove {key!r} on {name!r}, or use a "
                                   f"recognized field or advisory tag.")

    def check_category_consistency(self):
        """Reconcile a stated entity ``category`` metadata tag against the model's
        derived semantic shape. Advisory — warnings only. A flat category is a
        denormalized convenience (DBML-style); KCF treats record-nature as emergent
        from lifecycle/event/transformation/mutability, so this never blocks a model.
        It flags only HIGH-CONFIDENCE contradictions: shape can separate transactional
        (a TRANSFORMATION target and/or event emitter) from stable, but cannot tell
        master/config/reference apart, so those are never flagged against each other.
        """
        entities = [c for c in self.model.get("concepts", []) if c.get("kind") == "ENTITY"]
        names = {c.get("qualifiedName") or c.get("id") for c in entities}
        lifecycle_subjects = {lc.get("subject") for lc in self.model.get("lifecycles", [])}
        transformation_targets = {r.get("target") for r in self.model.get("relationships", [])
                                  if r.get("rootKind") == "TRANSFORMATION"}
        event_subjects = set()
        for ev in self.model.get("events", []):
            event_subjects.update(ev.get("subjects", []) or [])
            if ev.get("subject"):
                event_subjects.add(ev["subject"])
        # reference in-degree: relationship edges + concept references pointing at it
        in_degree = {}
        for rel in self.model.get("relationships", []):
            tgt = rel.get("target")
            if tgt in names:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1
        for concept in self.model.get("concepts", []):
            for ref in concept.get("references", []):
                tgt = ref.get("target") if isinstance(ref, dict) else ref
                if tgt in names:
                    in_degree[tgt] = in_degree.get(tgt, 0) + 1
        HIGH_INDEGREE = 3
        for concept in entities:
            name = concept.get("qualifiedName") or concept.get("id", "<entity>")
            meta = concept.get("metadata", {}) or {}
            stated = meta.get("category")
            if stated is None:
                continue
            if stated not in ENTITY_CATEGORIES:
                self.report("warning", "kcf.entity.category-vocab", name,
                            f"Unknown entity category {stated!r}; expected one of "
                            f"{', '.join(sorted(ENTITY_CATEGORIES))}.",
                            correction=f"Set {name!r} category to a known value or remove it.")
                continue
            read_only = meta.get("mutability") == "read-only" or meta.get("readOnly") is True
            transactional_shape = name in transformation_targets or name in event_subjects
            referenced = in_degree.get(name, 0)
            if stated in {"master", "reference", "config"} and transactional_shape:
                self.report(
                    "warning", "kcf.entity.category-shape", name,
                    f"Marked category {stated!r} but the shape is transactional "
                    f"(a TRANSFORMATION target and/or emits events) — likely 'transactional'.",
                    correction=f"Reconcile {name!r}: set category 'transactional', or drop the "
                               f"transformation/event shape if it is truly {stated}.")
            elif (stated == "transactional" and read_only and not transactional_shape
                  and referenced >= HIGH_INDEGREE):
                self.report(
                    "warning", "kcf.entity.category-shape", name,
                    f"Marked 'transactional' but read-only, referenced by {referenced}, with no "
                    f"events/transformation — likely 'reference' or 'master'.",
                    correction=f"Reconcile {name!r}: set category 'reference'/'master', or give it "
                               f"a mutable, event/transformation shape if it is truly transactional.")

    def run(self):
        self.build_symbols()
        self.check_refs()
        self.check_capabilities_skills()
        self.check_events()
        self.check_entities()
        self.check_measures()
        self.check_actors()
        self.check_work()
        self.check_lifecycle_refs()
        self.check_quantitative()
        self.check_resources()
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
        self.check_category_consistency()
        self.check_containment_consistency()
        self.check_concept_metadata()
        self.check_relationship_qualifiers()
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
