# pyRevit ModularPipelines build

C# ModularPipelines project that replaces the YAML-heavy CI steps previously driven by `pipenv run pyrevit ...`.

## Prerequisites

- .NET 10 SDK (preinstalled on `windows-2025` runners)
- `dotnet`, `msbuild`, `go` on PATH
- Inno Setup 6 (`ISCC.exe`) for installer builds — preinstalled on `windows-2025`
- WiX Toolset v3.x build tools for the legacy CLI MSI project — preinstalled on `windows-2025`
- `choco` for Chocolatey packaging/publish
- `wingetcreate` for WinGet manifest updates (release publish workflow)
- Azure Trusted Signing credentials for `sign` steps (production only)

### Local development

If a dev clone is attached to this repository, **close Revit** before running `dotnet run -c Release -- ci`. Revit loads engine DLLs from `bin/netfx/engines/` and blocks in-place updates (same constraint as core DLL updates in pyRevit).

If the build fails with MSB3021 on paths under `bin/netfx/engines/...`, close Revit and retry.

Open [`pyRevit.Build.slnx`](pyRevit.Build.slnx) in Visual Studio to inspect or debug the build project.

## Run locally

From the repository root:

```powershell
cd build
dotnet run -c Release -- ci
```

### Build DLLs from the command line

The `ci` pipeline mode replaces `pipenv run pyrevit build products` (and the old CI stamping steps on the main repo). It builds all product DLLs, tools, and engines into `bin/`:

```powershell
cd build

# Unsigned product build (no version stamping; Channel=none by default)
dotnet run -c Release -- ci

# WIP-style stamping + product build (matches develop push on the main repo)
$env:Build__Channel = 'wip'
dotnet run -c Release -- ci

# Release-style stamping + product build (matches master / tag CI on the main repo)
$env:Build__Channel = 'release'
$env:DOTNET_ENVIRONMENT = 'Production'
dotnet run -c Release -- ci
```

Debug configuration (legacy `pipenv run pyrevit build products Debug`):

```powershell
dotnet run -c Debug -- ci
```

Outputs land under `bin/` (`netfx/`, `netcore/`, engines, CLI, doctor, autocomplete, etc.). LibGit2 native DLL verification runs at the end of `ci`.

`Channel=none` (the default) is valid for unsigned local builds and fork PR validation. The pipeline seeds `bin/pyrevit-products.json` from [`release/pyrevit-products.json`](../release/pyrevit-products.json) before building labs.

On a **clean checkout** (no tracked `bin/`), `ci` builds in this order:

0. Seed `bin/pyrevit-products.json` from `release/` (stamping may update it when `Build__Channel` is `wip` or `release` on the main repo)
1. Labs (`pyRevitLabs.sln` + CLI/doctor)
2. IronPython deps → seeds `bin/*/engines/IPY2712PR/` from `dev/modules/`
3. Loaders (`pyRevitLoader.*`, not runners)
4. Runtime (`pyRevitLabs.PyRevit.Runtime.sln`)
5. Runners (`pyRevitRunner.*`)
6. Static assets from `release/`

This mirrors the legacy `pipenv run pyrevit build deps` + `build engines` + `build runtime` sequence.

The `bin/` directory is **not tracked in git**. It is produced locally by `dotnet run -- ci` or downloaded by `pyrevit clone` / `pyrevit clones update` from **public GitHub Release assets** on the `ci-binaries` tag (`unsigned-bin-{sha}.zip`). Only **`develop`** and **`master`** are supported for CI binary download. Static assets are staged from [`release/bin-assets/`](../release/bin-assets/) and [`release/cengines/`](../release/cengines/); host/product JSON templates live under [`release/`](../release/). **Contributors edit** [`release/pyrevit-hosts.json`](../release/pyrevit-hosts.json), not files under `bin/`.

### Clone workflows (getting `bin/`)

