---
name: locally-ci
description: Run Locally inside GitHub Actions using the locallybuild/setup-locally actions. Use when setting up CI that needs Locally, writing or fixing a workflow, or debugging why Locally fails to start in Actions. Covers OIDC trust setup, the id-token permission, plugin selection, teardown and log artifacts. Triggers on "github actions", "workflow", "CI", "setup-locally", "OIDC", "id-token", "run tests against locally in CI".
---

# Locally CI

Running Locally inside a GitHub Actions workflow via the `locallybuild/setup-locally`
family of actions: the top-level `setup-locally` action, its `install-plugins` sister
action, and its `teardown` sister action.

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

## A Complete, Correct Workflow

This is what most people copying this skill actually want. Start from it and adjust:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write        # required: GitHub mints the OIDC token Locally signs in with
    steps:
      - uses: actions/checkout@v5
      - uses: locallybuild/setup-locally@v1
        with:
          team-uuid: ${{ vars.LOCALLY_TEAM_UUID }}
      - run: locally run terraform apply -auto-approve
      - uses: locallybuild/setup-locally/teardown@v1
        if: always()
```

## The Four Things That Break Real Workflows

### 1. `permissions: id-token: write` is required

Without it, GitHub never injects `ACTIONS_ID_TOKEN_REQUEST_URL` /
`ACTIONS_ID_TOKEN_REQUEST_TOKEN` into the job environment, and Locally's OIDC sign-in
fails with an opaque authentication error rather than a clear "no token" message.

The natural objection is "why not `read`, so the workflow can't do anything with it?"
`id-token` doesn't offer that choice: GitHub's own workflow-syntax reference states it
"does not support `read` access" - the only values are `write` and `none`. `id-token:
read` isn't a more restrictive setting, it's invalid.

And `write` here grants no write access to any resource. Per GitHub, `id-token: write`
"only allows the workflow to request (fetch) and use (set) an OIDC token" for the job -
it does not touch repo contents, packages, or anything else. Grant it at job level,
paired with an explicit `contents: read` so the job's overall permission footprint stays
minimal and legible:

```yaml
permissions:
  contents: read
  id-token: write
```

### 2. Exactly one of `team-uuid` / `user-uuid`

`setup-locally` and `install-plugins` both require exactly one of these. Set both, or
set neither, and the action fails fast with an explicit error rather than guessing.
Which one you set depends on where the OIDC trust relationship was configured -
team-scoped or user-scoped (see below).

### 3. `teardown` needs `if: always()`

Without it, a failed test step skips the teardown step entirely: the `locally ci`
instance leaks past the end of the job, and no log gets uploaded to help debug the
failure. `if: always()` on the teardown step is what makes cleanup and log capture run
regardless of whether earlier steps passed.

### 4. `plugins: custom` requires `plugins-list`; every other mode requires it stay empty

`plugins-list` is only meaningful when `plugins: custom`. Set it under `none`,
`recommended`, or `all` and the action rejects the input rather than silently ignoring
it. Set `plugins: custom` without `plugins-list` (or with a list that's just whitespace
or separators) and it fails the same way - that combination has no reasonable default.

```yaml
- uses: locallybuild/setup-locally@v1
  with:
    team-uuid: ${{ vars.LOCALLY_TEAM_UUID }}
    plugins: custom
    plugins-list: |
      Microsoft.ServiceBus
      Microsoft.Storage
```

## Version References

Reference `locallybuild/setup-locally` and its sister actions by the major tag -
**`@v1`** - which is what the repo's own README uses for all three, and the default to
write unless the user asks for something stricter.

**A commit SHA is the hardened alternative, and it is a legitimate thing to want.** A
tag is mutable: whoever controls the action's repository can repoint it, which is how
supply-chain attacks on GitHub Actions have actually worked. GitHub's own Actions
hardening guidance and OpenSSF Scorecard both recommend pinning third-party actions to a
full-length commit SHA for that reason, and `locallybuild/setup-locally` is third-party
from the consuming repository's point of view. So if someone asks for SHA pins, or the
repo already uses them elsewhere, pin the SHA - don't talk them out of it:

```yaml
- uses: locallybuild/setup-locally@<40-char-sha>  # v1
```

Keep the version in a trailing comment, since a bare SHA tells a reader nothing, and
suggest Dependabot or Renovate alongside it (`package-ecosystem: github-actions`) -
that is the part people forget, and an unattended SHA pin silently stops receiving
fixes.

Don't confuse either with the `version` input, which takes a CLI version like
`v2026.09` and is unrelated to the action's ref. They use different schemes, and
reading the CLI's scheme onto the action ref produces a tag that does not exist.

## Getting a Team or User UUID

Both `team-uuid` and `user-uuid` come from an OIDC trust relationship configured at
`account.locally.build`: **Add Trust → GitHub Actions**, on either the **Team CI
(OIDC)** page (for a `team-uuid`) or the **User CI (OIDC)** page (for a `user-uuid`).
Configuring trust there is what lets a GitHub Actions job authenticate as that team or
user without a stored secret - the job's OIDC token is what `setup-locally` presents.

Store the resulting UUID as a repository or organization variable (`vars.*`), not a
secret - it identifies the team or user, it isn't a credential by itself.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Opaque authentication failure starting Locally | Missing `id-token: write` in `permissions` |
| "exactly one of team-uuid or user-uuid is required" / "...are mutually exclusive" | Both or neither of `team-uuid` / `user-uuid` set |
| Job hangs, then "Locally CI did not become ready within 120s" | Read `ci.log` from the `locally-ci-log` failure artifact (uploaded by `teardown` when `if: always()` is set and the job failed) |

## Reference

`references/setup-locally-inputs.md` has the full input table for all three actions,
the environment variables `setup-locally` exports, and the readiness-polling behavior in
detail.

## When to Use Other Skills

| Situation | Use |
|---|---|
| Starting, stopping, or restarting an instance outside of CI | `locally-lifecycle` |
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| Pointing `az`, Terraform or another tool at a running instance | `locally-run` |
| The instance starts in CI but behaves unexpectedly once running | `locally-debug` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |
