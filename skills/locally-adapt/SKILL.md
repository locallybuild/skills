---
name: locally-adapt
description: Updates your Terraform, OpenTofu, Pulumi, ARM/Bicep, Azure CLI, PowerShell and Azure SDK configurations to work with both Locally and Azure from one definition. Use when a config written for real Azure needs to run against Locally too, when deciding how a config should detect which one it is on, when a resource, region, SKU or API version exists on one side and not the other, or when hardcoded endpoints, credentials, subscription IDs or locations need parameterising. Triggers on "work with both", "run against both locally and azure", "adapt this terraform", "make this config work with locally", "same config for azure and locally", "detect locally", "environment_is_locally", "TF_VAR_location", "injected variables", "conditional resource", "hardcoded subscription id", "hardcoded region", "hardcoded endpoint", "provider block", "one definition two targets", "portable config".
---

# Locally Adapt

Taking a configuration written for real Azure and making one definition serve both it
and Locally: what Locally supplies through the environment, what a config must therefore
stop hardcoding, how each tool asks which target it is on, and how to gate the parts
that only exist on one side.

**Most of this is authoring work, and needs no instance.** Reading a config, finding
what is hardcoded, rewriting it and checking the resource types it declares
(`locally plugin supports`) all work with Locally stopped. Only two things need a
running instance: `locally run env`, whose credentials are minted by it, and actually
applying. Finding nothing running is not a reason to hand the task back - do the work
that doesn't need one, then say that starting an instance is what remains.

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
proceed to any of the commands below - without the CLI there is nothing further this
skill can do.

## Automatic Configuration Is the Contract

`locally run` states the requirement in its own help text:

> This requires that the command in question supports Automatic Configuration - meaning
> that the credentials and configuration must be sourced from Environment Variables.

That is the whole of this skill in one sentence. `locally run` does not rewrite a
config or intercept a tool's traffic - it builds an environment and executes the tool
inside it. A tool that takes its endpoint, cloud and credentials from that environment
reaches Locally. A tool told those values in a file reaches whatever the file says,
which is real Azure.

So every dual-target decision reduces to one question, asked of each value in the
config:

**Does this come from the environment, or is it written into the file?**

Anything Locally supplies must not be restated in the config, because a config that
restates it wins - and then wins identically on both targets, which is precisely the
bug. Anything Locally cannot supply (a template parameter, a SKU name, a resource that
exists on one side only) has to be parameterised or gated instead.

## What Locally Supplies

Read the set off the install rather than recalling it - the values are per-install, and
several are per-invocation:

```bash
locally run env | grep -E '^(LOCALLY|TF_VAR|ARM_|AZURE_)'
```

The names are stable enough to design against; the values are not, and **this file
deliberately does not print them**. They group into six jobs:

| Group | Variables | What it means for a config |
|---|---|---|
| Which target | `LOCALLY_ENVIRONMENT`, `TF_VAR_environment_is_locally` | The flag a config branches on. Present and `true` under `locally run`; absent everywhere else |
| Credentials | `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` | Never write credentials into a dual-target config for either side |
| Endpoints | `ARM_RESOURCE_MANAGER_ENDPOINT`, `ARM_RESOURCE_MANAGER_AUDIENCE`, `ARM_ACTIVE_DIRECTORY_AUTHORITY_HOST`, `ARM_METADATA_HOSTNAME`, `AZURE_AUTHORITY_HOST`, `AZURE_MICROSOFT_GRAPH_ENDPOINT` | Locally points the tool at its own control plane. A config that sets any of these overrides that |
| Cloud selection | `ARM_ENVIRONMENT`, `AZURE_CLOUD`, `AZURE_DISABLE_INSTANCE_DISCOVERY`, `ARM_DISABLE_INSTANCE_DISCOVERY` | Locally presents itself as a custom cloud, with authority-metadata discovery turned off. Naming a cloud in the config breaks this |
| Subscriptions and tenants | `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`, `TF_VAR_primary_subscription_id`, `TF_VAR_secondary_subscription_id`, `TF_VAR_ternary_subscription_id` | A multi-subscription config needs no hardcoded UUIDs |
| Regions | `AZURE_LOCATION`, `TF_VAR_location` | The region to deploy into, from the install's active location set. `TF_VAR_location` fills a Terraform variable named `location` with no work at all |
| Test regions | `ARM_TEST_LOCATION`, `ARM_TEST_LOCATION_ALT`, `ARM_TEST_LOCATION_ALT2` | **For acceptance-test suites**, which need two or three distinct regions. Not the general-purpose region variable - reach for `AZURE_LOCATION` instead |

