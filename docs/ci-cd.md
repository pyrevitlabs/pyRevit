# CI/CD and release flow

This guide explains how GitHub Actions and the C# ModularPipelines project in [`build/`](../build/) work together: integrating work on **`develop`** (WIP builds), shipping from **`master`** via signed Git tags (releases), how versions are bumped, and the manual maintainer ritual that drives a release.

The legacy Python CLI (`pipenv run pyrevit ...`) in [`dev/pyrevit.py`](../dev/pyrevit.py) remains available for local/manual workflows; CI/CD is driven by `dotnet run` in [`build/`](../build/README.md).

## Branches and roles

| Branch | Role |
|--------|------|
| **`develop`** | Day-to-day integration. Pushes produce signed **WIP** installers and tester notifications. |
| **`master`** | Release line. Holds the version-stamped commit that gets tagged `v*` to drive a release. |

Feature work branches from **`develop`**. Changes reach **`develop`** and **`master`** through pull requests; releases are cut by pushing a `v<version>` tag from a clean clone of `master`.

## Workflow architecture

pyRevit's pipeline is split across workflows in [`.github/workflows/`](https://github.com/pyrevitlabs/pyRevit/tree/develop/.github/workflows), each invoking the ModularPipelines console project via `dotnet run`:

| Workflow | File | What it does |
|----------|------|--------------|
| **`pyRevit CI`** | [`ci.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/ci.yml) | Runs `dotnet run -- ci` to build unsigned DLLs, runs `dotnet test` on the build project, uploads `unsigned-bin-<sha>` (Actions artifact for WIP/release), and publishes the same zip to the public **`ci-binaries`** GitHub Release (for `pyrevit clone`). Runs on every push to `develop` / `master` / `v*` tag (with a path filter), on PRs to those branches, and on manual dispatch. |
| **`pyRevit WIP`** | [`wip.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/wip.yml) | Downloads CI artifacts, runs `dotnet run -- pack sign` under the **`production`** environment, and uploads signed WIP installers. |
| **`pyRevit Release`** | [`release.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/release.yml) | On `v*` tag pushes, waits for CI, runs `dotnet run -- release pack sign publish` under **`production`**, then notifies linked issues. |
| **`Update Winget manifests`** | [`winget.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/winget.yml) | After a GitHub release is **published**, runs `dotnet run -- winget` to submit WinGet manifest PRs. Strips `ElevationRequirement: elevationProhibited` from generated user-scope installers before submit (see Troubleshooting). |

The CI **`notify`** job (develop pushes only) runs `dotnet run -- notify` inline in `ci.yml` with `issues: write` and does **not** use the `production` environment.

This split guarantees that:

- every DLL shipped inside an installer carries an Authenticode signature,
- the installer `.exe`/`.msi` themselves are Authenticode-signed,
- the `.nupkg`'s embedded checksum matches the signed installer users actually download, and
- the `.nupkg` itself carries a NuGet author signature so Chocolatey clients can verify it.

### `ci.yml` triggers and path filter

`ci.yml` runs when changes touch build-related paths:

- `build/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, `site-packages/`

It is triggered by:

- **Push** to `develop`, `master`, or any `v*` tag (with the path filter above).
- **Pull request** (`opened`, `reopened`) targeting `develop` or `master` (with the path filter).
- **`workflow_dispatch`** for manual runs.

Doc-only or other out-of-scope changes skip CI entirely.

!!! warning "PR pushes do not re-run CI"

    The PR trigger is restricted to `opened` and `reopened`. New commits pushed to an **open** PR do **not** trigger another run. Close and reopen the PR, or push to the head branch after closing and reopening, if you need a fresh CI run after fixes.

### Official repository vs forks

The stamping steps (`set year`, `set build wip|release`, `set products`) only run when `Build__Channel` is `wip` or `release` **and** `GITHUB_REPOSITORY` is the main repo (`pyrevitlabs/pyRevit`). The downstream `wip.yml` and `release.yml` jobs are similarly gated on the main repo so secrets are never exposed to forks. Forks still get checkout and an **unsigned** product build via `ci.yml` (useful for PR validation). Unsigned builds (`Channel=none`) still seed `bin/pyrevit-products.json` from `release/` before the labs build so fork PR validation succeeds.

## Prebuilt binaries for clone

**User workflows** (full commands for run-only vs C# contributor): [Developer Guide — Clone workflows](dev-guide.md#clone-workflows).

End users and contributors who only need to **run** pyRevit (not build C#) get `bin/` via `pyrevit clone` or `pyrevit clones update` on **`develop`** or **`master`** — **no GitHub token** on the public repo when Release assets are available. C# contributors use `git clone`, local `dotnet run -- ci`, and `pyrevit clones update --skip-bin` instead — see Profile 2 in the dev guide.

| Consumer | Source | Auth |
|----------|--------|------|
| `pyrevit clone` / `clones update` | GitHub Release **`ci-binaries`** assets (fork → upstream SHA fallback) | None (anonymous HTTPS) |
| `pyrevit clone` / `clones update` (token fallback) | GitHub Packages **`PyRevit.UnsignedBin`** NuGet mirror | `GITHUBTOKEN` (`read:packages`) |
| `pyrevit clone` / `clones update` (token fallback) | Actions artifact `unsigned-bin-<sha>` | `GITHUBTOKEN` (`actions:read`) |
| WIP / release pack pipelines | Actions artifact `unsigned-bin-<sha>` | `GITHUB_TOKEN` in CI |

After each successful CI push to **`develop`** or **`master`** on the main repo:

1. CI zips `bin/` → `unsigned-bin-{fullSha}.zip`
2. Uploads to Release tag **`ci-binaries`** (pre-release), plus rolling **`unsigned-bin-{branch}-latest.zip`**
3. Pushes **`PyRevit.UnsignedBin`** NuGet package to GitHub Packages (token-authenticated CLI mirror)
4. Prunes per-SHA release assets older than the **last 3 successful CI builds** per branch (`develop`, `master`); branch-latest zips are always kept
5. Prunes **`PyRevit.UnsignedBin`** NuGet versions older than the **last 2 successful CI builds** per branch (`develop`, `master`)

Anonymous download URL pattern:

```text
https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-{sha}.zip
https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-develop-latest.zip
```

CLI download order:

1. Release asset for clone remote + commit SHA
2. Release asset for upstream (`pyrevitlabs/pyRevit`) + same SHA (synced forks)
3. Release branch-latest on clone remote, then upstream
4. NuGet `PyRevit.UnsignedBin` (when `GITHUBTOKEN` is set)
5. Actions artifacts (when `GITHUBTOKEN` is set)

See also [`build/README.md`](../build/README.md) and the [developer guide](dev-guide.md).

## Feature or fix → `develop` (WIP)

1. Create a branch from **`develop`**, implement the change, open a **PR into `develop`** (touch paths under the filter if you need CI).
2. After the PR is **merged** into **`develop`**, `ci.yml` runs `dotnet run -- ci` on the push event:

    - Stamps copyright/year, applies WIP versioning, refreshes product metadata, builds products, verifies LibGit2, and stages release metadata.
    - Uploads the unsigned `bin/` tree as `unsigned-bin-<sha>`.

3. `wip.yml` is triggered automatically when that CI run finishes successfully on `develop`. On the main repo:

    - Downloads CI artifacts and runs `dotnet run -- pack sign` to sign DLLs, build/sign installers and the Chocolatey `.nupkg`, and upload `pyrevit-wip-installers-<install-version>`.
    - The **`notify`** job in `ci.yml` runs `dotnet run -- notify` with a link to the **WIP workflow run** (where signed installers are published).

**Push to `develop` ⇒ signed WIP installers and notification, not a public GitHub Release.**

## Cutting a release (tag-driven)

Releases are no longer auto-triggered by merging into `master`. A maintainer runs through the ritual below, and pushing the `v<version>` tag triggers `ci.yml` (rebuild on the tagged SHA) and `release.yml` (waits for CI, then signs and publishes) in parallel.

### Pre-flight

- Confirm **`develop`** is green: the latest CI run on `develop` succeeded and `wip.yml` produced the signed artifact.
- Confirm `pyrevitlib/pyrevit/version` and `release/version` reflect the version you intend to publish. `release.yml` hard-fails if the tag name does not match `pyrevitlib/pyrevit/version`.
- On **tag** pushes, CI preserves the committed build version (including the `+HHMM` suffix) from git. **`develop`** and **`master`** branch pushes still re-stamp the build number as before.
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
    - **`release.yml`** starts immediately and polls for the matching CI run (via `gh run watch`). The **`release`** job downloads CI artifacts, runs `dotnet run -- release pack sign publish` under **`production`** (sign via `sign code trusted-signing`, draft GitHub Release, Chocolatey push). **`notify`** then posts to linked issues. After you publish the draft release, **`winget.yml`** submits WinGet manifest PRs.

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

The DLLs under `dev/libs/netfx/` and `dev/libs/netcore/` (`pyRevitLabs.MahAppsMetro.dll`, `pyRevitLabs.NLog.dll`, `pyRevitLabs.Json.dll`, `pyRevitLabs.PythonNet.dll`, `ControlzEx.dll`, ...) are vendored: projects that consume these DLLs reference them via `HintPath="$(PyRevitDevLibsDir)\..."`, and the files are committed to git. CI does **not** rebuild them; the ModularPipelines build invokes labs, engines, runtime, and autocomplete builds.

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

CI invokes the ModularPipelines project from [`build/`](../build/) via `dotnet run`; the legacy `pyrevit` CLI commands remain for local use:

| Command | When / purpose |
|---------|----------------|
| `dotnet run -- ci` (in `build/`) | CI build path (replaces `pyrevit check`, `set year`, `set build`, `set products`, `build products`) |
| `dotnet test tests/Build.Tests.csproj` | Build-project unit tests (also run in CI) |
| `dotnet run -- pack sign` | WIP/release pack path after artifact restore |
| `dotnet run -- publish` | Draft GitHub release + Chocolatey push |
| `dotnet run -- notify` | Post WIP/release URL to linked issues |
| `pipenv run pyrevit set year` | Updates copyright year (local/manual) |
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

- **Release fails on `Validate tag matches version`**: the tag (e.g. `v4.8.16`) doesn't match `pyrevitlib/pyrevit/version`. Delete and recreate the tag with the right name, or update the version file and re-tag. If the tag and checkout match but the error shows different `+HHMM` suffixes (e.g. tag `+1406` vs file `+1212`), CI re-stamped the build number on a tag push — tag CI must preserve the committed version; move the tag to a commit that includes that fix and re-run.
- **Release fails on `Wait for CI to complete on tagged commit`**: CI either failed or didn't start within 10 minutes of the tag push. Investigate the CI run for the tagged SHA; once it is green, re-run `release.yml`.
- **Release fails on `Download unsigned bin artifact`**: the CI run exists but the expected `unsigned-bin-<sha>` artifact is missing (most often because CI failed before the upload step). Fix CI and re-run `release.yml`.
- **Release fails on `Build Installers`**: Inno Setup (`ISCC.exe`), MSBuild, or the legacy WiX v3.x CLI MSI project failed. `windows-2025` preinstalls Inno Setup 6 and WiX Toolset v3.x; MSBuild is resolved from `PATH` or Visual Studio's `vswhere.exe`. Local installer builds need the same tools installed.
- **Release fails on `Build Choco Package`**: `choco pack` failed, or the upstream signed installer was missing when the SHA was computed. Confirm `Sign installers` produced the expected `dist/*.exe`/`.msi` outputs before this step ran.
- **Release fails on `Sign Choco Package`**: this step uses the `dotnet sign` CLI (installed via `dotnet tool install --global sign --prerelease`) and authenticates to Azure Trusted Signing via the `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` env vars (DefaultAzureCredential chain). Common causes: (a) the certificate profile lacks the `1.3.6.1.5.5.7.3.3` Code Signing EKU required for NuGet author signing; (b) the App Registration is missing the `Trusted Signing Certificate Profile Signer` role on the Signing Account; (c) the `--prerelease` flag was removed and `sign` is no longer marked prerelease (drop `--prerelease` once the tool has a stable GA release). The previous attempt used `Azure/artifact-signing-action`, but its v2.0.0 PowerShell module routes `.nupkg` to `signtool.exe`, which doesn't recognize the format. Don't switch back without verifying upstream support for NuGet via that action.
- **Signing step fails (DLLs or installers)**: verify the `production` environment secrets above are present and not expired.
- **Choco push fails**: check `CHOCO_TOKEN` and that `dist/pyrevit-cli.<version>.nupkg` was produced by `Build Choco Package` in the **`release`** job. Re-run the workflow without re-pushing the tag.
- **Draft release exists but issues were not notified**: check the **`notify`** job log. If `notify` succeeded but no comments appeared, commits since the previous tag must include `#<issue>` in the message. If `notify` failed with 403, confirm the job has `issues: write` and is **not** assigned to the `production` environment (environment deployment tokens can block issue comments).
- **Notify hit GitHub secondary rate limit**: large merges can reference many issues; GitHub may throttle rapid comment creation (`SecondaryRateLimitExceededException`). The notify step uses `continue-on-error: true` so **`build`** / **`wip`** / **`release`** are unaffected. `NotifyIssuesModule` throttles comments and stops gracefully when rate-limited — check logs for `Posted X of Y` and re-run **`notify`** later if needed.
- **Notify failed on empty `release_url`**: the **`release`** job did not write `dist/github-release-url.txt` during publish (check **`Run release pipeline`** logs for `Deployment GitHub`). Re-run **`release`**, then re-run **`notify`**. The notify job receives the URL from the release job output; it no longer looks up releases by tag (tags containing `+` break `gh release view`).
- **Draft release exists but `notify` did not run**: the **`release`** job must finish successfully (including Choco push) before **`notify`** starts. Fix or re-run **`release`**, then re-run **`notify`** if the draft release URL is already available.
- **WinGet validation fails with `0x8A150056` / `elevationProhibited`**: WinGet's validation VM uses an administrator-capable account. Inno user installers built with `PrivilegesRequired=lowest` still block installation there even after removing `ElevationRequirement: elevationProhibited` from the manifest (WinGet reads the restriction from the installer). The `winget` pipeline publishes **machine-scope admin installers only** and strips `elevationProhibited` if `wingetcreate` adds it. Per-user installers remain on GitHub Releases. Pushing a manifest update to the winget-pkgs PR re-triggers validation automatically (`@wingetbot run` requires Moderator).

## Related reading

- [Developer Guide](dev-guide.md) — local setup and building.
- [Architecture](architecture.md) — how pyRevit is structured at runtime.
