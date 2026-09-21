# Data-Plane Commands

`locally storage`, `locally servicebus`, `locally eventhub`, `locally iothub` and
`locally function` manage resources inside a running instance directly, without
wrapping `az` or another tool. Most resource types share the same shape -
`add | delete | list`, several also add `show`, and the message-bearing ones add
`peek` and `send` - but the shape isn't perfectly uniform across every type, so check
the table for the one you're using rather than assuming.

Every subcommand takes `--help` for its exact flags; what follows is what each one
does and the flags that matter, verified against a live build.

## Storage

`locally storage <container|queue|share|table> <subcommand>`, plus
`locally storage connection-string`.

| Resource | Subcommands | Key flags |
|---|---|---|
| `container` | `add`, `delete`, `list`, `show` | `--account`, `--name` |
| `queue` | `add`, `delete`, `list` | `--account`, `--name` |
| `share` | `add`, `delete`, `list` | `--account`, `--name` |
| `table` | `add`, `delete`, `list` | `--account`, `--name` |

Only `container` has `show`; `queue`, `share` and `table` don't.

`locally storage dashboard --name <account>` opens the account's blob endpoint in a
browser. It is for a person, not a script - don't run it on someone's behalf mid-task.

```bash
locally storage container add --account mystorageacct --name uploads
locally storage queue list --account mystorageacct
locally storage connection-string --name mystorageacct
```

## Service Bus

`locally servicebus <queue|topic> <subcommand>`, plus
`locally servicebus connection-string`.

| Resource | Subcommands | Key flags |
|---|---|---|
| `queue` | `add`, `delete`, `list`, `show`, `peek`, `send` | `--namespace`, `--name`; `add` also takes `--max-size-mb`, `--default-message-ttl`, `--lock-duration`, `--max-delivery-count`, `--dead-letter-on-expiry` |
| `topic` | `add`, `delete`, `list`, `show`, `peek`, `send` | `--namespace`, `--name`; `add` also takes `--max-size-mb`, `--default-message-ttl`; `peek` also takes `--subscription` (the topic subscription, not a Locally/Azure subscription) |

`peek` on both takes `--limit` (max 100, default 10) and `--dead-letter` (peek the
dead-letter sub-queue instead of active messages).

```bash
locally servicebus queue add --namespace mysbns --name orders
locally servicebus queue peek --namespace mysbns --name orders --limit 5
locally servicebus connection-string --name mysbns
```

`locally servicebus automation --name <namespace>` prints the namespace with its queues
and topics as JSON - the one to reach for when a script needs to read the shape of a
namespace, rather than parsing `list` output that is formatted for a person.

## Event Hub

`locally eventhub <hub|consumer-group> <subcommand>`, plus
`locally eventhub connection-string`.

| Resource | Subcommands | Key flags |
|---|---|---|
| `hub` | `add`, `delete`, `list`, `show`, `peek`, `send` | `--namespace`, `--name`; `add` also takes `--partition-count` (default 4); `peek` also takes `--partition` and `--limit` (default 10) |
| `consumer-group` | `add`, `delete`, `list`, `show` | `--namespace`, `--hub`, `--name` (no `peek`) |

```bash
locally eventhub hub add --namespace myehns --name telemetry --partition-count 8
locally eventhub hub peek --namespace myehns --name telemetry --partition 0
locally eventhub connection-string --name myehns
```

## IoT Hub

`locally iothub <device|twin> <subcommand>`, plus `locally iothub connection-string`.
`twin` has a different shape from the others - a twin belongs to a device rather than
being independently listable, so it only has `show` and `update`, no `add` / `delete`
/ `list`.

| Resource | Subcommands | Key flags |
|---|---|---|
| `device` | `add`, `delete`, `list`, `show`, `peek`, `send` | `--hub`, `--device`; `peek` also takes `--limit` (default 10) and reads D2C telemetry, not messages |
| `twin` | `show`, `update` | `--hub`, `--device`; `update` also takes `--desired` (a JSON string of desired properties) |

```bash
locally iothub device add --hub myiothub --device sensor-01
locally iothub twin update --hub myiothub --device sensor-01 --desired '{"targetTemp":21}'
locally iothub connection-string --name myiothub
```

## Function Apps

`locally function` deploys a package and invokes an HTTP-triggered function against
a running instance:

| Subcommand | What it does | Key flags |
|---|---|---|
| `deploy` | Deploys a zip package to a function app | `[zip file]` (positional), `--name`, `--env` (repeatable `KEY=VALUE`) |
| `invoke` | Invokes an HTTP-triggered function and prints the response | `--name`, `--endpoint` |

```bash
locally function deploy --name myfuncapp app.zip
locally function invoke --name myfuncapp --endpoint /api/hello
```

There's no `locally function connection-string` - function apps don't have one.

## Sending Messages

`send` seeds a queue, topic, hub or device with real messages, so client code has
something to read without writing a producer first. It exists on `servicebus queue`,
`servicebus topic`, `eventhub hub` and `iothub device`, and they share a core:

| Flag | What it does |
|---|---|
| `--body` | Inline message body |
| `--body-file` | Read the body from a file instead |
| `--content-type` | Content-Type of the body |
| `--count` | Send this many copies (default 1) |
| `--property` | Custom property as `key=value`, repeatable |

Then per-surface:

| Surface | Also takes |
|---|---|
| `servicebus queue` / `topic` | `--session-id` for session-enabled entities; `--dead-letter` to seed **straight into the dead-letter sub-queue**, with `--dead-letter-reason` and `--dead-letter-description` |
| `eventhub hub` | `--partition-key` to route the event |
| `iothub device` | `--hub` and `--device`, sending D2C telemetry |

```bash
# Seed a queue, then read it back
locally servicebus queue send --namespace mysbns --name orders --body '{"id":1}' --count 5
locally servicebus queue peek --namespace mysbns --name orders

# Put a message straight into the dead-letter queue, to test dead-letter handling
locally servicebus queue send --namespace mysbns --name orders --body '{"id":2}' \
  --dead-letter --dead-letter-reason "poison"
```

**`--dead-letter` is the useful one.** Testing dead-letter handling otherwise means
sending a message and failing it `--max-delivery-count` times; this puts it there
directly. Note it is a flag on `send`, not on `add` - `--dead-letter-on-expiry` on
`add` is a different thing, a queue property that dead-letters expired messages.

## Opening a Dashboard

`storage`, `servicebus`, `eventhub`, `iothub` and `function` each have a `dashboard`
subcommand that opens that resource's UI in a browser, taking `--name`:

```bash
locally servicebus dashboard --name mysbns
```

These are for a person to run. Opening a browser window on someone's machine mid-task
is not a step to take unasked - offer the command instead.

## Connection Strings

Every namespace/account-level resource type has a `connection-string` subcommand
that prints its primary connection string, taking a single `--name`:

```bash
locally storage connection-string --name <storage account>
locally servicebus connection-string --name <Service Bus namespace>
locally eventhub connection-string --name <Event Hub namespace>
locally iothub connection-string --name <IoT Hub>
```