**Reading them is the point; capturing them is the anti-pattern.** Writing
`locally run env` output into a committed `.tfvars`, `.env`, `local.settings.json` or
stack config produces exactly the failure this skill exists to prevent: values that are
per-install and sometimes per-invocation, frozen into a file that another machine will
read and another subscription will contradict. `AZURE_CONFIG_DIR` is the sharpest
example - it is keyed to the credentials in use, so a captured one points the Azure CLI
at another identity's profile and the command then succeeds against the wrong
subscription. `locally-run` covers this in full. Let `locally run` set the environment
every time.

## The Four Things That Break a Dual-Target Config

### 1. Configuration that overrides the environment

The most common cause, and the least obvious, because the config looks more explicit
and more correct than the one that works. A provider block that pins
`subscription_id`, `tenant_id`, `environment` or `metadata_host`; an SDK client built
with a literal endpoint; a script that calls `az cloud set` - each of these takes
precedence over what `locally run` supplied, so the tool authenticates against Locally's
credentials and then talks to the cloud named in the file, or fails in a way that reads
like a Locally fault.

The fix is subtraction, not addition: **delete the value from the config and let the
environment carry it.** That also leaves the real-Azure path working, because the same
variables are how Azure's own tooling is configured in CI.

### 2. Hardcoded regions

Locally's region names are its own - a per-install *location set*, whose default is
city-scale names that exist nowhere in Azure. `locally regions list` is the authority
for a given install. A literal `"westeurope"` in a config cannot work here, and
Locally's own names cannot work against Azure.

This asymmetry is a safety feature rather than an obstacle: because the names don't
overlap, a config aimed at Locally cannot silently deploy to a real cloud, and one
aimed at Azure fails loudly here instead of half-succeeding. **Never "fix" it by
swapping the install's location set to a real cloud's names** - that removes the safety
net, needs the Team plan, and requires an empty install. `locally-run` covers the region
rules and the location set in full.

**Prefer inheriting the location over parameterising it.** A region only has to be named
once per deployment - where the resource group itself is created. Everything deployed
into it can take its location from the group, and a value that is never written down
can't be written down wrong:

| Surface | Inherit with |
|---|---|
| ARM template | `"location": "[resourceGroup().location]"` |
| Bicep | `param location string = resourceGroup().location`, then `location: location` |
| ARM/Bicep at subscription scope | `[deployment().location]` - there is no resource group to inherit from yet |
| Terraform / OpenTofu | `location = azurerm_resource_group.example.location` |

This is the strongest form of the fix, because it removes the difference from the
template rather than managing it: the same file is correct on both targets with no
parameter file, no variable and no branch.

**Inheriting is not permission to hardcode it one level up.** Somewhere a region does
have to be named - the resource group, or a subscription-scope deployment - and at that
point it still must not be a literal. Make it a variable or parameter so the call site
can override it per target:

```hcl
variable "location" {
  type        = string
  description = "Region for the resource group - Locally's own names differ from Azure's"
}

resource "azurerm_resource_group" "example" {
  name     = var.name
  location = var.location
}
```

**In Terraform and OpenTofu that variable fills itself in.** Locally injects
`TF_VAR_location`, so a variable named exactly `location` is supplied automatically
under `locally run` - the config above needs nothing on the command line here, and takes
its region from a tfvars file or CI variable against real Azure. Declaring it with no
default is what makes both halves work: Locally supplies one, and a real-Azure run that
forgets to fails loudly instead of deploying somewhere unintended.

Confirm the variable is actually there before relying on it - `locally run env` lists
what *this* install sets, and where `TF_VAR_location` is absent the region has to be
passed explicitly. That is the general rule for every variable in this skill, and it is
cheap to check.

Bicep's idiom does the same job differently, and is the shape to copy where there is no
injected variable: `param location string = resourceGroup().location` is an overridable
parameter whose *default* inherits, so callers get correct behaviour for free and can
still override it when they need to.

**Expand Locally's variables inside `locally run`, not outside it.** Wherever a
Locally-supplied region *does* have to reach a command line - `az`, Pulumi, a
`--parameters` override, or Terraform on an install without `TF_VAR_location` - the
obvious way to write it silently passes nothing:

```bash
locally run az group create -n rg -l "$AZURE_LOCATION"          # WRONG - empty
locally run sh -c 'az group create -n rg -l "$AZURE_LOCATION"'  # correct
```

The outer shell expands `$AZURE_LOCATION` *before* `locally run` executes, and the
outer shell is the one that doesn't have it - `locally run` builds that environment for
the process it starts. So the first form expands to `-l ""` and the command is handed an
empty region. Wrap a shell (single-quoted, so expansion is deferred) whenever a
Locally-supplied value has to appear in the command line itself, or set it as a variable
inside that shell: `locally run sh -c 'TF_VAR_location="$AZURE_LOCATION" terraform
apply'`.

This is why the injected variables are worth preferring wherever they exist: a value the
tool reads from the environment itself can't be lost to the wrong shell.

### 3. Hardcoded subscription and tenant UUIDs

A UUID written into a config is valid on exactly one install. Locally mints its own, and
publishes them as `ARM_SUBSCRIPTION_ID` / `ARM_TENANT_ID` plus, for Terraform,
`TF_VAR_primary_subscription_id`, `TF_VAR_secondary_subscription_id` and
`TF_VAR_ternary_subscription_id` - so even a config that spans three subscriptions needs
no literal.

### 4. Resources, SKUs, images and API versions that exist on one side only

The irreducible differences. What Locally supports is a property of the installation,
so this is asked of the install and never recalled:

```bash
locally plugin supports Microsoft.KeyVault/vaults
```

Check every type the config declares, not just the namespace - a provider can be
installed while a specific type is not implemented. VM sizes, images and app stacks are
a separate axis with their own answer, and API versions another; `locally-debug` covers
all three, including what to do when the answer is "not implemented" and no flag works
around it.

Once a difference is real, gate it rather than forking the config - which needs a way to
ask which target this is.

## How Each Surface Asks "Am I On Locally?"

| Surface | How it asks | Notes |
|---|---|---|
| Terraform / OpenTofu | `var.environment_is_locally` | From `TF_VAR_environment_is_locally`. Declare the variable with `default = false` so a real-Azure run needs no extra input |
| Pulumi | `LOCALLY_ENVIRONMENT` read from the process environment in the program's language | No Pulumi-specific variable exists. Read the environment, not stack config - see below |
| Azure CLI / shell scripts | `$LOCALLY_ENVIRONMENT` | Test for presence, not just truth |
| PowerShell | `$env:LOCALLY_ENVIRONMENT` | Same variable, read inside a `locally run pwsh` session - a session started any other way isn't on Locally |
| Azure SDK applications | `LOCALLY_ENVIRONMENT` via the language's environment accessor | See `references/azure-sdk.md` |
| ARM / Bicep | **It cannot.** | Templates have no access to the environment at all |

**The ARM and Bicep row is a structural limit, not an oversight.** A template is
evaluated by the control plane, which never sees the caller's environment, so there is
no expression that can detect Locally from inside one. That is why per-target parameter
files are the ARM answer rather than a stylistic preference - the branch has to happen
outside the template, in the parameters passed to it.

Fewer templates need that branch than it first appears, though. One whose resources take
`[resourceGroup().location]` and whose types Locally implements is already correct on
both targets, with nothing to parameterise and no second file to keep in step. Reach for
per-target parameters for the differences that survive that, not as the starting point.

## Terraform and OpenTofu

