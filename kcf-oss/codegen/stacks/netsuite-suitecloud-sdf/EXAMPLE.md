# Single-shot example — NetSuite customizations (SuiteCloud SDF + SuiteScript 2.1)

This realizes the reference `business-application` model as a **SuiteCloud SDF
Account Customization Project**: platform-native objects (custom record types,
fields, a status list, a role, a SuiteFlow workflow, a saved search) plus
SuiteScript 2.1 (a RESTlet for the action contract, a User Event script for
validation + lifecycle guard + the immutable event log, a Client Script for
instant feedback), all packaged for `suitecloud project:deploy`.

The platform owns the datastore, the runtime, and the default UI — so there is **no
OpenAPI mandate** here (a backend concern). The customization surface *is* the
deliverable; a RESTlet is generated only because the model declares programmatic
actions.

## Input (excerpt of the KCF IR)
```jsonc
// ENTITY customer.Customer { identity customerId: UUID; required name: String; optional email: String }
// ACTOR customer.ServiceAgent ; WORK customer.UpdateCustomerWork ; EVENT customer.CustomerUpdated (immutable)
// lifecycle CustomerLifecycle: Active -> Suspended, Suspended -> Active, Active -> Archived (terminal)
// actions: CreateCustomer(create), GetCustomer(read), UpdateCustomer(update; mutate=name; optimistic; conditional idempotency),
//          DeleteCustomer(delete), UpsertCustomer(upsert), BulkUpdateCustomers(bulk-update; scope=set; best-effort)
// collection ActiveCustomers (filter: "customer status is Active")
// rule CustomerUpdateConstraint (CONSTRAINT): "email is present when a customer is Active"
// policy CustomerUpdatePolicy: authority ServiceAgent; rule CustomerUpdateConstraint; deny-overrides
```

## SDF project layout
```
customer-service/
  src/
    manifest.xml
    deploy.xml
    Objects/
      customlist_cs_customer_state.xml       # lifecycle states
      customrecord_cs_customer.xml           # ENTITY Customer + fields (incl. status, version)
      customrecord_cs_customer_updated.xml   # EVENT CustomerUpdated (immutable log)
      customrole_cs_service_agent.xml        # ACTOR + policy coarse gate
      customworkflow_cs_customer_life.xml     # lifecycle (SuiteFlow, UI transitions)
      customsearch_cs_active_customers.xml   # collection ActiveCustomers
    FileCabinet/
      SuiteScripts/
        customer/
          cs_policy.js          # deny-overrides policy engine (shared module)
          cs_customer_ue.js      # User Event: identity uniqueness, CONSTRAINT, lifecycle guard, event log
          cs_customer_cs.js      # Client Script: instant CONSTRAINT feedback
          cs_customer_restlet.js # RESTlet: the full action contract
```

## Output

### `src/Objects/customlist_cs_customer_state.xml` — lifecycle states
```xml
<customlist scriptid="customlist_cs_customer_state">
  <name>Customer State</name>
  <customvalues>
    <customvalue scriptid="val_active"><value>Active</value></customvalue>
    <customvalue scriptid="val_suspended"><value>Suspended</value></customvalue>
    <customvalue scriptid="val_archived"><value>Archived</value></customvalue>
  </customvalues>
</customlist>
```

### `src/Objects/customrecord_cs_customer.xml` — ENTITY Customer
```xml
<customrecordtype scriptid="customrecord_cs_customer">
  <recordname>Customer</recordname>
  <includename>T</includename>
  <showid>T</showid>
  <customrecordcustomfields>
    <!-- identity customerId (UUID). NetSuite has its own internal id; this is the
         business identity: mandatory + uniqueness enforced in the User Event script. -->
    <customrecordcustomfield scriptid="custrecord_cs_customer_id">
      <label>Customer Id</label><fieldtype>FREEFORMTEXT</fieldtype>
      <ismandatory>T</ismandatory><isunique>T</isunique>
    </customrecordcustomfield>
    <!-- required name: String -->
    <customrecordcustomfield scriptid="custrecord_cs_customer_name">
      <label>Name</label><fieldtype>FREEFORMTEXT</fieldtype><ismandatory>T</ismandatory>
    </customrecordcustomfield>
    <!-- optional email: String -->
    <customrecordcustomfield scriptid="custrecord_cs_customer_email">
      <label>Email</label><fieldtype>EMAIL</fieldtype><ismandatory>F</ismandatory>
    </customrecordcustomfield>
    <!-- lifecycle status: SELECT over the state list -->
    <customrecordcustomfield scriptid="custrecord_cs_customer_status">
      <label>Status</label><fieldtype>SELECT</fieldtype>
      <selectrecordtype>[scriptid=customlist_cs_customer_state]</selectrecordtype>
      <ismandatory>T</ismandatory>
    </customrecordcustomfield>
    <!-- optimistic-concurrency token -->
    <customrecordcustomfield scriptid="custrecord_cs_customer_version">
      <label>Version</label><fieldtype>INTEGER</fieldtype>
      <ismandatory>T</ismandatory><defaultvalue>0</defaultvalue>
    </customrecordcustomfield>
  </customrecordcustomfields>
</customrecordtype>
```

