---
name: locally-setup
description: Configure a machine to run Locally, and manage the account behind it - certificates, DNS resolution for *.locally, the container runtime, signing in, licence renewal and what each plan includes. Use when Locally will not start, when *.locally does not resolve, when a pre-flight check fails, when setting Locally up for the first time, or when a feature is refused because of the plan or an expired certificate. Triggers on "locally won't start", "*.locally doesn't resolve", "certificate expired", "mkcert", "dns check", "podman can't reach", "docker can't reach", "validate my setup", "first time setup", "locally login", "locally logout", "locally refresh", "locally validate says", "installation certificate", "switch locally account", "sign in to a different account", "deregister this installation", "requires a plan", "session limit", "which plan do I need".
---

# Locally Setup

Configuring a machine so Locally can run at all: TLS certificates, DNS resolution for
`*.locally`, and the container runtime (Docker and/or Podman). Once a machine is
configured, use `locally-lifecycle` to start, stop or restart an instance on it - this
skill is about the machine, not the instance.

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
proceed to any of the checks below - without the CLI there is nothing further this skill
can do.

**A reachable instance is not evidence the CLI is installed.** The two are independent:
a response on `5678` means a process is listening, not that `locally` is on this PATH -
the instance may have been started by another user on this machine, or from a binary
that has since been moved or removed. So "it's already running" never answers a request
that needs the CLI. If `locally version` errored, report that, whatever is or
isn't listening.

## Start With `locally validate`

This is the first diagnostic step for almost anything in this skill's territory. It
checks the TLS certificate (loaded, unexpired, covers every required domain, trusted by
the system), and this machine's configuration (DNS resolver, and - if installed - Docker
and Podman), and reports each with ✅/❌/➖. It works whether or not a Locally instance
is running:

```bash
locally validate
```

For example, the DNS line reads configuration rather than testing live resolution when
nothing is running, and says so explicitly:

```
✅ dns: /etc/resolver/locally points at 127.0.0.1 port 5673 (Locally is not running, so this reads the configuration rather than testing resolution)
```

And Docker/Podman report `➖ not required` rather than failing when the tool is
installed but its daemon isn't running - there's nothing to reach in that state, so
there's nothing to check.

Read `locally validate`'s output before reaching for anything else in this skill. It
names exactly what's wrong; don't guess ahead of it.

## The Wizard: `locally setup`

`locally setup` is an interactive wizard that gets this machine's certificates, DNS and
container runtime into a working state - the same things `locally validate` checks.
Each of those has an equivalent standalone command, documented below, for a reader who'd
rather run one thing directly than be walked through the whole wizard: `locally
certificate generate`, `locally configure dns`, and `locally configure docker` /
`locally configure podman`.

Run the wizard for first-time setup, or whenever `locally validate` reports something
wrong and the user wants to be walked through fixing it rather than running the
individual `certificate` / `configure` commands themselves.

`locally setup --help` only describes the certificate side of this - that text is
stale, not a statement that the wizard is certificates-only. Describe the wizard by what
it does, not by what `--help` says.

**It's safe to re-run.** Re-running `locally setup` doesn't force certificate
regeneration - reusing the certificate you already have (and already trusted in your
system's trust store) is an option the wizard offers. There's no need to approach
re-running it nervously.

**This skill does not run `locally setup`.** It's an interactive wizard, so an agent
can't drive it meaningfully or predictably. Walk the user through running it themselves,
or point them at the narrower `certificate` / `configure` commands below if they'd
rather change one thing at a time.

### Certificate drift

The certificate `locally validate` checks must cover every domain Locally needs. A
release can add a newly-required domain that an existing certificate predates; when that
happens, `locally validate` names the specific missing domain rather than failing
generically, and the fix is `locally setup` (or `locally certificate generate`) to
generate a certificate that covers the current list. Re-running `locally setup` for this
is safe, same as above - it isn't a destructive operation the user should hesitate over.

## Certificates

`locally certificate` has three subcommands, none of which require Locally to already be
configured:

| Command | What it does |
|---|---|
| `locally certificate generate` | Generates a certificate, key and CA covering every domain Locally needs, writing to `~/.config/locally` by default. Prefers mkcert (its CA installs machine-wide with one `mkcert -install`); falls back to Locally's built-in CA. `--source` forces one or the other. Prompts before overwriting an existing certificate at `--out-dir` (or requires `--force` without a TTY). |
| `locally certificate get-mkcert-command` | Prints a ready-to-run mkcert command covering every required domain, for running mkcert yourself: `$(locally certificate get-mkcert-command)`. |
| `locally certificate get-required-domains` | Prints the comma-separated list of domains the certificate must cover - useful for feeding a CI cert-generation step. |

Don't hardcode the domain list in a script or document - it can change between
releases. Always fetch it live:

```bash
locally certificate get-required-domains
```

## Machine Configuration

`locally configure` has three subcommands, each a single, idempotent, safe-to-re-run
change:

| Command | What it does |
|---|---|
| `locally configure dns` | Configures this machine's resolver so `*.locally` addresses resolve. |
| `locally configure docker` | Configures Docker so its daemon can reach Locally's container registry. |
| `locally configure podman` | Configures Podman so its daemon can reach Locally's container registry. |

Each accepts `--status` (report only, no change), `--dry-run` (print what would change),
and `--remove` (undo only what Locally added). Certificates are configured separately -
see above, not `locally configure`.

**The DNS requirement, concretely:** `*.locally` must resolve to `127.0.0.1`, served by
Locally's own DNS on port `5673`. `locally configure dns` (and `locally setup`) sets
this up, and prints the exact resolver command for the current platform when the check
finds it isn't already in place.

If `*.locally` doesn't resolve, the fix is to configure the resolver - `locally
configure dns` or `locally setup` - not to route around the check. `--skip-dns-check`
gets a broken machine running for one process; it doesn't fix DNS, so the next thing
that assumes `*.locally` resolves will fail too.

## Pre-flight Checks (`locally build`)

Before launching, `locally build` checks that this machine is configured: that
`*.locally` resolves, and that any *installed* container runtime can reach Locally. A
misconfigured machine doesn't fail later inside Locally where the cause would be
unclear - `locally build` refuses to start and names what to fix.

Each check can be waived individually, with a flag for an interactive run or the
matching environment variable - the environment variable is usually the better fit for a
prepared CI image where the check is known to be redundant:

| Check | Flag | Environment variable |
|---|---|---|
| DNS (`*.locally` resolves) | `--skip-dns-check` | `LOCALLY_SKIP_DNS_CHECK=1` |
| Docker reaches Locally | `--skip-docker-check` | `LOCALLY_SKIP_DOCKER_CHECK=1` |
| Podman reaches Locally | `--skip-podman-check` | `LOCALLY_SKIP_PODMAN_CHECK=1` |

These flags waive a check, they don't fix the underlying configuration. Use them to get
a known-good, already-configured image (or a machine where the failing runtime is
irrelevant to what's being tested) past a redundant check - not as a substitute for
running `locally configure` or `locally setup` on a machine that actually needs
configuring.

**If `locally build` refuses because an instance is already running**, that is a
different failure from a pre-flight one, and there is no CLI command that stops the
running instance - not `locally stop`, not `locally shutdown`, under any name. A
`build` instance ends when the terminal running it gets Ctrl-C. Ask the user to do
that rather than reaching for a plausible-sounding subcommand: an unknown one prints
the banner and **exits 0**, so a zero exit status is not evidence anything stopped.
`locally-lifecycle` covers starting, stopping and restarting in full.

## The Account and the Licence

`locally account` prints the signed-in account - username, email, organisation, and when
it last synced. It reads local state, so it works with nothing running.

**Two different certificates expire, and they are not interchangeable.** `locally
validate` reports both, under separate headings:

| What `validate` calls it | What it is | When it expires |
|---|---|---|
| "the TLS certificate" | The certificate Locally serves HTTPS with | `locally setup`, or `locally certificate generate` |
| "the Locally Installation Certificate" | The licence for this installation | `locally refresh` |

Read which one `validate` named before acting. Regenerating a TLS certificate does
nothing for an expired licence, and refreshing the licence does nothing for a
certificate that has stopped covering a required domain.

The installation certificate renews itself automatically once it is inside two weeks of
expiry, so `locally refresh` is normally unnecessary. It is worth running by hand before
a stretch offline - renewal needs to reach the account API, and a laptop that spends the
expiry window on a plane will not have had the chance.

If a refresh fails because the account needs attention - terms to accept, billing to
settle - the CLI prints what the account API said. That is a message to relay to the
user, not something to work around.

### Signing In

An installation can be set up without an account. That works, and it stays working, but
it carries two limits: a maximum session length, and an allowance for how many plugins
it may run.

```bash
locally login                  # opens a browser
locally login --skip-browser   # prints the URL instead
```

Signing in lifts both, and it is free - so when someone hits either limit, `locally
login` is the first thing to offer, ahead of any paid plan. **Don't quote the specific
numbers.** They are claims on the certificate, set when it is issued rather than
compiled into the CLI, so a figure repeated from memory can be wrong without anything
looking wrong. Read them from `locally validate` or the dashboard.

An instance that hits the session limit exits with **status 2**. A non-zero exit from a
long-running instance is worth checking against that before it is treated as a crash.

### `locally logout` Is Destructive

It signs out, deregisters the installation, **and removes the installation certificate**.
Locally will not run again until `locally setup` has been re-run. That is not a
"sign in as someone else" command, and it is not reversible by signing back in.

Confirm with the user before running it. It prompts, and `--force` skips the prompt -
don't pass `--force` on their behalf.

## Plans Gate Features

Some things the other skills describe are not available on every plan. When a command or
an MCP tool refuses with `this feature requires a <plan> plan`, that is the cause -
the feature is present and working, the plan doesn't include it.

| Feature | Needs |
|---|---|
| More than one subscription (Starter is capped at one) | Standard |
| Creating or deleting subscriptions | Standard |
| Policy and governance | Standard |
| Chaos (`locally chaos`) | Standard |
| Cost estimation | Standard |
| Minimum necessary permissions | Standard |
| Organisation policies | Team |
| Location sets (`locally locations`) | Team |
| Edge zones | Team |
| Unlimited subscriptions (Standard allows three) | Team |

Enterprise carries the same runtime features as Team; what it adds sits in licensing and
support rather than in what the instance can do.

**A plan change needs a refresh and a restart.** The plan is enforced from the
installation certificate, and a running instance keeps enforcing the plan it started
with. After upgrading: `locally refresh`, then restart the instance. Skipping either
leaves the new features refused, which reads exactly like the upgrade not having worked.

## When to Use Other Skills

| Situation | Use |
|---|---|
| The machine is configured, but no instance is running | `locally-lifecycle` |
| An instance is running and you need to drive tools against it (`az`, Terraform, data-plane commands) | `locally-run` |
| Setting up Locally inside a GitHub Actions workflow | `locally-ci` |
| An instance is running but behaving unexpectedly | `locally-debug` |
| A VM size, image or app stack Azure has but Locally doesn't know | `locally-debug` - that is bundled reference data going stale, not machine configuration |
| Registering Locally's MCP server in a client | `locally-mcp` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |
