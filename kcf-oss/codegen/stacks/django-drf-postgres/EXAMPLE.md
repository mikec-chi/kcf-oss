# Single-shot example — Django + DRF + Django ORM + PostgreSQL

This realizes the reference `business-application` model in this stack. Imitate
its layering and idioms; substitute the target model's concepts, attributes,
lifecycle, and action contract.

## Input (excerpt of the KCF IR)

```jsonc
// concept customer.Customer (ENTITY): identity customerId:UUID, required name:String, optional email:String
// concept customer.ServiceAgent (ACTOR)          // the authorized principal / role
// concept customer.UpdateCustomerWork (WORK)     // the update process the actor performs
// concept customer.CustomerUpdated (EVENT, immutable)   // emitted when an update commits
// relationship agent-performs-update: PARTICIPATION ServiceAgent -> UpdateCustomerWork
// relationship update-changes-customer: TRANSFORMATION UpdateCustomerWork -> Customer
// lifecycle CustomerLifecycle: Active->Suspended, Suspended->Active, Active->Archived (terminal Archived)

// action customer.CreateCustomer: create/record, idempotency=conditional, atomicity=atomic
// action customer.GetCustomer:    read/record,   selection=identity
// action customer.UpdateCustomer: update/record, selection=identity, mutate=[name],
//   idempotency=conditional, atomicity=atomic, concurrency=optimistic,
//   authorization=customer.CustomerUpdatePolicy
// action customer.DeleteCustomer: delete/record, selection=identity, idempotency=conditional
// action customer.UpsertCustomer: upsert/record, selection=identity,
//   idempotency=conditional, atomicity=atomic
// action customer.BulkUpdateCustomers: bulk-update/set, selection=predicate,
//   input=many, output=many, atomicity=best-effort, concurrency=optimistic

// collectionTransform customer.ActiveCustomers: filter, inputSchema=Customer,
//   outputSchema=Customer, predicate="customer status is Active", bounded=true
// rule customer.CustomerUpdateConstraint: kind=CONSTRAINT, applies-to=Customer,
//   authority=ServiceAgent, condition="email is present when a customer is Active"
// policy customer.CustomerUpdatePolicy: authority=ServiceAgent,
//   rule=CustomerUpdateConstraint, default-conflict=deny-overrides
```

## Output

### `customers/models.py`
```python
import uuid
from django.db import models
from django.core.exceptions import ValidationError


class Customer(models.Model):
    class State(models.TextChoices):
        ACTIVE = "Active"
        SUSPENDED = "Suspended"
        ARCHIVED = "Archived"

    # customerId is the IR identity attribute → primary key.
    customerId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)                 # required
    email = models.EmailField(null=True, blank=True)        # optional
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE)
    version = models.IntegerField(default=1)                # optimistic-concurrency token


# From CustomerLifecycle — only declared transitions are legal.
CUSTOMER_TRANSITIONS = {
    (Customer.State.ACTIVE, Customer.State.SUSPENDED),
    (Customer.State.SUSPENDED, Customer.State.ACTIVE),
    (Customer.State.ACTIVE, Customer.State.ARCHIVED),
}


def assert_transition(current: str, target: str) -> None:
    if current != target and (current, target) not in CUSTOMER_TRANSITIONS:
        raise ValidationError(f"illegal transition {current} -> {target}")
```

### `customers/serializers.py`
```python
from rest_framework import serializers


class UpdateCustomerRequest(serializers.Serializer):
    customerId = serializers.UUIDField()        # selection = identity
    name = serializers.CharField()              # only `name` is in the mutate set
    expectedVersion = serializers.IntegerField()  # optimistic concurrency


class CustomerResponse(serializers.Serializer):
    customerId = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    state = serializers.CharField()
    version = serializers.IntegerField()


# customer.CreateCustomer — input one; identity is server-assigned.
class CreateCustomerRequest(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_null=True)
    state = serializers.CharField(required=False, default="Active")


# customer.UpsertCustomer — selection=identity, create-or-update by customerId.
class UpsertCustomerRequest(serializers.Serializer):
    customerId = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_null=True)
    state = serializers.CharField(required=False, default="Active")


# customer.BulkUpdateCustomers — input=many; each item selected by identity.
class BulkUpdateItem(serializers.Serializer):
    customerId = serializers.UUIDField()
    name = serializers.CharField()
    expectedVersion = serializers.IntegerField()


class BulkUpdateRequest(serializers.Serializer):
    items = BulkUpdateItem(many=True)


# output=many: per-item result so best-effort partial success is observable.
class BulkUpdateResultItem(serializers.Serializer):
    customerId = serializers.UUIDField()
    ok = serializers.BooleanField()
    error = serializers.CharField(allow_null=True, required=False)
    customer = CustomerResponse(allow_null=True, required=False)
```

