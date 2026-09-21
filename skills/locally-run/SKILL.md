---
name: locally-run
description: Point Azure tooling at a running Locally instance - az, Terraform, OpenTofu, Pulumi, PowerShell and the Azure SDKs - drive its data planes, and deploy team runbooks. Use when running a command against Locally instead of real Azure, deploying an ARM or Bicep template, choosing a subscription or region, picking a tenant, working with storage, Service Bus, Event Hub, IoT Hub or Functions, or provisioning shared team setup. Triggers on "point terraform at locally", "run az against locally", "locally run", "deploy this template", "connection string", "which subscription", "which region", "what location do I use", "detect locally from terraform", "which environment variables", "against the emulator", "runbook", "locally runbooks", "provision the team directory".
---

# Locally Run

Driving Azure tooling against a running Locally instance: `locally run` wraps a command
so it authenticates against Locally instead of real Azure, by building the environment
it runs in - `locally run env` shows exactly what it sets; `locally deploy` runs an ARM
or Bicep template directly; the data-plane commands (`storage`, `servicebus`,
`eventhub`, `iothub`, `function`) manage resources without going through a wrapped
tool at all.

Most of this skill assumes an instance is already running - if it isn't, use
`locally-lifecycle` to start one first. The one exception is the plugin pre-flight
check below (`locally plugin supports`): it reads the installed plugin manifests,
not the running instance, so do it regardless of whether Locally is started. Whenever
asked to confirm IaC will work against Locally, run that check - don't treat "no
instance is running" as a reason to skip straight to asking the user to start one.

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

**A reachable instance is not evidence the CLI is installed.** The two are independent:
a response on `5678` means a process is listening, not that `locally` is on this PATH -
the instance may have been started by another user on this machine, or from a binary
that has since been moved or removed. So "it's already running" never answers a request
that needs the CLI. If `locally version` errored, report that, whatever is or
isn't listening.

## Flag Ordering

Locally's own flags go **before** the wrapped command, not after:

```
locally run --subscription "Second Subscription" az group list   # correct
locally run az group list --subscription "Second Subscription"   # the flag reaches az, not Locally
```

Once `az` (or `terraform`, or whatever) starts, everything after it on the command line
belongs to that tool. A Locally flag placed there is parsed by the wrapped command, not
by Locally, and Locally never sees it.

Locally's flags:

| Flag | Meaning |
|---|---|
| `--subscription <name|uuid>` | Run against a specific subscription instead of the default |
| `--tenant <name|uuid>` | Run against a specific tenant |
| `--user <upn|uuid>` | Run as a directory user other than the default - a delegated token; the password never touches the environment |
| `--service-principal <uuid|name>` | Run as a service principal, by appId or display name |
| `--managed-identity <uuid|name>` | Run as a managed identity, by client id or display name; no secret touches the environment |
| `--allow-no-subscriptions` | Run in a tenant that has no subscriptions |
| `--allow-remote-backend` | Run Terraform/OpenTofu without confirming its remote backend - see below before ever using this |

## Running as a Non-Default Identity

By default `locally run` uses the installation's default credential. Three flags run the
wrapped command as a different directory identity instead - Locally mints the token that
principal would carry:

```bash
locally run --user ada.lovelace@default.tenants.locally az account show   # directory user - a delegated token; the password never touches the environment
locally run --service-principal billing-runner terraform plan             # service principal, by appId or display name
locally run --managed-identity deploy-mi terraform apply                  # managed identity, by client id or display name; no secret touches the environment
```

Like every Locally flag, these go before the wrapped command. This is the direct way to
run a tool under a specific identity - cleaner than requesting a token by hand with a
client-credentials grant, which is still the path when a tool needs the raw token rather
than an environment to run in. `locally-identity` covers the seeded users and service
principals these flags name, and how their Graph permissions resolve.

## What `locally run` Puts in the Environment

Wrapping a command is not a redirect - `locally run` builds an environment for it
and executes it there. Credentials, endpoints, the subscription and tenant, and a
few hints all arrive as environment variables, which is why an unwrapped `az` or
`terraform` talks to real Azure and a wrapped one does not.

