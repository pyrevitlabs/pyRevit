# Python config API

How scripts read and write pyRevit settings from Python: the typed sections, the flat `snake_case` aliases, and the raw escape hatches. `dev/scripts/check_config_api.py` checks the Python code against the C# section schemas and the contract constants in the checker, and fails the commit on drift when Python files under `pyrevitlib/` or `extensions/` change (a pre-commit hook; CI and the build do not run it).

## Two ways to reach a setting

`PyRevitConfig` exposes three typed sections — `core`, `routes`, `telemetry` — whose property names come from the C# records in
`dev/pyRevitLabs/pyRevitLabs.Configurations/Sections/`. Those names are
PascalCase, so a setting can be reached two ways:

```python
user_config.core.RocketMode = True   # typed section, PascalCase
user_config.rocket_mode = True       # flat alias, snake_case
```

Both work and read the same stored value.

**PascalCase on the typed section is the canonical spelling.** The C# property name is the only spelling that survives a rename of the underlying key, and it is a real CLR member, so autocomplete, hover documentation and language servers see it. The flat `snake_case` aliases are frozen:

- the 35 aliases keep working for reads, and for writes except `config_file` and `config_type`, which are read-only properties;
- they are not deprecated, and no new ones may be added (the checker fails on one);
- no alias may be removed or retargeted without updating this page, because third-party code depends on the spelling;
- an alias must stay a statically declared property. Moving one behind `__getattr__` removes it for tooling, and the checker fails on it.

Eleven aliases are renames rather than spelling conversions (see the second table below). For these, all three spellings work:

```python
user_config.routes_port = 8080        # flat alias
user_config.routes.Port = 8080        # typed property, canonical
user_config.routes.set_option("port", 8080)   # escape hatch
```

## Inventory

`PyRevitConfig` has 35 flat aliases. `dev/scripts/check_config_api.py` derives
this table from the source; the counts below are asserted by
`dev/scripts/test_check_config_api.py` so the two cannot drift.

### 31 direct delegations

The getter is a bare read of one typed property, and the setter a bare write of
it. For 20 of them, the property name is what the alias name converts to
mechanically (`rocket_mode` → `RocketMode`).

| flat alias | section | typed property | INI key |
| --- | --- | --- | --- |
| `auto_update` | `core` | `AutoUpdate` | `autoupdate` |
| `bin_cache` | `core` | `BinCache` | `bincache` |
| `check_updates` | `core` | `CheckUpdates` | `checkupdates` |
| `colorize_docs` | `core` | `ColorizeDocs` | `colorize_docs` |
| `cpython_engine_version` | `core` | `CpythonEngineVersion` | `cpyengine` |
| `file_logging` | `core` | `FileLogging` | `filelogging` |
| `load_beta` | `core` | `LoadBeta` | `loadbeta` (legacy `load_beta`) |
| `load_core_api` | `routes` | `LoadCoreApi` | `core_api` |
| `read_script_metadata` | `core` | `ReadScriptMetadata` | `read_script_metadata` |
| `required_host_build` | `core` | `RequiredHostBuild` | `requiredhostbuild` |
| `rocket_mode` | `core` | `RocketMode` | `rocketmode` |
| `telemetry_file_dir` | `telemetry` | `TelemetryFileDir` | `telemetry_file_dir` |
| `telemetry_include_hooks` | `telemetry` | `TelemetryIncludeHooks` | `include_hooks` |
| `telemetry_server_url` | `telemetry` | `TelemetryServerUrl` | `telemetry_server_url` |
| `telemetry_status` | `telemetry` | `TelemetryStatus` | `active` |
| `tooltip_debug_info` | `core` | `TooltipDebugInfo` | `tooltip_debug_info` |
| `user_can_config` | `core` | `UserCanConfig` | `usercanconfig` |
| `user_can_extend` | `core` | `UserCanExtend` | `usercanextend` |
| `user_can_update` | `core` | `UserCanUpdate` | `usercanupdate` |
| `user_locale` | `core` | `UserLocale` | `user_locale` |

For the other 11, the property is **not** the alias converted to PascalCase.
These are renames, and no spelling rule can recover them:

| flat alias | section | typed property | mechanical conversion would give | INI key |
| --- | --- | --- | --- | --- |
| `apptelemetry_event_flags` | `telemetry` | `AppTelemetryEventFlags` | `ApptelemetryEventFlags` | `apptelemetry_event_flags` |
| `apptelemetry_server_url` | `telemetry` | `AppTelemetryServerUrl` | `ApptelemetryServerUrl` | `apptelemetry_server_url` |
| `apptelemetry_status` | `telemetry` | `AppTelemetryStatus` | `ApptelemetryStatus` | `active_app` |
| `min_host_drivefreespace` | `core` | `MinHostDriveFreeSpace` | `MinHostDrivefreespace` | `minhostdrivefreespace` |
| `output_close_others` | `core` | `CloseOtherOutputs` | `OutputCloseOthers` | `closeotheroutputs` |
| `output_stylesheet` | `core` | `OutputStyleSheet` | `OutputStylesheet` | `outputstylesheet` |
| `routes_host` | `routes` | `Host` | `RoutesHost` | `host` |
| `routes_port` | `routes` | `Port` | `RoutesPort` | `port` |
| `routes_server` | `routes` | `Status` | `RoutesServer` | `enabled` |
| `startuplog_timeout` | `core` | `StartupLogTimeout` | `StartuplogTimeout` | `startuplogtimeout` |
| `telemetry_utc_timestamp` | `telemetry` | `TelemetryUseUtcTimeStamps` | `TelemetryUtcTimestamp` | `utc_timestamps` |

