# Chaos Surfaces and Faults

`locally chaos` injects transient failures into a running instance so client code can
be tested against them: throttling, outages, dropped connections, latency, and a
handful of surface-specific faults. Every fault has **one rate** that applies to any
request no rule claims, plus (on most surfaces) any number of **rules** that override
that rate for a narrower scope. Rules are overrides, not a filter - a request matching
no rule still runs at the fault's own rate. "Everywhere except one place" is therefore
written as a rate of 100 plus a rule at 0 for that place, not a rate of 0 plus a rule at
100.

Arming any fault turns its own master switch on automatically. There is no separate
"turn chaos on" step before setting a rate.

## The 11 Surfaces

| Surface | Scope | What it covers |
|---|---|---|
| `control-plane` | subscription | ARM requests - resource provisioning and management |
| `directory` | tenant | Entra ID / Microsoft Graph requests |
| `cosmos` | subscription | Cosmos DB data plane |
| `eventgrid` | subscription | Event Grid data plane |
| `eventhub` | subscription | Event Hubs data plane |
| `functions` | subscription | Functions data plane |
| `keyvault` | subscription | Key Vault data plane |
| `managedhsm` | subscription | Managed HSM data plane |
| `monitor` | subscription | Monitor data plane |
| `servicebus` | subscription | Service Bus data plane |
| `storage` | subscription | Storage data plane |

`control-plane` and the nine data-plane surfaces are subscription-scoped, and share one
master switch (`locally chaos enable` / `locally chaos disable`). `directory` is
tenant-scoped and carries its own separate switch (`locally chaos directory enable` /
`locally chaos directory disable`) - the top-level switch does not touch it, and its own
switch does not touch anything else.

## Faults on `cosmos`, `eventgrid`, `eventhub`, `functions`, `keyvault`, `managedhsm`, `monitor`, `servicebus`, `storage`

These nine data-plane surfaces carry the same six faults:

| Fault | Simulates |
|---|---|
| `403` | Forbidden |
| `429` | Too Many Requests (throttling) |
| `500` | Internal Server Error |
| `drop-connection` | The connection is dropped mid-request - no HTTP response at all |
| `latency` | Delay before responding. `--seconds` is a ceiling: each firing rolls a random delay between 0 and that many seconds. Arming this fault with a percentage but no `--seconds` is refused. |
| `outage` | The surface is unreachable |

Each fault also has `reset` (drop one rule, or the whole fault back to zero) and `show`
(print the surface's current configuration) as subcommands, plus `locally chaos
<surface> reset` and `locally chaos <surface> show` at the surface level for all faults
at once.

Rules on these nine surfaces are scoped with `--location` (e.g. `london`). Region
names come from the location set the install has applied - the default set is
Locally's own city-scale names (`berlin`, `london`, `oslo`, ...), not Azure's. Run
`locally regions list` for the active set rather than assuming an Azure region name
like `westeurope` resolves.

```bash
# Throttle everywhere
locally chaos storage 429 --percentage 100

# Throttle everywhere except one location
locally chaos storage 429 --percentage 100
locally chaos storage 429 --percentage 0 --location london

# Add latency, capped at 30 seconds
locally chaos storage latency --percentage 50 --seconds 30

# Put one rule back, then the whole fault back to zero
locally chaos storage 429 reset --location london
locally chaos storage reset

# See what's configured
locally chaos storage show
```

## Faults on `control-plane`

`control-plane` carries the same six faults as the data-plane surfaces, plus five more
that only make sense for ARM:

| Fault | Simulates |
|---|---|
| `lro-delay` | Delays completion of a long-running operation. `--seconds` ceiling, same 0..N roll as `latency`. |
| `lro-failure` | A long-running operation fails after it has started, rather than failing the initial request synchronously. |
| `out-of-capacity` | An out-of-capacity error for the requested SKU or region. |
| `quota-exceeded` | A subscription quota-exceeded error. |
| `recase-names` | Resource or property names come back in different casing than requested. |

Rules on `control-plane` are scoped with `--location` **or** `--plugin` (an ARM
provider namespace, e.g. `Microsoft.Compute`) - the only surface with two scope axes:

```bash
# Inject 500s on 10% of ARM requests
locally chaos control-plane 500 --percentage 10

# An outage in one location, for one plugin only
locally chaos control-plane outage --percentage 100 --location london --plugin Microsoft.Storage
```

## Faults on `directory`

`directory` has five of the base six faults - **no `outage`** - plus one fault of its
own:

| Fault | Simulates |
|---|---|
| `403` | Forbidden |
| `429` | Too Many Requests (throttling) |
| `500` | Internal Server Error |
| `drop-connection` | The connection is dropped mid-request |
| `latency` | Delay before responding. `--seconds` ceiling. |
| `eventual-consistency` | A newly-written directory object takes longer to become visible to reads. `--seconds` ceiling. |

Graph is regionless and has no plugins, so a `directory` fault is a single flat rate -
there is no `--location` or `--plugin` scoping, and no rules. `directory` also has its
own `enable` / `disable` subcommands, separate from the top-level switch that covers
`control-plane` and the data planes.

## Checking and Clearing State

`locally chaos show` prints the configuration for every subscription-scoped surface
(`control-plane` plus the nine data planes) in one shot; `locally chaos directory show`
covers the Directory separately. Per-surface `show` (`locally chaos storage show`) and
per-fault `show` narrow further.

To put things back, use `reset` - at whichever scope matches what was armed:

```bash
locally chaos storage 429 reset   # one fault: zeroes its rate, drops its rules
locally chaos storage reset       # one surface: every fault on it
```

**`--percentage 0` is not an "off" switch.** The rate only governs requests no rule
claims, so zeroing it leaves every rule armed and still firing:

```bash
locally chaos storage 429 --percentage 100
locally chaos storage 429 --percentage 50 --location london
locally chaos storage 429 --percentage 0    # london STILL throttles at 50%
```

Only `reset` clears rules. When a fault has been turned off, read the `show` output
rather than skimming it - a surviving rule is listed on its own line under the fault
("any plugin in london  50%"), directly below the zeroed "All other requests" line.

`locally chaos disable` (or `locally chaos directory disable`) is a third action again:
it turns the relevant master switch off without clearing rates or rules, so everything
is still configured when the switch goes back on. After finishing a chaos test, reach
for `reset` rather than leaving faults armed.

All of these commands need a running instance - they configure the control plane, the
same way `locally logs` and `locally audit` read from one. There is no way to inspect
or edit chaos configuration without something listening on 5680.
