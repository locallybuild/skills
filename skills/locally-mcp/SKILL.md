---
name: locally-mcp
description: Check whether Locally's built-in MCP server is registered in an MCP client, register or remove it, troubleshoot a failing tool call, and decide when to prefer its 70 tools over shelling out to the CLI. Use whenever the question involves Locally and MCP together - am I set up, how do I register it, which client, why did a tool fail, should I use a tool or a command. Triggers on "locally mcp", "mcp server", "locally mcp install", "locally mcp list", "am I set up to use Locally's MCP tools", "is the mcp server set up", "register locally in claude", "add locally to cursor", "mcp tool failed", "use tools instead of the cli".
---

# Locally MCP

Locally ships an MCP server, built into the same binary as the CLI. Where the other
skills teach shelling out and reading output, this one is about calling the tools
directly: `deploy_arm_template_at_resource_group_scope` rather than `locally deploy` and
parsing what comes back.

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
user Locally is not installed. Do not attempt to install it on their behalf - the MCP
server is the `locally` binary, so without it there is nothing to register.

**A reachable instance is not evidence the CLI is installed.** The two are independent:
a response on `5678` means a process is listening, not that `locally` is on this PATH.
If `locally version` errored, report that, whatever is or isn't listening.

## Is It Registered?

```bash
locally mcp list
```

Prints every supported client and whether Locally is registered in it:

```
CLIENT          STATUS
claude-code     installed (no locally entry)
claude-desktop  installed (locally entry registered)
codex-cli       not installed
```

Three states, and the difference matters: **not installed** means the client isn't on
this machine, **installed (no locally entry)** means the client is there but Locally
isn't registered in it, and **installed (locally entry registered)** means the tools are
available. Only the middle one is something to act on.

## Registering It

```bash
locally mcp install claude-code
locally mcp uninstall claude-code
```

Supported clients: `claude-desktop`, `claude-code`, `cursor`, `opencode`, `windsurf`,
`copilot-vscode`, `copilot-cli`, `codex-cli`, `gemini-cli`.

The server registers under the name `locally`, pointing at the current binary's absolute
path - so a `locally` that later moves, or a second copy installed elsewhere, needs
registering again.

**It edits the user's client configuration, so it is theirs to run.** If a `locally`
entry already exists the command fails rather than clobbering hand-edited state, and
`--force` overwrites. Don't reach for `--force` on someone's behalf: the failure means
they have something there already, and replacing it silently is not yours to decide.
(`uninstall --force` is the harmless one - it just makes removal idempotent for scripts.)

Registering does not affect a session already running. The client spawns the server when
the *client* starts, so new tools will not appear mid-conversation - the user has to
restart their client.

## Never Run `locally mcp` Yourself

Bare `locally mcp`, with no subcommand, **launches the server** and speaks the MCP
protocol over stdin/stdout. Run from a shell it produces no output and does not exit -
it sits there waiting for a client that will never speak to it.

It is only ever launched by an MCP client. The three subcommands - `list`, `install`,
`uninstall` - are the ones to run by hand.

## When to Prefer the Tools

Prefer MCP tools when one exists for the job. They return structured data, so nothing has
to be parsed out of human-formatted output that can change between releases.

Reach for the CLI when:

- **No tool covers it.** Chaos, plugin management, lifecycle, setup, logs, audit and CI
  are CLI-only.
- **The user asked for a command.** Someone asking "what do I run" wants something they
  can type and re-run themselves.
- **You are driving a tool that isn't Locally.** `locally run terraform apply` wraps
  another program's entire execution; no MCP tool substitutes for that.

## What the Tools Cover

Seventy tools. The client's own listing is the authority for what a given version
exposes, but the groups are stable:

| Area | Examples |
|---|---|
| Deployment | `deploy_arm_template_at_resource_group_scope`, `deploy_arm_template_at_subscription_scope`, `deploy_bicep_template_at_resource_group_scope` |
| ARM inventory | `get_resource_by_id`, `list_subscriptions`, `list_tenants`, `list_resource_groups_in_subscription`, `list_all_resources_of_type_in_subscription` |
| Capability | `list_all_available_resource_types`, `list_which_resource_providers_are_available`, `list_which_resource_providers_and_api_versions_are_being_used` |
| Directory (Graph) | `graph_find_objects`, `graph_get_object_by_id`, `graph_list_group_members`, `graph_list_member_of`, `list_available_graph_types` |
| Storage | `storage_list_containers`, `storage_create_container`, `storage_create_queue`, `storage_create_table`, `storage_create_file_share` (+ deletes) |
| Service Bus | `servicebus_create_queue`, `servicebus_create_topic`, `servicebus_get_connection_string` (+ lists, deletes) |
| Event Hub | `eventhub_create_hub`, `eventhub_get_connection_string`, consumer groups (+ lists, deletes) |
| Key Vault | `keyvault_get_secret`, `keyvault_set_secret`, `keyvault_list_secrets`, `keyvault_delete_secret` |
| DNS | `dns_create_zone`, `dns_get_zone`, `dns_create_record`, `dns_delete_zone` |
| IoT Hub | `iothub_get`, `iothub_delete` |
| Policy | `policy_evaluate_subscription`, `policy_explain_resource`, `policy_list_assignments` |
| Runbooks | `locally_runbooks_list`, `locally_runbooks_deploy` |

Every tool advertises a hint - read-only, idempotent, or destructive - so a client can
tell `storage_list_containers` from `storage_delete_container` before calling it. Treat
the destructive ones the way you would a destructive shell command.

**The capability tools do not replace `locally plugin supports`.** They report what the
control plane knows about, which includes resource types a plugin declares but has not
implemented. Only `locally plugin supports` reads the grades - see `locally-debug`.

`deploy_bicep_template_at_resource_group_scope` shells out to `bicep build`, so it needs
the `bicep` binary on PATH and fails with `could not find the bicep binary on your PATH`
without it. That is the standalone Bicep CLI, not `az bicep`.

## When a Tool Call Fails

Four causes, with different fixes. The message distinguishes them - read it rather than
re-registering on spec.

| Message says | Cause | Fix |
|---|---|---|
| `Locally does not appear to be running` | No instance | Start one - see `locally-lifecycle` |
| `this MCP server is Locally X but the running instance is Y` | The registered binary and the running stack are different versions | Update Locally, then restart the MCP client so it respawns the server |
| `this feature requires a <plan> plan` | The account's plan doesn't include it | See below |
| Nothing - the tools aren't there at all | Not registered, or the client hasn't restarted | `locally mcp list` |

The version check compares the binary hosting the server against the running stack, so
updating Locally is only half the fix: the client spawned the old binary at startup and
keeps it until the client restarts.

## Some Tools Need a Paid Plan

The six `policy_*` tools require the Governance capability, which starts at the Standard
plan. On Starter they are refused at call time with the plan message above - they still
appear in the tool listing, so a missing feature looks like a broken tool until you read
the error.

The plan comes from the **running instance**, not from the certificate on disk. Signing
in or upgrading mid-session re-issues the certificate, but a stack that is already
running keeps enforcing the plan it started with. After an upgrade, restart the instance.

`locally-setup` covers plans and what each one includes.

## It Needs a Running Instance

Every tool checks the running stack first, so none of them work while Locally is stopped.
The server itself starts fine without one - the client spawns it when the client
launches, long before Locally is necessarily up - which is why the failure shows up
per-call rather than as a server that won't start.

```bash
locally validate
```

It ends with whether an instance is up. Read the output, not the exit code - it exits 0
either way. Starting one is `locally-lifecycle`'s territory.

## When to Use Other Skills

| Situation | Use |
|---|---|
| Nothing is running, or it needs starting or stopping | `locally-lifecycle` |
| Driving `az`, Terraform, Pulumi or the SDKs against Locally | `locally-run` |
| Whether a resource type is actually implemented | `locally-debug` |
| Plans, signing in, certificates, or the machine isn't configured | `locally-setup` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |
