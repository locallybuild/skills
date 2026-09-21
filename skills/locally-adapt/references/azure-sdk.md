# Azure SDK Applications Against Both Targets

An application built on the Azure SDKs reaches Locally the same way any other tool does
- `locally run ./myapp`, or `locally run dotnet run` - and the same contract applies:
credentials and configuration have to come from the environment. The difference is that
SDK clients are constructed in code, so "don't hardcode it" has to be expressed in a
constructor rather than deleted from a config file.

Three things must line up. Credentials are the easy one; the other two are where
dual-target apps break.

| What | Variables Locally sets | Usual state |
|---|---|---|
| Credentials | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | Read automatically by every Azure Identity library |
| Authority | `AZURE_AUTHORITY_HOST` | Read automatically by every Azure Identity library |
| Instance discovery | `AZURE_DISABLE_INSTANCE_DISCOVERY`, `AZURE_CORE_INSTANCE_DISCOVERY` | **May need passing explicitly** |
| ARM endpoint and audience | `AZURE_RESOURCE_MANAGER_ENDPOINT`, `AZURE_RESOURCE_MANAGER_AUDIENCE` | **Almost always needs passing explicitly** |
| Graph endpoint and audience | `AZURE_MICROSOFT_GRAPH_ENDPOINT`, `AZURE_MICROSOFT_GRAPH_AUDIENCE` | **Almost always needs passing explicitly** |

Run `locally run env` to see the current values; they are per-install, and the ones
above are names to design against rather than values to copy.

## Check the Installed Version Before Wiring By Hand

Locally Build is contributing changes upstream to the Azure SDKs so that the ARM
endpoint and audience are picked up from the environment automatically, the way the
credentials and authority already are. The work covers C++, Go, .NET, JavaScript /
TypeScript, Java, Python and Rust.

Where that has landed in the version an app actually depends on, the explicit wiring
described below stops being necessary: the client reads
`AZURE_RESOURCE_MANAGER_ENDPOINT` and `AZURE_RESOURCE_MANAGER_AUDIENCE` itself, and
needs no options object to reach Locally. So **check what the installed package does
before adding the wiring** - the manual path is for versions that don't yet do it.

The pattern in *The Shape That Works* below is safe either way, because it keys off
whether the variables are set rather than off the SDK's behaviour: once an SDK reads
them itself, setting the same values explicitly changes nothing.

**This file deliberately doesn't track which SDKs have shipped it.** That state changes
per language and per release, so it belongs in the SDK's own changelog or release notes,
not here - and a version this file called unsupported six months ago is exactly the kind
of claim that sends someone wiring around a problem they no longer have.

C++ and Rust are not in the per-language table below. The two variables are the same
there; what differs is how a client is constructed, so read that off the installed
package rather than assuming it matches one of the tabulated languages.

## Why the Last Three Need Wiring

**The management endpoint is compiled in.** `ArmClient`, `ResourceManagementClient` and
their equivalents default to `https://management.azure.com`. A credential picked up
correctly from the environment will happily mint a token and send it to Azure, so the
symptom is not an authentication error - it is an app that authenticates against Locally
and then operates on the real cloud, or fails with a 401 because the token's audience
doesn't match where it was sent.

**The audience travels with the endpoint.** Locally issues tokens for its own ARM
audience, not `https://management.azure.com/`. An SDK asked for a token with the default
scope gets one Locally's control plane will reject. Wherever the endpoint is set, the
credential scope has to be set alongside it - usually the audience with `/.default`
appended.

**Instance discovery must stay off.** Identity libraries normally fetch authority
metadata from a well-known Microsoft endpoint to validate the authority before using it.
Locally's authority is not in that list, so discovery either fails or rejects it. Locally
disables it through the environment; whether the installed library version reads those
variables or requires the corresponding option depends on the version, so treat this as
something to confirm rather than assume.

## The Shape That Works

Build one cloud-configuration object from the environment at startup, and construct
every client from it. The branch is a single `LOCALLY_ENVIRONMENT` check, and the
real-Azure path is the one where the optional variables are absent and the SDK defaults
apply:

```csharp
var armEndpoint = Environment.GetEnvironmentVariable("AZURE_RESOURCE_MANAGER_ENDPOINT");
var armAudience = Environment.GetEnvironmentVariable("AZURE_RESOURCE_MANAGER_AUDIENCE");

var options = new ArmClientOptions();
if (armEndpoint is not null && armAudience is not null)
{
    options.Environment = new ArmEnvironment(new Uri(armEndpoint), armAudience);
}

var client = new ArmClient(new DefaultAzureCredential(), subscriptionId, options);
```

Keyed on the variables rather than on `LOCALLY_ENVIRONMENT` directly, the same code path
serves both targets: against Azure the variables are unset, the `if` doesn't fire, and
the SDK's own defaults are what run. Reserve an explicit `LOCALLY_ENVIRONMENT` check for
behaviour that genuinely differs - skipping a resource, choosing a smaller SKU - rather
than for endpoint wiring.

## Where Each SDK Exposes It

The APIs below are the right place to look in each language; **confirm the exact shape
against the package version actually installed** rather than taking these as current.
The SDKs revise these surfaces, and this file is not the authority on any of them.

| Language | ARM endpoint + audience | Instance discovery |
|---|---|---|
| .NET | `ArmClientOptions.Environment` = `new ArmEnvironment(uri, audience)` | `DefaultAzureCredentialOptions.DisableInstanceDiscovery` |
| Python | `base_url=` and `credential_scopes=[audience + "/.default"]` on the management client | `disable_instance_discovery=True` on the credential |
| JavaScript / TypeScript | `{ endpoint }` in the client options; scope via the credential's `getToken` options | `disableInstanceDiscovery` in the credential options |
| Java | `AzureProfile` built with a custom `AzureEnvironment` | Credential-builder option |
| Go | `azcore.ClientOptions.Cloud`, a `cloud.Configuration` with the ARM service's `Endpoint` and `Audience` | `cloud.Configuration` / credential options |

Go's `cloud.Configuration` is the cleanest fit for this pattern - it holds the endpoint
and the audience together as one value that every client takes, which is exactly the
"one cloud object built from the environment" shape described above.

## Data-Plane Clients Are a Separate Question

`BlobServiceClient`, `ServiceBusClient` and the rest don't use the ARM endpoint at all -
they take the resource's own endpoint or connection string, which comes from the
resource that was created rather than from the environment. So a dual-target app should
read those from configuration in both cases, never construct them from an account name
and a hardcoded suffix like `.blob.core.windows.net`.

`locally storage connection-string` and the other data-plane commands produce the values
for a running instance; `locally-run` covers the full command set.

## Verifying It Reached Locally

An app that silently talks to real Azure looks identical to one that works, right up
until it bills someone. The check is whether the request arrived:

```bash
locally logs
```

If a call fails and nothing appears there, the client never reached Locally - an
endpoint is still pointing at Azure. If it appears and fails, it is a resource type,
API version or permission question instead, and `locally-debug` covers those.
