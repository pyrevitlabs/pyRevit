# Release qualification

Release qualification is the set of checks a build passes before its `v*` tag is pushed. It puts in one place what CI already proves, what has to be run in Revit, and what was not covered. [`testing.md`](testing.md) describes the test surfaces these checks use, and [`ci-cd.md`](ci-cd.md) describes the release ritual that follows a passed qualification.

Each release gets one qualification issue made from [`.github/RELEASE_QUALIFICATION_TEMPLATE.md`](https://github.com/pyrevitlabs/pyRevit/blob/develop/.github/RELEASE_QUALIFICATION_TEMPLATE.md). The template is the checklist. This page says how to run each part and when it counts as passed.

## Parts of a qualification

| Part | Content | Changes between releases |
|---|---|---|
| Automated gates | CI results for the candidate commit | No |
| Core checks | Install, Revit years, engines, hosted tests, agent runtime, languages, performance, stability, documentation | Only through a pull request against the template |
| Release-specific checks | The new features, fixes and risky changes of this release | Written when the issue is opened |
| Not covered | Every check that could not be run, with the reason | Filled in during the run |
| Sign-off | Open findings and the release decision | Filled in at the end |

The core checks are the same for every release so that results can be compared between releases. What is particular to one release goes into the release-specific part and never into the core list.

How much is run depends on the kind of release:

| Release | Run |
|---|---|
| Major or minor | Everything |
| Patch | Automated gates, install and upgrade, load and **Run All Tests** on one Revit year per runtime group, and a release-specific check for every fix it contains |

A runtime group is the set of Revit years that share a pyRevit runtime project: 2021-2024, 2025-2026, and 2027 and later (see [Revit versions and .NET](adding-revit-version.md#revit-versions-and-net)). Where a check asks for one Revit year per runtime group, a pass on one year of a group stands for the group.

## Candidate commit

A qualification is valid for one commit. Record its full SHA and build version in the issue before running anything.

- The automated gates are read from the CI runs of that commit.
- The install checks use the signed WIP installers that the `wip` job of that commit's `pyRevit CI` run uploaded (`pyrevit-wip-installers-<install-version>`). A hotfix branch has no WIP job, so its install checks cannot run before the tag. List them under *Not covered* at sign-off and run them on the draft release, before it is published.
- The in-Revit checks use a build of that commit: a git worktree at the commit, built with `dotnet run -c Release -- ci` in `build/`, with every session started by `pyrevit launch <worktree> <engine> <year> --isolated` (see [Running several clones at the same time](dev-guide.md#running-several-clones-at-the-same-time)).

When commits land after the run started, the newest commit becomes the candidate. Change the SHA in the issue, and add a comment that names the old and the new SHA and the checks that were re-run. Re-run the automated gates and the checks whose area the new commits touch; a check in an untouched area keeps its result from the earlier candidate. Re-run everything when the loader, the engines, the installer or the build pipeline changed.

The release pipeline builds and signs again on the tag, so the published installers are not the WIP installers that were qualified. The [draft release checks](#draft-release-and-after-publishing) cover that gap.

## Opening the issue

```shell
gh issue create --repo pyrevitlabs/pyRevit --title "Release qualification for <version>" --milestone <version> --body-file .github/RELEASE_QUALIFICATION_TEMPLATE.md
```

The template is not an issue template in `.github/ISSUE_TEMPLATE/`, so it does not appear in the issue chooser that users see.

Then fill in the candidate commit and write the release-specific part from the milestone's closed issues and `git log v<previous>..<candidate>`:

| Change in this release | Check to add |
|---|---|
| New feature | Its main workflow and one failure path, on IronPython 2.7.12 and 3.4.2 when it is Python, and on one Revit year per runtime group |
| Fix for a reported bug | The reporter's reproduction on the candidate build |
| Change to the loader, an engine, the installer, the config or `pyrevit attach` / `clone` | A targeted regression check of that area, plus the upgrade check |
| New Revit year or .NET runtime | All core checks on that year |
| Updated dependency or submodule | One tool that uses it |
| Removed or deprecated API, changed default | An entry in the release notes |

## Core checks

### Automated gates

| Check | Passed when |
|---|---|
| `pyRevit CI` run of the candidate commit | Green, including its `wip` job when the candidate is on `develop`. A hotfix branch has no `wip` job, and the gate is the rest of the run. Covers the build, the C# suites, the build pipeline tests, the standalone Python tests and the Revit API compatibility lint |
| `pyRevit Revit integration tests` run of the candidate commit | Green for 2022-2027: the add-in loads and no Unsigned Add-In dialog appears |
| Host-free Python modules CI omits: `python -m unittest discover -s dev/scripts -p "test_check_*.py"` | No failure |
| `mkdocs build --strict` | No warning that the previous release did not have. The build reports existing warnings, so compare instead of expecting a clean run |
| Published vulnerabilities in shipped dependencies (Dependabot alerts, advisories of the vendored and native libraries) | None with a fixed version available |

### Install and upgrade

Run these on a machine or virtual machine that has no development clone attached. They are the only checks that see what a user sees.

| Check | Passed when |
|---|---|
| Fresh install with the pyRevit installer, per user and for all users | Revit starts without the Unsigned Add-In dialog, the pyRevit tab loads, and **About** and `pyrevit env` show the candidate version |
| Upgrade over the previous release, with a changed config and one third-party extension installed | The config values and the extension are kept and load |
| CLI installer, alone and next to a full install | `where pyrevit` lists the new CLI first and `pyrevit --version` shows the candidate version |
| Uninstall | The `pyRevit.addin` manifests are gone and Revit starts without pyRevit |

### Revit years

pyRevit loads on every supported Revit year (see [Supported Revit versions](https://github.com/pyrevitlabs/pyRevit/blob/develop/AGENTS.md#supported-revit-versions)). The integration workflow proves the load for 2022-2027. Revit 2021 is outside it and always needs a manual start.

On each year that is installed: start a session, check that the startup log has no error, run **Reload**, and run one IronPython, one CPython and one C# button, for example from DevTools **Bundle Tests**. Passed when all of them complete. List the years that are not installed under *Not covered*.

### Engines

The IronPython version is fixed per session, so the engine checks need two sessions per Revit year: `pyrevit launch <clone> default <year> --isolated` for 2.7.12 and `pyrevit launch <clone> 342 <year> --isolated` for 3.4.2. Run them on one year per runtime group.

| Check | Passed when |
|---|---|
| DevTools **Engine Tests** pulldown, every button that needs no input | No failure. Expected reports that are not failures: `Test IronPython Compile` skips on .NET, `Test CPython Events` reports the pythonnet unsubscribe limitation, `Test CPython Command` lists optional packages that are not installed |
| **Py3 Compat Tests** and **Py3 Compat Tests (CPython)** | No failure |
| Buttons that need a person: `Test IronPython Threading`, `Test Persistent Engine`, `Rocket Mode Scope Test`, the debugger buttons, and `Test CPython Namespace` (waits for a pick) | Run by a person, or listed under *Not covered* |

### Hosted unit tests

| Check | Passed when |
|---|---|
| **Debug > Unit Tests > Run All Tests** on 2.7.12 and 3.4.2, one year per runtime group, with a sample model open | No failure and no error. Record the passed count per session |
| **Revit API Catalog Tests** (not part of Run All Tests) | No failure |
| **Dynamo Module Tests** on each installed year, in a model that is never saved | Cold and repeat run pass. Record the Dynamo version |

### Agent runtime and CLI

| Check | Passed when |
|---|---|
| The four **Agent Tests** buttons on 2.7.12 and 3.4.2 | No failure, and afterwards the agent policy is what it was before and no scratch project is open |
| `pyrevit agent status`, `context`, `run` and `runs` from the candidate's CLI | Each answers for a running session |
| `pyrevit mcp` | Answers `initialize` and `tools/list` |
| Two or more sessions side by side, different years or engines | Each answers `get_context` with its own clone, engine and config root |
| A long run in one session and a second request to the same session | The second request fails with `revit_busy`, and the other sessions answer at once |

### Languages and encodings

A pass in an English session on an ASCII path says nothing about these four cases. Each has produced a bug of its own.

| Case | How | Passed when |
|---|---|---|
| Revit UI language | `pyrevit launch ... --language=<code>` with one Latin language other than English and one non-Latin language | pyRevit loads, the ribbon is complete, and **Run All Tests** has no language-dependent failure |
| Windows regional format with a decimal comma | A Windows user whose regional format is, for example, German | Numbers in output windows, messages and written files have the expected format |
| Characters outside ASCII in paths and names | Cyrillic, umlauts or accented Latin, and CJK in the Windows user name, the clone or extension path, an extension and bundle name, and the model path | pyRevit loads, the buttons run and read and write their files, and names are displayed correctly |
| pyRevit language (`user_locale`) | A locale other than English that the bundles are translated to | Titles and tooltips are translated and every button still runs |

The Windows user name case needs a second Windows account or a virtual machine. `pyrevit launch` refuses a model path with characters outside ASCII, so open that model from the running session.

### Performance

Measure on one machine, one session at a time, with the same Revit year, engine and set of extensions for the candidate and for the previous release. A session that also loads DevTools is not comparable with one that does not; compare the per-extension lines in that case.

| Measurement | Source |
|---|---|
| Cold load until the UI is built, and its preload part | `[PERF]` lines of the session's runtime log |
| `BuildUI` of `pyRevitCore` and `pyRevitTools` | `[PERF]` lines |
| **Reload** in the same session | `[PERF]` lines |
| Agent engine warm-up | `[PERF] agent engine warm-up` line |

Record the numbers of both versions in the issue. A like-for-like measurement that is more than 10 % slower than the previous release needs an explanation there before the release is signed off.

### Stability

| Check | Passed when |
|---|---|
| **Reload** five times in one session | Every reload completes and the log has no new error |
| A session without an open document | pyRevit loads and **Settings**, **Extensions** and **Reload** work |
| Closing Revit after a test session | The process exits |

### Core tools

In the installed session from [Install and upgrade](#install-and-upgrade): **Settings** opens and saves, **Extensions** lists the available extensions and installs and removes one, **Update** reports the state, **About** shows the version, one tool with an output window shows working element links, and both the light and the dark theme render. One public third-party extension loads without errors, as a check of the API that extension authors rely on.

### Documentation and links

| Check | Passed when |
|---|---|
| Link check over the tracked text files: internal links with anchors, and external URLs | No dead first-party link. List URLs that block automated requests as unverified. The repository has no link checker of its own; any one will do |
| Documentation of the areas this release changed | It describes what the candidate does |
| Supported Revit years and engine versions in `README.md`, `AGENTS.md` and `docs/` | They match the build |

### Release content

| Check | Passed when |
|---|---|
| Milestone | No open issue other than the qualification issue itself, which stays open until the release is published. Every other open issue is moved to a later milestone |
| `pyrevitlib/pyrevit/version` and `release/version` | They carry the version to publish |
| Release notes | Breaking changes, deprecations and the known issues of this qualification are listed |

## Setting up the test sessions

- **Check `agent.reckless` first.** `--isolated` seeds the session's config from yours, including `[agent] reckless`. With it on, runs have no timeout and **Run Agent Tests** never returns. Turn it off with `pyrevit configs agent reckless disable` before launching, and confirm with `get_context` that the session reports `agent.reckless` as `false`.
- **Open a model before running hosted buttons.** A sample model that ships with Revit gives the tests the elements they expect. Never save it.
- **An unsigned build raises the Unsigned Add-In dialog.** Answer **Load Once**. **Always Load** stores the decision and hides the dialog from later checks.
- **`pyrevit run` uses the attached clone**, not a launched one. Use the DevTools buttons in a launched session, or attach the candidate, for `dev/tests/revit/run_dynamo.py`.
- **Copy the runtime log while the session runs** when you need its `[PERF]` lines. The pyRevit user folder of an isolated session is removed when Revit exits.
- **When Revit hangs**, the last line of `%TEMP%\pyrevit-agent-tests.log` names the running agent test. Take a stack dump before ending the process; a hang without one can rarely be fixed.

The in-Revit checks can be driven by a coding agent through the MCP server, as described in [Testing agent skills and library changes through MCP](agent-runtime.md#testing-agent-skills-and-library-changes-through-mcp). The install checks, the buttons that need a person and the visual checks stay manual.

## Recording results

Tick a box only when the check passed on the candidate commit, or on an earlier candidate whose later commits do not touch the check's area (see [Candidate commit](#candidate-commit)). For everything else add a comment with the evidence: the commit, Revit year and build, engine, model, the button or command, and the result. A check that was not run goes under *Not covered* with the reason and stays unticked.

Every finding becomes an issue, linked from the qualification issue.

## Exit criteria

The release can be tagged when:

- every automated gate is green on the candidate commit,
- every core and release-specific check is ticked or listed under *Not covered* with a reason the signing maintainer accepts, and
- no blocker is open.

A blocker is any of:

- pyRevit does not install or load on a supported Revit year,
- Revit crashes, hangs or loses model data in a workflow of a shipped tool,
- a shipped tool that worked in the previous release fails without a workaround,
- the Unsigned Add-In dialog appears for a signed build, or
- a shipped dependency has a published vulnerability with a fixed version available.

Every other finding is either fixed, or listed as a known issue in the release notes and assigned to a milestone.

## Draft release and after publishing

Pushing the tag builds the artifacts that users download. Check them before publishing the draft release:

| Check | Passed when |
|---|---|
| Installers of the draft release | `Get-AuthenticodeSignature` reports `Valid`, and a fresh install loads in Revit without the Unsigned Add-In dialog and shows the tagged version |
| Release notes of the draft | Reviewed, with the known issues of the qualification |

After publishing:

| Check | Passed when |
|---|---|
| `pyrevit clone <name> --branch=v<version>` | The clone gets its binaries |
| `Update Winget manifests` workflow and the Chocolatey package | The workflow ran and the package version is listed |
| Documentation site | Shows the released state |
| `develop` | Carries the next version (see [Post-release](ci-cd.md#post-release)) |

Then close the milestone and the qualification issue.

## Keeping the checklist current

- A finding of a qualification, or a regression users report after a release, adds an automated test where one is possible (see [Test levels and regression coverage](testing.md#test-levels-and-regression-coverage)) and otherwise a line in the core checks.
- A core check that CI starts to run moves to the automated gates.
- The core checks change only through a pull request against the template and this page, in the same change.
