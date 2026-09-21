```
ooooo                                      oooo  oooo              
`888'                                      `888  `888              
 888          .ooooo.   .ooooo.   .oooo.    888   888  oooo    ooo 
 888         d88' `88b d88' `"Y8 `P  )88b   888   888   `88.  .8'
 888         888   888 888        .oP"888   888   888    `88..8'
 888       o 888   888 888   .o8 d8(  888   888   888     `888'
o888ooooood8 `Y8bod8P' `Y8bod8P' `Y888""8o o888o o888o     .8'
                                                       .o..P'
                                                       `Y8P'
```

# Locally Skills

This repository contains Agent skills for [Locally](https://locally.build), which is a local
cloud environment for Azure that allows the Azure CLI, HashiCorp Terraform, OpenTofu, Pulumi,
PowerShell and applications built using the Azure SDKs to run against a local cloud running
on your machine instead of the real cloud.

> [!NOTE]
> Locally is made by Locally Build. It emulates Azure but is not a Microsoft product, and
> its documentation lives at [locally.build/docs](https://locally.build/docs) rather than
> anywhere under `microsoft.com` or `aka.ms`.

## Install

```bash
npx skills add locallybuild/skills
```

Or install a specific skill:

```bash
npx skills add locallybuild/skills --skill locally-run
```

## Skills

| Skill | Summary |
|---|---|
| [`locally-setup`](skills/locally-setup) | Configure a machine to run Locally, and manage the account behind it - certificates, DNS resolution for `*.locally`, the container runtime, signing in, licence renewal and what each plan includes. |
| [`locally-lifecycle`](skills/locally-lifecycle) | Start, stop, restart and check a Locally instance. |
| [`locally-run`](skills/locally-run) | Point Azure tooling at a running Locally instance - `az`, Terraform, OpenTofu, Pulumi, PowerShell and the Azure SDKs - drive its data planes, and deploy team runbooks. |
| [`locally-identity`](skills/locally-identity) | Work with identity in Locally - the seeded example directory, users and groups, service principals, tokens and Microsoft Graph permissions. |
| [`locally-debug`](skills/locally-debug) | Check whether Locally supports a provider, resource type or API version, work out why something behaves differently against Locally than against Azure, read request and audit logs, refresh reference data, and inject transient failures to test resilience. |
| [`locally-ci`](skills/locally-ci) | Run Locally inside GitHub Actions using the `locallybuild/setup-locally` actions. |
| [`locally-mcp`](skills/locally-mcp) | Use Locally's built-in MCP server instead of shelling out - registering it in a client, and which of its 70 tools to reach for. |
| [`locally-adapt`](skills/locally-adapt) | Adapt a Terraform, OpenTofu, Pulumi, ARM/Bicep, CLI or Azure SDK configuration so one definition works against both Locally and Azure. |

## Contributing

Skills are markdown: a `SKILL.md` per skill, plus optional `references/*.md` for
detail that would otherwise bloat it. There is nothing to build.

Text that every skill has to carry lives once in `common/` and is inlined into each
`SKILL.md` between `<!-- common:... -->` markers:

```bash
scripts/sync-common.py           # write the shared blocks into each SKILL.md
scripts/sync-common.py --check   # exit 1 if any skill has drifted
```

The copies exist because skills install independently - `npx skills add
locallybuild/skills --skill locally-run` puts exactly one directory on disk, so a
skill cannot reference a file outside its own folder. Edit `common/`, never the
generated block.
