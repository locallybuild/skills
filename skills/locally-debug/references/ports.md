# Fixed Ports

Locally listens on a fixed set of loopback ports. They are not configurable, so a skill
or script can state them literally rather than discovering them.

Running more than one instance side by side isn't supported today. If that's something
you need, say so in Locally's Discord - what gets built next is driven by what people
ask for.

| Port | Surface | What it's for |
|---|---|---|
| `5664` | App Configuration | Application configuration served to other Locally components |
| `5673` | DNS | Resolves `*.locally` to `127.0.0.1` |
| `5674` | CI control | Start/stop and readiness signalling for a `locally ci` instance |
| `5675` | State store | Holds runtime resource state |
| `5676` | Event log | Records events for the audit/activity surfaces |
| `5677` | Token service | Issues tokens |
| `5678` | Dashboard | The web UI, and the quickest way to check whether an instance is up |
| `5679` | Directory | The seeded Entra-style directory (users, groups, service principals) |
| `5680` | Control plane | The API that provisions and manages resources |

## Data-Plane Ports

The table above is the control and infrastructure surface. The emulated Azure services
listen separately, and these are the ports a connection string or SDK client actually
talks to:

| Port | Service |
|---|---|
| `5660` | Storage (blob, queue, table, file) |
| `5661` | Key Vault |
| `5662` | Service Bus, Event Hubs and IoT Hub over HTTPS |
| `5663` | Functions / App Service |
| `5664` | App Configuration |
| `5665` | Cosmos DB |
| `5666` | Cosmos DB for MongoDB |
| `5667` | Container Registry |
| `5668` | Monitor, Application Insights and Log Analytics |
| `5671` | Service Bus, Event Hubs and IoT Hub over AMQP |
| `5883` | IoT Hub over MQTT |

Three services share `5662` and `5671`, and Monitor, App Insights and Log Analytics
share `5668` - so a port alone does not identify a service. Don't reverse a connection
string from this table: get it from `locally <service> connection-string`, which is
right whether or not these numbers move.

The control and infrastructure table was verified live against a running instance on
2026-08-22 (`lsof -nP -iTCP -sTCP:LISTEN` for the TCP surfaces, `lsof -nP -iUDP` for
DNS) - every port had something bound to it. The data-plane table is read from the
product's own service metadata rather than observed live, so a service nothing has
created yet may have nothing listening on its port.

Checking whether an instance is up:

```bash
locally validate
```

It ends with whether an instance is up, and needs no flags of its own. Read the output
rather than the exit code - it exits 0 either way.

Probing `5678` directly works too, but it is HTTPS with a certificate from Locally's own
CA, so a client that doesn't trust that CA refuses the connection - which is not the same
as nothing listening. Skip verification (`curl -k`, or your client's equivalent) when the
CA isn't trusted, and treat any HTTP status as "something answered".
