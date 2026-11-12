---
name: locally-snapshots
description: Save, restore, compare and share everything in a Locally instance with Locally Snapshots. Use when the user wants a checkpoint before a risky change (applying Terraform, deploying a new version of an app), to roll back to one, to see what changed since one, to hand a working environment to a teammate, or to load one a teammate shared. Covers `locally snapshot` save, load, list, inspect, diff, share, download, delete and status, encrypting with a passphrase, and the plan each needs. Triggers on "snapshot", "take a snapshot", "checkpoint", "roll back", "restore", "undo what that deployment did", "what changed since", "diff against", "share my environment", "send my setup to a teammate", "load the team's snapshot", "LOCALLY_SNAPSHOT_PASSPHRASE".
---

# Locally Snapshots

A Locally Snapshot is a point-in-time copy of everything in a Locally instance: every
Subscription and resource, the directory, role assignments and policy, and the data in
the Data Plane Emulators - including databases running in containers. Snapshots are
saved in the Locally config directory, and can be restored, compared with each other or
with the instance now, and shared with a Locally Team.

`locally --help` text lags the product in places. This skill states only what live
commands show - never a paraphrase of help text.

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
| Take a checkpoint | `locally snapshot save --name <n> --description "<why>"` | Name defaults to the date and time. Writes pause while it's taken. |
| Roll back to it | `locally snapshot load <n>` | **Replaces everything in the instance.** Confirm first. |
| What changed since | `locally snapshot diff <n>` | `--exit-code` to fail a script on any difference, `--json` for a machine-readable diff. |
| What a snapshot holds | `locally snapshot inspect <name\|path>` | Checks it the way `load` would, without loading it. |
| List | `locally snapshot list` | Includes snapshots shared with your teams; `--local` for this machine only. |
| Share with a team | `locally snapshot share <n>` | Team plan. Save it with `--passphrase` first - see Credentials. |
| Fetch a teammate's | `locally snapshot download <n>` | Into the snapshots folder, without loading it. |
| Is a save or load running | `locally snapshot status` | Also shows what persistent mode is doing. |

## Before You Start

**Plans.** Snapshots need the Standard plan or above. Sharing with a team (`share`,
`download`, and `--team` on the other commands) needs the Team plan or above. A refusal
naming the plan is the account, not a fault - `locally-setup` covers plans.

**A running instance.** `save`, `load`, `inspect` and `diff` against the current state
all need one. `locally-lifecycle` covers checking for one and asking the user to start
it - an agent can't start one itself.

## Taking a Checkpoint

The common case: the user is about to do something that changes a lot - apply a
Terraform configuration, deploy v2 of their app, run a script against the data - and
wants to be able to get back to where they were.

```bash
locally snapshot save --name before-v2 --description "Before deploying v2 of the orders app"
```

- **Name it for what it's before**, not the date - the user will be choosing between
  snapshots by name later. Without `--name` it's named for the current date and time.
- **`--description`** is one line, at most 500 characters. It shows in `list`, so say why
  the snapshot was taken.
- **Writes pause while it's taken.** Running operations are allowed to finish first, then
  requests get a 503 until the save completes - the Azure SDKs and tools retry these on
  their own. `--timeout` gives up if running operations take too long to finish.

Offer a snapshot before anything destructive you're about to do on the user's behalf,
and before asking them to restart an instance that wasn't started with `--persist` (a
restart empties it).

## Rolling Back

```bash
locally snapshot load before-v2
```

**`load` replaces everything in the instance with the snapshot.** Anything created or
changed since it was taken is gone - so confirm with the user before running it, and say
what will be lost. If they might want the current state back, `save` it first.

A load is all-or-nothing: if any of the snapshot can't be loaded, the instance is left as
it was. `load` also takes a path, for a snapshot file a teammate sent directly.

## Seeing What Changed

```bash
locally snapshot diff before-v2                # the snapshot against the instance now
locally snapshot diff before-v2 after-v2       # two snapshots
locally snapshot diff before-v2 --exit-code    # exit 1 on any difference, 0 on none
locally snapshot diff before-v2 --json
```

The first snapshot is the earlier side: something only in the instance now (or only in
the second snapshot) shows as added.

- Resources are matched by resource ID and compared on what a client reads back from
  them. Everything else - blobs, directory users, queue messages - is compared record by
  record.
- **Credentials are never shown.** A changed key or secret is reported as changed,
  without its value.
- Timestamps, etags, the activity log, delivered events and issued tokens change on their
  own, so they're left out. `--all` includes them.
- Diffing against the instance now saves its current state first, so writes pause as they
  do for `save`. That temporary copy is removed afterwards.

`--exit-code` makes `diff` a test: take a snapshot, run something that shouldn't change
anything, and fail if it did.

## Credentials

**Snapshots contain the credentials of the resources in them** - Key Vault secrets and
keys, storage account keys, database passwords. Say so before a snapshot leaves the
user's machine, and suggest encrypting it:

```bash
locally snapshot save --name shared-baseline --passphrase
```

`--passphrase` prompts for the passphrase, or reads `LOCALLY_SNAPSHOT_PASSPHRASE`. An
agent can't answer the prompt, so either the user runs the command themselves or sets
the variable - never put a passphrase on a command line or in a file yourself. `load`
asks for it automatically when a snapshot is encrypted.

## Sharing With a Team

```bash
locally snapshot share shared-baseline        # Team plan; at most 500 MiB
locally snapshot list                         # includes your teams' snapshots
locally snapshot download shared-baseline     # into the snapshots folder, not loaded
locally snapshot inspect shared-baseline      # before loading it
locally snapshot load shared-baseline
```

- **`--team`** names the team (by name or ID) when the user is in more than one.
- **`--id`** picks one shared snapshot when several share a name.
- **`download --as <name>`** keeps it under a different name locally; `load --team`
  downloads and loads in one go, with `--as` for the local name.
- **Run `inspect` before loading someone else's snapshot.** It shows what the snapshot
  holds, the plugins it needs, what it would run or contact, and whether the load would
  be refused. A snapshot can need plugins this install doesn't have - those are installed
  as part of the load, **and stay installed even if the load is then refused**.

`delete <name>` removes a local snapshot; with `--team` it deletes the shared one, and
asks first unless given `--yes`. Don't pass `--yes` on the user's behalf.

## Persistent Mode

`locally build --persist` is built on snapshots: the instance loads a snapshot called
`default` (or `--persist=<name>`) when it starts, autosaves it every 15 minutes when
something changed, and saves on shutdown. Those saved states show in `locally snapshot
list` like any other. Starting and stopping an instance - and so `--persist` and
`--clear-state` - is `locally-lifecycle`'s.

## When to Use Other Skills

| Situation | Use |
|---|---|
| No instance is running, or the user wants to start one with `--persist` | `locally-lifecycle` |
| A command is refused because of the plan, or the user isn't signed in | `locally-setup` |
| Running the Terraform or deployment the snapshot is a checkpoint for | `locally-run` |
| Data is missing after a restart | `locally-debug` |
