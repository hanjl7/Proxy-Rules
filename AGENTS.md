# Project Memory

## Purpose and trust boundary

This repository publishes the owner's reusable proxy routing rules for multiple
clients.

- GitHub repository: `hanjl7/Proxy-Rules`
- Required visibility: **Public**
- Default branch: `main`
- Private configuration repository: `hanjl7/Clash-Config`

This public repository may contain domains, IP ranges, ASNs, ports, user-agent
patterns, and process names used for routing. It must never contain proxy
nodes, subscription URLs, UUIDs, passwords, access tokens, complete Clash
configurations, or complete Shadowrocket configurations.

Never copy files or Git history from the private `Clash-Config` repository into
this repository.

## Current model

The manifest currently aggregates:

- 5 upstream repositories;
- 34 declared upstream inputs;
- 6 local override files;
- 10 provider categories;
- 10 Clash outputs and 10 Shadowrocket outputs.

The provider categories are:

| Provider | Output basename | Purpose |
| --- | --- | --- |
| `Directrp` | `Direct` | Explicit direct traffic |
| `AIrp` | `AI` | AI services |
| `Cryptorp` | `Crypto` | Cryptocurrency services |
| `Socialrp` | `Social` | Social networks |
| `Videorp` | `Video` | Video and streaming |
| `Techrp` | `Tech` | Technology platforms |
| `Brokerrp` | `Broker` | Finance and foreign brokers |
| `Gamerp` | `Game` | Gaming platforms |
| `Chinarp` | `China` | Broad mainland China rules |
| `Proxyrp` | `Proxy` | Broad proxy rules |

If these counts or categories change, update this file and `README.md` in the
same change.

## Repository map

- `sources.yaml`: authoritative source, aggregation, transform, target, and
  override manifest.
- `overrides/clash/*.yaml`: repository-maintained additions that survive future
  upstream synchronization.
- `rules/clash/*.yaml`: generated Clash classical rule providers.
- `rules/shadowrocket/*.list`: generated Shadowrocket RULE-SET files.
- `scripts/sync_rules.py`: synchronization, conversion, validation, checksum,
  and atomic replacement implementation.
- `checksums.sha256`: SHA-256 values for all 20 managed outputs.
- `.github/workflows/sync-rules.yml`: weekly and manually triggered upstream
  synchronization.
- `THIRD_PARTY_NOTICES.md`: upstream authorship and license status.

Files under `rules/` and `checksums.sha256` are generated. Do not edit them
manually. Persistent personal additions belong in `overrides/clash/`.

## Upstream sources and licensing

The current upstreams are declared in `sources.yaml`:

- `blackmatrix7/ios_rule_script` at `master`, GPL-2.0;
- `haha-miao/rule_file` at `main`, license not declared;
- `Accademia/Additional_Rule_For_Clash` at `main`, MIT;
- `SkywalkerJi/Clash-Rules` at `master`, GPL-3.0;
- `hanjl7/Shadowrocket-Rules` at `main`, MIT.

Preserve generated source comments and upstream attribution. Do not apply one
new repository-wide license to third-party rule content. When adding or
removing an upstream, update both `sources.yaml` and
`THIRD_PARTY_NOTICES.md`.

## Manifest invariants

`sources.yaml` is version 1. Every input must define:

- `provider`;
- `client`;
- `format`;
- `source`;
- `upstream_path`;
- `target_path`.

The supported input format is `clash-classical`. A Shadowrocket list input may
declare `transform: shadowrocket-list-to-clash-classical`.

Each provider maps to exactly one Clash target, and each target maps to exactly
one provider. Input triples must be unique. Paths must be safe relative paths
without `.` or `..`.

Overrides:

- must reference an existing provider;
- must live under `overrides/`;
- must be Clash YAML containing a non-empty `payload` list;
- are merged after upstream inputs;
- participate in normalization and exact de-duplication.

Aggregation order is significant. Preserve manifest input order and provider
order unless a routing change explicitly requires reordering.

## Client conversion rules

Clash output is classical YAML:

```yaml
payload:
  - "DOMAIN-SUFFIX,example.com"
```

Shadowrocket output is derived from that exact Clash payload:

- remove the Clash `payload:` wrapper;
- convert `IP-CIDR6` to `IP-CIDR`;
- omit all `PROCESS-NAME*` and `PROCESS-PATH*` rule types;
- preserve every other supported rule in the same order;
- fail if an unsupported rule type remains.

The validator reconstructs the expected Shadowrocket list from the Clash
payload and requires exact equality. Never maintain the two client formats
independently.

## Synchronization safety

Use `gh`, `git`, Python, and `uv`. Do not replace `uv` with a global Python
environment.

Full synchronization:

```bash
uv run --frozen python scripts/sync_rules.py sync
uv run --frozen python scripts/sync_rules.py validate
```

Synchronization:

1. shallow-clones each upstream through `gh repo clone`;
2. uses sparse checkout for only the declared inputs;
3. builds both client trees in a temporary staging directory;
4. validates all inputs and generated outputs;
5. computes all checksums;
6. replaces both client directories only after every step succeeds.

If any upstream, transform, rule, or checksum fails, preserve the last known
good snapshots. Do not partially publish a successful subset.

Before running `sync`, inspect `git status`. Existing changes belong to the
user unless proven otherwise. Synchronization replaces generated trees and can
mix fresh upstream drift into an unrelated local routing change. Do not discard
or overwrite a dirty generated tree without understanding its origin.

Read-only repository validation:

```bash
uv run --frozen python scripts/sync_rules.py validate
```

Expected current result:

```text
Validated 20 managed rule files
```

## Adding a persistent routing rule

For a personal domain, IP, ASN, port, or desktop process rule:

1. choose the narrowest existing category;
2. edit its `overrides/clash/<Category>.yaml`;
3. use a valid Clash classical rule;
4. regenerate with `sync`;
5. validate both output formats and checksums;
6. confirm the rule appears exactly once in the Clash output;
7. confirm Shadowrocket contains the converted rule, or intentionally omits a
   desktop process rule.

Do not add a new provider when an existing category is semantically correct.
If a new provider is necessary, update the manifest, both client outputs,
README category documentation, checksums, and consuming private configuration
in a coordinated change.

When diagnosing traffic that matched `DIRECT` or the wrong policy, prefer
evidence from the client's connection log. Add the narrowest stable rule and
place it in a category that the private configuration evaluates before broad
`China`, `Proxy`, or fallback rules.

## GitHub Actions

`.github/workflows/sync-rules.yml` runs:

- every Monday at `03:17 UTC`;
- on manual `workflow_dispatch`.

The workflow has `contents: write`, validates before committing, and commits
only `rules/` plus `checksums.sha256` when content changes. An unchanged sync
must not produce an empty commit.

After pushing a synchronization-related change:

```bash
gh run list \
  --repo hanjl7/Proxy-Rules \
  --workflow sync-rules.yml \
  --limit 1
```

Wait for the run to reach `completed/success`. For release verification, fetch
all expected raw URLs or at minimum every changed output and compare their
SHA-256 values with `checksums.sha256`.

## Relationship to Clash-Config

The private `hanjl7/Clash-Config` repository consumes these public raw URLs:

```text
https://raw.githubusercontent.com/hanjl7/Proxy-Rules/refs/heads/main/rules/clash/<Category>.yaml
https://raw.githubusercontent.com/hanjl7/Proxy-Rules/refs/heads/main/rules/shadowrocket/<Category>.list
```

Normal rule-content updates do not require publishing the private complete
configuration again; clients obtain provider updates from this public
repository according to their configured refresh behavior.

Changes to provider names, filenames, paths, or category ordering require a
coordinated update in `Clash-Config`. Preserve the public URL contract whenever
possible.

## Standard release checklist

1. Inspect repository status and identify pre-existing changes.
2. Review changes without dumping unrelated generated rule files.
3. Run `sync` when upstream or override content changed.
4. Run `validate`.
5. Run `git diff --check`.
6. Verify that exactly 10 Clash and 10 Shadowrocket files are managed unless
   the manifest intentionally changed.
7. Verify `checksums.sha256` contains one entry for every managed output.
8. Scan staged content for private configuration material and credentials.
9. Commit only files belonging to the current task.
10. Push `main`, wait for Actions when applicable, and verify raw files.

Do not report success merely because files were generated locally. A published
change is complete only after the intended Git commit is on remote `main` and
the relevant raw outputs are accessible.
