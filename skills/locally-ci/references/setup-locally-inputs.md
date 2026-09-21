# `setup-locally` Actions: Full Input Reference

Three actions live in the `locallybuild/setup-locally` repo. This page lists every
input, its default, and the validation rules the action itself enforces, taken from
each action's `action.yml`. The repo's README is the source for the usage examples and
the action refs; this page just goes deeper on the inputs than the README's tables do.

## `locallybuild/setup-locally` (top-level action)

| Input | Default | Notes |
|---|---|---|
| `version` | `latest` | CLI version. `latest` resolves at run time from the Locally API; or pin an explicit version (e.g. `v2026.09`) for the CLI binary itself - unrelated to the action's own tag. |
| `team-uuid` | `''` | Locally team UUID. Mutually exclusive with `user-uuid`; exactly one must be set. |
| `user-uuid` | `''` | Locally user UUID. Mutually exclusive with `team-uuid`; exactly one must be set. |
| `plugins` | `recommended` | One of `none`, `recommended`, `all`, `custom`. |
| `plugins-list` | `''` | Comma- or newline-separated plugin namespaces (e.g. `Microsoft.ServiceBus,Microsoft.Storage`). Required when `plugins: custom`; must be empty for every other value of `plugins`. A list that's only whitespace/separators is treated the same as empty and rejected under `custom`. |
| `start` | `'true'` | Whether to generate TLS material, install plugins, and start `locally ci`. Setting this `'false'` gets you the CLI on `PATH` and nothing else - no certs, no plugins, no running instance. |
| `cache` | `'true'` | Whether to cache the plugin directory between runs. Only takes effect when `start` is also `'true'`. |
| `cache-key-prefix` | `''` | Optional prefix on the cache key - e.g. to isolate the cache per branch or force a fresh one. |
| `expected-checksum` | `''` | Optional SHA-256 hex digest to verify the downloaded CLI tarball against. When set, this value is used instead of the sibling `.sha256` file the action would otherwise fetch from the same origin as the binary - use it to anchor trust to a hash verified out-of-band. |

Validation the action performs before doing anything else:

- Runner OS must be Linux, macOS, or Windows.
- Exactly one of `team-uuid` / `user-uuid` must be set (checked even when `start:
  false`, since the resulting env vars are exported either way).
- `plugins` must be one of `none` / `recommended` / `all` / `custom`, and the
  `plugins-list` emptiness rule above is enforced.

## `locallybuild/setup-locally/install-plugins`

Callable standalone (e.g. to install additional plugins later in the same workflow),
or invoked internally by the top-level action when `start: true`.

| Input | Default | Notes |
|---|---|---|
| `plugins` | `none` | Same four values as the top-level action. Note the default here is `none`, not `recommended` - the top-level action always passes an explicit value through, so this default only matters for standalone use. |
| `plugins-list` | `''` | Same rules as the top-level action. |
| `team-uuid` | `''` | Optional. Falls back to the `LOCALLY_TEAM_UUID` environment variable when blank. Mutually exclusive with `user-uuid`. |
| `user-uuid` | `''` | Optional. Falls back to the `LOCALLY_USER_UUID` environment variable when blank. Mutually exclusive with `team-uuid`. |

Standalone callers (not chained after the top-level action) must have `locally` on
`PATH` and must themselves set `LOCALLY_WORKING_DIRECTORY`, `LOCALLY_PLUGIN_DIRECTORY`,
and exactly one of `LOCALLY_TEAM_UUID` / `LOCALLY_USER_UUID` (or the matching
`team-uuid` / `user-uuid` input) - normally these already exist in the environment
because `setup-locally` ran earlier in the job.

When `plugins: none`, this action exits immediately without checking for a UUID at
all - a no-UUID job that never installs plugins is a valid configuration.

## `locallybuild/setup-locally/teardown`

| Input | Default | Notes |
|---|---|---|
| `upload-logs-on-failure` | `'true'` | Whether to upload `ci.log` as a workflow artifact when the job has failed. |

Behavior:

- Always runs `locally ci --stop`, tolerating failure (e.g. nothing was running).
- Uploads `$LOCALLY_WORKING_DIRECTORY/ci.log` as an artifact named `locally-ci-log`
  only when the job has failed (`if: failure()`) and `upload-logs-on-failure` is
  `'true'`. If no log file exists, the upload step is silently skipped rather than
  failing the job.
- This step only runs at all if the workflow schedules it - hence `if: always()` on
  the step that calls this action, so it still runs after an earlier step fails.

## Environment Variables `setup-locally` Exports

When `team-uuid` or `user-uuid` is set (which is required), the top-level action writes
these to `GITHUB_ENV` for use by later steps in the same job:

| Variable | Value |
|---|---|
| `LOCALLY_WORKING_DIRECTORY` | A per-job scratch directory holding certs and the CI log |
| `LOCALLY_TLS_CA_FILE_PATH` | Path to the generated CA certificate |
| `LOCALLY_TLS_CERT_FILE_PATH` | Path to the generated leaf (localhost) certificate |
| `LOCALLY_TLS_KEY_FILE_PATH` | Path to the generated leaf certificate's private key |
| `LOCALLY_PLUGIN_DIRECTORY` | Directory plugins are installed into (and cached, if `cache: true`) |
| `LOCALLY_TEAM_UUID` or `LOCALLY_USER_UUID` | Whichever of `team-uuid` / `user-uuid` was set, passed through |

The TLS variables are only meaningful when `start: true`, since certificate generation
is part of the start sequence.

## Readiness Behavior

After starting `locally ci` in the background, the action polls the CI control
endpoint - `https://127.0.0.1:5674/_locally/ci/endpoints` - every 2 seconds, up to 60
times, for a total of **120 seconds**. Any successful response means the instance is
ready. If none arrives inside that window, the action fails the step and dumps
`ci.log` to the workflow's error output, in addition to whatever `teardown` later
uploads as an artifact (if `if: always()` is set on that step).

That endpoint is the action's own business - internal, unversioned, and free to change
between releases. Describing it here explains what the action is waiting for; it is not
something to poll from a workflow step of your own. If a job needs to know Locally is
up, let `setup-locally` be the thing that waits.

**120 seconds is a ceiling, not an expectation.** The poll exits as soon as the
endpoint answers, so a fast runner spends a couple of seconds here. The window is
deliberately generous so that a slower or less powerful runner - a smaller hosted
image, a busy self-hosted machine, a cold plugin cache - still comes up, rather than a
job failing over a few seconds it would have got there in. A run that times out has
almost certainly hit a real fault rather than a slow machine, so read `ci.log` instead
of assuming the window is too tight.
