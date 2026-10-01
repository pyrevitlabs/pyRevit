# Plan: sign test builds locally so CI can run tests inside Revit

Status: proposal. Nothing here is implemented yet.

## Problem

Everything that can only be checked inside a running Revit is checked by hand today:
the DevTools *Engine Tests*, `pyrevitlib/pyrevit/unittests`, the agent runtime guard
end to end, and the live QA list for each PR. CI builds unsigned DLLs (`dotnet run -- ci`),
and Revit asks about every unsigned add-in it loads with a modal *Security - Unsigned
Add-In* dialog. An unattended Revit started by CI stops at that dialog, so no in-Revit
test can run unattended.

Real signing can't be used for this. It runs only in `wip.yml` and `release.yml`, under the
`production` environment, through Azure Trusted Signing, and is gated off for forks and PRs
(`SkipDecisions.WithSigningGate`). Test builds must not use the production identity.

## Proposal

Add a test-only signing path: CI creates a throwaway code-signing certificate, signs the
build with it, and trusts it only on the machine that runs Revit.

1. **`sign-test` pipeline mode** (`build/Modules/SignTestBinariesModule.cs`). It reuses
   `SigningHelper.FindPyRevitBinaries(PyRevitPaths.BinPath)` so it signs exactly the files
   that production signing covers. It signs with `sign code certificate-store` (the `sign`
   tool is already installed by `SigningHelper.EnsureSignToolInstalledAsync`) and the
   thumbprint of the throwaway certificate. It never reads `SigningOptions`, and it refuses
   to run when `Build__Channel` is `wip` or `release`.
2. **Throwaway certificate per run.** `New-SelfSignedCertificate -Type CodeSigningCert
   -CertStoreLocation Cert:\CurrentUser\My` with a subject such as
   `CN=pyRevit CI Test <run id>` and a lifetime of one day. The private key never leaves the
   runner. It is created with the private key marked non-exportable and deleted in an
   `always()` cleanup step.
3. **Trust only on the test runner.** The public certificate goes into the runner account's
   `CurrentUser\Root` and `CurrentUser\TrustedPublisher` stores, so Revit loads the signed
   loader and runner add-ins without the dialog. It is removed again in the cleanup step.
4. **In-Revit test job** on a self-hosted Windows runner with a licensed Revit (GitHub-hosted
   runners have no Revit). The job:
   - downloads the `unsigned-bin-<sha>` artifact that `ci.yml` already uploads,
   - runs `sign-test` against it,
   - attaches it with `pyrevit clones add ci <path>` and `pyrevit attach ci default --installed`,
   - runs the test scripts with `pyrevit run <script> --revit=<year>`, which already drives Revit
     through a generated journal and its own `PyRevitRunner.addin`,
   - collects results from files the scripts write, and fails the job on any failure.
5. **Test entry points.** One script per suite, each writing a JUnit-style XML file:
   the Engine Tests pulldown scripts, `pyrevitlib/pyrevit/unittests`, and agent runtime runs
   driven through the named pipe (`pyrevit agent run`) once the agent runtime has merged.

## Local mode: `dotnet run -- ci local`

The same signing step runs on a developer machine, so testing a change in Revit doesn't wait
for CI or stop at the unsigned add-in dialog after every rebuild.

- `dotnet run -c Debug -- ci local` runs the normal `ci` build, then signs `bin/` with a
  per-machine developer certificate. Modes are plain words in `build/Program.cs`
  (`ci`, `pack`, `sign`), so `local` is one more; `--local` can be accepted as an alias.
- The first run creates `CN=pyRevit Local Dev (<machine>)` in `CurrentUser\My` with a
  one-year lifetime and a non-exportable key, and trusts it in the developer's own
  `CurrentUser\Root` and `CurrentUser\TrustedPublisher`. Windows asks once to confirm the
  root. Later runs reuse the certificate by subject and renew it when it is near expiry.
- `dotnet run -- ci local --remove-cert` deletes the certificate from all three stores.
- `local` refuses to run when `CI` is set or `Build__Channel` is `wip` or `release`, so a
  developer certificate can never sign a CI or shipped build. `pack`, `sign` and `publish`
  can't be combined with it.
- `local` signs only `bin/`, which `pyrevit attach` points Revit at. Locally signed binaries
  are never uploaded, and the installers keep using production signing.
- The CI test job calls the same module with the throwaway certificate, so the local and CI
  paths sign the same files the same way.

## Guard rails

- The test certificate never signs anything that is uploaded, released, or installed
  outside the test runner. Signed test binaries are not uploaded as artifacts.
- The `sign-test` mode and the production `sign` mode cannot run in the same pipeline
  invocation.
- The job runs only for pushes to `develop` and for PRs from branches in
  `pyrevitlabs/pyRevit`. A fork PR must never reach a self-hosted runner that has Revit and
  a trusted certificate store.
- Cleanup removes the certificate from every store even when the job fails or is cancelled.

## Open questions

- **Revit's trust check.** Confirm on each supported Revit year (2021–2027) that a
  certificate in `CurrentUser\TrustedPublisher`, with its root in `CurrentUser\Root`, loads
  the add-in silently. If a year still prompts, fall back to its per-user "always load"
  registry entry for the add-in, written by the job.
- **Runner.** Which machine, which Revit years, and who maintains the licenses.
- **Dialogs.** `pyrevit run` has `--allowdialogs`; decide whether test runs fail on any
  dialog instead of dismissing it.
- **Time budget.** One Revit start per year per suite may take minutes; decide whether every
  PR runs it or only pushes to `develop`.

## Steps

1. Prove the trust check by hand on one Revit year: sign with a self-signed certificate,
   trust it, and confirm there is no dialog.
2. Add the `sign-test` module and the `ci local` mode, with tests in `build/tests`, so
   developers get dialog-free local builds first.
3. Add a workflow for the self-hosted runner that runs one Engine Test end to end.
4. Add the remaining suites and the JUnit results.
5. Document the job in `docs/ci-cd.md`.