`routes_host`, `routes_port` and `routes_server` are the clearest case: the
alias repeats the section name that the section already carries.

### 4 derived aliases

Not renames, and not delegations. They compute something, so they have to
survive whatever happens to the naming:

| flat alias | what it does |
| --- | --- |
| `log_level` | derives a level from `core.Debug` + `core.Verbose` via `PyRevitConfigs.ToLoggingLevel` |
| `output_close_mode_enum` | converts `core.CloseOutputMode` via `PyRevitConfigs.ToCloseOutputMode` |
| `config_file` | the path the service resolved, falling back to `PyRevitConsts.ConfigFilePath` |
| `config_type` | `"Admin"` when `is_readonly`, else `"User"` |

`output_stylesheet` and `cpython_engine_version` also transform on write — the
former removes the key when cleared, the latter coerces to `int` — but they
remain 1:1 delegations on read, so they are counted above.

### Coverage

The three typed sections declare 35 properties. 34 of them have a flat alias,
counting `Debug` and `Verbose` under `log_level`. The one without is
`core.UserExtensions`, which is read and written through
`get_option`/`set_option` — see [Raw escape hatches](#raw-escape-hatches).

### Call sites

`pipenv run check-config-api --census` reports the first-party cost of any
change: **34 of the 35 aliases have a first-party call site, 66 reads and 32
writes.** The exception is `cpython_engine_version`,
because `get_active_cpython_engine` and `set_active_cpython_engine` reach it
through `self` rather than through `user_config`.

The census counts executable lines only — comments and string literals are
blanked before matching — so a docstring showing a spelling does not inflate
the total, and a string argument sharing a line with a real call does not hide
it.

This is the floor, not the total. Third-party extension call sites are not
greppable from this repository, so the real number of users of each alias is
larger.

## Typed-section behavior

`user_config.core`, `user_config.routes`, `user_config.telemetry` and
`user_config.environment` return a wrapper over the C# section. Its behavior is
fixed as follows:

- **A declared C# property wins on read.** `user_config.core.RocketMode` reads
  the typed property, applying the section's default when the key is absent.
- **A typed-property write goes through the service** and reaches the store
  immediately; `save_changes()` flushes to disk once. Assigning `None` is a
  no-op, not a delete — use `remove_option`.
- **Anything else falls back to a raw option.** A read falls through to a raw
  option of the same name, and a write stores one. This permissiveness is
  deliberate and is what makes the escape hatches below work.
- **Writes are skipped on a read-only (admin-locked) config**, matching what
  `save_changes` does with the flush, so no caller is handed a success it will
  not get.

The permissiveness has a sharp edge, and it is the single most important thing
to know on this page:

```python
user_config.core.rocket_mode = True    # does NOT set RocketMode
```

`rocket_mode` is not a declared property, so it is stored as a raw option under
the key `rocket_mode`, in a section whose real key is `rocketmode`. The write
succeeds, the file grows a junk key, and `RocketMode` keeps its old value. No
exception is raised. `check-config-api` fails on this spelling in
first-party code (`SECTION-SNAKE`); third-party code is not covered.
`pyrevitlib/pyrevit/unittests/test_config_api_contract.py` pins this permissive
behavior, so changing it is a visible diff.

`core.UserExtensions` is a declared property with no flat alias, and is reached
through `get_option`/`set_option` even by pyRevit's own Extensions button — to
preserve configured paths that no longer resolve on disk. The escape hatch is
load-bearing for a typed property, not just for custom keys.

## Raw escape hatches

For anything outside a typed section's declared properties, use these. They are
part of the contract and the checker fails if one is removed.

| surface | members |
| --- | --- |
| `user_config` | `get_section`, `add_section`, `has_section`, `remove_section` |
| `user_config.core` / `.routes` / `.telemetry` | `get_option`, `set_option`, `has_option`, `remove_option` |
| a section from `get_section`/`add_section` | the same four, plus `add_subsection`, `get_subsections`, `get_subsection`, `has_subsection` |
| a tool's own ini file | `pyrevit.coreutils.configparser.open_config_file` |

```python
cfg = script.get_config()              # the command's own section
cfg.my_option = value                   # permissive: a raw option
cfg.set_option("my_option", value)      # explicit: same effect
script.save_config()
```

`ConfigSection` — what a script gets — is permissive in both directions.

## Enforcing this page

```bash
pipenv run check-config-api            # same check as the pre-commit hook, on demand
pipenv run check-config-api --census   # first-party read/write cost per alias
pipenv run test-config-api             # tests for the checker itself
```

The checker is pure source analysis: no pyRevit import, no Revit, no labs
assemblies. It cross-references the Python aliases against the C# section
schemas, so a C# property rename surfaces as a finding rather than as a setting
that quietly stops responding.

Runtime behavior of the contract is pinned by
`pyrevitlib/pyrevit/unittests/test_config_api_contract.py`, which runs in Revit
from the DevTools "Config Module Tests" button. The encode/decode and
round-trip behavior underneath it is covered by
`pyrevitlib/pyrevit/unittests/test_config_roundtrip.py`.