Full copy-paste commands for **run in Revit** (CI binaries) vs **C# contributor** (local build): [Developer Guide — Clone workflows](../docs/dev-guide.md#clone-workflows).

**Profile 1 — CI binaries** (no local build):

```powershell
pyrevit clone myclone --source <repo-url> --dest <parent-dir> --branch develop
pyrevit attach myclone default --installed
pyrevit clones update myclone
```

**Profile 2 — local build** (do not use `pyrevit clone`):

```powershell
git clone <your-fork-url>
cd pyRevit
git checkout develop
git submodule update --init --recursive
cd build && dotnet run -c Release -- ci && cd ..
pyrevit clones add dev .
pyrevit attach dev default --installed
# after git pull:
pyrevit clones update dev --skip-bin
```

CI publishes `unsigned-bin-<sha>.zip` to the **`ci-binaries`** release and mirrors **`PyRevit.UnsignedBin`** on GitHub Packages (CLI fallback when `GITHUBTOKEN` is set). Release assets are pruned to the last **3 SHAs per branch** (`develop`, `master`); NuGet package versions are pruned to the last **2 SHAs per branch**. See [CI/CD](../docs/ci-cd.md#prebuilt-binaries-for-clone).

Run unit tests:

```powershell
dotnet test tests/Build.Tests.csproj -c Release
```

### Pipeline modes

| Args | Purpose |
|------|---------|
| `ci` (default) | Stamp versions, build products, verify LibGit2, stage release metadata |
| `pack` | Restore CI-stamped metadata (if present), build Inno/MSI installers and Chocolatey package (requires `bin/`) |
| `sign` | Sign binaries, installers, and `.nupkg` via `sign code trusted-signing` |
| `publish` | Generate release notes, create draft GitHub release, push Chocolatey |
| `winget` | Submit WinGet manifest PRs (after GitHub release is published) |
| `notify` | Comment on linked GitHub issues |

Combine modes as needed, e.g. WIP pack+sign:

```powershell
dotnet run -c Release -- pack sign
```

After downloading CI artifacts locally (`bin/` + `ci-stamped/` at the repo root), `pack` restores stamped installer/version files from `ci-stamped/` before building installers.

Release (tag builds, after CI artifacts are restored):

```powershell
dotnet run -c Release -- release pack sign publish
```

## Configuration

Non-secret defaults live in [`appsettings.json`](appsettings.json). Override via environment variables:

| Variable | Purpose |
|----------|---------|
| `Build__Channel` | `none`, `wip`, or `release` |
| `Build__NotifyUrl` | URL posted to linked issues |
| `Signing__TenantId`, `Signing__ClientId`, `Signing__ClientSecret`, `Signing__Endpoint`, `Signing__SigningAccountName`, `Signing__CertificateProfileName` | Azure Trusted Signing |
| `Publish__ChocoToken` | Chocolatey push token |
| `Publish__WingetToken` | WinGet manifest submit token |
| `GITHUB_TOKEN` | GitHub API access for releases/notify |
| `GITHUBTOKEN` | Optional: pyRevit CLI fallback to Actions artifacts for private forks (`actions:read`) |

Set `DOTNET_ENVIRONMENT=Production` to load [`appsettings.Production.json`](appsettings.Production.json).

On GitHub Actions, version stamping on the main repo is gated by `Build__Channel` **and** `GITHUB_REPOSITORY == pyrevitlabs/pyRevit`.

## GitHub workflows

- [`ci.yml`](../.github/workflows/ci.yml) — `dotnet run -- ci` + unit tests
- [`wip.yml`](../.github/workflows/wip.yml) — `dotnet run -- pack sign`
- [`release.yml`](../.github/workflows/release.yml) — `dotnet run -- release pack sign publish`
- [`winget.yml`](../.github/workflows/winget.yml) — `dotnet run -- winget` (on release published)

The legacy Python CLI in [`dev/pyrevit.py`](../dev/pyrevit.py) remains available for local/manual workflows during transition.
