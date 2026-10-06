# CI/CD and release flow

This guide explains how GitHub Actions and the C# ModularPipelines project in [`build/`](../build/) work together: integrating work on **`develop`** (WIP builds), shipping from **`master`** via signed Git tags (releases), how versions are bumped, and the manual maintainer ritual that drives a release.

CI/CD and local product builds are driven by `dotnet run` in [`build/`](../build/README.md).

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
| **`pyRevit CI`** | [`ci.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/ci.yml) | Runs `dotnet run -- ci` to build unsigned DLLs, runs `dotnet test` on the build project, uploads `unsigned-bin-<sha>` (Actions artifact for WIP/release), and publishes the same zip to the public **`ci-binaries`** GitHub Release (for `pyrevit clone`). Runs on every push to `develop` / `master` / `v*` tag (with a path filter), on PRs to those branches, and on manual dispatch. Tag pushes also refresh `unsigned-bin-master-latest.zip`. |
| **`pyRevit WIP`** | [`wip.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/wip.yml) | **Reusable workflow** (`workflow_call`) — it has no trigger of its own. The **`wip` job** of `ci.yml` calls it on `develop` pushes to the main repo. It downloads the CI artifacts, runs `dotnet run -- pack sign` under the **`production`** environment, and uploads signed WIP installers. Because it runs as a job, WIP activity appears **inside the `pyRevit CI` run**, not as a separate workflow run. |
| **`pyRevit Release`** | [`release.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/release.yml) | On `v*` tag pushes, waits for CI, runs `dotnet run -- release pack sign publish` under **`production`**, attaches signed `bin-v{version}.zip` to the draft GitHub Release, then notifies linked issues. |
| **`Update Winget manifests`** | [`winget.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/winget.yml) | After a GitHub release is **published**, runs `dotnet run -- winget` to submit WinGet manifest PRs. Strips `ElevationRequirement: elevationProhibited` from generated user-scope installers before submit (see Troubleshooting). |
| **`pyRevit Revit integration tests`** | [`revit-integration.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/revit-integration.yml) | Signs `bin/` with a throwaway certificate, launches every supported Revit year, and fails if any of them shows the unsigned add-in dialog. Needs a self-hosted runner with Revit; see [Revit integration tests](#revit-integration-tests). |

The CI **`notify`** job (develop pushes only) runs `dotnet run -- notify` inline in `ci.yml` with `issues: write` and does **not** use the `production` environment. It `needs` both `build` and `wip`, so a failed WIP pack also holds back the notification.

This split guarantees that:

- every DLL shipped inside an installer carries an Authenticode signature,
- the installer `.exe`/`.msi` themselves are Authenticode-signed,
- the `.nupkg`'s embedded checksum matches the signed installer users actually download, and
- the `.nupkg` itself carries a NuGet author signature so Chocolatey clients can verify it.

## Revit integration tests

GitHub-hosted runners cannot run Revit, so [`revit-integration.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/revit-integration.yml) targets a self-hosted runner labelled `self-hosted, windows, revit`. It answers one question the unit tests cannot: **does Revit load the build without the unsigned add-in dialog?**

The job builds `bin/`, signs it with a throwaway certificate via `dotnet run -- sign-test`, then launches each Revit year and reads the outcome out of that session's journal:

| Journal evidence | Meaning |
|---|---|
| `Registering <event> event by application PyRevitLoader` | The add-in loaded and initialised |
| `TaskDialog_Security_Unsigned_File_Loading` | The Unsigned Add-In dialog appeared — the failure this job exists to catch |
| `TaskDialog_External_Tools_External_Tool_Failure` naming `PyRevitLoader` | Revit refused the add-in outright |

Any dialog fails the job. An unattended prompt that nobody answers would otherwise hang Revit until the job timed out, and "it eventually loaded after a prompt" is exactly the regression being guarded against.

The engine directory per year is not a free choice. `pyrevitlib/pyrevit/compat.py` defines `NETCORE` as Revit 2025 onwards and `NETFRAMEWORK` as 2024 and earlier, so the job points 2025-2027 at `bin/netcore/engines/` and 2022-2024 at `bin/netfx/engines/`. Handing a year the wrong one makes Revit refuse the add-in, which reads like a trust failure but is not.