Scope here is `hashicorp/azurerm` and `Azure/azapi`. Both authenticate from the same
`ARM_*` variables, so both work under `locally run` with no provider-level changes -
which is the point of the next rule.

**Keep the provider block minimal.** Everything the block could set, the environment has
already set:

```hcl
provider "azurerm" {
  features {}
}
```

Adding `subscription_id`, `tenant_id`, `client_id`, `environment` or `metadata_host` to
that block overrides `locally run` and sends the provider somewhere else. If a value has
to be configurable, take it from a variable whose default comes from the environment
rather than writing it in HCL.

**Gate the differences with `count`.** One config, both targets, no second copy:

```hcl
variable "environment_is_locally" {
  type    = bool
  default = false
}

resource "azurerm_some_azure_only_thing" "example" {
  count = var.environment_is_locally ? 0 : 1
  # ...
}

locals {
  sku = var.environment_is_locally ? "Standard" : "Premium"
}
```

The `default = false` matters: it is what lets an unwrapped `terraform apply` against
real Azure run unchanged, with no tfvars file and no extra flag. Under `locally run`,
`TF_VAR_environment_is_locally` supplies `true` automatically.

Prefer this to a separate `.tfvars` per target. A tfvars file has to be selected on the
command line, which means every invocation is a chance to select the wrong one against
the wrong cloud; the environment variable cannot be mismatched, because the only thing
that sets it is the wrapper that also supplies the matching credentials.

### The Injected Variables

Terraform is the best-served surface here, because Locally supplies variables by name
rather than only as raw environment settings. Declare the variable, and `locally run`
fills it:

| Variable to declare | Injected as | What it saves |
|---|---|---|
| `environment_is_locally` | `TF_VAR_environment_is_locally` | Branching without a per-target tfvars file |
| `location` | `TF_VAR_location` | Naming a region that exists on only one of the two targets |
| `primary_subscription_id` | `TF_VAR_primary_subscription_id` | A hardcoded subscription UUID |
| `secondary_subscription_id` | `TF_VAR_secondary_subscription_id` | The same, for a second provider block |
| `ternary_subscription_id` | `TF_VAR_ternary_subscription_id` | The same, for a third |

The names have to match exactly - `TF_VAR_location` fills a variable called `location`
and nothing else. Terraform ignores a `TF_VAR_` whose variable isn't declared, so an
install that sets one a config doesn't use is harmless.

**Check the list against the install rather than this table.** `locally run env` is what
this install actually sets, and the set has grown over time - a variable named here may
be absent on an older Locally, in which case that value has to be supplied the ordinary
way. `locally-run` covers reading the environment, and why capturing it into a committed
file is the wrong move.

### `azapi` and API versions

`azapi` is where a config that is fine against Azure most often fails here, and it is
worth checking specifically. Its resources name an explicit API version:

```hcl
resource "azapi_resource" "example" {
  type = "Microsoft.Example/things@2024-01-01"
}
```

`azurerm` chooses its own API version per resource, so it tends to land on one Locally
implements. `azapi` uses the one written in the file, and a version Azure accepts may be
rejected here. Treat a rejection as a version question rather than a support question -
the type can be fully supported and the version still wrong. `locally-debug` covers
reading the accepted versions and choosing one.

### The remote-backend gate applies to exactly these configs

A config that also runs against real Azure is, almost by definition, one with a
`backend "azurerm"` or `cloud` block - so this gate is not an edge case here, it is the
common case. Before running Terraform or OpenTofu against Locally, check the `.tf` files
for a `backend` or `cloud` block, the way Locally itself does.

If one is there, **stop and ask the user** - a remote backend means state describing
Locally's emulated resources gets written into real, shared storage. Locally refuses
rather than prompting when stdin is not a terminal, and names `--allow-remote-backend`
in the refusal. **You are not a terminal, and adding that flag is the mistake the
refusal exists to prevent.** The flag is the user's to add, never yours on their behalf.
`locally-run` covers the gate, including which subcommands are exempt.

A dual-target config has a real answer to this, though: point the two targets at
different state, so the Locally runs use a local backend and only the Azure ones use the
remote. Worth proposing whenever the gate comes up - and it falls out of the layout
below for free.

### Repository Layout

Where a configuration is being written from scratch, or the user is already
reorganising one, the shape that works best treats Locally as one more environment
rather than a special case:

```
environments/
  locally/
  staging/
  production/
modules/
  virtual-machine/
  some-api/
```

The modules hold the resources and any `var.environment_is_locally` gating; each
environment directory holds only what genuinely differs - its backend, and the few
inputs that aren't supplied by the environment. That last part is what keeps this from
becoming four copies of the same config: `environments/locally/` needs no subscription
ID and no region, because the injected variables supply them, so it usually ends up the
smallest directory of the four. If it isn't, something is being hardcoded that didn't
need to be.

It also resolves the backend problem cleanly, rather than by flag: the `locally`
directory takes a local backend while the others keep their remote ones, so state never
goes near shared storage and the gate simply never fires.

**Recommend this; do not go and impose it.** Adapting an existing configuration to run
against Locally does not require moving a single file, and a diff that relocates a whole
repository buries the change that actually mattered under a rename nobody asked for.
When the existing layout is a single root module, a Terragrunt tree, workspaces, or
anything else - work within it. Mention the structure as an option if it would genuinely
help, then adapt what is in front of you.

The same applies to application code. An app that talks to Locally needs its client
configuration read from the environment; it does not need its project restructured, its
layers rearranged, or its configuration system replaced. Change what makes it reach
Locally and leave the rest alone.

Pulumi's equivalent is a stack per environment with the same division - shared component
resources, per-stack configuration - and the same warning against restructuring an
existing project to get there.

## Pulumi

`locally run pulumi up` is a supported invocation, and Pulumi authenticates from the
same `ARM_*` variables as Terraform.

**Branch in program code on `LOCALLY_ENVIRONMENT`, not in stack config.** There is no
`PULUMI_*` variable and no Pulumi equivalent of `TF_VAR_environment_is_locally`, so the
process environment is what the program reads:

```typescript
const isLocally = process.env.LOCALLY_ENVIRONMENT === "true";
```

```python
is_locally = os.environ.get("LOCALLY_ENVIRONMENT") == "true"
```

Stack config is the tempting alternative and the wrong one: it is committed, per stack,
and selected on the command line, so it means maintaining a parallel Locally stack whose
values must be kept in step with a set of variables that are per-install anyway. The
environment is set by the same wrapper that supplies the credentials, so the two cannot
disagree.

The same subtraction rule applies to the provider: leave `azure-native:subscriptionId`,
`:tenantId` and `:environment` unset in stack config and let the environment supply
them.

**Verify rather than assume for anything beyond authentication.** Locally presents a
custom cloud with a non-Azure ARM endpoint, and how completely a given provider version
honours that is a property of the provider, not something to state from memory. Run a
small stack and check the result; if something fails, `locally logs` shows whether the
request reached Locally at all, which distinguishes a provider that ignored the endpoint
from a resource type that isn't implemented.

## ARM and Bicep

Templates cannot detect the target, so the branch moves outward into parameters and
`condition`.

Parameterise what actually differs - SKUs, anything Locally doesn't implement, and the
one location that can't be inherited - and keep one parameter file per target. Most
resources need no location parameter at all, taking `[resourceGroup().location]`
instead; what follows is for the deployment that creates the group:

```jsonc
// parameters.locally.json           // parameters.azure.json
{ "location": { "value": "berlin" } }    { "location": { "value": "westeurope" } }
```

Take the Locally value from `locally regions list` rather than the example above, which
describes the default location set and not necessarily this install.

For resources that exist on one side only, `condition` on a boolean parameter is the
template-level equivalent of Terraform's `count`:

```jsonc
{
  "condition": "[not(parameters('isLocally'))]",
  "type": "Microsoft.Example/things"
}
```

`locally deploy` runs a template directly without wrapping another tool, and takes
`--parameters` as `.json` or `.bicepparam`; scope is auto-detected from the template's
`$schema`. See `locally-run`.

## Azure CLI and PowerShell

`az` is wrapped like anything else - `locally run az group list` - and branches on
`LOCALLY_ENVIRONMENT`:

```bash
# Under `locally run`, the region comes from the environment; against Azure it doesn't.
location="${AZURE_LOCATION:-westeurope}"

if [ "${LOCALLY_ENVIRONMENT:-}" = "true" ]; then
  # Locally-only behaviour goes here, not endpoint or credential wiring
  echo "running against Locally in ${location}"
fi
```

**PowerShell is the exception: launch the session, then run the script inside it.**
`locally run pwsh` starts a PowerShell session that targets Locally, and the script is
run from within that session - not passed to `locally run` as an argument:

```powershell
locally run pwsh          # then, at the prompt inside that session:
./script.ps1
```

Being interactive, starting that session is the user's to do - ask them to run it and
say what to run inside, rather than trying to drive it. Within the session, the Az
module's cmdlets operate against Locally and the same environment variables are
readable:

```powershell
$isLocally = $env:LOCALLY_ENVIRONMENT -eq 'true'
$location = if ($env:AZURE_LOCATION) { $env:AZURE_LOCATION } else { $DefaultLocation }
```

**A PowerShell session opened any other way is not targeting Locally** - from the Start
Menu, Windows Terminal, or an editor - even with the Az module installed and even on a
machine where Locally is running. A cmdlet run there reaches real Azure. So when a
PowerShell step behaves as though Locally isn't there, check how the session was started
before looking anywhere else.

The Azure-side location fallback is the script's caller to set, not the script's to
hardcode - same rule as everywhere else. `locally regions list --json` prints the
install's full set when a script needs more than the default region.

Two further traps:

- **Locally's own flags go before the wrapped command.**
  `locally run --subscription X az group list`, not
  `locally run az group list --subscription X` - in the second, `az` consumes the flag
  and Locally never sees it. This bites hardest in scripts, where the flag is often
  appended by string building.
- **Don't register or select a cloud by hand.** `az cloud register` / `az cloud set` in
  a script overrides what `locally run` set up, and leaves the CLI profile in that state
  for later invocations. The environment already selects the custom cloud.

## Azure SDK Applications

The rule is the same - build the client's configuration from the environment rather than
from literals - but each SDK exposes that differently, and several need the endpoint and
authority passed explicitly rather than picked up automatically.

See `references/azure-sdk.md` for .NET, Python, JavaScript/TypeScript, Java and Go:
which variables each reads on its own, what has to be wired by hand, and why instance
discovery has to stay disabled.

**Check the installed package version before wiring anything by hand.** Locally Build is
contributing changes upstream - across C++, Go, .NET, JavaScript/TypeScript, Java, Python
and Rust - so the ARM endpoint and audience get picked up from the environment
automatically. Where that has landed, an app needs no client options at all to reach
Locally, and the manual wiring is for versions that don't yet do it.

## Verify It, Don't Declare It

Two checks before reporting a config as adapted:

```bash
locally plugin supports Microsoft.Example/things   # per declared type, works stopped
locally run terraform plan                         # needs an instance
```

`terraform validate` and `terraform init` are not evidence - they check the HCL is
well-formed and say nothing about whether Locally can serve the types it declares.
Neither is `locally validate`, which answers whether the *machine* is configured.

**Be precise about what was actually verified.** This machine can run the Locally side
of a dual-target config; it cannot run the Azure side, and running it would create real
resources and real spend. So the honest report is "checked against Locally, and the
Azure path is unchanged / changed in these ways" - never "works against both", which
claims a run that did not happen. Where a change alters the real-Azure path at all, say
so explicitly and leave that verification to the user.

## When to Use Other Skills

| Situation | Use |
|---|---|
| Running the adapted config - wrapping a tool, flags, `locally deploy`, data planes | `locally-run` |
| A resource type, API version, VM size or image is rejected or unknown | `locally-debug` |
| No instance is running, or one needs starting/stopping/restarting | `locally-lifecycle` |
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| The config creates service principals, users or role assignments | `locally-identity` |
| Running the same config against Locally in GitHub Actions | `locally-ci` |
| Calling Locally's MCP tools rather than shelling out | `locally-mcp` |