### `customers/services.py`
```python
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, APIException, ValidationError

from .models import Customer
from .events import record_customer_updated
from .policy import CUSTOMER_UPDATE_POLICY, Effect


class Conflict(APIException):
    status_code = 409
    default_detail = "version conflict"


def enforce_policy(*, name, email, state) -> None:
    """Evaluate customer.CustomerUpdatePolicy over a proposed record.

    Realizes rule customer.CustomerUpdateConstraint as a validator: mutating
    commands call this before committing, so an Active customer with no email
    is rejected (deny-overrides).
    """
    decision = CUSTOMER_UPDATE_POLICY.evaluate(
        {"customer": {"name": name, "email": email, "state": state}}
    )
    if decision.effect is not Effect.ALLOW:
        raise ValidationError(decision.reason)


@transaction.atomic                                     # atomicity = atomic
def update_customer(customer_id, name, expected_version, agent=None) -> Customer:
    """Realizes customer.UpdateCustomer — this handler IS UpdateCustomerWork.

    scope=record, selection=identity, mutate={name},
    idempotency=conditional, concurrency=optimistic.
    Authorization is enforced by the view's permission class.
    """
    try:
        current = Customer.objects.get(pk=customer_id)   # selection = identity
    except Customer.DoesNotExist:
        raise NotFound("customer not found")

    # idempotency=conditional: a no-op request neither errors nor bumps version.
    if current.name == name:
        return current

    # concurrency=optimistic: guarded UPDATE; 0 rows => stale version.
    updated = Customer.objects.filter(
        pk=customer_id, version=expected_version
    ).update(name=name, version=F("version") + 1)        # only mutate-listed field
    if updated == 0:
        raise Conflict()
    fresh = Customer.objects.get(pk=customer_id)
    record_customer_updated(agent=agent, customer=fresh)  # emit customer.CustomerUpdated
    return fresh


# ---- Remaining action contract (concise; same idioms as above) --------------

@transaction.atomic                                     # customer.CreateCustomer
def create_customer(name, email=None, state="Active") -> Customer:
    """create/record, atomicity=atomic. Constraint enforced before insert."""
    enforce_policy(name=name, email=email, state=state)
    return Customer.objects.create(name=name, email=email, state=state)


def get_customer(customer_id) -> Customer:              # customer.GetCustomer (read)
    try:
        return Customer.objects.get(pk=customer_id)     # selection = identity
    except Customer.DoesNotExist:
        raise NotFound("customer not found")


@transaction.atomic                                     # customer.DeleteCustomer
def delete_customer(customer_id) -> None:
    # idempotency=conditional: deleting an absent record is a no-op, not an error.
    Customer.objects.filter(pk=customer_id).delete()


@transaction.atomic                                     # customer.UpsertCustomer
def upsert_customer(customer_id, name, email=None, state="Active", agent=None) -> Customer:
    """upsert/record, selection=identity, idempotency=conditional, atomicity=atomic."""
    enforce_policy(name=name, email=email, state=state)
    customer, created = Customer.objects.update_or_create(
        pk=customer_id,
        defaults={"name": name, "email": email, "state": state},
    )
    if not created:
        record_customer_updated(agent=agent, customer=customer)
    return customer


def bulk_update_customers(items, agent=None) -> list[dict]:
    """Realizes customer.BulkUpdateCustomers.

    scope=set, selection=predicate, input/output=many, concurrency=optimistic,
    atomicity=best-effort: each item runs in its OWN transaction so one failure
    does not abort the batch; the caller gets a per-item result.
    """
    results: list[dict] = []
    for item in items:
        try:
            with transaction.atomic():                  # per-record boundary
                customer = update_customer(
                    item["customerId"], item["name"], item["expectedVersion"], agent=agent
                )
            results.append({"customerId": item["customerId"], "ok": True,
                            "error": None, "customer": customer})
        except (Conflict, NotFound, ValidationError) as exc:
            results.append({"customerId": item["customerId"], "ok": False,
                            "error": str(exc.detail if hasattr(exc, "detail") else exc),
                            "customer": None})
    return results


def active_customers():
    """collectionTransform customer.ActiveCustomers (operation=filter, bounded=true).

    predicate: "customer status is Active"; input/outputSchema = Customer.
    """
    return Customer.objects.filter(state=Customer.State.ACTIVE)
```

### `customers/events.py`
```python
import django.dispatch

# concept customer.CustomerUpdated (EVENT, immutable) — a fact, never mutated.
customer_updated = django.dispatch.Signal()


def record_customer_updated(*, agent, customer) -> None:
    """Emit customer.CustomerUpdated.

    Carries both declared relationships as an immutable fact:
      - agent-performs-update  (PARTICIPATION ServiceAgent -> UpdateCustomerWork)
      - update-changes-customer (TRANSFORMATION UpdateCustomerWork -> Customer)
    """
    customer_updated.send(
        sender="customer.UpdateCustomerWork",
        agent=str(getattr(agent, "username", agent)),
        customer_id=str(customer.pk),
        version=customer.version,
    )
```

### `customers/policy.py`
```python
from dataclasses import dataclass
from enum import Enum


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class Decision:
    effect: Effect
    reason: str = ""


class CustomerUpdateConstraint:
    """rule customer.CustomerUpdateConstraint (kind CONSTRAINT).

    condition: "email is present when a customer is Active"; applies-to Customer.
    """
    id = "customer.CustomerUpdateConstraint"

    def evaluate(self, ctx: dict) -> Decision:
        c = ctx["customer"]                        # proposed post-state of the record
        if c.get("state", "Active") == "Active" and not c.get("email"):
            return Decision(Effect.DENY, "email is required while a customer is Active")
        return Decision(Effect.ALLOW)


@dataclass
class Policy:
    """policy customer.CustomerUpdatePolicy — a real evaluator over its rules."""
    id: str
    authority: str            # actor customer.ServiceAgent
    rules: list
    default_conflict: str = "deny-overrides"

    def evaluate(self, ctx: dict) -> Decision:
        decisions = [r.evaluate(ctx) for r in self.rules]
        # default-conflict = deny-overrides: any DENY wins over any ALLOW.
        deny = next((d for d in decisions if d.effect is Effect.DENY), None)
        if deny is not None:
            return deny
        if any(d.effect is Effect.ALLOW for d in decisions):
            return Decision(Effect.ALLOW)
        return Decision(Effect.DENY, "no rule permitted (default deny)")


CUSTOMER_UPDATE_POLICY = Policy(
    id="customer.CustomerUpdatePolicy",
    authority="customer.ServiceAgent",
    rules=[CustomerUpdateConstraint()],
    default_conflict="deny-overrides",
)
```

### `customers/permissions.py`
```python
from rest_framework.permissions import BasePermission

from .policy import CUSTOMER_UPDATE_POLICY, Effect


class CustomerUpdatePolicy(BasePermission):
    """authorization = customer.CustomerUpdatePolicy, wired to the real engine.

    Request-time: enforce the policy's authority — the principal must hold the
    ServiceAgent role. The data-dependent CONSTRAINT rule (email-present-while-
    Active) is evaluated in the command handlers via `enforce_policy`, since it
    needs the proposed record, but it is the SAME policy object either way.
    """
    policy = CUSTOMER_UPDATE_POLICY

    def has_permission(self, request, view) -> bool:
        # authority: actor customer.ServiceAgent
        return bool(request.user and request.user.has_perm("customer.update_customer"))
```

### `customers/views.py`
```python
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

from .permissions import CustomerUpdatePolicy
from .serializers import (
    UpdateCustomerRequest, CreateCustomerRequest, UpsertCustomerRequest,
    BulkUpdateRequest, BulkUpdateResultItem, CustomerResponse,
)
from . import services


class UpdateCustomerView(APIView):
    permission_classes = [CustomerUpdatePolicy]     # enforced before the handler

    def post(self, request):
        req = UpdateCustomerRequest(data=request.data)
        req.is_valid(raise_exception=True)
        customer = services.update_customer(
            req.validated_data["customerId"],
            req.validated_data["name"],
            req.validated_data["expectedVersion"],
            agent=request.user,                     # ServiceAgent performs the work
        )
        return Response(CustomerResponse(customer).data)


class CreateCustomerView(APIView):                  # customer.CreateCustomer
    permission_classes = [CustomerUpdatePolicy]

    def post(self, request):
        req = CreateCustomerRequest(data=request.data)
        req.is_valid(raise_exception=True)
        customer = services.create_customer(**req.validated_data)
        return Response(CustomerResponse(customer).data, status=201)


class GetCustomerView(APIView):                     # customer.GetCustomer (read)
    def get(self, request, customer_id):
        customer = services.get_customer(customer_id)
        return Response(CustomerResponse(customer).data)


class DeleteCustomerView(APIView):                  # customer.DeleteCustomer
    permission_classes = [CustomerUpdatePolicy]

    def delete(self, request, customer_id):
        services.delete_customer(customer_id)       # output=zero
        return Response(status=204)


class UpsertCustomerView(APIView):                  # customer.UpsertCustomer
    permission_classes = [CustomerUpdatePolicy]

    def put(self, request):
        req = UpsertCustomerRequest(data=request.data)
        req.is_valid(raise_exception=True)
        customer = services.upsert_customer(agent=request.user, **req.validated_data)
        return Response(CustomerResponse(customer).data)


class BulkUpdateCustomersView(APIView):             # customer.BulkUpdateCustomers
    permission_classes = [CustomerUpdatePolicy]

    @extend_schema(request=BulkUpdateRequest,
                   responses=BulkUpdateResultItem(many=True))
    def post(self, request):
        req = BulkUpdateRequest(data=request.data)
        req.is_valid(raise_exception=True)
        # best-effort: per-item results, partial success possible.
        results = services.bulk_update_customers(
            req.validated_data["items"], agent=request.user)
        return Response(BulkUpdateResultItem(results, many=True).data)


class ActiveCustomersView(APIView):
    """collectionTransform customer.ActiveCustomers — GET /queries/ActiveCustomers."""

    @extend_schema(responses=CustomerResponse(many=True))   # visible in OpenAPI
    def get(self, request):
        qs = services.active_customers()            # predicate: status is Active
        return Response(CustomerResponse(qs, many=True).data)


# urls.py wires each of these — see the routing block below.
```

### `customers/tests/test_update_customer.py`
```python
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from customers.models import Customer, assert_transition
from customers.services import (
    update_customer, create_customer, upsert_customer, bulk_update_customers, Conflict,
)


@pytest.mark.django_db
def test_update_happy_path():
    c = Customer.objects.create(name="Acme", version=1)
    out = update_customer(c.pk, "Acme Holdings", 1)
    assert out.name == "Acme Holdings" and out.version == 2


@pytest.mark.django_db
def test_stale_version_conflicts():
    c = Customer.objects.create(name="Acme", version=3)
    with pytest.raises(Conflict):
        update_customer(c.pk, "New", 1)


def test_illegal_lifecycle_transition():
    with pytest.raises(DjangoValidationError):
        assert_transition(Customer.State.ARCHIVED, Customer.State.ACTIVE)  # not declared


@pytest.mark.django_db
def test_constraint_rejects_active_without_email():
    # rule CustomerUpdateConstraint via CustomerUpdatePolicy (deny-overrides).
    with pytest.raises(ValidationError):
        create_customer(name="Acme", email=None, state="Active")


@pytest.mark.django_db
def test_upsert_is_idempotent_on_identity():
    import uuid
    cid = uuid.uuid4()
    a = upsert_customer(cid, "Acme", email="a@x.io")
    b = upsert_customer(cid, "Acme Holdings", email="a@x.io")
    assert a.pk == b.pk and b.name == "Acme Holdings"


@pytest.mark.django_db
def test_bulk_update_is_best_effort():
    ok = Customer.objects.create(name="Ok", version=1)
    results = bulk_update_customers([
        {"customerId": ok.pk, "name": "Renamed", "expectedVersion": 1},   # succeeds
        {"customerId": ok.pk, "name": "Stale",   "expectedVersion": 99},  # conflicts
    ])
    assert results[0]["ok"] is True            # a failure did not abort the batch
    assert results[1]["ok"] is False
```

