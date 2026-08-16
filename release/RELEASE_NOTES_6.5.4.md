# pyRevit v6.5.4

Last 6.x hotfix before 7.0. Ships the post-6.5.3 fixes that were waiting on `develop` **without** the Revit &lt;2021 drop from #3438 (that work stays on `develop` for 7.0).

---

### Highlights

* **Admin installer settings** — standard users can save settings again on all-users installs; writable config lives in AppData, ProgramData stays a machine-wide seed (#3512 @jmcouffin, #3523 @jmcouffin, #3504)
* **Output window** — trailing prints, logger records, and uncaught traceback bodies flush correctly; normal output no longer inherits red error styling (#3477 @ChrisCrosley)
* **Filter Legend** — new tool builds a legend of view/template filters (swatch, name, parameter, value) with 8-language localization and column auto-fit (#3522 @Wurschdhaud, #3542 @Wurschdhaud)
* **Keynote Manager** — modeless-window crash fix plus DB/runtime reliability (#3517, #3518 @tay0thman, #3519 @tay0thman)
* **Icon theme on reload** — Dark/Light switch no longer needs a Revit restart; ribbon icons refresh in place (#3493 @app/copilot-swe-agent)
* **Convert Line Styles** — source styles are retired (merged/renamed) instead of hard-deleted, avoiding Linework crashes (#3505 @jmcouffin, #3385)
* **C# loader auth + Search** — `authusers` from `extensions.json` is honored; `.nobutton` commands show up in Search again (#3461 @jmcouffin, #3498 @app/copilot-swe-agent)

---

### Admin Installer & Configuration

* **Settings save on all-users installs** — non-elevated processes fall back to `%AppData%\pyRevit` when the ProgramData config is ACL-locked (#3512 @jmcouffin, #3504)
* **Per-user writable config** — ProgramData is a read-only seed; each user’s writable copy lives in AppData (Citrix / shared-machine safe) (#3523 @jmcouffin)
* **ACL-protected admin configs** — Python and extension-source reads no longer degrade when the machine config is not writable (#3495 @app/copilot-swe-agent, #3496 @app/copilot-swe-agent)
* **Telemetry config path** — CLI telemetry path/URL getters return the configured values instead of boolean flags (#3474 @thumDer)
* **Telemetry heal** — short malformed leftover values (quote/escape garbage) are reset on startup, not only 8 KB+ bloat (#3536 @jmcouffin)
* **Clearer telemetry errors** — missing local folder disables file telemetry only; logs include the configured path (#3491 @DailenG, #3532 @app/copilot-swe-agent)

---

### UI & C# Loader

* **Output flush + traceback styling** — `ScriptExecutor` flushes the buffer before disposing the runtime; each output entry keeps its own error state (#3477 @ChrisCrosley)
* **IronPython 3 Settings sort** — Settings smartbutton no longer compares mixed env-var types (#3477 @ChrisCrosley)
* **`authusers` on ribbon load** — C# loader merges registry `authusers` / `authgroups` from `extensions.json` and configured lookup sources, matching the Extensions Manager (#3461 @jmcouffin)
* **Icon theme** — theme cache cleared on reload; in-place ribbon icon refresh and theme-change reload prompt (#3493 @app/copilot-swe-agent)
* **`.nobutton` discovery** — hidden commands are emitted into generated assemblies again and appear in Search (#3498 @app/copilot-swe-agent)

---

### Tools

* **Filter Legend** — legend view per selected view/template; equals-filters resolve values; compound filters still get a swatch (#3522 @Wurschdhaud)
* **Legend column auto-fit** — long filter/parameter/value text no longer overflows into the next column (#3542 @Wurschdhaud)
* **Convert Line Styles** — remaining curve/MEP refs are remapped, then source categories are merged and renamed so ElementIds stay valid (#3505 @jmcouffin, #3385)
* **Keynote Manager** — persistent-engine / runtime wrappers so modeless WPF events cannot crash Revit; DB connect retries and usage-collection hardening (#3518 @tay0thman, #3519 @tay0thman, #3517)
* **Wipe AVF** — purge Analysis Visualization Framework overlays from the model (#3483 @Wurschdhaud)
* **Wipe External Services** — combined wipe for DirectContext3D and TemporaryGraphicsHandlerService leftovers (#3482 @Wurschdhaud)
* **ReNumber** — progress bar no longer starts at zero (#3481 @Wurschdhaud)
* **Get Central Path** — cloud-model path fixes, Forma/ACC/BIM360 indicator, Shift+Click opens the cloud project page (#3486 @Wurschdhaud)
* **Match History** — deduplication still works when a box is ticked and search is started afterwards (#3508 @Wurschdhaud)

---

### Revit API & Core Library

* **`pyrevit.revit.tmpgfx`** — TemporaryGraphics manager/handler helpers plus a DevTools sample (#3440 @Wurschdhaud)
* **`pyrevit.revit.avf`** — paint numeric values onto elements via Analysis Visualization Framework / SpatialFieldManager (#3487 @Wurschdhaud)
* **`unique_name()` / `get_solid_fillpattern_element()`** — shared helpers, wired into ColorSplasher, Override VG, Filter Legend, and Custom Properties (#3537 @Wurschdhaud)
* **`get_elements_by_parameter()`** — optional `view_id` to restrict the search to a view (#3501 @Wurschdhaud)
* **`get_name()`** — universal `Name` lookup (categories, worksets, and other named elements) (#3521 @Denver-22)
* **`create.py`** — helpers can optionally return created element ids (#3490 @Wurschdhaud)
* **`import requests` on IronPython** — restored missing `urllib3` `weakref_finalize` backport (#3494 @app/copilot-swe-agent, #3471)

---

### CLI

* **`--persist-credentials`** — `pyrevit extend ui|lib` can store private-repo credentials the same way the in-Revit Extensions Manager does (#3506 @jmcouffin, #3293)
* **Clone after failed install** — stale registrations from a rolled-back install no longer block the next `pyrevit clone` (#3462 @jmcouffin)
* **BIM360 cache clear** — `pyrevit caches bim360 clear` honors Revit 2024+ `CacheLocation` from Revit.ini (#3499 @jmcouffin, #3488)

---

### Extensions Catalog

* **Blendit** added (#3463 @lewismconte)
* **WWPTools** added (#3507 @jason-svn, #3509 @jason-svn)

---

### CI / Dependencies

Dependabot updates for pip and GitHub Actions (`ruff`, `mypy`, `mkdocs-material`, `mkdocstrings`, `pylint`, `setuptools`, `gitpython`, `actions/checkout`, `actions/cache`, `actions/download-artifact`, `actions/setup-python`, `actions/stale`).

---

### Not in this release

* **#3438** (Revit &lt;2021 drop and loader entry-module refactor) remains on `develop` for 7.0.

---

### Full PR List

| PR | Title | Author |
|----|----|----|
| #3440 | Add TemporaryGraphics wrapper and developer example bundle | @Wurschdhaud |
| #3461 | Honor `authusers` from extensions.json for C# UI loading | @jmcouffin |
| #3462 | Allow clone registration after failed install rollback | @jmcouffin |
| #3463 | Add Blendit to the extensions catalog | @lewismconte |
| #3474 | Fix telemetry config path / URL getters | @thumDer |
| #3477 | Flush buffered output and fix traceback styling | @ChrisCrosley |
| #3481 | Prevent ProgressBar from starting with zero numbering | @Wurschdhaud |
| #3482 | Add combined wipe tool for DC3D + TemporaryGraphics | @Wurschdhaud |
| #3483 | Add Wipe AVF tool | @Wurschdhaud |
| #3486 | Cloud-model fixes for Get Central Path | @Wurschdhaud |
| #3487 | Add `pyrevit.revit.avf` helpers | @Wurschdhaud |
| #3490 | Optionally return ids from create helpers | @Wurschdhaud |
| #3491 | Clarify local telemetry folder error | @DailenG |
| #3493 | Fix icon theme on reload after Dark/Light switch | @app/copilot-swe-agent |
| #3494 | Restore missing urllib3 `weakref_finalize` | @app/copilot-swe-agent |
| #3495 | Handle ACL-protected admin configs | @app/copilot-swe-agent |
| #3496 | Fix CI build break from uninitialized `isWritable` | @app/copilot-swe-agent |
| #3498 | Restore `.nobutton` command discovery | @app/copilot-swe-agent |
| #3499 | Honor custom BIM360 CacheLocation from Revit.ini | @jmcouffin |
| #3501 | View-scoped `get_elements_by_parameter()` | @Wurschdhaud |
| #3505 | Retire converted line styles instead of hard-delete | @jmcouffin |
| #3506 | Add `--persist-credentials` to CLI extend | @jmcouffin |
| #3507 | Add WWPTools to the extensions catalog | @jason-svn |
| #3508 | Fix Match History dedup when search is active | @Wurschdhaud |
| #3509 | Point WWPTools catalog entry at the personal repo | @jason-svn |
| #3512 | Fix settings not saving on all-users installs | @jmcouffin |
| #3518 | Refactor keynote DB reliability | @tay0thman |
| #3519 | Keynote Manager runtime wrappers and crash fixes | @tay0thman |
| #3521 | Universal `get_name()` lookup | @Denver-22 |
| #3522 | Filter Legend tool | @Wurschdhaud |
| #3523 | Keep admin-install config writable in AppData | @jmcouffin |
| #3532 | Clarify file-telemetry disable path logging | @app/copilot-swe-agent |
| #3536 | Heal short malformed telemetry config empties | @jmcouffin |
| #3537 | Shared unique-name and solid-fill helpers | @Wurschdhaud |
| #3542 | Horizontal auto-fit for Filter Legend columns | @Wurschdhaud |
| #3565 | Merge `release/6.5.4` to `master` | @jmcouffin |

---

### Contributors

@Wurschdhaud, @jmcouffin, @ChrisCrosley, @tay0thman, @thumDer, @Denver-22, @DailenG, @lewismconte, @jason-svn, @app/copilot-swe-agent

---

# Downloads

:small_blue_diamond: See **Assets** section below for all download options

### pyRevit

* :package: [pyRevit 6.5.4.26228 Installer](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.4.26228%2B1146/pyRevit_6.5.4.26228_signed.exe) — Per-user / `%LOCALAPPDATA%`
* :package: [pyRevit 6.5.4.26228 Admin Installer](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.4.26228%2B1146/pyRevit_6.5.4.26228_admin_signed.exe) — All users / `%PROGRAMDATA%`

### pyRevit CLI (Command line utility)

* :package: [pyRevit CLI 6.5.4.26228 Installer](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.4.26228%2B1146/pyRevit_CLI_6.5.4.26228_signed.exe) — Per-user
* :package: [pyRevit CLI 6.5.4.26228 Admin Installer](https://github.com/pyrevitlabs/pyRevit/releases/download/v6.5.4.26228%2B1146/pyRevit_CLI_6.5.4.26228_admin_signed.exe) — All users / System `%PATH%`

### WinGet (after manifest PRs merge)

* `winget install pyRevit.pyRevit`
* `winget install pyRevit.pyRevit.CLI`