### Runner requirements

- The runner session must be **non-interactive** (service or session 0). Adding the certificate to `CurrentUser\Root` raises a modal Windows Security Warning; a session that can display it blocks the add forever with nobody to answer, so the job runs that add under a 90-second watchdog and fails with an actionable message instead of hanging. `CurrentUser\TrustedPublisher` never prompts, which is why the job adds the certificate there without a watchdog.
- Either let the job create the throwaway certificate, or pre-provision one and pass its SHA-256 fingerprint in `TestSigning__Fingerprint` — the sign tool rejects a SHA-1 thumbprint, so the job computes SHA-256 over `RawData`. The subject must start with `CN=pyRevit CI Test` so `RejectTestSignedBinariesModule` can detect the signatures and keep them out of installers.
- The certificate is removed from `My`, `Root` and `TrustedPublisher` in an `if: always()` step.

### Why not on pull requests

The job does not run for pull requests, and in particular never for fork PRs. It needs a runner that holds a trusted certificate and executes the code under test; running unreviewed code there would let a PR sign binaries with a certificate the runner trusts. It is also slow, because each Revit year needs its own launch. Pushes to `develop` cover the change before it lands, and `workflow_dispatch` takes a `revit_years` input for targeted re-runs.

### Verified support matrix

Confirmed on a Windows 11 host with Revit 2021-2027 installed, using a self-signed code-signing certificate in `CurrentUser\Root` plus `CurrentUser\TrustedPublisher`:

| Revit | Engine | Result |
|---|---|---|
| 2021 | `netfx` | Not verified: this host's Revit 2021 install is missing `Autodesk Shared\Revit Schemas 2021` and aborts at startup before add-ins are considered |
| 2022-2024 | `netfx` | Loads silently |
| 2025-2027 | `netcore` | Loads silently |

### `ci.yml` triggers and path filter

`ci.yml` runs when changes touch build-related paths:

- `.github/workflows/`, `build/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, `site-packages/`

It is triggered by:

- **Push** to `develop`, `master`, or any `v*` tag (with the path filter above).
- **Pull request** (`opened`, `reopened`, `synchronize`) targeting `develop` or `master` (with the path filter).
- **`workflow_dispatch`** for manual runs.

Doc-only or other out-of-scope changes skip CI entirely.

!!! note "New commits to an open PR do re-run CI"

    The pull-request trigger includes `synchronize`, so every push to an open PR's head branch starts a fresh run — no need to close and reopen to get one after fixes. Concurrency is keyed by `pyrevit-ci-<pr number>` with `cancel-in-progress`, so a push supersedes the PR's previous run instead of queueing behind it.

!!! warning "Anything the `build` job runs must be inside the filter"

    The filter decides whether a change is verified at all. The host-free suites used to sit in a root `tests/`, outside the filter, so deleting the only two files under it triggered no run and the next build-touching push failed on `ImportError: Start directory is not importable: tests` — which on a `v*` tag also blocks `release.yml`, since it polls for that CI run. They now live under `dev/scripts`, which the filter already covers. When adding a step to the `build` job, add its inputs to both `paths:` lists in the same change.

### Official repository vs forks

The version, year, and product-data stamping modules only run when `Build__Channel` is `wip` or `release` **and** `GITHUB_REPOSITORY` is the main repo (`pyrevitlabs/pyRevit`). The downstream `wip` job and the whole `release.yml` workflow are similarly gated on the main repo so secrets are never exposed to forks. Forks still get checkout and an **unsigned** product build via `ci.yml` (useful for PR validation). Unsigned builds (`Channel=none`) still seed `bin/pyrevit-products.json` from `release/` before the labs build so fork PR validation succeeds.

## Prebuilt binaries for clone

**User workflows** (full commands for run-only vs C# contributor): [Developer Guide — Clone workflows](dev-guide.md#clone-workflows).

End users and contributors who only need to **run** pyRevit (not build C#) get `bin/` via `pyrevit clone` or `pyrevit clones update` on **`develop`**, **`master`**, or a **published `v*` release tag** — **no GitHub token** on the public repo when Release assets are available. C# contributors use `git clone`, local `dotnet run -- ci`, and `pyrevit clones update --skip-bin` instead — see Profile 2 in the dev guide.

| Consumer | Source | Auth |
|----------|--------|------|
| `pyrevit clone` / `clones update` (`develop` / `master`) | GitHub Release **`ci-binaries`** assets (fork → upstream SHA fallback) | None (anonymous HTTPS) |
| `pyrevit clone --branch=v*` | GitHub Release **`bin-v{version}.zip`** on the published version tag (signed `bin/`) | None (anonymous HTTPS) |
| `pyrevit clone` / `clones update` (token fallback) | GitHub Packages **`PyRevit.UnsignedBin`** NuGet mirror | `GITHUBTOKEN` (`read:packages`) |
| `pyrevit clone` / `clones update` (token fallback) | Actions artifact `unsigned-bin-<sha>` | `GITHUBTOKEN` (`actions:read`) |
| WIP / release pack pipelines | Actions artifact `unsigned-bin-<sha>` | `GITHUB_TOKEN` in CI |

After each successful CI push to **`develop`** or **`master`** on the main repo (and after each **`v*`** tag CI run):

1. CI zips `bin/` → `unsigned-bin-{fullSha}.zip`
2. Uploads to Release tag **`ci-binaries`** (pre-release), plus rolling **`unsigned-bin-{branch}-latest.zip`**. Tag runs publish as **`unsigned-bin-master-latest.zip`** so clone-of-master does not depend on the master push event.
3. Pushes **`PyRevit.UnsignedBin`** NuGet package to GitHub Packages (token-authenticated CLI mirror)
4. Prunes per-SHA release assets older than the **last 3 successful CI builds** per branch (`develop`, `master`), **including the in-progress run's SHA** (the Actions API `status=completed` filter would otherwise omit it and the just-uploaded zip would be deleted) **and the SHAs of the last 3 `v*` tags** (tag CI reports `head_branch` as the tag name, so those runs never appear in the `branch=develop` / `branch=master` queries). Branch-latest zips are always kept.
5. Prunes **`PyRevit.UnsignedBin`** NuGet versions older than the **last 2 successful CI builds** per branch (`develop`, `master`), also keeping the in-progress run's SHA and the last 2 `v*` tag SHAs.

`release.yml` then re-uploads the same unsigned payload as `unsigned-bin-{sha}.zip` and `unsigned-bin-master-latest.zip` after it downloads the CI artifact — a second, **best-effort** path so a dropped master push cannot leave clone-of-master on a previous release's binaries. A failure there does not block pack/sign/publish.

Anonymous download URL pattern:

```text
https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-{sha}.zip
https://github.com/pyrevitlabs/pyRevit/releases/download/ci-binaries/unsigned-bin-develop-latest.zip
https://github.com/pyrevitlabs/pyRevit/releases/download/v{version}/bin-v{version}.zip
```

`+` in a version tag is URL-encoded as `%2B` (for example `v6.5.3.26176%2B2017`). Tag clones work after the GitHub Release is **published**; draft assets are not anonymous.

CLI download order:

1. Release asset for clone remote + commit SHA (`ci-binaries`)
2. Release asset for upstream (`pyrevitlabs/pyRevit`) + same SHA (synced forks)
3. Signed `bin-v{version}.zip` on the version GitHub Release when `--branch` is not `develop`/`master`
4. Release branch-latest on clone remote, then upstream (`develop` / `master` only)
5. NuGet `PyRevit.UnsignedBin` (when `GITHUBTOKEN` is set)
6. Actions artifacts (when `GITHUBTOKEN` is set)

See also [`build/README.md`](../build/README.md) and the [developer guide](dev-guide.md).

## Feature or fix → `develop` (WIP)

1. Create a branch from **`develop`**, implement the change, open a **PR into `develop`** (touch paths under the filter if you need CI).
2. After the PR is **merged** into **`develop`**, `ci.yml` runs `dotnet run -- ci` on the push event:

    - Stamps copyright/year, applies WIP versioning, refreshes product metadata, builds products, verifies LibGit2, and stages release metadata.
    - Uploads the unsigned `bin/` tree as `unsigned-bin-<sha>`.

3. The same CI run's **`wip` job** (`needs: build`, gated on the main repo) calls the reusable `wip.yml` workflow — there is no separate WIP trigger to wait for. It:

    - Downloads CI artifacts and runs `dotnet run -- pack sign` to sign DLLs, build/sign installers and the Chocolatey `.nupkg`, and upload `pyrevit-wip-installers-<install-version>`.
    - Exports its run id, which the **`notify`** job in `ci.yml` (`needs: [build, wip]`) passes to `dotnet run -- notify` as the link to the **WIP job** of the same run (where signed installers are published).

**Push to `develop` ⇒ signed WIP installers and notification, not a public GitHub Release.**

## Cutting a release (tag-driven)

Releases are no longer auto-triggered by merging into `master`. A maintainer runs through the ritual below, and pushing the `v<version>` tag triggers `ci.yml` (rebuild on the tagged SHA) and `release.yml` (waits for CI, then signs and publishes) in parallel.

### Pre-flight

- Confirm **`develop`** is green: the latest `pyRevit CI` run on `develop` succeeded and its **`wip` job** produced the signed artifact (`pyrevit-wip-installers-<install-version>`). The WIP job is part of that run, not a workflow of its own — check it in the run's job list.
- Confirm `pyrevitlib/pyrevit/version` and `release/version` reflect the version you intend to publish. `release.yml` hard-fails if the tag name does not match `pyrevitlib/pyrevit/version`.
- On **tag** pushes, CI preserves the committed build version (including the `+HHMM` suffix) from git. **`develop`** and **`master`** branch pushes still re-stamp the build number as before.
- Make sure the required secrets are configured in the **`production`** GitHub environment:

    - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_ENDPOINT`, `AZURE_CODE_SIGNING_NAME`, `AZURE_CERT_PROFILE_NAME`
    - `CHOCO_TOKEN`

### Cut a release

1. From a clean local clone on **`develop`**, run the supported release-channel build to stamp the version, copyright, and product metadata:

    ```powershell
    cd build
    $env:Build__Channel = 'release'
    $env:DOTNET_ENVIRONMENT = 'Production'
    dotnet run -c Release -- ci
    cd ..
    ```

    This updates `pyrevitlib/pyrevit/version` and the related tracked release metadata. Review those changes before committing them.

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
    - **`release.yml`** starts immediately and polls for the matching CI run (via `gh run watch`). The **`release`** job downloads CI artifacts, runs `dotnet run -- release pack sign publish` under **`production`** (sign via `sign code trusted-signing`, draft GitHub Release including signed `bin-v{version}.zip` for `pyrevit clone --branch=v*`, Chocolatey push). **`notify`** then posts to linked issues. After you publish the draft release, **`winget.yml`** submits WinGet manifest PRs.

5. Open the draft release on GitHub, review the auto-generated notes, then publish it.

!!! tip "Manual re-run"

    Running **`workflow_dispatch`** on `release.yml` is supported but the `if` guard still requires `github.ref_type == 'tag'`, so the dispatch must be invoked against an existing `v*` tag — not a branch. Use it to retry a failed release without re-pushing the tag.

    The dispatch takes three inputs: `notify_only` (run only the `notify` job, for example to re-post the release URL to linked issues), `release_url` (the published release URL passed to `notify` — required when `notify_only` is set), and `tag_ref` (the `v*` tag the run checks out).

### Post-release

Bump **`develop`** to the next development version so subsequent WIP builds carry the right number. Increment the patch component in both version files and commit them together:

```text
pyrevitlib/pyrevit/version
release/version
```

```bash
git checkout develop
git pull --rebase origin develop
git add pyrevitlib/pyrevit/version release/version
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

# publish the changed dependency project directly into the appropriate vendored folder
dotnet publish <dependency.csproj> -c Release -f <target-framework> -o dev/libs/<netfx-or-netcore>

# review and commit the diff
git add dev/libs
git commit -m "chore(libs): refresh vendored deps for <submodule> bump"
```

