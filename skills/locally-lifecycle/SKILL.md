---
name: locally-lifecycle
description: Start, stop, restart and check a Locally instance. Use when Locally needs to be running and is not, when a command fails because nothing is listening, or when the user wants to stop or restart it. Covers why `locally build` is the only way to start one on a developer machine, and how to tell when an instance is ready. Triggers on "start locally", "stop locally", "restart locally", "is locally running", "locally isn't running", "nothing listening", "connection refused".
---

# Locally Lifecycle

Detecting, starting, stopping and restarting a Locally instance. Every other runtime
skill (`locally-run`, `locally-identity`, `locally-debug`) needs an instance running and
delegates here rather than restating this.

`locally --help` text lags the product in places. This skill states only what live
commands and live endpoints show - never a paraphrase of help text.

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

## Quick Reference

| Task | Command | Notes |
|---|---|---|
| Check if running | `locally validate` | Reads the whole machine, and ends with whether an instance is up. Read the output, not the exit code - it exits 0 either way. |
| Start interactively | `locally build --skip-browser` | Full-screen TUI. Run it in the user's own terminal - an agent cannot usefully run this at all. Include `--skip-browser` in a command you hand over, so the dashboard doesn't grab focus mid-task. |
| Start in CI | `locally ci` | **CI only** - needs OIDC, so it cannot start an instance on a developer machine. |
| Stop a CI instance | `locally ci --stop` | Only stops a `locally ci` instance, so CI only too. There is no `locally stop`. |
| Target another instance | - not supported | Running more than one instance at a time isn't supported today. If you need it, ask in Locally's Discord. |

## Verify the CLI Is Installed

Do this first, before anything else in this skill - including checking whether an
instance is already running. Controlling Locally in any way needs the CLI, so confirm
it's there before spending a step on the state of an instance:

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
proceed to check for a running instance - without the CLI there is nothing further this
skill can do.

**A reachable instance is not evidence the CLI is installed.** The two are independent:
a response on `5678` means a process is listening, not that `locally` is on this PATH -
the instance may have been started by another user on this machine, or from a binary
that has since been moved or removed. So "it's already running" never answers a request
that needs the CLI. If `locally version` errored, report that, whatever is or
isn't listening.

## Is an Instance Already Running?

Ask Locally:

```bash
locally validate
```

It ends with either `✅ Locally is running.` or `❌ Locally isn't currently running.`,
and it works on every platform without any flags of its own. **Read the output, not the
exit code** - `locally validate` exits 0 whether or not an instance is up, so a zero
status is not an answer.

It also reports why the machine might not be able to run one - certificates, DNS, the
container runtime - which is usually the next question anyway.

**If you do probe the port directly**, the dashboard is on `5678` and the control plane
on `5680`. Both are fixed, not configurable. Two things to get right:

- **It is HTTPS, with a certificate issued by Locally's own CA for `localhost`.** A
  client that doesn't trust that CA rejects the connection, and that rejection is *not*
  evidence Locally is down. `locally setup` installs the CA into the system trust store;
  where it isn't trusted, tell the client to skip verification (`curl -k`, and the
  equivalent elsewhere) rather than reading the failure as "nothing is listening".
- **Any HTTP status means an instance is answering** - `200`, `404`, anything. Only a
  connection-level failure (refused, timed out) means nothing is there.

```bash
curl -sk --max-time 5 -o /dev/null -w "%{http_code}\n" https://localhost:5678/
```

That is a POSIX-shell example, not the only way: `Invoke-WebRequest -SkipCertificateCheck
https://localhost:5678/` is the PowerShell equivalent, and any HTTP client works.

## Starting

| Command | Where | Notes |
|---|---|---|
| `locally build` | a developer machine | Full-screen TUI, opens a browser, runs DNS/container pre-flight. Refuses to run in a CI environment. |
| `locally ci` | **CI only** | No TUI. Needs OIDC, which a developer machine does not have. |

**On a developer machine, `locally build` is the only way to start an instance.**
`locally ci` authenticates through the CI provider's OIDC - GitHub Actions' `id-token`,
for example - so there is nothing for it to authenticate against on a laptop and it
cannot work there. Never reach for it as a way to start an instance non-interactively;
that is not a configuration gap the user can close, it is the wrong command. For CI
itself, `locally-ci` covers the whole setup.

**An agent cannot usefully run `locally build` either.** It is a full-screen alt-screen
TUI that opens a browser and never returns - shelling it out blocks the calling process
indefinitely, and backgrounding it strands a process on the fixed ports that outlives
the session. Ask the user to start it in their own terminal and say when it's up. There
is no third option: if no instance is running and the user cannot start one, say so
rather than substituting a command that will not work.

**The command to hand them is `locally build --skip-browser`:**

```bash
locally build --skip-browser
```

Someone starting Locally on their own initiative expects the dashboard to open - that
is the interactive default and there is no reason to talk them out of it. This is the
other case: they are starting it because *you* asked, in the middle of work they
delegated, possibly while you are running in the background. A browser window taking
focus unprompted interrupts exactly the flow they handed over to you. Suppressing it
costs them nothing, because the dashboard stays at `https://localhost:5678` for
whenever they actually want it - say so when you hand the command over, so the flag
doesn't look like something being hidden from them.

## Flags on `build`

Each pre-flight check `locally build` runs can be waived individually - with a flag for
an interactive run, or the matching environment variable, which is usually the better
fit for a prepared CI image:

| Flag | Environment variable | Skips |
|---|---|---|
| `--skip-browser` | - | Opening the dashboard in a browser on launch. Include this in any command you hand the user to run - see Starting. |
| `--skip-dns-check` | `LOCALLY_SKIP_DNS_CHECK=1` | The `*.locally` resolution check |
| `--skip-docker-check` | `LOCALLY_SKIP_DOCKER_CHECK=1` | The Docker-reaches-Locally check |
| `--skip-podman-check` | `LOCALLY_SKIP_PODMAN_CHECK=1` | The Podman-reaches-Locally check |

## Stopping

`locally ci --stop` stops a CI instance - in CI. It has nothing to stop on a developer
machine, where instances are started with `locally build`.

**No CLI command stops a `build` instance - under any name.** Not `locally stop`, not
`locally shutdown`, not `locally down` or `halt`. It ends when the terminal running it
receives Ctrl-C. Ask the user to press it; don't reach for a plausible-sounding
subcommand.

**And don't signal the process yourself.** `pkill -f locally`, `pgrep … | xargs kill`,
`kill -9` on whatever holds `5680` - these work, which is the problem. That instance is
the user's, it may hold state they care about, and stopping it is their call rather than
a workaround for there being no stop command. Tell them what to press.

Guessing is especially unsafe here because a wrong subcommand does not announce itself:
`locally shutdown` prints the banner and **exits 0**, exactly like a command that
worked. A zero exit status is not evidence the instance stopped. Check what is listening
if you need to know.

## Restarting

Stop the instance the way it was started - Ctrl-C for a `build` instance, `locally ci
--stop` for a CI instance - then start it again. That's it: there is no separate
restart command and no wait step to add. If a restart intermittently fails to bind,
that's a product issue to report, not something to poll around here.

## When to Use Other Skills

| Situation | Use |
|---|---|
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| An instance is running and you need to drive tools against it (`az`, Terraform, data-plane commands) | `locally-run` |
| An instance is running but behaving unexpectedly | `locally-debug` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |

See `references/ports.md` for the full fixed port table.
