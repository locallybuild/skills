---
name: locally-identity
description: Work with identity in Locally - the seeded example directory, users and groups, service principals, tokens and Microsoft Graph permissions. Use when writing tests or Terraform against directory objects, creating a service principal, getting a token, or debugging a 403 from Graph. Triggers on "service principal", "seeded user", "example directory", "graph", "entra", "client credentials", "access token", "app registration", "role assignment", "Authorization_RequestDenied".
---

# Locally Identity

Directory objects, service principals, tokens and Microsoft Graph permissions in
Locally: the seeded example tenant every instance ships with, signing in as one of its
users, and how Graph calls against it are authorized.

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

## The Seeded Example Directory Is a Published Contract

Every Locally instance seeds the same tenant, `default.tenants.locally`, with the same
twelve users and five groups: fixed display names, UPNs, mail nicknames and object ids.
It's a published contract, safe to hardcode into Terraform configs, test fixtures and
CI scripts. A test written against `3ee3ec24-d0eb-4f28-9c8e-5078aa953cd8` today reads
the same object next year, on someone else's machine, against a freshly-seeded
instance.

See `references/seeded-directory.md` for the full user and group tables.

Two objects worth knowing by name rather than looking up every time:

- **Ada Lovelace** (`3ee3ec24-d0eb-4f28-9c8e-5078aa953cd8`) holds the Global
  Administrator directory role. Reach for her when a test needs a caller that passes
  every permission check.
- **Project Apollo** nests the **Research** group as a member, rather than adding
  Research's members to Apollo directly. This is the one place in the seeded directory
  where transitive membership and direct membership genuinely disagree: Apollo's
  `members` does not include Research's people, but its `transitiveMemberOf` traversal
  does. If a test needs to prove `transitiveMemberOf` handling is correct rather than
  incidentally correct, this is the pair to use - most other group relationships in the
  seed data don't exercise the difference.

## Signing In as a Seeded User

Every seeded user already has a working credential registered - unlike a service
principal you create yourself, there's no `addPassword` call needed first. The client
id is the user's own object id (from the table above, or the full list in
`references/seeded-directory.md`); the client secret is one fixed password shared by
all twelve seeded users:

```
Locally-Seed-Pa55!
```

Sign in with the standard OAuth2 client-credentials grant: `grant_type=client_credentials`,
`client_id=<the user's object id>`, `client_secret=Locally-Seed-Pa55!`. This is the
documented request shape, not something exercised end-to-end here - write it, don't
assume the round trip has been watched to succeed.

**To run a tool *as* a seeded user, prefer `locally run --user`.** `locally run --user
<upn|uuid> <command>` runs the wrapped command under that user's delegated token, with no
password in the environment - so `locally run --user ada.lovelace@default.tenants.locally
az account show` skips the token request entirely. Do the client-credentials grant by hand
when a tool needs the raw token itself rather than an environment to run in; `locally-run`
documents the flag alongside its `--service-principal` and `--managed-identity` siblings.

**Don't hardcode a host into the token URL.** Running inside `locally run` means the
authority and tenant come from the environment Locally sets, `AZURE_AUTHORITY_HOST` and
`ARM_TENANT_ID` - so the same command keeps working if those change, rather than baking
in a detail the product owns:

```bash
locally run bash -c 'curl -s "$AZURE_AUTHORITY_HOST/$ARM_TENANT_ID/oauth2/v2.0/token" \
  -d grant_type=client_credentials \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=<the resource you want a token for>"'
```

`/{tenant}/oauth2/v2.0/token` is the MSAL-shaped endpoint; `/{tenant}/oauth2/token` is
an ADAL-era alias for the same handler, for a caller that still speaks the older shape.
To confirm the endpoint rather than take it on faith, OIDC discovery is a real,
supported path: `GET /{tenant}/v2.0/.well-known/openid-configuration` (again, resolved
against `$AZURE_AUTHORITY_HOST`/`$ARM_TENANT_ID`, not a literal host) advertises
`token_endpoint` directly.

Use Ada Lovelace's object id (`3ee3ec24-d0eb-4f28-9c8e-5078aa953cd8`) as `client_id`
when a test needs a token that passes every permission check; use any other seeded
user's object id to test a specific, narrower set of grants instead.

If you've created your own service principal rather than using a seeded user, it needs
a client secret from `addPassword` first - seeded users are the only identities in
Locally with a credential already in place.

## Graph Permissions Are Enforced

A Microsoft Graph call against Locally is authorized against the caller's *effective*
grants, resolved from every source that feeds the calling identity's permissions:

- directory role membership, including a role held only through membership in a group;
- app role assignments (application permissions, from a client-credentials token);
- OAuth2 permission grants (delegated permissions, from a user token).

A caller holding Global Administrator short-circuits the check - Ada Lovelace (above)
passes every permission gate for exactly this reason.

When none of a route's required permissions resolve, the call is denied with a real
Graph `403`:

```json
{
  "error": {
    "code": "Authorization_RequestDenied",
    "message": "Insufficient privileges to complete the operation."
  }
}
```

That's Microsoft's own error code and message text - tooling that string-matches on
`Authorization_RequestDenied` behaves identically against Locally and against real
Azure.

## Grant the Least-Privileged Permission That Works

Locally's permission catalogue is trimmed to the least-privileged permission(s) that
authorize each route. Where a route has more than one entry, those entries are
**alternatives, not a conjunction** - holding any *one* of them authorizes the call.
Where a route has exactly one entry, that's the only grant that works - many routes
are this way. Either way, the right move when a call 403s is to grant the narrowest
thing the route's catalogue entry actually contains, not to reach for `.ReadWrite.All`
because it's guaranteed to cover everything.

Listing users (`GET /users`) is a one-entry route: Locally authorizes it on
`User.ReadBasic.All` alone, for both a delegated and an application token. Real
Microsoft Graph documents a broader set for the same route - `User.Read.All`,
`Directory.Read.All`, `User.ReadWrite.All` and `Directory.ReadWrite.All` also work
against real Azure - but Locally's catalogue doesn't extend that far, and a caller
holding only `Directory.Read.All` still 403s against Locally. Don't assume a route
accepts everything Microsoft's own docs list for it. Check what Locally's catalogue
contains for the specific failing route, and grant only that - not whichever
`.ReadWrite.All` scope happens to be lying around from another app registration.

## Delegated and Application Tokens Resolve Different Requirements

The same Graph route can require a different grant depending on what kind of token is
presenting it:

- A **delegated** (user) token is authorized by an `oAuth2PermissionGrant` - permission
  consented to for a user or the whole tenant.
- An **application** (client-credentials, app-only) token is authorized by an
  `appRoleAssignment` - permission granted directly to the app's service principal.

These are not interchangeable. A route that 403s with a client-credentials token can
work fine with a user token carrying the matching delegated permission, and vice versa.
Before debugging why a grant "isn't working," check which kind of token the call
actually used - the fix for a missing `oAuth2PermissionGrant` and the fix for a missing
`appRoleAssignment` are different actions, and applying the wrong one leaves the same
403 in place.

## Graph Permissions and ARM RBAC Are Separate Systems

Both are enforced, and neither implies the other. A caller authorized for a Graph call
- say, reading a user or a group - is not thereby authorized for the equivalent ARM
operation, and a role assignment on an ARM scope (a subscription, a resource group)
grants nothing on the Graph side. A caller that can read directory data but gets a 403
on a resource-management call (or the reverse) isn't a contradiction to chase down -
it's two independent authorization systems, each with its own grant to check.

## SKU Gating Is a Different Axis From Permissions

Some capabilities are gated by installation tier rather than by permission, and that
check is separate from - and on top of - Graph and ARM authorization. A caller can hold
exactly the right permission and still be refused because the installation's tier
doesn't include that capability. This looks like a permissions problem (a 403, or
something that reads like one) but isn't fixed like one: granting a broader permission
does nothing for a tier gate, and the fix is a tier change, not a grant. When a denial
doesn't clear after confirming the permission grant is correct, check whether tier is
the actual blocker before re-checking the grant a second time.

`locally-setup` carries the matrix of which plan includes what, and the wording of the
refusal - `this feature requires a <plan> plan` - is how a tier gate identifies itself.

## Team Directory Objects

A team can publish directory objects - users, groups, applications, service principals -
that every install provisions the same way, separately from the seeded example directory
above:

```bash
locally runbooks directory list        # what is synced
locally runbooks directory provision   # create them on the running instance
```

These are synced from the account, so an install with none is not misconfigured. They
are a change to the instance's directory: say what `provision` will create before
running it. `locally-run` covers runbooks in full.

## When to Use Other Skills

| Situation | Use |
|---|---|
| No instance is running, or one needs starting/stopping/restarting | `locally-lifecycle` |
| The machine itself isn't configured - certificates, DNS, container runtime | `locally-setup` |
| Pointing `az`, Terraform or another tool at a running instance | `locally-run` |
| The **Locally account** rather than a directory object - signing in, switching account, licence, plans | `locally-setup`. Identity here means the emulated Entra directory; who you are signed in to Locally *as* is a different thing entirely |
| An instance is running but behaving unexpectedly | `locally-debug` |
| Adapting a config to run against both Locally and Azure | `locally-adapt` |