Use the target framework already referenced by the consuming pyRevit project, and inspect the output before committing because `dotnet publish` can include transitive assemblies. This keeps the CI hot path on the SDKs preinstalled on `windows-2025` (.NET 4.8 + .NET 8 + .NET 10) and avoids depending on the EOL 3.1 archives in a hosted runner. If a submodule ships only via NuGet, switch the consuming `.csproj` to a `PackageReference` instead of a vendored `HintPath`.

## Version files and commands

| File | Purpose |
|------|---------|
| `pyrevitlib/pyrevit/version` | Full **build** version string used across the product (drives the `v*` tag name). |
| `release/version` | **Install** / marketing version used for installers and the release title. |

CI and local product builds invoke the ModularPipelines project from [`build/`](../build/) via `dotnet run`:

| Command | When / purpose |
|---------|----------------|
| `dotnet run -- ci` (in `build/`) | Validate the environment, stamp configured metadata, build products, and stage CI outputs. |
| `dotnet test tests/Build.Tests.csproj` | Build-project unit tests (also run in CI) |
| `python -m unittest discover -s dev/scripts -p 'test_standalone_*.py'` | Host-free CPython suites for `pyrevitlib` modules (also run in CI, and as `pipenv run test-standalone`). They live in `dev/scripts` because every test in `pyrevitlib/pyrevit/unittests/` imports `pyrevit` and needs a Revit host, so a suite that gates CI cannot live beside the code it covers. Same reason for the load-by-path at the top of each file. |
| `dotnet run -- pack sign` | WIP/release pack path after artifact restore |
| `dotnet run -- publish` | Draft GitHub release + Chocolatey push |
| `dotnet run -- notify` | Post WIP/release URL to linked issues |

## Quick reference

| Goal | Action |
|------|--------|
| Validate a change in CI | PR to **`develop`**; ensure changed paths match the workflow filter. |
| WIP installers + issue ping | Merge PR → **`develop`** (the push runs `ci.yml`; its `wip` job calls `wip.yml`, then `notify`). |
| Ship a release | Stamp release on `develop`, merge to `master`, tag `v<version>` on `master`, push the tag. |
| Publish the release | Open the **draft** release on GitHub and publish when ready. |
| Next dev version after release | Increment both version files on `develop`, commit, and push. |

## Troubleshooting

- **Release fails on `Validate tag matches version`**: the tag (e.g. `v4.8.16`) doesn't match `pyrevitlib/pyrevit/version`. Delete and recreate the tag with the right name, or update the version file and re-tag. If the tag and checkout match but the error shows different `+HHMM` suffixes (e.g. tag `+1406` vs file `+1212`), CI re-stamped the build number on a tag push — tag CI must preserve the committed version; move the tag to a commit that includes that fix and re-run.
- **Release fails on `Wait for CI to complete on tagged commit`**: CI either failed or didn't start within 10 minutes of the tag push. Investigate the CI run for the tagged SHA; once it is green, re-run `release.yml`.
- **Release fails on `Download unsigned bin artifact`**: the CI run exists but the expected `unsigned-bin-<sha>` artifact is missing (most often because CI failed before the upload step). Fix CI and re-run `release.yml`.
- **`unsigned-bin-master-latest.zip` is older than the current `master` HEAD / tagged release**: the master push event may have been dropped, or prune previously deleted the per-SHA zip. Run **`workflow_dispatch`** of `ci.yml` on **`master`** to rebuild and refresh `ci-binaries`. Tag CI and `release.yml` also refresh `unsigned-bin-master-latest.zip` so clone-of-master does not depend on that push.
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
- **`pyrevit clone --branch=v*` fails to find binaries**: the GitHub Release for that tag must be **published** (draft assets are not anonymous). Confirm `bin-v{version}.zip` is listed on the release, then retry. Use `--skip-bin` only when you will sideload `bin/` yourself.

## Related reading

- [Developer Guide](dev-guide.md) — local setup and building.
- [Architecture](architecture.md) — how pyRevit is structured at runtime.