### `src/Objects/customrecord_cs_customer_updated.xml` — EVENT (immutable log)
```xml
<customrecordtype scriptid="customrecord_cs_customer_updated">
  <recordname>Customer Updated</recordname>
  <!-- immutable: the ServiceAgent role grants CREATE only (no EDIT/DELETE) -->
  <customrecordcustomfields>
    <customrecordcustomfield scriptid="custrecord_cu_customer">
      <label>Customer</label><fieldtype>SELECT</fieldtype>
      <selectrecordtype>[scriptid=customrecord_cs_customer]</selectrecordtype>
    </customrecordcustomfield>
    <customrecordcustomfield scriptid="custrecord_cu_agent">
      <label>Agent</label><fieldtype>SELECT</fieldtype><selectrecordtype>-4</selectrecordtype>
    </customrecordcustomfield>
    <customrecordcustomfield scriptid="custrecord_cu_at">
      <label>Occurred At</label><fieldtype>DATETIMETZ</fieldtype>
    </customrecordcustomfield>
  </customrecordcustomfields>
</customrecordtype>
```

### `src/Objects/customrole_cs_service_agent.xml` — ACTOR + policy coarse gate
```xml
<role scriptid="customrole_cs_service_agent">
  <name>Service Agent</name>
  <permissions>
    <!-- full rights on Customer; CREATE-only on the immutable event log -->
    <permission><permkey>[scriptid=customrecord_cs_customer]</permkey><permlevel>FULL</permlevel></permission>
    <permission><permkey>[scriptid=customrecord_cs_customer_updated]</permkey><permlevel>CREATE</permlevel></permission>
  </permissions>
</role>
```

### `src/Objects/customworkflow_cs_customer_life.xml` — lifecycle (SuiteFlow, UI transitions)
```xml
<!-- Declarative UI-driven state machine on Customer. The exact same transition set
     is enforced in cs_customer_ue.js for RESTlet/CSV changes (they must agree). -->
<workflow scriptid="customworkflow_cs_customer_life">
  <name>Customer Lifecycle</name>
  <recordtypes>[scriptid=customrecord_cs_customer]</recordtypes>
  <fieldsetting><field>custrecord_cs_customer_status</field></fieldsetting>
  <initstate>[scriptid=wfs_active]</initstate>
  <workflowstates>
    <workflowstate scriptid="wfs_active"><name>Active</name>
      <workflowtransitions>
        <workflowtransition scriptid="wft_a_susp"><tostate>[scriptid=wfs_suspended]</tostate><buttonaction>Suspend</buttonaction></workflowtransition>
        <workflowtransition scriptid="wft_a_arch"><tostate>[scriptid=wfs_archived]</tostate><buttonaction>Archive</buttonaction></workflowtransition>
      </workflowtransitions>
    </workflowstate>
    <workflowstate scriptid="wfs_suspended"><name>Suspended</name>
      <workflowtransitions>
        <workflowtransition scriptid="wft_s_act"><tostate>[scriptid=wfs_active]</tostate><buttonaction>Reactivate</buttonaction></workflowtransition>
      </workflowtransitions>
    </workflowstate>
    <workflowstate scriptid="wfs_archived"><name>Archived</name></workflowstate> <!-- terminal -->
  </workflowstates>
</workflow>
```

### `src/Objects/customsearch_cs_active_customers.xml` — collection ActiveCustomers (filter)
```xml
<savedsearch scriptid="customsearch_cs_active_customers">
  <definition>Active Customers</definition>
  <!-- predicate: "customer status is Active" -->
  <searchtype>customrecord_cs_customer</searchtype>
  <filters>
    <filter><field>custrecord_cs_customer_status</field><operator>ANYOF</operator>
      <values><value>[scriptid=val_active]</value></values></filter>
  </filters>
</savedsearch>
```

### `src/FileCabinet/SuiteScripts/customer/cs_policy.js` — deny-overrides policy engine
```javascript
/**
 * @NApiVersion 2.1
 * Realizes policy customer.CustomerUpdatePolicy (authority ServiceAgent; deny-overrides).
 * Mirrors the IR `policies` block: any DENY wins; otherwise an explicit PERMIT is required.
 */
define([], () => {
  const ROLE_SERVICE_AGENT = 'customrole_cs_service_agent';

  // Rules the policy composes. CustomerUpdateConstraint is enforced structurally in the
  // User Event (see cs_customer_ue.js); here we gate the *authority* to act.
  function evaluatePolicy(ctx) {
    // ctx: { roleScriptId, operation }  → 'permit' | { deny: reason }
    const decisions = [
      ctx.roleScriptId === ROLE_SERVICE_AGENT ? 'permit' : { deny: 'not a Service Agent' }
    ];
    // deny-overrides: any deny wins
    const deny = decisions.find(d => d && d.deny);
    return deny ? deny : (decisions.includes('permit') ? 'permit' : { deny: 'no applicable permit' });
  }
  return { evaluatePolicy, ROLE_SERVICE_AGENT };
});
```

### `src/FileCabinet/SuiteScripts/customer/cs_customer_ue.js` — validation, lifecycle guard, event log
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType UserEventScript
 * Deploy on customrecord_cs_customer. Realizes:
 *   - identity uniqueness (customerId)         [entity identity]
 *   - rule CustomerUpdateConstraint            [CONSTRAINT: email present when Active]
 *   - lifecycle guard                          [only declared transitions are legal]
 *   - immutable event log CustomerUpdated      [EVENT, afterSubmit]
 */
define(['N/search', 'N/record', 'N/runtime', './cs_policy'],
(search, record, runtime, policy) => {

  const LEGAL = { Active: ['Suspended', 'Archived'], Suspended: ['Active'], Archived: [] };
  const F = {
    id: 'custrecord_cs_customer_id', name: 'custrecord_cs_customer_name',
    email: 'custrecord_cs_customer_email', status: 'custrecord_cs_customer_status',
    version: 'custrecord_cs_customer_version'
  };
  const stateText = (rec) => rec.getText({ fieldId: F.status });

  function beforeSubmit(ctx) {
    if (ctx.type === ctx.UserEventType.DELETE) return;
    const rec = ctx.newRecord;

    // authority gate (deny-overrides) — RESTlet & UI both pass through here
    const decision = policy.evaluatePolicy({ roleScriptId: runtime.getCurrentUser().roleId, operation: ctx.type });
    if (decision.deny) throw errorConflict('FORBIDDEN', 'policy denied: ' + decision.deny);

    // identity uniqueness (custom fields have no native unique constraint)
    const cid = rec.getValue({ fieldId: F.id });
    const dupes = search.create({ type: 'customrecord_cs_customer',
      filters: [[F.id, 'is', cid], 'AND', ['internalid', 'noneof', rec.id || '@NONE@']] }).run().getRange({ start: 0, end: 1 });
    if (dupes.length) throw errorConflict('DUPLICATE', 'customerId already exists: ' + cid);

    // rule CustomerUpdateConstraint: email present when Active
    if (stateText(rec) === 'Active' && !rec.getValue({ fieldId: F.email }))
      throw errorConflict('CONSTRAINT', 'email is required when a customer is Active');

    // lifecycle guard: reject undeclared transitions
    if (ctx.type === ctx.UserEventType.EDIT && ctx.oldRecord) {
      const from = ctx.oldRecord.getText({ fieldId: F.status }), to = stateText(rec);
      if (from !== to && !(LEGAL[from] || []).includes(to))
        throw errorConflict('ILLEGAL_TRANSITION', `${from} -> ${to} is not a declared transition`);
    }
  }

  function afterSubmit(ctx) {
    if (ctx.type === ctx.UserEventType.DELETE) return;
    // EVENT customer.CustomerUpdated (immutable) — append-only log
    const ev = record.create({ type: 'customrecord_cs_customer_updated' });
    ev.setValue({ fieldId: 'custrecord_cu_customer', value: ctx.newRecord.id });
    ev.setValue({ fieldId: 'custrecord_cu_agent', value: runtime.getCurrentUser().id });
    ev.setValue({ fieldId: 'custrecord_cu_at', value: new Date() });
    ev.save();
  }

  function errorConflict(name, message) { return require('N/error').create({ name, message, notifyOff: true }); }
  return { beforeSubmit, afterSubmit };
});
```

### `src/FileCabinet/SuiteScripts/customer/cs_customer_cs.js` — instant CONSTRAINT feedback
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType ClientScript
 * Mirrors rule CustomerUpdateConstraint for instant UI feedback. The User Event
 * (server) remains the source of truth.
 */
define([], () => {
  function saveRecord(ctx) {
    const rec = ctx.currentRecord;
    const active = rec.getText({ fieldId: 'custrecord_cs_customer_status' }) === 'Active';
    if (active && !rec.getValue({ fieldId: 'custrecord_cs_customer_email' })) {
      alert('Email is required when a customer is Active.');
      return false;
    }
    return true;
  }
  return { saveRecord };
});
```

### `src/FileCabinet/SuiteScripts/customer/cs_customer_restlet.js` — the action contract
```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * Realizes the action contract as a RESTlet. Map operation+scope to HTTP verbs:
 *   get  → GetCustomer (read)            post → CreateCustomer (create)
 *   put  → UpdateCustomer / UpsertCustomer / BulkUpdateCustomers
 *   delete → DeleteCustomer
 * Record save is atomic per record; optimistic concurrency via the version field;
 * a command writes only its `mutate` fields; conditional idempotency is a no-op on no-change.
 */
define(['N/record', 'N/search', 'N/error'], (record, search, error) => {
  const TYPE = 'customrecord_cs_customer';
  const F = { id: 'custrecord_cs_customer_id', name: 'custrecord_cs_customer_name',
    email: 'custrecord_cs_customer_email', status: 'custrecord_cs_customer_status',
    version: 'custrecord_cs_customer_version' };

  const findByBusinessId = (cid) => {
    const r = search.create({ type: TYPE, filters: [[F.id, 'is', cid]], columns: ['internalid'] })
      .run().getRange({ start: 0, end: 1 });
    return r.length ? r[0].getValue('internalid') : null;
  };
  const dto = (rec) => ({
    customerId: rec.getValue(F.id), name: rec.getValue(F.name), email: rec.getValue(F.email),
    status: rec.getText(F.status), version: Number(rec.getValue(F.version))
  });

  // GetCustomer (read) — selection: identity
  function get(q) {
    const iid = findByBusinessId(q.customerId);
    if (!iid) throw error.create({ name: 'NOT_FOUND', message: q.customerId });
    return dto(record.load({ type: TYPE, id: iid }));
  }

  // CreateCustomer (create) — atomic, conditional idempotency (business id is the key)
  function post(body) {
    const existing = findByBusinessId(body.customerId);
    if (existing) return dto(record.load({ type: TYPE, id: existing })); // idempotent create
    const rec = record.create({ type: TYPE });
    rec.setValue({ fieldId: F.id, value: body.customerId });
    rec.setValue({ fieldId: F.name, value: body.name });
    if (body.email != null) rec.setValue({ fieldId: F.email, value: body.email });
    rec.setValue({ fieldId: F.status, value: statusVal(body.status || 'Active') });
    rec.setValue({ fieldId: F.version, value: 0 });
    return dto(record.load({ type: TYPE, id: rec.save() }));
  }

  // put dispatches UpdateCustomer / UpsertCustomer / BulkUpdateCustomers by shape
  function put(body) {
    if (Array.isArray(body)) return bulkUpdate(body);        // BulkUpdateCustomers (scope=set)
    if (body.upsert) return upsert(body);                    // UpsertCustomer
    return update(body);                                     // UpdateCustomer
  }

  // UpdateCustomer — mutate={name}; optimistic concurrency; conditional idempotency
  function update(body) {
    const iid = findByBusinessId(body.customerId);
    if (!iid) throw error.create({ name: 'NOT_FOUND', message: body.customerId });
    const rec = record.load({ type: TYPE, id: iid });
    if (Number(rec.getValue(F.version)) !== Number(body.version))
      throw error.create({ name: 'CONFLICT', message: 'stale version' });     // optimistic guard
    if (rec.getValue(F.name) === body.name) return dto(rec);                    // idempotent no-op
    rec.setValue({ fieldId: F.name, value: body.name });                        // only the mutate field
    rec.setValue({ fieldId: F.version, value: Number(rec.getValue(F.version)) + 1 });
    return dto(record.load({ type: TYPE, id: rec.save() }));
  }

  // UpsertCustomer — create-or-update by business identity
  function upsert(body) { return findByBusinessId(body.customerId) ? update(body) : post(body); }

  // BulkUpdateCustomers — scope=set, atomicity best-effort → per-item try/catch + per-item result
  function bulkUpdate(items) {
    return items.map(it => {
      try { return { customerId: it.customerId, ok: true, record: update(it) }; }
      catch (e) { return { customerId: it.customerId, ok: false, error: e.name }; }
    });
  }

  // DeleteCustomer — conditional idempotency (missing = success)
  function del(q) {
    const iid = findByBusinessId(q.customerId);
    if (iid) record.delete({ type: TYPE, id: iid });
    return { deleted: !!iid };
  }

  function statusVal(text) {
    return { Active: 'val_active', Suspended: 'val_suspended', Archived: 'val_archived' }[text];
  }
  return { get, post, put, delete: del };
});
```

### `src/manifest.xml` + `src/deploy.xml`
```xml
<!-- manifest.xml -->
<manifest projecttype="ACCOUNTCUSTOMIZATION">
  <projectname>customer-service</projectname>
  <frameworkversion>1.0</frameworkversion>
</manifest>
```
```xml
<!-- deploy.xml — deploy every object + script with `suitecloud project:deploy` -->
<deploy>
  <objects><path>~/Objects/*</path></objects>
  <files><path>~/FileCabinet/SuiteScripts/customer/*</path></files>
</deploy>
```

> The RESTlet, User Event, and Client Script also need `<scriptdeployment>` objects
> (audience/role = Service Agent) — generate one per script; omitted here for brevity
> but listed in the coverage self-audit as realized via `deploy.xml`.

### `__tests__/customer_restlet.test.js` (jest, N/* mocked)
```javascript
// happy path, illegal transition, stale-version conflict, and the CONSTRAINT.
jest.mock('N/record'); jest.mock('N/search'); jest.mock('N/error');
// - post() creates then returns the same record on a duplicate customerId (idempotent create)
// - update() with a mismatched version throws CONFLICT
// - beforeSubmit rejects Active -> (no email) with CONSTRAINT
// - beforeSubmit rejects Suspended -> Archived (not a declared transition) with ILLEGAL_TRANSITION
```

## Coverage self-audit
```
Coverage self-audit  (tier: platform, stack: netsuite-suitecloud-sdf)
- concept customer.Customer (ENTITY)          → realized: customrecord_cs_customer + custom fields (id/name/email/status/version)
- concept customer.ServiceAgent (ACTOR)       → realized: customrole_cs_service_agent (role; policy coarse gate)
- concept customer.UpdateCustomerWork (WORK)  → realized: the update process (RESTlet put + User Event), named on the event log
- concept customer.CustomerUpdated (EVENT, immutable) → realized: customrecord_cs_customer_updated (append-only; role has CREATE only) written in afterSubmit
- relationship agent-performs-update (PARTICIPATION) → realized: custrecord_cu_agent (ServiceAgent → work) on the event log
- relationship update-changes-customer (TRANSFORMATION) → realized: custrecord_cu_customer (work → Customer) on the event log
- lifecycle CustomerLifecycle                 → realized: customlist_cs_customer_state + status field + customworkflow_cs_customer_life (UI) + beforeSubmit guard (RESTlet/CSV); both enforce the same transition set
- action customer.CreateCustomer (create)     → realized: RESTlet post (idempotent create by business id)
- action customer.GetCustomer (read)          → realized: RESTlet get (selection: identity)
- action customer.UpdateCustomer (update)     → realized: RESTlet put→update (atomic save, optimistic version guard, conditional idempotency, mutate={name})
- action customer.DeleteCustomer (delete)     → realized: RESTlet delete (conditional idempotency)
- action customer.UpsertCustomer (upsert)     → realized: RESTlet put→upsert (create-or-update by business id)
- action customer.BulkUpdateCustomers (bulk-update, set) → realized: RESTlet put(array), best-effort per-item try/catch + per-item result
- collection customer.ActiveCustomers (filter) → realized: customsearch_cs_active_customers (status ANYOF Active)
- rule customer.CustomerUpdateConstraint (CONSTRAINT) → realized: beforeSubmit validation (server) + Client Script saveRecord (instant UI feedback)
- policy customer.CustomerUpdatePolicy (deny-overrides) → realized: customrole_cs_service_agent permissions (coarse) + cs_policy.evaluatePolicy() called in beforeSubmit (fine)
- deployment                                  → realized: SDF ACCOUNTCUSTOMIZATION project (manifest.xml/deploy.xml); `suitecloud project:deploy`; one scriptdeployment per script (audience = Service Agent)
- OpenAPI/Swagger                             → n/a: platform tier — NetSuite exposes the RESTlet directly; no OpenAPI mandate
- experience / design                         → delegated: NetSuite-native custom forms/UI (not declared in this model)
dropped: []
```
