# Python config API: naming contract

This page records the decision for issue [#3645](https://github.com/pyrevitlabs/pyRevit/issues/3645)
— `snake_case` versus `PascalCase` for the Python config API after
[#3450](https://github.com/pyrevitlabs/pyRevit/pull/3450) replaced the
hand-rolled INI parser with the typed C# configuration service.

It is a **contract**, not a proposal. The API it describes is the one that
merged in #3450; what is new here is that the parts #3450 left open are now
written down, and that `dev/scripts/check_config_api.py` fails the build when
the code and this page disagree.

## Status

Accepted. Two items below are flagged as **needing maintainer approval**; they
are the ones where the product owner, not the code, has to choose. Neither is
implemented. Everything else is the current, enforced behavior.

## The shape of the problem

`PyRevitConfig` exposes three typed sections — `core`, `routes`, `telemetry` —
whose property names come from the C# records in
`dev/pyRevitLabs/pyRevitLabs.Configurations/Sections/`. Those names are
PascalCase, so a setting can be reached two ways:

```python
user_config.core.RocketMode = True   # typed section, PascalCase
user_config.rocket_mode = True       # flat alias, snake_case
```

Both work. Nothing in this repository depends on which one it uses, and
neither do the 25 extensions in `extensions/extensions.json`. The question is
which one is *the* API for extension authors, and what happens to the other.

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
change. At the time of writing: **34 of the 35 aliases have a first-party call
site, 64 reads and 32 writes.** The exception is `cpython_engine_version`,
because `get_active_cpython_engine` and `set_active_cpython_engine` reach it
through `self` rather than through `user_config`.

The census counts executable lines only — comments and string literals are
blanked before matching — so a docstring showing a spelling does not inflate
the total, and a string argument sharing a line with a real call does not hide
it.

This is the floor, not the total. Third-party extension call sites are not
greppable from this repository, and #3450's own review noted that the
authoritative set of users is the extension ecosystem, not this tree.

## The decision

**PascalCase on the typed section is the canonical spelling. The flat
snake_case aliases are frozen: they are not deprecated, not scheduled for
removal, and no new ones may be added.**

### Why PascalCase

1. **One name per setting.** The C# property name is the only spelling that
   survives a rename of the underlying key. `rocket_mode`, `RocketMode` and the
   INI key `rocketmode` are three names for one setting, and no Python choice
   makes them agree. Choosing the C# name leaves exactly two.
2. **A derived name has to be maintained by hand.** The 11 renames above prove
   it. Any scheme that derives property names from alias names needs a
   mapping table, and a typo in that table is a runtime `AttributeError` —
   #3450's own review says so, which is why the checker here compares every
   alias target against the C# schema instead.
3. **The derivation is not cheaper.** The obvious way to get `snake_case` on the
   typed sections is `__getattr__`/`__setattr__` translation. The explicit
   alternative is a facade of `@property` pairs — 35 typed properties across the
   three sections, so about 70 property bodies, which is more code than the 35
   aliases it would replace, and it has to be kept in step with the C# records
   by hand. Neither is free; the explicit one is at least visible to tooling.
4. **Dynamic dispatch costs the tooling a maintainer asked to protect.**
   @sanzoghenzo's objection to `__getattr__` was not stylistic: dynamic
   attributes do not appear in autocomplete, have no hover documentation, and
   are invisible to LSP servers, which are what coding agents read to decide
   whether code is correct. A property that exists only after a name transform
   is a property the tooling cannot see. The typed property is a real CLR
   member, so none of this applies to it.
5. **The mixed style is already the house style.** Attribute accesses across
   `pyrevitlib/pyrevit` skew PascalCase roughly two to one (about 5,300 against
   2,500 snake_case), and the config file itself is mixed: `bincache` and
   `rocketmode` alongside `user_locale` and `tooltip_debug_info`. A module that
   disagreed with both would be the odd one out, not the standard.
6. **The INI keys do not favour snake_case.** For 20 of the 31 delegations the
   key is flat lowercase (`bincache`, `rocketmode`, `autoupdate`,
   `closeotheroutputs`). PascalCase is the closer of the two Python spellings
   to what is actually on disk.

### Why the aliases are frozen rather than deprecated

#3450's module docstring called the flat aliases "legacy" and "expected to be
deprecated in a future release". That was the unsettled part of #3645, and this
page supersedes it: **no deprecation, no timeline, no warning.**

- The audience for a deprecation warning is extension authors, and there is no
  channel in this repository that reaches all of them. A warning that only
  fires for authors who happened to read a release note is not a migration
  plan.
- The read and write sides cannot be separated safely. The flat aliases are the
  only spelling for 34 settings, and a write that silently stops taking effect
  is worse than a name that never changes.
- The cost of keeping them is 35 property pairs that are already written,
  tested, and mechanically checkable. It is not a tax that grows.

What "frozen" means concretely:

- the 35 aliases keep working, for reads and writes, indefinitely;
- no new alias may be added — the checker fails on one;
- no alias may be removed or retargeted without a separate decision recorded
  here, because third-party code depends on the spelling;
- an alias must stay a statically declared property. Moving one behind
  `__getattr__` is a removal in all the ways that matter, and the checker fails
  on it.

### The 11 renames

All three spellings are supported and none is being taken away:

```python
user_config.routes_port = 8080        # flat alias, unchanged
user_config.routes.Port = 8080        # typed property, canonical
user_config.routes.set_option("port", 8080)   # escape hatch, unchanged
```

`routes_port` is a rename, not a naming convention, so the typed property is
`Port` and there is no `routes_port` property to be confused with. The flat
spelling stays because third-party extensions are already using it.

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
first-party code (`SECTION-SNAKE`); third-party code is not covered, which is
one of the reasons the strictness question below is worth answering.

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

`ConfigSection` — what a script gets — stays permissive in both directions.
Strictness is proposed only for the three built-in typed sections, and only
needs to be decided once.

## Options considered

| | option | verdict |
| --- | --- | --- |
| A | Status quo as merged in #3450 | **Chosen**, with the "legacy / will be deprecated" wording replaced by the frozen policy above. |
| B | `snake_case` on the typed sections, via translation plus an 11-entry table | Rejected. Needs a hand-maintained table whose typos are runtime `AttributeError`s; the explicit-facade variant costs more code than the 35 aliases it removes; the `__getattr__` variant is invisible to the tooling a maintainer asked to protect. |
| C | Both spellings on the typed sections, permanently | Rejected. Two public spellings for one setting, and the snake_case one is the silent-write footgun above. |
| D | Rename the C# properties to match, and generate | Rejected for now. Cleanest end state, largest blast radius: those names are public API for the CLI, the loader, and any .NET consumer. Worth revisiting if a major version ever renames the INI keys too. |

## Decisions that still need maintainer approval

These are **not** implemented. Both are behavior changes for third-party
extensions, so neither can be inferred from the code.

### 1. Should the typed sections become strict?

@ChrisCrosley proposed that attribute assignment on `core`/`routes`/`telemetry`
reject any name that is not a declared property, raising `AttributeError`
instead of writing a raw option, with `set_option()` as the explicit way to do
that, leaving custom sections permissive.

- For: the `user_config.core.rocket_mode = True` footgun disappears. A
  mis-cased or typo'd name fails at the line that made the mistake.
- Against: it is a breaking change for any extension that stores a non-schema
  key in `[core]`, `[routes]` or `[telemetry]`. The Extensions button's
  `userextensions` use is the one in-tree exception, and it would need to stay
  on `get_option`/`set_option` or the raw-key capability would be lost
  entirely.
- The current permissive behavior is pinned by
  `pyrevitlib/pyrevit/unittests/test_config_api_contract.py`, so adopting
  strictness is a visible diff rather than a silent one.

### 2. Is there ever a deprecation timeline for the flat aliases?

The recommendation is that there is not — freeze them. If maintainers want one
anyway, this page's constraints say it has to come with a migration channel
that reaches extension authors, write-side removal strictly before read-side
removal, and a major-version boundary. The census above is the number to
quote when that discussion happens; it is a lower bound.

## Enforcing this page

```bash
pipenv run check-config-api            # fails on any drift from this contract
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
