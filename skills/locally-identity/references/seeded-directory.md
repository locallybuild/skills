# The Seeded Example Directory

Every Locally instance seeds the same tenant - `default.tenants.locally` - with the
same twelve users and five groups. Display names, UPNs, mail nicknames and object ids
are fixed across instances: they are a published contract, safe to hardcode into
Terraform configs, test fixtures and CI scripts.

A user's UPN and mail nickname both use the same slug: `<slug>@default.tenants.locally`
is the UPN, `<slug>` is the mail nickname.

## Users (12)

| Display name | Slug (UPN / mail nickname) | Job title | Department | Manager | Object id |
|---|---|---|---|---|---|
| Ada Lovelace | `ada.lovelace` | Director of Engineering | Engineering | - | `3ee3ec24-d0eb-4f28-9c8e-5078aa953cd8` |
| Grace Hopper | `grace.hopper` | Principal Engineer | Engineering | Ada Lovelace | `1cb929ec-2007-41e8-98ef-50c05d070812` |
| Alan Turing | `alan.turing` | Senior Engineer | Engineering | Ada Lovelace | `b483e7a5-d76b-4606-84da-7274ec7359ac` |
| Dennis Ritchie | `dennis.ritchie` | Senior Engineer | Engineering | Ada Lovelace | `0686c14e-12b7-48ec-9897-a59192470a99` |
| Margaret Hamilton | `margaret.hamilton` | Software Engineering Lead | Engineering | Ada Lovelace | `90df63fc-2723-437f-9b3b-2c0399be93f9` |
| Frances Allen | `frances.allen` | Compiler Engineer | Engineering | Margaret Hamilton | `c516402a-e5ae-4d25-96eb-596b6092a0fe` |
| Claude Shannon | `claude.shannon` | Head of Research | Research | - | `b4214862-db7f-4ef6-90eb-8febf00e073b` |
| Katherine Johnson | `katherine.johnson` | Research Scientist | Research | Claude Shannon | `30a533b8-4a32-46b5-85ce-fb8d82a998e7` |
| Karen Spärck Jones | `karen.sparck.jones` | Research Scientist | Research | Claude Shannon | `610278b2-ba5b-4c6d-9b9a-bcef5f02b86f` |
| Douglas Engelbart | `douglas.engelbart` | Director of Platform | Platform | - | `f5aa2869-8c23-44b5-8f53-4a91b07e8a7d` |
| Edsger Dijkstra | `edsger.dijkstra` | Principal Engineer | Platform | Douglas Engelbart | `2ac26a70-66f7-45da-9e6b-3db2cb3a9e8c` |
| John von Neumann | `john.vonneumann` | Systems Architect | Platform | Douglas Engelbart | `9e4bf930-514f-410b-b941-dce97e12cfac` |

Ada Lovelace holds the Global Administrator directory role.

**Two of these names are there to exercise real-world name handling.** Karen Spärck
Jones has a diacritic inside a two-word surname; John von Neumann has a multi-part
surname with a lowercase particle. Both are perfectly ordinary names - the seed data
includes them because slugification, sorting and display logic written for a simple
"first last" shape routinely mangles them, and the defect in that case is in the code,
not the name. Reach for these two specifically when a test needs to prove name handling
is correct rather than merely untested.

## Groups (5)

| Display name | Mail nickname | Type | Owner | Members | Object id |
|---|---|---|---|---|---|
| Engineering | `engineering` | Security | Ada Lovelace | Ada, Grace, Alan, Dennis, Margaret, Frances | `c4a3aed4-10bd-4632-add2-388421fa62ee` |
| Research | `research` | Security | Claude Shannon | Claude, Katherine, Karen | `e54c1624-2cff-44dc-b0be-548882b40b20` |
| All Employees | `all-employees` | Microsoft 365 (unified) | Ada Lovelace | all twelve users | `1ea2a16f-95d0-4da8-bb43-761faca8c2cd` |
| Platform Admins | `platform-admins` | Security | Ada Lovelace | Ada, Douglas, Edsger, John | `b2001b4c-ff88-411d-916a-6a2b9cb41d44` |
| Project Apollo | `project-apollo` | Security | Margaret Hamilton | Margaret, Grace, Douglas, **and the Research group itself (nested)** | `d78d86f8-736f-48bc-86b4-28472a543805` |

Group type follows from mail-enabled / security-enabled the same way it does in Entra: a
unified (Microsoft 365) group is mail-enabled and not security-enabled, while the other
four are security-enabled and not mail-enabled. All Employees is the only unified group
in the seed data - the rest are plain security groups.

**Project Apollo nests the Research group as a member, rather than adding Research's
people to Apollo directly.** Apollo's direct `members` are Margaret, Grace and Douglas,
plus the Research group object itself - Katherine and Karen are not in that list. But
Apollo's `transitiveMemberOf` traversal does include Katherine and Karen, through
Research. This is the one place in the seed data where direct membership and transitive
membership genuinely disagree, and so it's the pair to reach for when a test needs to
prove `transitiveMemberOf` handling is correct rather than incidentally correct.

## Signing In

Every seeded user has a working credential already registered - no `addPassword` call
needed first. The client id is the user's own object id from the table above; the
client secret is one fixed password, shared by all twelve seeded users:

```
Locally-Seed-Pa55!
```

## Deletion

Deleting a seeded user does not stick: a later sync tick resurrects them as a service
principal with the same object id and display name. **Deleting a seeded group does
stick** - a deleted group stays deleted. Don't rely on a seeded user staying deleted in
a test; do rely on a seeded group staying deleted.