`locally run env` prints the complete set for this installation. Read it rather than
working from a remembered list - the values are per-install and several are
per-instance:

```bash
locally run env | grep -E '^(LOCALLY|TF_VAR|ARM_|AZURE_)'
```

Two are worth knowing by name, because they let a config notice where it is:

| Variable | Value | Use |
|---|---|---|
| `LOCALLY_ENVIRONMENT` | `true` | Any tool or script: branch on running against Locally |
| `TF_VAR_environment_is_locally` | `true` | Terraform: read as `var.environment_is_locally` |

The Terraform one is the tidier way to handle "this resource only exists in real
Azure" or "use a smaller SKU locally" - a `count` or a `local` keyed on
`var.environment_is_locally`, rather than a separate tfvars file per target.
`TF_VAR_primary_subscription_id`, `_secondary_` and `_ternary_` arrive the same
way, so a multi-subscription config needs no hardcoded UUIDs.

`ARM_TEST_LOCATION`, `ARM_TEST_LOCATION_ALT` and `ARM_TEST_LOCATION_ALT2` carry
regions from the active location set, which is what an acceptance-test suite should
use instead of naming one (see the region section below).

**Read these, don't capture them.** Some are not merely per-install but
per-invocation: `AZURE_CONFIG_DIR` is keyed to the credentials in use, so it
differs between subscriptions and tenants, and between the identities the flags
above select. Reusing a value seen under one
`--subscription` points the Azure CLI at another identity's profile, which fails
in the worst way available - the command succeeds, against the wrong
subscription. Let `locally run` set the environment each time rather than lifting
values out of it.

All of this needs an instance: the credentials are minted by the running one, so
`locally run env` has nothing to report without it.

## The Remote-Backend Gate

Before running Terraform or OpenTofu, Locally parses the `.tf` files Terraform itself
would load and looks for a `backend` or `cloud` block. Most subcommands are gated on
this check; a short list is exempt because they can't write state or touch a backend
in the first place: `fmt`, `validate`, `version`, `login`, `logout`, `help`, any
invocation with `-help` / `--help` / `-h`, and `init -backend=false`. Everything else -
`init`, `plan`, `apply`, `destroy`, and so on - is gated.

When a `backend` or `cloud` block is found, Locally asks for confirmation. When stdin
is not a terminal, it refuses outright rather than prompting, and names the flag that
would bypass it:

```
WARNING: this Terraform configuration is configured with a remote backend.

  main.tf: backend "azurerm"

The state for this configuration is stored remotely, so this run would write state
describing Locally's emulated resources into real, shared storage.
refusing to run against a remote backend with no terminal to confirm at - pass --allow-remote-backend to `locally run` if this is intentional
```

This is deliberate, not a rough edge. A piped `y` isn't consent, so a non-interactive
caller gets a refusal instead of a prompt it could rubber-stamp.

**You are not a terminal.** When this refusal appears, the natural next move is to add
the flag it just named - that is exactly the mistake the design exists to prevent. A
remote backend means Terraform state for Locally's *emulated* resources gets written
into a real, shared destination: Terraform Cloud, or a real Azure storage account.

Check the `.tf` files for a `backend` or `cloud` block **before** running Terraform or
OpenTofu against Locally, the same way Locally itself would. If one is there, stop and
ask the user whether this is intentional - don't decide for them, and never pass
`--allow-remote-backend` on their behalf. If they confirm it's intentional (for example,
a config they run against real Azure too, with a backend block that's expected to be
there), that's the point where the flag is theirs to add, not yours to add on their
say-so.

## `locally deploy`

Deploys an ARM or Bicep-compiled template directly, without wrapping another tool. Use
this instead of `locally run az deployment group create ...` - it's the more direct
path:

```bash
locally deploy ./template.json
locally deploy --resource-group example ./template.json
locally deploy --parameters ./parameters.json ./template.json
locally deploy --parameters ./parameters.bicepparam ./template.bicep
locally deploy --location berlin ./subscription-template.json
```

Scope (resource-group vs. subscription) is auto-detected from the template's `$schema`
field - nothing to choose explicitly. Flags:

| Flag | Meaning |
|---|---|
| `--resource-group` | Resource group name. Generated if unspecified. Not used for subscription-scoped deployments. |
| `--deployment` | Deployment name. Generated if unspecified. |
| `--parameters` | Parameters file - `.json` or `.bicepparam`. |
| `--location` | Deployment metadata location. Defaults to `berlin`. Only used for subscription-scoped deployments. |
| `--subscription` | Subscription UUID. Uses the default if unspecified. |

## Regions Are Locally's Own, Not Azure's

**Read the region set off the install; never recall it.** Which names are valid is a
per-install property - an installation applies a *location set*, and Locally's own
city-scale names are only the default one. An install that has applied a real cloud's set
answers to that cloud's names instead, so a remembered list is wrong on exactly the
installs where being wrong matters most. **This file deliberately does not
enumerate them**, because any list written here describes some other install:

```bash
locally regions list     # identifiers, display names, and availability zones
```

Run it before naming a region, and treat its output as the authority for any
`--location`, any `location` in a template or parameter file, and any `-l` passed through
`locally run az`. Don't answer from the examples in this file - they illustrate the
default set, they do not describe the install in front of you.

Getting it wrong is cheap, though: the control plane's error enumerates the valid
regions for you - `the resource location "westeurope" is not a valid region for
subscription ... (allowed: ...)` - so a wrong guess is self-correcting rather than
mysterious.

**That rejection is a feature, not an obstacle.** Because Locally's names exist nowhere
in Azure, a config aimed at Locally cannot silently deploy to a real cloud, and one aimed
at Azure fails loudly here instead of half-succeeding. Never "fix" it by editing Locally's
region set to match a cloud's - keep the difference and parameterise the location, one
value per target:

```jsonc
// parameters.locally.json      // parameters.azure.json
{ "location": { "value": "berlin" } }   { "location": { "value": "westeurope" } }
```

`locally regions list` also reports which set is active, and warns when it has been
replaced with a real cloud's names - the case where that safety net is gone. So does
`locally locations`, which reports the active set and its region count and nothing else.

**Changing the set is not something to reach for.** It needs the Team plan, and it needs
the installation to be empty: swapping the set replaces every region, and resources in a
region that no longer exists are orphaned rather than moved. Locally refuses a swap
against a populated install for that reason. Parameterise the location in your config
instead, as above.

## Subscriptions and Tenants

`locally subscriptions list` shows every subscription this installation knows about,
with the display name and UUID `--subscription` accepts:

```bash
locally subscriptions list
```

```
DISPLAY NAME          UUID                                   ID                                       GROUPS   RES
First Subscription    07a602cc-fbac-427d-8eaa-9cb80ae6f50d   /subscriptions/07a602cc-...                    0     0
Second Subscription   9e757125-2b0f-4a15-94d3-3aa679c20a07   /subscriptions/9e757125-...                    0     0
```

`locally subscriptions get <uuid | id | display-name>` looks up one subscription;
matching is case-insensitive. `--subscription` on `locally run` and `locally deploy`
accepts either the display name or the UUID from this list.

**How many subscriptions exist depends on the plan**, so don't assume a second one is
there to point at. Starter installs get one and cannot add more; Standard allows three;
Team and above are unlimited. Creating and deleting subscriptions needs Standard. An
attempt past the cap is refused with the plan and the limit - `your current plan
(Starter) allows a maximum of 1 subscription(s)` - which is a plan message, not a bug.
Run `locally subscriptions list` and work with what is there.

## Plugin Pre-Flight

Before authoring IaC, check that Locally can actually serve what it uses. A config for
a provider that isn't there doesn't fail at authoring time - it fails during apply,
somewhere less obvious than "this provider isn't installed":

```bash
locally plugin supports Microsoft.KeyVault/vaults
```

**This is the check that answers "will this actually work against Locally" - run it
whenever asked to verify that, and don't substitute something else for it.**
`terraform validate` and `terraform init` only check the HCL is well-formed; they say
nothing about whether Locally can serve the resource types the config uses. Check each
type the config declares, not just the namespace - a provider can be installed while
the specific type it needs is not implemented.