### `config/settings.py` + `config/urls.py` (Swagger by default)
```python
# settings.py
INSTALLED_APPS += ["rest_framework", "drf_spectacular", "customers"]
REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"}
SPECTACULAR_SETTINGS = {"TITLE": "CustomerService", "VERSION": "1.0.0"}
```
```python
# urls.py — OpenAPI schema + Swagger UI (the frontend's contract).
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from customers.views import (
    CreateCustomerView, GetCustomerView, UpdateCustomerView, DeleteCustomerView,
    UpsertCustomerView, BulkUpdateCustomersView, ActiveCustomersView,
)

urlpatterns = [
    path("actions/CreateCustomer", CreateCustomerView.as_view()),
    path("actions/GetCustomer/<uuid:customer_id>", GetCustomerView.as_view()),
    path("actions/UpdateCustomer", UpdateCustomerView.as_view()),
    path("actions/DeleteCustomer/<uuid:customer_id>", DeleteCustomerView.as_view()),
    path("actions/UpsertCustomer", UpsertCustomerView.as_view()),
    path("actions/BulkUpdateCustomers", BulkUpdateCustomersView.as_view()),
    path("queries/ActiveCustomers", ActiveCustomersView.as_view()),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: django-drf-postgres)
- concept customer.Customer (ENTITY)            → realized: Customer Django model + fields
- concept customer.ServiceAgent (ACTOR)         → realized: auth principal/role; policy authority
      + CustomerUpdatePolicy permission (has_perm "customer.update_customer")
- concept customer.UpdateCustomerWork (WORK)    → realized: services.update_customer is the
      update handler (the work performed on the record)
- concept customer.CustomerUpdated (EVENT, immutable) → realized: events.customer_updated Signal,
      emitted by record_customer_updated on committed update/upsert
- relationship agent-performs-update (PARTICIPATION) → realized: event carries the acting
      ServiceAgent (request.user) alongside the UpdateCustomerWork sender
- relationship update-changes-customer (TRANSFORMATION) → realized: event carries the changed
      customer_id + new version (work -> Customer)
- lifecycle CustomerLifecycle                   → realized: State TextChoices + assert_transition guard
- action customer.CreateCustomer (create)       → realized: services.create_customer + CreateCustomerView (201)
- action customer.GetCustomer (query/read)      → realized: services.get_customer + GetCustomerView
- action customer.UpdateCustomer (update)       → realized: services.update_customer (transaction.atomic,
      conditional idempotency, filter(...).update version guard, mutate={name}) — deep walkthrough
- action customer.DeleteCustomer (delete)       → realized: services.delete_customer (conditional, 204) + view
- action customer.UpsertCustomer (upsert)       → realized: services.upsert_customer (update_or_create,
      selection=identity, atomic) + UpsertCustomerView (PUT)
- action customer.BulkUpdateCustomers (bulk-update) → realized: services.bulk_update_customers
      (per-record transaction = best-effort, optimistic guard, many-in/many-out) + view
- collectionTransform customer.ActiveCustomers (filter) → realized: services.active_customers +
      ActiveCustomersView GET /queries/ActiveCustomers (bounded, predicate=status Active)
- rule customer.CustomerUpdateConstraint (CONSTRAINT) → realized: policy.CustomerUpdateConstraint
      validator, enforced by enforce_policy in every mutating command
- policy customer.CustomerUpdatePolicy          → realized: policy.Policy engine (deny-overrides)
      over its rule(s), wired into the CustomerUpdatePolicy DRF permission
- OpenAPI/Swagger                               → realized: drf-spectacular /api/schema + /api/docs
      (all actions + the ActiveCustomers query via @extend_schema)
- experience / design                           → out-of-tier: frontend owns these
dropped: []
```
