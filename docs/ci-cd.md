# CI/CD and release flow

This guide explains how GitHub Actions and the `pyrevit` build CLI work together: integrating work on **`develop`** (WIP builds), shipping from **`master`** (releases), and how versions are bumped.

## Branches and roles

| Branch | Role |
|--------|------|
| **`develop`** | Day-to-day integration. Merged PRs produce **WIP** builds and tester notifications. |
| **`master`** | Release line. Merges here drive **release** builds, a draft GitHub Release, Chocolatey publish, and an automatic patch bump on **`develop`**. |

Feature work branches from **`develop`**. Changes reach **`develop`** and **`master`** through pull requests (and maintainers can also trigger the workflow manually on **`master`**).

## Workflow: `pyRevitCI`

The pipeline lives in [`.github/workflows/main.yml`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/workflows/main.yml) as job **`pyRevitCI`**.

### Triggers

- **Pull requests** targeting **`develop`** or **`master`**: events **`opened`**, **`reopened`**, and **`closed`** (merge is a `closed` event with `merged == true`).
- **`workflow_dispatch`**: manual run from the Actions tab.

!!! warning "PR pushes do not re-run CI"

    The workflow does **not** subscribe to `synchronize`. New commits pushed to an **open** PR do **not** trigger another run. Close and reopen the PR, or merge and follow up, if you need a fresh CI run after fixes.

### Path filter

PRs only trigger the workflow if they change files under:

- `bin/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, or `site-packages/`

Doc-only or other out-of-scope changes may skip CI entirely.

### Official repository vs forks

Many steps run only when `github.repository` is **`pyrevitlabs/pyRevit`**:

- Environment check, copyright year, WIP/release build stamping, signing, commits, tags, GitHub Release, Chocolatey, issue notifications.

Forks still get checkout, pipenv, and **unsigned** product and installer builds (useful for validation).

## Feature or fix → `develop` (WIP)

1. Create a branch from **`develop`**, implement the change, open a **PR into `develop`** (touch paths under the filter if you need CI).
2. After the PR is **merged** into **`develop`**, the workflow sets **`WipRun`**. On the main repo it:

    - Runs `pipenv run pyrevit set build wip` (refreshes the build segment and applies WIP versioning; see `dev/_props.py`).
    - Runs `pipenv run pyrevit set products`, then `pipenv run pyrevit build products`, signs binaries, `pipenv run pyrevit build installers`, and uploads installer artifacts.
    - Runs `pipenv run pyrevit notify wip` with the Actions run URL so linked issues can be updated for testers.

**Merge to `develop` ⇒ WIP build and notification, not a public GitHub Release.**

## `develop` → `master` (release)

1. Open a **PR from `develop` into `master`** and merge when ready.
2. That merge sets **`ReleaseRun`**. On the main repo the workflow:

    - Runs `pipenv run pyrevit set build release`.
    - Builds and signs products and installers (same overall shape as WIP).
    - Generates release notes: `pipenv run pyrevit report releasenotes` → `release_notes.md`.
    - Runs `pipenv run pyrevit build commit`: commits metadata with message `Publish! [skip ci]`, creates tags `v<build-version>` and `cli-v<build-version>`, pushes commits and tags (`dev/_release.py`).
    - Publishes a **draft** GitHub Release (title uses the install version) and attaches installers.
    - Pushes the Chocolatey package.
    - Notifies linked issues: `pipenv run pyrevit notify release` with the release URL.
    - Checks out **`develop`**, rebases on `origin/develop`, runs `pipenv run pyrevit set next-version`, and pushes **`develop`** (patch bump + commit `Next Version [skip ci]`).

!!! tip "Manual release"

    Running **`workflow_dispatch`** on **`master`** also sets **`ReleaseRun`**, so the same release steps can run without a PR merge when maintainers need it.

## Version files and commands

| File | Purpose |
|------|---------|
| `pyrevitlib/pyrevit/version` | Full **build** version string used across the product. |
| `release/version` | **Install** / marketing version used for installers and the release title. |

CI invokes the `pyrevit` CLI from the repo root (via pipenv); relevant commands:

| Command | When / purpose |
|---------|----------------|
| `pipenv run pyrevit set year` | Updates copyright year (CI on main repo, before stamping). |
| `pipenv run pyrevit set build wip` | After merge to **`develop`**. |
| `pipenv run pyrevit set build release` | Release build on **`master`**. |
| `pipenv run pyrevit set products` | Refreshes product metadata before `build products`. |
| `pipenv run pyrevit set version <ver>` | Manual bump, e.g. `4.8.0`; tooling adds build/time segments (and WIP suffix when used in that mode). |
| `pipenv run pyrevit set next-version` | **Patch** bump on **`develop`** after a release (normally done by CI). |

## Quick reference

| Goal | Action |
|------|--------|
| Validate a change in CI | PR to **`develop`**; ensure changed paths match the workflow filter. |
| WIP installers + issue ping | Merge PR → **`develop`**. |
| Ship a release | Merge **`develop` → `master`** (or dispatch workflow on **`master`**). |
| Publish the release | Open the **draft** release on GitHub and publish when ready. |
| Next dev version after release | Usually automatic via `set next-version` on **`develop`** after release. |

## Related reading

- [Developer Guide](dev-guide.md) — local setup and building.
- [Architecture](architecture.md) — how pyRevit is structured at runtime.