It reads the installed plugin manifests rather than a running instance, so **run it
regardless of whether Locally is started** - don't wait for an instance to come up, and
don't let "no instance is running" become a reason to skip it. Matching is
case-insensitive, and it exits non-zero when the answer is no, so it chains:

```bash
locally plugin supports Microsoft.KeyVault/vaults && terraform apply
```

**`locally validate` is not this check.** It answers whether the *machine* is set up and
whether an instance is up - certificates, DNS, the container runtime. It says nothing
about whether the resource types your config declares are implemented, so a clean
`validate` is not evidence the config will apply. Asked "will this work against
Locally", run `locally plugin supports` for every type the config uses; `validate` is a
different question with a similar-sounding answer.

**Finding nothing running does not end the task.** Asked to write a config and check it
will work, an agent that health-checks first, sees nothing listening and stops - handing
back `locally build --skip-browser` and waiting - has delivered nothing it could have
delivered. The pre-flight and the config both work with Locally stopped; only actually
applying needs an instance. Run the check, write the config, and say that starting an
instance is what remains. The health check belongs *after* the work that doesn't need
one, not in front of it as a gate.

Three answers need different responses, and `locally-debug` covers the distinction in
full:

- **supported** - proceed.
- **available but not installed** - the user can fix it:
  `locally plugin install --name Microsoft.KeyVault`.
- **not implemented** - an installed plugin declares the type but hasn't implemented it.
  Installing something will not help, and no flag works around it. Try `locally plugin
  update` in case a newer release implements it; if not, the config has to avoid that
  type on this version. Users have binaries, not source, so never suggest editing a
  plugin or building one - say plainly that it isn't available yet.

## `locally connect`

Connects to a virtual machine registered with Locally: resolves its public endpoint
and admin credentials, then runs `ssh` (Linux VMs, attached to the current terminal) or
opens an `.rdp` file (Windows VMs, macOS only - other platforms get the file path
printed to open manually).

```bash
locally connect --virtual-machine my-vm
locally connect --virtual-machine my-vm --subscription abc123
locally connect --bastion my-bastion                      # list VMs reachable through it
locally connect --bastion my-bastion --virtual-machine my-vm
```

## Data Planes

`storage`, `servicebus`, `eventhub`, `iothub` and `function` manage resources directly
- no wrapped tool involved. See `references/data-plane-commands.md` for the full
command set.

## Runbooks

Runbooks are shared setup that a team syncs to every install, so a new machine can be
brought to a known state without anyone hand-running a deployment. Three kinds:

```bash
locally runbooks list                    # everything synced, with each one's type
locally runbooks deploy <name>           # run one by name
locally runbooks directory list          # synced users, groups, applications, SPs
locally runbooks directory provision     # create all of them on the running instance
locally runbooks datascripts             # list and execute team data scripts
```

`locally runbooks deploy` covers both an ARM template (at subscription or resource-group
scope) and a data script run against a specific resource - `list` reports which a given
runbook is, so check there rather than guessing from the name.

**Runbooks are synced from the account, not authored locally.** An install with none
says so and points at the fix:

```
No runbooks found. Sync your teams with 'locally setup' or check the dashboard.
```

That is the expected state on a personal install, and it is not a fault to debug. If a
user expects runbooks and has none, they are either not in a team that publishes them or
have not synced since joining - `locally setup` re-syncs. Don't offer to write a runbook
file by hand as a substitute; they are managed through the account.

Because they provision directory objects and deploy templates, treat
`directory provision` and `deploy` as changes to the instance and say what they will do
before running them. `locally-identity` covers what the directory objects then look like.

## When to Use Other Skills

| Situation | Use |
|---|---|
| No instance is running, or one needs starting/stopping/restarting | `locally-lifecycle` |
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| Setting up Locally inside a GitHub Actions workflow | `locally-ci` |
| A deployment names a VM size, image or app stack Locally doesn't know, though Azure does | `locally-debug` (its reference data is out of date, and `locally refresh-reference-data` imports the current answer) |
| A resource type or API version is rejected | `locally-debug` |
| An instance is running but behaving unexpectedly | `locally-debug` |
| Calling Locally's MCP tools rather than shelling out | `locally-mcp` |
| Plans, signing in, or a feature refused because of the plan | `locally-setup` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |
