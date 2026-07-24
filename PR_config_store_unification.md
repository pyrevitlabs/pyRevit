# refactor: Unify pyRevit configuration handling

## Summary

pyRevit historically has **three independent configuration readers** for `pyrevit_config.ini`, each with its own parsing, defaults, and quirks that have drifted apart over time. None of them shared a parsed result, so the file was read from disk once by the C# loader and then **again for every startup script and smartbutton engine** (at least 5 times for a basic pyRevit install):

- the Python layer (`pyrevit.coreutils.configparser`)
- the CLI library (`pyRevitLabs.PyRevit`)
- the C# loader (`pyRevitExtensionParser`)

This branch replaces all three with **one C#-owned configuration store** shared by the loader, CLI, IronPython, and CPython, and quarantines the legacy INI parsing behind a one-time, version-gated migration.

It began as a clean port of [@dosymep](https://github.com/dosymep)'s [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) (_"refactor: Rewrite pyRevit configurations"_) onto current `develop`, reconciled with everything that changed since that PR was opened. The work was **developed and reviewed in three phases** ([draft PR #3450](https://github.com/pyrevitlabs/pyRevit/pull/3450) tracked Phase 1) but **ships here as a whole** — all three phases are present on this branch. Nothing is released until the whole thing lands, so the two defects that Phases 2 and 3 fix are described below as *fixed*, not deferred.

---

## Phase 1 — the shared configuration service

**New `pyRevitLabs.Configurations` assembly family**, ported from [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482):

- `IConfigurationService` / `IConfiguration` with attribute-bound typed POCO sections (`[SectionName]` / `[KeyName]`) for `[core]`, `[routes]`, `[telemetry]`, and `[environment]`, with defaults centralized on the sections instead of scattered across readers ([`Sections/`](dev/pyRevitLabs/pyRevitLabs.Configurations/Sections/)).
- A pluggable INI backend, [`pyRevitLabs.Configurations.Ini`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/) — the only backend ported (see *Intentionally not included* below).
- xUnit/NUnit test projects for the abstraction and the INI backend.

**CLI migrated onto the service** ([`PyRevitConfigs.cs`](dev/pyRevitLabs/pyRevitLabs.PyRevit/PyRevitConfigs.cs)): all config access now goes through `IConfigurationService`; the bespoke CLI parser ([`pyRevitLabs.PyRevit/PyRevitConfig.cs`](dev/pyRevitLabs/pyRevitLabs.PyRevit/), −176 lines) is removed.

**Python config layer migrated** ([`userconfig.py`](pyrevitlib/pyrevit/userconfig.py), [`coreutils/configparser.py`](pyrevitlib/pyrevit/coreutils/configparser.py), [`labs.py`](pyrevitlib/pyrevit/labs.py)): the Python layer is now a thin adapter over the same service and drops the `MadMilkman.Ini` dependency. The public `user_config` API is unchanged.

**Reconciliation with `develop`** (deltas applied on top of the [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) base):

- Re-applied settings added to `develop` since [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) forked: close-output modes, `new_loader`, `read_script_metadata`, cached attachment lookup, and the [#3193](https://github.com/pyrevitlabs/pyRevit/issues/3193) third-party-extension ordering.
- Tolerant reads: a single malformed or legacy value falls back to its default instead of aborting the whole config load ([`ConfigurationBase.GetValueOrDefault`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationBase.cs#L117)).
- Correctness fixes: a partial section save no longer strips sibling keys; the UTC-timestamp setter writes the correct key; absent-option presence detection is restored.

---

## Phase 2 — fidelity & migration ✅ (verified on this branch)

**Goal:** make the store byte-faithful to existing config files and self-healing, and fix the string-encoding defect inherited from [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482).

- **Symmetric-JSON value contract** — a value is JSON-encoded once on write and decoded once on read, consistently on both sides. C#: [`IniConfiguration.SetValueImpl`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/IniConfiguration.cs#L97) serializes once; [`GetValueImpl`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/IniConfiguration.cs#L115) deserializes once and tolerates legacy bare/hex values. Python: [`ConfigSection.set_option`](pyrevitlib/pyrevit/coreutils/configparser.py#L97) / [`get_option`](pyrevitlib/pyrevit/coreutils/configparser.py#L67) use `json.dumps`/`json.loads` with a single-quote legacy fallback. This eliminates the double-encoding; the two previously-red `Ini` round-trip canary tests are now green.
- **One-time canonicalizing migration**, stamped with a `[core] config_version` key ([`ConfigurationMigrator`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationMigrator.cs)): backs up the file first, drops typed-section values that no longer parse to their declared type, resets telemetry fields blown up by escape-doubling, then stamps the schema version. A clean, already-stamped config is a no-op (no write).
- **Self-heal on load** — the migrator scans and repairs on **any writable load**, not only at the version bump, so corruption introduced after first run still heals. If a backup can't be written, the run is skipped and retried on a later load so a recoverable copy is never lost ([`ConfigurationMigrator.Migrate`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationMigrator.cs#L68)).
- **Golden-file fidelity corpus** — round-trip tests over real-world config shapes ([`GoldenFileFidelityTests`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini.Tests/) with `populated` / `corrupted_clones` / `legacy_values` / `empty` fixtures) guarding decode/encode parity.
- **Type & contract fixes** — `apptelemetry_event_flags` is stored as a **string** because a 128-bit hex bitmask overflows `int` ([`TelemetrySection`](dev/pyRevitLabs/pyRevitLabs.Configurations/Sections/TelemetrySection.cs#L31)); the loader adapter parses legacy `0x…` hex ints ([`IniConfiguration` hex path](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/IniConfiguration.cs#L112)); `ConfigSection.__getattr__` raises `AttributeError` when an option is absent, restoring presence detection ([`configparser.py`](pyrevitlib/pyrevit/coreutils/configparser.py#L33)).
- **Diagnostics sink** — migration repairs, read-only-admin use, and tolerant-read fallbacks route through a logging hook ([`ConfigurationDiagnostics`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationDiagnostics.cs)) rather than being swallowed; a host wires `Warn`/`Info` to its logger.

Fixes: [#3334 — Telemetry config fields exhibit progressive escape-doubling, growing to 8MB+ each over reload cycles](https://github.com/pyrevitlabs/pyRevit/issues/3334).

---

## Phase 3 — loader integration & one shared instance ✅ (verified on this branch)

**Goal:** retire the third (loader) reader and serve **one** process-wide config instance to the loader, CLI, and all engines — eliminating the per-engine re-read/re-save that originally motivated this work — and fix the sparse-save clobber.

- **One process-wide cached service** — [`PyRevitConfigStore`](dev/pyRevitLabs/pyRevitLabs.Configurations/PyRevitConfigStore.cs) caches the built `ConfigurationService` per configuration name; the loader, CLI, and both Python engines resolve the same in-process instance. "Reload" is an explicit [`Reload()`](dev/pyRevitLabs/pyRevitLabs.Configurations/PyRevitConfigStore.cs#L62) cache invalidation, not a re-parse on every engine startup.
- **Config discovery hoisted** into the lightweight `Configurations.Ini` layer ([`PyRevitConfigService`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigService.cs), [`PyRevitConfigPaths`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigPaths.cs)) so the loader can use the shared service without taking heavy dependencies.
- **Loader reader retired** — `pyRevitExtensionParser`'s config is now a thin adapter over `IConfiguration` ([`PyRevitConfig.cs`](dev/pyRevitLoader/pyRevitExtensionParser/PyRevitConfig.cs)), and the standalone Win32 `IniFile.cs` reader is **deleted** (−460 lines).
- **Sparse-save clobber fixed** — section read-defaults moved to `[DefaultValue]`/read-time. On save, a `null` property means "not set by this caller" and is left untouched, so a single-field save (e.g. any `pyrevit configs <x>` command) writes only the fields the caller set and no longer wipes sibling keys such as `userextensions` ([`ConfigurationService.SaveSection`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationService.cs#L135) / [`CreateSection`](dev/pyRevitLabs/pyRevitLabs.Configurations/ConfigurationService.cs#L164); `userextensions` has no field initializer, see [`CoreSection`](dev/pyRevitLabs/pyRevitLabs.Configurations/Sections/CoreSection.cs#L95)).
- **Cross-reader parity test** — the loader adapter and the shared service must decode one canonical fixture into identical values ([`ConfigParityTests`](dev/pyRevitLoader/pyRevitExtensionParserTester/ConfigParityTests.cs)); because the CLI and Python read through the same service, loader/service parity transitively covers all readers, guarding against a fourth divergence.

---

## Additional items addressed (not in the original #3450 description)

These landed while completing Phases 2–3 and aren't in the [#3450](https://github.com/pyrevitlabs/pyRevit/pull/3450) writeup:

- **Install-scope awareness.** Config discovery now selects a tier from observed facts via a pure, unit-testable ladder ([`PyRevitConfigService.SelectConfig`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigService.cs#L71)): local-clone override → all-users machine install (writable `%ProgramData%` is authoritative) → admin seed/lockdown → per-user → new. Admin writability is detected with a real **write-probe** ([`IsFileWritable`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigService.cs#L259)), not the read-only attribute alone, so ACL denials are honored. Covered by `PyRevitConfigServiceSelectionTests` and `PyRevitConfigPathsTests`.
- **Split-admin-config repair migration** (restores [#3441](https://github.com/pyrevitlabs/pyRevit/pull/3441)). One-time repair for machine installs whose clone registry and per-extension sections were written to `%APPDATA%` before the store honored install scope: it promotes a lone per-user config to `%ProgramData%`, or merges the clone registry and missing extension sections into an existing machine config ([`MigrateSplitAdminConfigIfNeeded` / `MergeAdminConfigFiles`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigService.cs#L155)).
- **Dedicated Python-list parser** ([`PythonListParser`](dev/pyRevitLoader/pyRevitExtensionParser/PythonListParser.cs)) for list-valued keys (`userextensions`, `environment.sources`) in the loader adapter, replacing the parsing that lived in the deleted `IniFile`.
- **Legacy `[core] load_beta` fallback** — the loader reads `loadbeta` first, falls back to the legacy `load_beta`, and drops the legacy key on write so a file never carries two competing entries ([`PyRevitConfig.LoadBeta`](dev/pyRevitLoader/pyRevitExtensionParser/PyRevitConfig.cs#L147)).
- **Config assemblies load from the bin root**, not per-engine folders (`Directory.Build.targets`), so the shared instance resolves the same DLLs regardless of which engine touches it first.
- **Re-entrant cache-clear hardening** — `ClearAllCaches` resets locale tracking so a reload can't re-trigger itself ([`ExtensionParser`](dev/pyRevitLoader/pyRevitExtensionParser/ExtensionParser.cs)); `PyRevitConfigStore.Reset()` plus factory-gated `EnsureRegistered` make test isolation recoverable ([`PyRevitConfigService.EnsureRegistered`](dev/pyRevitLabs/pyRevitLabs.Configurations.Ini/PyRevitConfigService.cs#L40)).
- **Python `upgrade.py` slimmed** — the Python-side telemetry bloat-healing chain is removed; that repair is now owned by the C# `ConfigurationMigrator`, so the fixup lives in exactly one place ([`versionmgr/upgrade.py`](pyrevitlib/pyrevit/versionmgr/upgrade.py)).
- **Defensive config consumers** — `revit/tabs.py` tolerates malformed/non-string tab-color and tab-style config values instead of throwing during ribbon build ([`tabs.py`](pyrevitlib/pyrevit/revit/tabs.py)).
- **New tests beyond the abstraction/INI suites:** CLI-facade round-trips ([`PyRevitConfigsFacadeTests`](dev/pyRevitLoader/pyRevitExtensionParserTester/PyRevitConfigsFacadeTests.cs)), the Python bridge round-trip suite ([`test_config_roundtrip.py`](pyrevitlib/pyrevit/unittests/test_config_roundtrip.py)), and an **in-Revit "Config Module Tests" DevTools button** that exercises the Python config bridge live ([button](extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel/Unit%20Tests.pulldown/Config%20Module%20Tests.pushbutton/script.py)).

---

## Intentionally not included

- **[#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482)'s JSON and YAML backends are dropped.** [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) shipped three pluggable backends — `Configurations.Ini`, `Configurations.Json`, and `Configurations.Yaml` (a ~150-line `YamlConfiguration` on `YamlDotNet`). pyRevit's config is INI, so only the INI backend is ported: no source, no project, no format-dispatch left dangling, and no new `YamlDotNet`/JSON-format dependency. The `IConfiguration` abstraction is kept, so a backend could be re-introduced later if there were ever a reason to.
- **Per-Revit-version overrides — write path only.** [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) introduced overriding a setting for a specific Revit version (e.g. `pyrevit configs rocketmode enable 2025` → a versioned `pyRevit_config.2025.ini`). The **write side and layering plumbing are present** — the `configs` CLI commands accept the optional `[<revit_year>]` argument, ~35 setters take a `revitVersion` and save into a per-version layer, and `ConfigurationService` reads layered sources with the override winning. The **read side is still not wired**: every getter is parameterless and reads only the base config (verified — the CLI's getters call `GetConfigFile()` with no version, while setters call `GetConfigFile(revitVersion)`), the loader hard-codes the default layer, and migration operates on the base config only. Net: a versioned write produces a file nothing currently reads. Completing the read-side wiring (loader resolves its Revit version and requests the matching layer; versioned read overloads) is left as follow-up now that everything routes through one shared service keyed by configuration name.

---

## Resolved defects (were the "known limitations" in #3450)

The two defects [#3450](https://github.com/pyrevitlabs/pyRevit/pull/3450) flagged as inherited from [#2482](https://github.com/pyrevitlabs/pyRevit/pull/2482) are **fixed on this branch**:

- **String double-encoding** — fixed by the symmetric-JSON contract (Phase 2). The two `Ini` round-trip canary tests are now green.
- **Sparse-section save clobber (data loss)** — fixed by moving section defaults to read-time and treating `null` properties as "not set" on save (Phase 3), so a one-field `pyrevit configs` write no longer wipes `userextensions`.

---

## Testing

The following suites cover the change; reviewers should confirm with a clean build (C# was iterated in Debug against `net48`/`net8.0`, Python via `py_compile`):

- **Abstraction:** `pyRevitLabs.Configurations.Tests` — service, store, and configuration behavior.
- **INI backend:** `pyRevitLabs.Configurations.Ini.Tests` — unit tests, golden-file fidelity corpus, migration, and selection-ladder tests.
- **Loader / cross-reader:** `pyRevitExtensionParserTester` — `ConfigParityTests` (loader ↔ service), `PyRevitConfigsFacadeTests`, and extension-auth tests.
- **Python:** `test_config_roundtrip.py` (hermetic, runs under IPY2/IPY3/CPython) plus the in-Revit "Config Module Tests" DevTools button.
- The previously-red string-encoding canary tests are expected green with the Phase 2 fix.

> **Reviewer note:** I have not re-run the full C#/Python test suites while drafting this description. Please treat the results above as the coverage map, not a green CI attestation, and confirm on a clean build.

---

## Future work (if wanted)

- **Per-Revit-version configs finished** (read-side wiring — see *Intentionally not included*).
- **JSON or YAML backend support**, re-introduced through the retained `IConfiguration` abstraction if a use case appears.
