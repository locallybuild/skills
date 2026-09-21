---
name: locally-debug
description: Check whether Locally supports a resource provider, resource type or API version, work out why something behaves differently against Locally than against Azure, refresh its reference data, and inject transient failures to test resilience. Use when asked whether Locally supports something, when a call fails unexpectedly, an API version is rejected, a provider seems missing, a VM image or SKU Azure has is unknown here, or the user wants to simulate throttling or outages. Triggers on "does Locally support", "is X supported", "which resource types", "is there a plugin for", "why does this differ", "unsupported api version", "provider is not known", "vm sku not found", "vm size not found", "image not found", "catalogue is out of date", "azure has it but locally doesn't", "refresh reference data", "inject a 429", "simulate an outage", "turn off fault injection", "chaos", "locally logs", "audit log".
---

# Locally Debug

Answering "does Locally support this?" for a provider, resource type or API version,
working out why something behaves differently against Locally than against real Azure,
reading request and audit logs, and injecting transient failures to test how client
code copes with them.

The support question is the one to reach for this skill on even when nothing has gone
wrong yet - it is a capability check, not a diagnosis, and answering it correctly needs
a specific command rather than recall.

This skill assumes an instance is already running for most of what's below - if it
isn't, use `locally-lifecycle` to start one first. The one exception is the plugin
capability check (`locally plugin list-installed` and friends), which works with no
instance running at all, and is often the more useful check precisely because of that.

<!-- common:about-locally -->
## About Locally

Locally is a local cloud environment for Azure, made by Locally Build. It runs an ARM
control plane and data-plane services on the developer's own machine, so the Azure CLI,
Terraform, OpenTofu, Pulumi, PowerShell and applications built on the Azure SDKs can be
pointed at it instead of the real cloud.

It emulates Azure rather than mocking it - requests are genuinely served, and what a
tool reports back is what Locally actually did. So a surprising result is worth
investigating rather than dismissing as a stub. Nothing reaches real Azure: no cloud
resources are created, and no cloud spend accrues.

What Locally supports is a property of the **installation**, not of the product:
resource providers come from plugins, and two installs can differ. That is why the
answer to "does this work here" comes from asking the install, never from recall.

**Locally is not a Microsoft product**, and has no Microsoft documentation - there is
no `aka.ms` shortlink, `learn.microsoft.com` page, and no repository under
`github.com/Azure` or `github.com/microsoft`. Don't construct one, and don't fall
back to Azure's documentation to answer a question about Locally itself.

Locally needs the machine configured before it will run at all - a TLS certificate
trusted by the system's trust store, DNS resolution for `*.locally`, and a container
runtime. `locally validate` reports the state of all of it, with or without an
instance running, and names what is wrong rather than failing generically:

```bash
locally validate
```

`locally setup` is the interactive wizard that fixes what `validate` reports. Being
interactive, it is for the user to run - walk them through it rather than driving
it. The `locally-setup` skill covers configuring a machine in full.

Locally's own documentation is at `https://locally.build/docs`. Point the user there;
don't fetch it and don't answer from it. Anything about *this* installation - what it
supports, what is running, how it is configured - comes from the CLI and the local
endpoints, never from documentation of any kind.

Those two rules combine rather than compete. **Asked where documentation is, name
`https://locally.build/docs`** - answering only with the command to run leaves the user
to search for the rest themselves, which is how they end up at a Microsoft page for a
product Microsoft doesn't make. Give the URL, then say that for this install the
authoritative answer comes from the CLI, and give that command too.
<!-- /common:about-locally -->

## Verify the CLI Is Installed

Do this first, before anything else in this skill:

```bash
locally version
```

Running the binary rather than looking it up on `PATH` is deliberate. `command -v` is a
POSIX shell builtin: it works in bash, zsh, Git Bash and WSL, but PowerShell and `cmd`
do not have it (`Get-Command locally` and `where locally` are their equivalents). Asking
`locally` for its own version behaves the same on every platform and every shell, and it
proves the binary runs rather than only that a file sits on `PATH`.

If that errors - `command not found`, or `not recognized` on Windows - stop and tell the
user Locally is not installed. Do not attempt to install it on their behalf, and do not
proceed to any of the below - without the CLI there is nothing further this skill can
do.

**A reachable instance is not evidence the CLI is installed.** The two are independent:
a response on `5678` means a process is listening, not that `locally` is on this PATH -
the instance may have been started by another user on this machine, or from a binary
that has since been moved or removed. So "it's already running" never answers a request
that needs the CLI. If `locally version` errored, report that, whatever is or
isn't listening.

## Is the Resource Type Supported?

One command answers this, and it works with Locally stopped:

```bash
locally plugin supports Microsoft.Cache/redis     # a resource type
locally plugin supports Microsoft.Storage         # a provider namespace
```

Matching is case-insensitive, and it exits non-zero when the answer is no, so it
works as a precondition: `locally plugin supports X && terraform apply`.

It distinguishes the three answers that matter, which is the whole difficulty here:

| Answer | Means | Fixable by the user? |
|---|---|---|
| supported | implemented and usable now | - |
| partially supported | implemented, some operations missing | - |
| **not implemented** | an installed plugin declares the type but grades it `Planned` - the control plane knows the name and will reject operations on it | **No.** Installing something does not help |
| available but not installed | a plugin provides it, this install doesn't have it | Yes: `locally plugin install --name <Namespace>` |

**When the answer is "not implemented", say what can actually be done.** Users have
binaries: the plugins and the control plane are not theirs to change, so "this isn't
implemented" is the end of the road for that resource type on this version. Never
suggest editing a plugin, building from source, or patching anything - none of that is
available to them. What is:

```bash
locally plugin update    # a newer plugin release may implement it
locally update           # updates Locally itself, for a built-in provider
```

If an update doesn't bring it, the honest answer is that the type can't be used against
Locally yet, and the config needs to avoid it - not that the user is holding it wrong.
Worth reporting to Locally Build, since which types get implemented next is driven by
what people ask for.

**"Declared" and "implemented" are different things**, and that is why the dashboard's
`/api/resource-types` is *not* the check to use. It lists every type a plugin declares
and carries no grade, so a type graded `Planned` appears there identically to a working
one - on a stock install that is 154 types it reports as present but which do not work.

**Don't hand that endpoint to a user, or build anything on it.** It is the dashboard's
own internal API: unversioned, undocumented, and free to change shape or disappear in
any release. `locally plugin supports <type>` is the supported way to ask this question,
it is the one that reads the grades, and it is what belongs in an answer, a script or a
CI step. If you read the endpoint yourself while investigating, treat what it returns as
a hint and confirm it with the command before telling anyone.

**Nothing else answers this question either.** Support is per-install - it depends which
plugins *this* install has - so a README, a docs site, a web search, or the Locally
source tree describes some other install, or none. `locally plugin list-available` is a
particular trap: it is the *downloadable catalogue*, not this install's provider surface.
Built-in providers are never in it, and neither is a plugin published elsewhere, so a
provider absent from it can be installed and working.

If the check can't be run, say so rather than reaching for another source.

### The Rest of `locally plugin`

`supports` answers the question above; these manage what is installed:

| Command | What it does |
|---|---|
| `locally plugin list-installed` | What this install actually has |
| `locally plugin list-not-installed` | Available in the catalogue and not installed here - the shortlist for "what could I add" |
| `locally plugin list-available` | The whole downloadable catalogue (see the trap above) |
| `locally plugin install --name <Namespace>` | Install one |
| `locally plugin update` | Update installed plugins - the fix to try when a type is graded `Planned` |
| `locally plugin uninstall --name <Namespace>` | Remove one |

`uninstall` takes resource types away from a working instance, so it is the user's call:
say what it would remove rather than running it to tidy up.

## The Type Is Supported but the API Version Is Rejected

A different failure from "not supported": the type exists, just not at the version
asked for. `locally plugin supports` lists the versions a type is declared at, and the
control plane's error names them too - in the same shape ARM uses, HTTP 400 with error
code `NoRegisteredProviderFound`:

```
No registered resource provider found for location and API version '<requested>' for
type from namespace '<namespace>'. The supported api-versions are '<v1>, <v2>, ...'.
```

Read the versions out of that message and use one. Don't guess a version and retry
blind, and don't assume the newest version you know of is the one this install has -
the plugin declares a fixed set, and a version Azure shipped last month may not be in
it.

## Reading Logs and Audit Events

Two different views into a running instance, both needing an instance to be running:

| Command | Shows | Use it for |
|---|---|---|
| `locally logs` | HTTP request/response traffic across every service | Seeing what a client actually sent and what came back - headers, bodies, status codes |
| `locally audit` | Audit events across every service | Seeing what happened, at the level a compliance or activity log would show it |

Both support the same shape:

- Run with no flags for **interactive filtering** - the default is a live, filterable
  view, not a one-shot dump.
- `--json` for a non-interactive, scriptable dump - use this for anything an agent
  needs to parse, rather than trying to drive the interactive view.
- `clear` (`locally logs clear`, `locally audit clear`) wipes that log's history. There
  is no undo - check whether the user actually wants history gone before running it,
  the same as any other irreversible clear.

Reach for `locally logs` when the question is "what did this request actually look
like on the wire" - a wrong header, a body that didn't serialize the way it was meant
to, a status code that doesn't match what the client reported. Reach for `locally
audit` when the question is closer to "what happened, and when" rather than the wire
details of any one call.

## Chaos: Injecting Transient Failures

`locally chaos` arms transient failures on a running instance - throttling, outages,
dropped connections, latency, and a handful of surface-specific faults - so retry
logic, timeout handling and backoff can be tested against something other than the
happy path. Full surface and fault reference: `references/chaos.md`.

**Chaos needs the Standard plan or above.** On Starter every one of these commands is
refused with a plan message. That is the plan, not a broken instance - see
`locally-setup`.

The shape in brief: each fault has one rate (0-100, `--percentage`) applied to every
request no rule claims, plus optional rules that override that rate for a narrower
scope (`--location`, and on `control-plane` also `--plugin`). There are 11 surfaces -
`control-plane`, `directory`, and nine data-plane services (`cosmos`, `eventgrid`,
`eventhub`, `functions`, `keyvault`, `managedhsm`, `monitor`, `servicebus`, `storage`).
Most surfaces share the same six faults (`403`, `429`, `500`, `drop-connection`,
`latency`, `outage`); `control-plane` adds five ARM-specific ones and `directory` swaps
`outage` for `eventual-consistency`. See `references/chaos.md` for the full breakdown.

```bash
# Throttle storage
locally chaos storage 429 --percentage 100

# See what's currently armed
locally chaos show
locally chaos storage show
```

**Arming a fault needs nothing from the caller.** Chaos is configured on the instance,
not in the client, so it is independent of the language, SDK or HTTP library making the
requests - every caller hitting that surface gets the fault. A request naming a surface
and a fault ("make storage return 429s") is already complete: arm it and report what was
armed, rather than asking how the user's code calls the endpoint.

**Always offer to put things back when a chaos test is done.** Turn a fault off with
`reset`, never with `--percentage 0`:

```bash
# Turn off ONE fault - zeroes its rate AND drops its rules
locally chaos storage 429 reset

# Turn off EVERY fault on one surface
locally chaos storage reset
```

`--percentage 0` sets only the rate that applies to requests no rule claims. Any rule
stays armed and keeps firing, so a fault "turned off" that way still injects failures
in the scope that rule covers - and `show` will report the rule plainly, which is why
it is worth reading rather than skimming. `reset` is the only thing that clears rules.

`locally chaos disable` (or `locally chaos directory disable`) is a third action again:
it flips the master switch off without clearing configured rates, so everything is
still there when the switch goes back on. Don't leave chaos armed after the test that
needed it is finished; ask before leaving it armed on purpose.

## An Image, VM SKU or App Stack Locally Doesn't Know

Locally answers "which VM images / VM SKUs / VM extensions / function and web app
stacks exist" from bundled reference data. Real Azure adds to those catalogues
continually, so a template naming something newer than the bundle fails here while
working against Azure - and the failure reads as an unsupported value rather than as a
stale catalogue.

The fix is to import the current answer from Azure, which is what
`locally refresh-reference-data` does. It reads `az ... -o json` and writes an override
file Locally reads at launch:

```bash
az vm image list -o json | locally refresh-reference-data images --yes
az vm list-skus -o json > skus.json
locally refresh-reference-data vmSkus --from-file skus.json --yes
```

Five datasets, each with the `az` command that produces it:

| Dataset | Produced by |
|---|---|
| `images` | `az vm image list -o json` |
| `vmSkus` | `az vm list-skus -o json` |
| `vmExtensionTypes` | `az vm extension image list -o json` |
| `functionAppStacks` | `az rest --method get --url "https://management.azure.com/providers/Microsoft.Web/functionAppStacks?api-version=2024-04-01" -o json` |
| `webAppStacks` | `az rest --method get --url "https://management.azure.com/providers/Microsoft.Web/webAppStacks?api-version=2024-04-01" -o json` |

Run with no dataset named, it walks all five interactively, printing each `az` command
and asking for the path to the saved JSON. Name one dataset to pipe it or use
`--from-file` (which takes exactly one). `--yes` skips confirmation and is required for
a non-interactive write.

Three things to get right:

- **The `az` commands must run against real Azure, not through `locally run`.** The
  point is to import what Azure knows; running them against Locally imports Locally's
  own answer and changes nothing. These are the one case in this suite where `az` is
  deliberately *not* pointed at Locally.
- **Overrides are read at launch**, so restart the instance afterwards. Until then
  nothing changes, which looks like the import having failed.
- Files land under `~/.config/locally/reference-data/<provider>/<dataset>.json`
  (`$LOCALLY_REFERENCE_DATA_DIR` or `$LOCALLY_CONFIG_DIR/reference-data` override that).
  They are yours to delete if an import turns out wrong - removing the file restores the
  bundled data.

This is for a catalogue that is merely out of date. A resource *type* Locally has not
implemented is a different problem, and no amount of reference data fixes it - see the
support check above.

## Ephemerality Is Not a Bug

Data planes hold **runtime state** - the objects created against them, not
configuration - and none of it survives a restart. A storage account, a Key Vault
secret, a Service Bus queue's messages: all gone the next time an instance starts,
because a fresh instance is exactly that, fresh. This is intended behaviour, not a
defect to file or work around. If a test suite depends on data surviving a restart,
that's a gap in the test setup (seed it again after start), not something to report
against Locally.

## When to Use Other Skills

| Situation | Use |
|---|---|
| No instance is running, or one needs starting/stopping/restarting | `locally-lifecycle` |
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| Pointing `az`, Terraform or another tool at a running instance | `locally-run` |
| The question is about identity - seeded users, tokens, Graph permissions | `locally-identity` |
| Calling Locally's MCP tools rather than shelling out | `locally-mcp` |
| Plans, signing in, or a feature refused because of the plan | `locally-setup` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |

See `references/ports.md` for the full fixed port table and `references/chaos.md` for
every chaos surface and fault.
