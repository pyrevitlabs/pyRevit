<!--
How to run each check and when it counts as passed: docs/release-qualification.md
Tick a box only when the check passed on the candidate commit. Put evidence in comments.
A check that was not run stays unticked and goes under "Not covered" with the reason.
-->

## Candidate

- Version:
- Commit (full SHA):
- Previous release compared against:
- Kind of release: major / minor / patch
- `pyRevit CI` run:
- `pyRevit Revit integration tests` run:

| Revit year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2027 |
|---|---|---|---|---|---|---|---|
| Installed on the test machine | | | | | | | |
| Loads | | | | | | | |
| IronPython 2.7.12 checks | | | | | | | |
| IronPython 3.4.2 checks | | | | | | | |
| CPython checks | | | | | | | |

## Automated gates

- [ ] `pyRevit CI` is green on the candidate commit, including the `wip` job
- [ ] `pyRevit Revit integration tests` is green on the candidate commit for 2022-2027
- [ ] Host-free Python modules that CI omits pass (`test_check_*.py`)
- [ ] `mkdocs build --strict` reports no warning the previous release did not have
- [ ] No shipped dependency has a published vulnerability with a fixed version available

## Core checks

**Install and upgrade** (machine without a development clone)

- [ ] Fresh install, per user and for all users: no Unsigned Add-In dialog, tab loads, candidate version shown
- [ ] Upgrade over the previous release keeps the config and a third-party extension
- [ ] CLI installer, alone and next to a full install: the new `pyrevit` is first on `PATH`
- [ ] Uninstall removes the manifests and Revit starts without pyRevit

**Revit years**

- [ ] Every installed supported year: loads without errors, Reload works, one IronPython, one CPython and one C# button run
- [ ] Revit 2021 started by hand (outside the integration workflow)

**Engines** (one year per runtime, a 2.7.12 and a 3.4.2 session each)

- [ ] Engine Tests pulldown, buttons that need no input
- [ ] Py3 Compat Tests and Py3 Compat Tests (CPython)
- [ ] Engine Tests buttons that need a person

**Hosted unit tests**

- [ ] Run All Tests on 2.7.12 and 3.4.2, one year per runtime
- [ ] Revit API Catalog Tests
- [ ] Dynamo Module Tests on each installed year, cold and repeat

**Agent runtime and CLI**

- [ ] The four Agent Tests buttons on 2.7.12 and 3.4.2; policy restored and no scratch project left open
- [ ] `pyrevit agent status`, `context`, `run`, `runs` and `pyrevit mcp` from the candidate's CLI
- [ ] Sessions side by side each report their own clone, engine and config root
- [ ] `revit_busy` for a second request to a busy session while other sessions answer

**Languages and encodings**

- [ ] Revit UI in a Latin language other than English and in a non-Latin language
- [ ] Windows regional format with a decimal comma
- [ ] Cyrillic, umlauts or accents, and CJK in the user name, clone or extension path, extension and bundle names, model path
- [ ] pyRevit language (`user_locale`) other than English

**Performance** (same machine, Revit year, engine and extensions as the previous release)

- [ ] Cold load, preload and `BuildUI` of `pyRevitCore` and `pyRevitTools`
- [ ] Reload
- [ ] Agent engine warm-up
- [ ] Nothing more than 10 % slower without an explanation

**Stability**

- [ ] Reload five times in one session
- [ ] Session without an open document
- [ ] Revit exits after every test session

**Core tools** (installed session)

- [ ] Settings, Extensions (install and remove one), Update, About
- [ ] Output window with working element links; light and dark theme
- [ ] One public third-party extension loads without errors

**Documentation and links**

- [ ] Link check over the tracked text files, internal and external
- [ ] Documentation of the areas this release changed describes the candidate
- [ ] Supported Revit years and engine versions match the build

**Release content**

- [ ] Milestone has no open issue
- [ ] Version files carry the version to publish
- [ ] Release notes list breaking changes, deprecations and known issues

## Release-specific checks

<!--
Write this part when opening the issue, from the milestone's closed issues and
git log v<previous>..<candidate>. One line per new feature (main workflow and a failure path),
per fix for a reported bug (the reporter's reproduction) and per change to the loader,
engines, installer, config or CLI attach/clone (targeted regression).
-->

- [ ] 

## Not covered

<!-- Every check that was not run, with the reason. -->

## Findings

<!-- One line per issue found, with its number and whether it blocks the release. -->

## Sign-off

- [ ] No blocker is open
- [ ] Everything under "Not covered" is accepted
- Signed off by:

## Draft release and after publishing

- [ ] Draft release installers are signed, install on a clean machine and load without the Unsigned Add-In dialog
- [ ] Draft release notes reviewed
- [ ] `pyrevit clone --branch=v<version>` gets its binaries
- [ ] Winget workflow ran and the Chocolatey package is listed
- [ ] Documentation site shows the released state
- [ ] `develop` carries the next version; milestone closed
