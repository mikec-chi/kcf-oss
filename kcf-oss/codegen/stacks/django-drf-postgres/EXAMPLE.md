# Single-shot example — Django + DRF + Django ORM + PostgreSQL

This realizes the reference `business-application` model in this stack. Imitate
its layering and idioms; substitute the target model's concepts, attributes,
lifecycle, and action contract.

## Input (excerpt of the KCF IR)

```jsonc
// concept customer.Customer: identity customerId:UUID, required name:String, optional email:String
// lifecycle CustomerLifecycle: Active->Suspended, Suspended->Active, Active->Archived (terminal Archived)
// action customer.UpdateCustomer: update/record, selection=identity, mutate=[name],
//   idempotency=conditional, atomicity=atomic, concurrency=optimistic,
//   authorization=customer.CustomerUpdatePolicy
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
```

### `customers/services.py`
```python
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, APIException

from .models import Customer


class Conflict(APIException):
    status_code = 409
    default_detail = "version conflict"


@transaction.atomic                                     # atomicity = atomic
def update_customer(customer_id, name, expected_version) -> Customer:
    """Realizes customer.UpdateCustomer.

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
    return Customer.objects.get(pk=customer_id)
```

### `customers/permissions.py`
```python
from rest_framework.permissions import BasePermission


class CustomerUpdatePolicy(BasePermission):
    """authorization = customer.CustomerUpdatePolicy."""
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.has_perm("customer.update_customer"))
```

### `customers/views.py`
```python
from rest_framework.views import APIView
from rest_framework.response import Response

from .permissions import CustomerUpdatePolicy
from .serializers import UpdateCustomerRequest, CustomerResponse
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
        )
        return Response(CustomerResponse(customer).data)


# urls.py: path("actions/UpdateCustomer", UpdateCustomerView.as_view())
```

### `customers/tests/test_update_customer.py`
```python
import pytest
from django.core.exceptions import ValidationError

from customers.models import Customer, assert_transition
from customers.services import update_customer, Conflict


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
    with pytest.raises(ValidationError):
        assert_transition(Customer.State.ARCHIVED, Customer.State.ACTIVE)  # not declared
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
from customers.views import UpdateCustomerView

urlpatterns = [
    path("actions/UpdateCustomer", UpdateCustomerView.as_view()),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

## Coverage self-audit
```
Coverage self-audit  (tier: backend, stack: django-drf-postgres)
- concept customer.Customer        → realized: Customer Django model + fields
- action  customer.UpdateCustomer  → realized: services.update_customer (transaction.atomic,
      conditional idempotency, filter(...).update version guard, mutate={name})
- lifecycle CustomerLifecycle      → realized: State TextChoices + assert_transition guard
- policy customer.CustomerUpdatePolicy → realized: CustomerUpdatePolicy DRF permission
- OpenAPI/Swagger                  → realized: drf-spectacular /api/schema + /api/docs
- experience / design              → out-of-tier: frontend owns these
dropped: []
```
