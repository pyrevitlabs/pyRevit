# CI/CD and release flow

This guide explains how GitHub Actions and the `pyrevit` build CLI work together: integrating work on **`develop`** (WIP builds), shipping from **`master`** via signed Git tags (releases), how versions are bumped, and the manual maintainer ritual that drives a release.

## Branches and roles

| Branch | Role |
|--------|------|
| **`develop`** | Day-to-day integration. Pushes produce signed **WIP** installers and tester notifications. |
| **`master`** | Release line. Holds the version-stamped commit that gets tagged `v*` to drive a release. |

Feature work branches from **`develop`**. Changes reach **`develop`** and **`master`** through pull requests; releases are cut by pushing a `v<version>` tag from a clean clone of `master`.

## Workflow architecture

pyRevit's pipeline is split into three workflows in [`.github/workflows/`](https://github.com/pyrevitlabs/pyRevit/tree/develop/.github/workflows):

| Workflow | File | What it does |
|----------|------|--------------|
| **`pyRevit CI`** | [`ci.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/ci.yml) | Builds unsigned DLLs and uploads them as `unsigned-bin-<sha>`. Runs on every push to `develop` / `master` / `v*` tag (with a path filter), on PRs to those branches, and on manual dispatch. |
| **`pyRevit WIP`** | [`wip.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/wip.yml) | Consumes the artifact from a successful CI run on **`develop`**. Job `sign-wip` ( **`production`** environment) signs DLLs, builds + signs installers and the Chocolatey package, and uploads the WIP artifact. Job `notify` runs afterward with `issues: write` only — it does **not** use `production`. |
| **`pyRevit Release`** | [`release.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/release.yml) | Runs on `v*` tag pushes. Job `release` (single **`production`** deployment) waits for CI, signs, builds installers and the `.nupkg`, publishes a draft GitHub Release, and pushes to Chocolatey. Job `notify` runs afterward (no `production` environment) and posts to linked issues. |

This split guarantees that:

- every DLL shipped inside an installer carries an Authenticode signature,
- the installer `.exe`/`.msi` themselves are Authenticode-signed,
- the `.nupkg`'s embedded checksum matches the signed installer users actually download, and
- the `.nupkg` itself carries a NuGet author signature so Chocolatey clients can verify it.

### `ci.yml` triggers and path filter

`ci.yml` runs when changes touch build-related paths:

- `bin/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, `site-packages/`

It is triggered by:

- **Push** to `develop`, `master`, or any `v*` tag (with the path filter above).
- **Pull request** (`opened`, `reopened`) targeting `develop` or `master` (with the path filter).
- **`workflow_dispatch`** for manual runs.

Doc-only or other out-of-scope changes skip CI entirely.

!!! warning "PR pushes do not re-run CI"

    The PR trigger is restricted to `opened` and `reopened`. New commits pushed to an **open** PR do **not** trigger another run. Close and reopen the PR, or push to the head branch after closing and reopening, if you need a fresh CI run after fixes.

### Official repository vs forks

The stamping steps (`pyrevit set year`, `pyrevit set build wip|release`, `pyrevit set products`, `pyrevit check`) only run when `github.repository == pyrevitlabs/pyRevit`. The downstream `wip.yml` and `release.yml` jobs are similarly gated on the main repo so secrets are never exposed to forks. Forks still get checkout, pipenv, and an **unsigned** product build via `ci.yml` (useful for PR validation).

## Feature or fix → `develop` (WIP)

1. Create a branch from **`develop`**, implement the change, open a **PR into `develop`** (touch paths under the filter if you need CI).
2. After the PR is **merged** into **`develop`**, `ci.yml` runs on the push event:

    - Runs `pipenv run pyrevit set year`, `pipenv run pyrevit set build wip` (refreshes the build segment and applies WIP versioning; see `dev/_props.py`), and `pipenv run pyrevit set products`.
    - Runs `pipenv run pyrevit build products`, verifies the LibGit2 native DLL is present, and uploads the unsigned `bin/` tree as `unsigned-bin-<sha>`.

3. `wip.yml` is triggered automatically when that CI run finishes successfully on `develop`. On the main repo:

    - **`sign-wip`** downloads `unsigned-bin-<sha>`, signs DLLs via Azure Trusted Signing, builds and signs installers and the Chocolatey `.nupkg`, and uploads `pyrevit-wip-installers-<install-version>` as a workflow artifact.
    - **`notify`** (separate job, no `production` environment) runs `pipenv run pyrevit notify wip <run-url>` so linked issues can be updated for testers.

**Push to `develop` ⇒ signed WIP installers and notification, not a public GitHub Release.**

## Cutting a release (tag-driven)

Releases are no longer auto-triggered by merging into `master`. A maintainer runs through the ritual below, and pushing the `v<version>` tag triggers `ci.yml` (rebuild on the tagged SHA) and `release.yml` (waits for CI, then signs and publishes) in parallel.

### Pre-flight

- Confirm **`develop`** is green: the latest CI run on `develop` succeeded and `wip.yml` produced the signed artifact.
- Confirm `pyrevitlib/pyrevit/version` and `release/version` reflect the version you intend to publish. `release.yml` hard-fails if the tag name does not match `pyrevitlib/pyrevit/version`.
- Make sure the required secrets are configured in the **`production`** GitHub environment:

    - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_ENDPOINT`, `AZURE_CODE_SIGNING_NAME`, `AZURE_CERT_PROFILE_NAME`
    - `CHOCO_TOKEN`

### Cut a release

1. From a clean local clone on **`develop`**, stamp the build as a release:

    ```bash
    pipenv run pyrevit set build release
    ```

    This updates `pyrevitlib/pyrevit/version` and related build info files.

2. Commit the version changes and merge them into **`master`** via your normal PR flow (or push directly if your branch protection allows it):

    ```bash
    git add -A
    git commit -m "release: vX.Y.Z"
    git push
    ```

3. Tag the release commit on **`master`**. The tag name must exactly match `pyrevitlib/pyrevit/version` prefixed with `v`:

    ```bash
    git checkout master
    git pull
    git tag "v$(cat pyrevitlib/pyrevit/version)"
    git push origin "v$(cat pyrevitlib/pyrevit/version)"
    ```

4. Pushing the tag triggers two workflows in parallel:

    - **`ci.yml`** rebuilds DLLs on the tagged commit and uploads `unsigned-bin-<sha>` (DLLs only; installers are no longer built in CI).
    - **`release.yml`** starts immediately and polls for the matching CI run (via `gh run watch`). The **`release`** job downloads `unsigned-bin-<sha>`, signs DLLs and installers, builds and signs the `.nupkg`, generates release notes, publishes a **draft** GitHub Release, and pushes the signed `.nupkg` to Chocolatey (all under one **`production`** deployment). **`notify`** then posts `pipenv run pyrevit notify release <release-url>` to linked issues without using the `production` environment.

5. Open the draft release on GitHub, review the auto-generated notes, then publish it.

!!! tip "Manual re-run"

    Running **`workflow_dispatch`** on `release.yml` is supported but the `if` guard still requires `github.ref_type == 'tag'`, so the dispatch must be invoked against an existing `v*` tag — not a branch. Use it to retry a failed release without re-pushing the tag.

### Post-release

Bump **`develop`** to the next development version so subsequent WIP builds carry the right number:

```bash
git checkout develop
git pull --rebase origin develop
pipenv run pyrevit set next-version
git add -A
git commit -m "chore: bump next version"
git push origin develop
```

### Hotfix flow

Same as above, but cut the release commit from **`master`** (or a `hotfix/*` branch off `master`) instead of `develop`. After tagging and publishing, cherry-pick the version bump back into `develop`.

## Refreshing vendored dependencies (maintainer-only)

The DLLs under `dev/libs/netfx/` and `dev/libs/netcore/` (`pyRevitLabs.MahAppsMetro.dll`, `pyRevitLabs.NLog.dll`, `pyRevitLabs.Json.dll`, `pyRevitLabs.PythonNet.dll`, `ControlzEx.dll`, ...) are vendored: projects that consume these DLLs reference them via `HintPath="$(PyRevitDevLibsDir)\..."`, and the files are committed to git. CI does **not** rebuild them — `pipenv run pyrevit build products` only invokes labs / engines / runtime / telem / autocmp.

When you bump a submodule under `dev/modules/` (MahApps.Metro, NLog, Newtonsoft.Json, Python.Net, IronPython2/3), you need to refresh the vendored output **locally** and commit the result:

```bash
# one-time setup: install the .NET Core 3.1 SDK (MahApps.Metro netcore TFM
# targets netcoreapp3.1; it's EOL but still publicly available)
winget install Microsoft.DotNet.SDK.3_1

# refresh dev/libs/{netfx,netcore} from the submodule sources
pipenv run pyrevit build deps

# review and commit the diff
git add dev/libs
git commit -m "chore(libs): refresh vendored deps for <submodule> bump"
```

This keeps the CI hot path on the SDKs preinstalled on `windows-2025` (.NET 4.8 + .NET 8 + .NET 10) and avoids depending on the EOL 3.1 archives in a hosted runner. If a submodule ever ships only via NuGet (e.g. modern MahApps.Metro), retire the local build from `_labs.build_deps` and switch the `.csproj` to a `PackageReference` instead of `HintPath`.

## Version files and commands

| File | Purpose |
|------|---------|
| `pyrevitlib/pyrevit/version` | Full **build** version string used across the product (drives the `v*` tag name). |
| `release/version` | **Install** / marketing version used for installers and the release title. |

CI invokes the `pyrevit` CLI from the repo root (via pipenv); relevant commands:

| Command | When / purpose |
|---------|----------------|
| `pipenv run pyrevit set year` | Updates copyright year (CI on main repo, before stamping). |
| `pipenv run pyrevit set build wip` | After push to **`develop`** (CI runs this automatically). |
| `pipenv run pyrevit set build release` | Release build on **`master`** (CI runs this on `master` / `v*` pushes; maintainer runs it locally before tagging). |
| `pipenv run pyrevit set products` | Refreshes product metadata before `build products`. |
| `pipenv run pyrevit set version <ver>` | Manual bump, e.g. `4.8.0`; tooling adds build/time segments (and WIP suffix when used in that mode). |
| `pipenv run pyrevit set next-version` | **Patch** bump on **`develop`** after a release (run manually by the maintainer). |
| `pipenv run pyrevit build commit` | Available but **not** used by CI any more; commits metadata, tags `v<build-version>` / `cli-v<build-version>`, and pushes. Kept for local convenience. |
| `pipenv run pyrevit report releasenotes` | Generates the release notes used by the draft GitHub Release. |
| `pipenv run pyrevit notify wip <url>` / `notify release <url>` | Posts the WIP run URL or release URL back to linked issue threads. |

## Quick reference

| Goal | Action |
|------|--------|
| Validate a change in CI | PR to **`develop`**; ensure changed paths match the workflow filter. |
| WIP installers + issue ping | Merge PR → **`develop`** (push triggers `ci.yml` → `wip.yml`). |
| Ship a release | Stamp release on `develop`, merge to `master`, tag `v<version>` on `master`, push the tag. |
| Publish the release | Open the **draft** release on GitHub and publish when ready. |
| Next dev version after release | `pipenv run pyrevit set next-version` on `develop` and push. |

## Troubleshooting

- **Release fails on `Validate tag matches version`**: the tag (e.g. `v4.8.16`) doesn't match `pyrevitlib/pyrevit/version`. Delete and recreate the tag with the right name, or update the version file and re-tag.
- **Release fails on `Wait for CI to complete on tagged commit`**: CI either failed or didn't start within 10 minutes of the tag push. Investigate the CI run for the tagged SHA; once it is green, re-run `release.yml`.
- **Release fails on `Download unsigned bin artifact`**: the CI run exists but the expected `unsigned-bin-<sha>` artifact is missing (most often because CI failed before the upload step). Fix CI and re-run `release.yml`.
- **Release fails on `Build Installers`**: Inno Setup (`iscc`) or MSBuild on the AIP files failed. Both run on `windows-2025`, which preinstalls Inno Setup 6; MSBuild is provisioned via `microsoft/setup-msbuild`. Check the step log for the underlying compiler error.
- **Release fails on `Build Choco Package`**: `choco pack` failed, or the upstream signed installer was missing when the SHA was computed. Confirm `Sign installers` produced the expected `dist/*.exe`/`.msi` outputs before this step ran.
- **Release fails on `Sign Choco Package`**: this step uses the `dotnet sign` CLI (installed via `dotnet tool install --global sign --prerelease`) and authenticates to Azure Trusted Signing via the `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` env vars (DefaultAzureCredential chain). Common causes: (a) the certificate profile lacks the `1.3.6.1.5.5.7.3.3` Code Signing EKU required for NuGet author signing; (b) the App Registration is missing the `Trusted Signing Certificate Profile Signer` role on the Signing Account; (c) the `--prerelease` flag was removed and `sign` is no longer marked prerelease (drop `--prerelease` once the tool has a stable GA release). The previous attempt used `Azure/artifact-signing-action`, but its v2.0.0 PowerShell module routes `.nupkg` to `signtool.exe`, which doesn't recognize the format. Don't switch back without verifying upstream support for NuGet via that action.
- **Signing step fails (DLLs or installers)**: verify the `production` environment secrets above are present and not expired.
- **Choco push fails**: check `CHOCO_TOKEN` and that `dist/pyrevit-cli.<version>.nupkg` was produced by `Build Choco Package` in the **`release`** job. Re-run the workflow without re-pushing the tag.
- **Draft release exists but issues were not notified**: check the **`notify`** job log. If `notify` succeeded but no comments appeared, commits since the previous tag must include `#<issue>` in the message. If `notify` failed with 403, confirm the job has `issues: write` and is **not** assigned to the `production` environment (environment deployment tokens can block issue comments).
- **Notify failed on empty `release_url`**: the `release` job did not produce a URL from `Publish GitHub Release`; fix that job and re-run `notify`.
- **Draft release exists but `notify` did not run**: the **`release`** job must finish successfully (including Choco push) before **`notify`** starts. Fix or re-run **`release`**, then re-run **`notify`** if the draft release URL is already available.

## Related reading

- [Developer Guide](dev-guide.md) — local setup and building.
- [Architecture](architecture.md) — how pyRevit is structured at runtime.
