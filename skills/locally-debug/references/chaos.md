# Chaos Surfaces and Faults

`locally chaos` injects transient failures into a running instance so client code can
be tested against them. Every fault has **one rate** (`--percentage`, 0-100) that applies
to anything no rule claims, plus any number of **rules** that override that rate for a
narrower scope. Rules are overrides, not a filter - a request matching no rule still
runs at the fault's own rate. "Everywhere except one place" is therefore written as a
rate of 100 plus a rule at 0 for that place, not a rate of 0 plus a rule at 100.

Setting a fault turns its surface's master switch on automatically. There is no
separate "turn chaos on" step before setting a rate.

**`locally chaos --help` is the authority on what this install has.** The surface and
fault lists below were read from v2026.11; run `locally chaos <surface> --help` for the
faults a surface carries before arming one that isn't listed here.

## Kinds of Fault

Faults come in two shapes, and arming one needs different flags:

- **Per-request faults** roll on each request (or message, or connection attempt):
  `403`, `429`, `500`, `outage`, `drop-connection`, `latency`, `stale-read` and most of
  the service-specific ones. They need only `--percentage`, plus a duration where the
  fault has one.
- **Scheduled faults** act on running services rather than on single requests:
  `incident`, `failover`, `freeze`, `exit`, `restart`, `disconnect`, `link-stolen` and
  `stream-reset`. **`--interval` is required** - every interval the fault rolls
  `--percentage` against each service in scope, and on a hit acts on it. Nothing else
  sets a scheduled fault off, so one armed without `--interval` never fires.

`drop-connection` and `latency` are both: they act per request, and with `--interval`
they *also* cut or stall connections that are already open (AMQP, MQTT, WebSockets,
gRPC, MongoDB wire protocol, database sessions). For periodic cuts with no per-request
drops, arm `disconnect` instead.

## Flags

| Flag | Meaning |
|---|---|
| `--percentage N` | How often the fault fires, 0-100. Required. |
| `--seconds` / `--millis` | The fault's duration. A bare number is in the flag's unit; `250ms` or `1.5s` means what it says. `N` picks 0..N each firing; `MIN-MAX` (e.g. `30-120`) picks within that range. Required whenever a fault that has a duration fires (`latency`, `incident`, `failover`, `freeze`, `stale-read`, `cold-start`, `slow-body`, `delivery-delay`, `object-being-deleted`, `eventual-consistency`, `lro-delay`, ...). |
| `--interval` | How often a scheduled fault starts (`30s`, `10m`). Required on scheduled faults; optional on `drop-connection` / `latency`, where it adds live-connection action. |
| `--retry-after` | The `Retry-After` a throttling or outage answer carries (`5s`, `500ms`). Omitted, the service's usual hint is used. Only offered on faults where a client reads it; refused elsewhere. |
| `--location` | Rule scope: one region, e.g. `london`. |
| `--name` | Rule scope: one resource - `acct1` in any resource group, `rg1/acct1` in one. On `storage`, add an endpoint to narrow further: `--name acct1:blob` (`blob`, `queue`, `table`, `file`, `dfs`). On `directory` / `identity`, a user or application. |
| `--plugin` | Rule scope, `control-plane` only: one ARM provider namespace, e.g. `Microsoft.Compute`. |
| `--subscription` / `--tenant` | Which subscription (or, on `directory` / `identity`, tenant) to configure. Defaults to the configured one. |

A value flag left out when editing keeps what the row already has. Region names come
from the location set the install has applied - the default set is Locally's own
city-scale names (`berlin`, `london`, `oslo`, ...), not Azure's. Run `locally regions
list` rather than assuming `westeurope` resolves.

## The 28 Surfaces

| Surface | Scope | What it covers |
|---|---|---|
| `control-plane` | subscription | ARM requests - resource provisioning and management |
| `directory` | tenant | Microsoft Graph / directory objects |
| `identity` | tenant | Sign-in and tokens: the token, discovery, signing-key and managed identity endpoints |
| `apimanagement` | subscription | API Management gateway, including WebSocket APIs |
| `appconfiguration` | subscription | App Configuration stores and replicas |
| `containerapps` | subscription | Container Apps |
| `containerinstances` | subscription | Container groups' connections (through Locally's network proxy) and the groups themselves |
| `containerregistry` | subscription | Container Registry, its token endpoint and layer downloads |
| `cosmos` | subscription | Cosmos DB - SQL API, Table API, MongoDB wire protocol and Direct mode |
| `durabletask` | subscription | Durable Task Scheduler, including workers' live gRPC streams |
| `eventgrid` | subscription | Event Grid, over HTTP and MQTT, and its deliveries |
| `eventhub` | subscription | Event Hubs, over HTTP and AMQP |
| `functions` | subscription | **Function Apps only** - Web Apps moved to `webapps` in v2026.11 |
| `horizondb` | subscription | HorizonDB connections |
| `iothub` | subscription | IoT Hub, over HTTP, AMQP and MQTT |
| `keyvault` | subscription | Key Vault data plane |
| `managedhsm` | subscription | Managed HSM data plane |
| `monitor` | subscription | **Queries, metrics and alert notifications only** - ingestion moved to `monitoringestion` in v2026.11 |
| `monitoringestion` | subscription | Sending telemetry and logs to Monitor / Application Insights / Log Analytics |
| `mysql` | subscription | MySQL Flexible Server connections |
| `postgresql` | subscription | PostgreSQL Flexible Server connections |
| `redis` | subscription | Redis connections |
| `servicebus` | subscription | Service Bus, over HTTP and AMQP |
| `sql` | subscription | Azure SQL Database connections |
| `storage` | subscription | Blob, Queue, Table, File and Data Lake endpoints, and Storage's Event Grid events |
| `virtualmachines` | subscription | VM guests, and `locally connect` sessions |
| `webapps` | subscription | Web Apps, including live WebSocket and gRPC connections |

`control-plane` and every data-plane surface are subscription-scoped and share one
master switch (`locally chaos enable` / `locally chaos disable`). `directory` and
`identity` are tenant-scoped and share a separate switch (`locally chaos directory
enable` / `disable`, or the same under `identity`) - the top-level switch does not
touch them, and theirs does not touch anything else.

**Identity faults affect Locally's own commands too.** Anything that signs in -
`locally servicebus`, the deploy and runbook tools of `locally mcp` - takes the fault like any other client. Locally's background work (autoscale,
diagnostic settings) does not. If a `locally` command starts failing to get a token
mid-test, check `locally chaos identity show` before anything else.

Database surfaces (`mysql`, `postgresql`, `sql`, `redis`) answer `403`, `429` and `500`
with **the engine's own equivalent error**, not an HTTP status - a client sees what
that engine would send.

## Faults by Surface

| Surface | Faults |
|---|---|
| `control-plane` | `403` `429` `500` `drop-connection` `incident` `latency` `lro-delay` `lro-failure` `out-of-capacity` `outage` `quota-exceeded` `recase-names` |
| `directory` | `403` `429` `500` `drop-connection` `eventual-consistency` `incident` `latency` `outage` `stale-read` |
| `identity` | `403` `429` `500` `clock-skew` `discovery-unavailable` `drop-connection` `incident` `invalid-grant` `jwks-unavailable` `latency` `msi-unavailable` `outage` `slow-down` |
| `apimanagement` | `403` `429` `500` `502` `504` `disconnect` `drop-connection` `incident` `latency` `outage` `partial-response` `slow-body` |
| `appconfiguration` | `403` `429` `500` `drop-connection` `failover` `incident` `latency` `outage` `stale-read` |
| `containerapps` | `403` `429` `500` `502` `504` `cold-start` `disconnect` `drop-connection` `exit` `freeze` `latency` `outage` `partial-response` `restart` `slow-body` |
| `containerinstances` | `disconnect` `drop-connection` `exit` `freeze` `incident` `latency` `outage` `restart` |
| `containerregistry` | `403` `429` `500` `drop-connection` `incident` `latency` `outage` `partial-response` `slow-body` |
| `cosmos` | `403` `429` `500` `disconnect` `drop-connection` `failover` `incident` `latency` `outage` `partial-response` `partition-split` `request-timeout` `retry-with` `session-not-available` `stale-read` `write-forbidden` |
| `durabletask` | `403` `429` `500` `disconnect` `drop-connection` `latency` `outage` `stream-reset` |
| `eventgrid` | `403` `429` `500` `connack-refuse` `delivery-delay` `delivery-drop` `disconnect` `drop-connection` `duplicate-delivery` `handshake-failure` `latency` `lock-lost` `outage` `reorder` |
| `eventhub` | `403` `429` `500` `delivery-delay` `disconnect` `drop-connection` `duplicate-delivery` `entity-disabled` `latency` `link-stolen` `outage` `quota-exceeded` `reorder` |
| `functions` | `403` `429` `500` `502` `504` `cold-start` `delivery-delay` `delivery-drop` `drop-connection` `duplicate-delivery` `exit` `freeze` `latency` `outage` `partial-response` `restart` `slow-body` |
| `horizondb` | `disconnect` `drop-connection` `incident` `latency` `outage` |
| `iothub` | `403` `429` `500` `connack-refuse` `delivery-delay` `delivery-drop` `disconnect` `drop-connection` `entity-disabled` `latency` `outage` `quota-exceeded` |
| `keyvault` | `403` `429` `500` `drop-connection` `incident` `latency` `object-being-deleted` `outage` |
| `managedhsm` | `403` `429` `500` `drop-connection` `incident` `latency` `object-being-deleted` `outage` |
| `monitor` | `403` `429` `500` `delivery-delay` `delivery-drop` `drop-connection` `duplicate-delivery` `incident` `latency` `outage` `request-timeout` `stale-read` |
| `monitoringestion` | `403` `429` `500` `drop-connection` `incident` `latency` `outage` `partial-success` `quota-exceeded` |
| `mysql` | `403` `429` `500` `disconnect` `drop-connection` `failover` `latency` `outage` `restart` `too-many-connections` |
| `postgresql` | `403` `429` `500` `disconnect` `drop-connection` `failover` `latency` `outage` `restart` `too-many-connections` |
| `redis` | `403` `429` `500` `busy` `disconnect` `drop-connection` `failover` `latency` `loading` `moved` `outage` `restart` `too-many-connections` |
| `servicebus` | `403` `429` `500` `delivery-delay` `disconnect` `drop-connection` `duplicate-delivery` `entity-disabled` `latency` `link-stolen` `lock-lost` `outage` `quota-exceeded` `reorder` |
| `sql` | `403` `429` `500` `disconnect` `drop-connection` `failover` `latency` `outage` `restart` `too-many-connections` |
| `storage` | `403` `429` `500` `delivery-delay` `delivery-drop` `drop-connection` `duplicate-delivery` `failover` `incident` `latency` `lock-lost` `outage` `partial-response` `request-timeout` `slow-body` `stale-read` |
| `virtualmachines` | `disconnect` `drop-connection` `exit` `freeze` `latency` `outage` `restart` |
| `webapps` | `403` `429` `500` `502` `504` `cold-start` `disconnect` `drop-connection` `exit` `freeze` `latency` `outage` `partial-response` `restart` `slow-body` `stream-reset` |

## What Each Fault Does

### Common

| Fault | Simulates |
|---|---|
| `403` / `429` / `500` | The service's own forbidden, throttled or server-error answer. On a database surface, the engine's equivalent. |
| `outage` | Every matching request fails outright, as during a regional or provider outage. |
| `drop-connection` | The connection is dropped before a response. With `--interval`, also cuts live connections. |
| `latency` | A random delay before responding (needs a duration). With `--interval`, also stalls live connections. |
| `incident` | Scheduled: the scope is unavailable for the rolled duration, then recovers. |
| `disconnect` | Scheduled: live connections are closed cleanly, in the protocol's own terms, so the client reconnects. |

### Gateways and sites

| Fault | Simulates |
|---|---|
| `502` / `504` | The front end can't reach, or times out waiting for, the app behind it. |
| `partial-response` | Headers and part of the body, then the connection is cut. |
| `slow-body` | The response body is paced slowly (per 32 KiB). |
| `cold-start` | Requests get the platform's warm-up `503` for the rolled duration, as an app starting from cold. |
| `freeze` / `exit` / `restart` | Scheduled: the workload is paused for the duration, killed (its restart policy decides what's next), or restarted the way its own restart action does. On the database surfaces, `restart` restarts the server. |
| `stream-reset` | Scheduled: live gRPC streams are reset with `RST_STREAM`. |

### Messaging and events

| Fault | Simulates |
|---|---|
| `delivery-delay` / `delivery-drop` / `duplicate-delivery` | A message, event or function trigger is held for the duration, not delivered, or delivered twice. Event Grid push treats a drop as an endpoint failure and retries. |
| `reorder` | A message is swapped with the next in its batch. |
| `lock-lost` | The lock or lease the client holds is gone - a Service Bus message lock, a blob lease, a queue message's pop receipt. |
| `link-stolen` | Scheduled: live AMQP receiver links are detached as stolen. |
| `entity-disabled` | `MessagingEntityDisabled` / `DeviceDisabled`. |
| `quota-exceeded` | The service's own quota error - a full queue or event hub; on `monitoringestion` the daily cap; on `control-plane` a `409 QuotaExceeded` on PUT. |
| `connack-refuse` | An MQTT connection refused in its CONNACK. |
| `handshake-failure` | An Event Grid webhook's validation handshake fails (only subscriptions that haven't delivered since Locally started). |

### Data and replicas

| Fault | Simulates |
|---|---|
| `failover` | Scheduled: the primary is unavailable for the duration and any secondary or replica serves reads only, then the primary returns. On `cosmos`, a rule scoped with `--location` fails only that region's endpoint, so the SDK fails over to the next. |
| `stale-read` | A read inside the window after a write sees the object as it was before that write. On `storage` it's served from the read-access secondary; on `monitor` it's ingestion latency. |
| `request-timeout` | The service's own server-side timeout (Cosmos `408`, Storage `OperationTimedOut`, a query timing out). |
| `partition-split` / `session-not-available` / `retry-with` / `write-forbidden` | Cosmos DB's `410/1002`, `404/1002`, `449` and `403/3` - the answers its SDKs retry on. |
| `object-being-deleted` | After a delete (or recover), the name answers `409 ObjectIsBeingDeleted` (or `ObjectIsBeingRecovered`) for the duration. |
| `partial-success` | A telemetry batch accepted with `206`, rejecting some of its items. |
| `too-many-connections` | A new connection refused with the engine's connection-limit error. |
| `busy` / `loading` / `moved` | Redis's `-BUSY`, `-LOADING` and `-MOVED`. |

### Identity and directory

| Fault | Simulates |
|---|---|
| `eventual-consistency` | A newly-written directory object takes the duration to become visible to reads. |
| `slow-down` | A device code poll told `slow_down`. |
| `invalid-grant` | A refresh token rejected with `AADSTS700082`. |
| `jwks-unavailable` / `discovery-unavailable` | `503` from the signing keys or OpenID discovery endpoint. |
| `clock-skew` | A token whose `nbf` is 5 minutes in the future. |
| `msi-unavailable` | A managed identity token request fails with `500`/`503`. |

### Control plane only

| Fault | Simulates |
|---|---|
| `lro-delay` | Extra delay before a long-running operation completes (needs a duration). |
| `lro-failure` | A long-running operation fails after it has started. |
| `out-of-capacity` | `AllocationFailed`-style capacity errors on creates and capacity-affecting updates. |
| `recase-names` | Resource group names come back in a different case. |

## Examples

```bash
# Throttle storage everywhere except one location, telling clients to wait 5s
locally chaos storage 429 --percentage 100 --retry-after 5s
locally chaos storage 429 --percentage 0 --location london

# Slow one storage account's blob endpoint by up to 800ms
locally chaos storage latency --percentage 100 --millis 800 --name acct1:blob

# Every 10 minutes, maybe take a Key Vault down for 30-120 seconds
locally chaos keyvault incident --percentage 50 --seconds 30-120 --interval 10m

# Every 30 seconds, maybe freeze a container group for 5-20 seconds
locally chaos containerinstances freeze --percentage 50 --seconds 5-20 --interval 30s

# Cut a quarter of live Service Bus connections every 30s
locally chaos servicebus disconnect --percentage 25 --interval 30s

# Fail Cosmos DB's london region over, so the SDK moves to the next region
locally chaos cosmos failover --percentage 100 --seconds 60 --interval 2m --location london

# Stop every sign-in from getting a token
locally chaos identity outage --percentage 100

# An outage in one location, for one ARM provider only
locally chaos control-plane outage --percentage 100 --location london --plugin Microsoft.Storage
```

## Checking and Clearing State

`locally chaos show` prints every subscription-scoped surface (`control-plane` plus the
data planes) in one shot. `locally chaos directory show` and `locally chaos identity
show` cover the tenant-scoped surfaces separately. Per-surface `show` (`locally chaos
storage show`) narrows further.

To put things back, use `reset` - at whichever scope matches what was armed:

```bash
locally chaos storage 429 reset --location london   # one rule
locally chaos storage 429 reset                     # one fault: zeroes its rate, drops its rules
locally chaos storage reset                         # one surface: every fault on it
```

**`--percentage 0` is not an "off" switch.** The rate only governs requests no rule
claims, so zeroing it leaves every rule armed and still firing:

```bash
locally chaos storage 429 --percentage 100
locally chaos storage 429 --percentage 50 --location london
locally chaos storage 429 --percentage 0    # london STILL throttles at 50%
```

Only `reset` clears rules. When a fault has been turned off, read the `show` output
rather than skimming it - a surviving rule is listed on its own line under the fault,
directly below the zeroed "All other requests" line. Clearing a scheduled fault also
ends any window it has open (a frozen workload thaws, an incident recovers).

`locally chaos disable` (or `locally chaos directory disable`) is a third action again:
it turns the relevant master switch off without clearing rates or rules, so everything
is still configured when the switch goes back on. After finishing a chaos test, reach
for `reset` rather than leaving faults armed - and remember that `reset` on one surface
leaves every other surface as it was, so check `locally chaos show` and the two tenant
`show`s if more than one was armed.

All of these commands need a running instance - they configure the control plane, the
same way `locally logs` and `locally audit` read from one. There is no way to inspect
or edit chaos configuration without something listening on 5680.
