using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Security;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Builds and shares the pyRevit configuration service backed by the per-user
/// INI file. Discovery, all-users fallback, seeding, and one-time migration live
/// here (not in the heavier pyRevit libraries) so the loader, CLI, and script
/// engines resolve and share one in-process instance via
/// <see cref="PyRevitConfigStore"/>. Diagnostics route through
/// <see cref="ConfigurationDiagnostics"/>; a host wires those to its logger.
/// </summary>
public static class PyRevitConfigService {
    /// <summary>
    /// Returns the shared service, building it on first request and caching it
    /// for the process.
    /// </summary>
    public static IConfigurationService GetShared() {
        EnsureRegistered();
        return PyRevitConfigStore.GetShared();
    }

    /// <summary>
    /// Drops the cached service so the next access re-reads from disk.
    /// </summary>
    public static void Reload() => PyRevitConfigStore.Reload();

    /// <summary>
    /// Ensures the INI-backed build factory is registered with the store so the
    /// first caller (loader or CLI) establishes the shared discovery. Gated on the
    /// store's live factory state, so a <see cref="PyRevitConfigStore.Reset"/>
    /// (e.g. test isolation) is recoverable: the next access re-installs the
    /// factory instead of leaving the store empty. An already-installed factory
    /// is never replaced.
    /// </summary>
    public static void EnsureRegistered() {
        if (!PyRevitConfigStore.HasFactory)
            PyRevitConfigStore.SetFactory(BuildConfigService);
    }

    /// <summary>
    /// The configuration tier selected for the current install.
    /// </summary>
    public enum ConfigSelection {
        /// <summary>A config file inside the running clone (developer override).</summary>
        Local,
        /// <summary>
        /// Elevated process on a machine-wide install: the %ProgramData% config is
        /// authoritative, used directly and writable, with no per-user seed in
        /// this mode.
        /// </summary>
        AdminInstall,
        /// <summary>An admin-locked config: used directly, user changes are not saved.</summary>
        AdminLockdown,
        /// <summary>An admin config with no user config yet: copy it to the user, then use the copy.</summary>
        Seed,
        /// <summary>An existing per-user config.</summary>
        User,
        /// <summary>Nothing found: create a fresh per-user config.</summary>
        New,
    }

    /// <summary>
    /// Pure selection of the config tier from the observed facts, so the ladder is
    /// unit-testable without touching real machine directories. Order mirrors the
    /// documented Python precedence: Local, admin lock, elevated all-users install,
    /// seed, user, new.
    /// <para>
    /// <paramref name="adminLocked"/> is the DOS ReadOnly attribute on the machine
    /// config and nothing else. Whether the process happens to be able to write that
    /// file is deliberately not an input: an admin install seeds a config a standard
    /// user cannot write, and treating that as a lockdown would hand every such user
    /// a config that silently discards their settings.
    /// </para>
    /// <para>
    /// A deliberate admin lock binds every install scope and every process, and
    /// is checked first. Only an elevated process (installer / admin CLI) is
    /// treated as owning %ProgramData%; a standard user recreating a deleted
    /// machine config would otherwise own it and lock out everyone else sharing
    /// the machine.
    /// </para>
    /// </summary>
    public static ConfigSelection SelectConfig(
        bool localExists, bool isAllUsers, bool isElevated,
        bool adminExists, bool adminLocked, bool userExists) {
        if (localExists)
            return ConfigSelection.Local;

        if (adminExists && adminLocked)
            return ConfigSelection.AdminLockdown;

        if (isAllUsers && isElevated)
            return ConfigSelection.AdminInstall;

        if (adminExists && !userExists)
            return ConfigSelection.Seed;

        return userExists ? ConfigSelection.User : ConfigSelection.New;
    }

    /// <summary>
    /// Builds the process's shared configuration service: repairs a split admin
    /// install, then selects and returns the appropriate config tier. The Seed,
    /// User, and New tiers all resolve to the same writable per-user config,
    /// after any seeding the Seed tier needs.
    /// </summary>
    private static IConfigurationService BuildConfigService() {
        MigrateSplitAdminConfigIfNeeded();

        string localConfig = PyRevitInstallScope.GetLocalConfigFilePath();
        string userConfig = PyRevitConfigPaths.UserConfigFilePath;
        string adminConfig = PyRevitConfigPaths.AdminConfigFilePath;

        bool adminExists = File.Exists(adminConfig);

        var selection = SelectConfig(
            localExists: !string.IsNullOrEmpty(localConfig) && File.Exists(localConfig),
            isAllUsers: PyRevitInstallScope.IsAllUsersInstall(),
            isElevated: PyRevitInstallScope.IsElevatedProcess(),
            adminExists: adminExists,
            adminLocked: adminExists && PyRevitInstallScope.HasReadOnlyAttribute(adminConfig),
            userExists: File.Exists(userConfig));

        switch (selection) {
            case ConfigSelection.Local:
                return BuildWritable(localConfig);

            case ConfigSelection.AdminInstall:
                return BuildWritable(adminConfig);

            case ConfigSelection.AdminLockdown:
                ConfigurationDiagnostics.ReportInfo(
                    "Using read-only admin config " + adminConfig + "; user changes will not be saved.");
                return CreateConfiguration(adminConfig, true);

            case ConfigSelection.Seed:
                SeedToUserConfig(adminConfig, userConfig);
                break;
        }

        return BuildWritable(userConfig);
    }

    private static IConfigurationService BuildWritable(string configPath) {
        var service = CreateConfiguration(configPath, false);
        RunMigration(service, configPath);
        return service;
    }

    private const string EnvironmentSectionName = "environment";
    private const string ClonesKeyName = "clones";
    private const string ExtensionSectionSuffix = ".extension";
    private const string LibrarySectionSuffix = ".lib";

    /// <summary>
    /// One-time repair for machine installs whose clone registry and per-extension
    /// settings live in the %APPDATA% (per-user) config rather than the machine
    /// config. On an all-users install it promotes a lone per-user
    /// config to %ProgramData%, or merges the clone registry and any missing
    /// extension sections into an existing %ProgramData% config. No-op otherwise.
    /// <para>
    /// Restricted to elevated processes, which are the only ones that own the
    /// machine config. For everyone else the %APPDATA% config this repair consumes
    /// is their own active config, and moving it aside would discard the settings
    /// they are running on.
    /// </para>
    /// </summary>
    internal static void MigrateSplitAdminConfigIfNeeded() {
        if (!PyRevitInstallScope.IsAllUsersInstall() || !PyRevitInstallScope.IsElevatedProcess())
            return;

        RepairSplitAdminConfig(
            PyRevitConfigPaths.UserConfigFilePath, PyRevitConfigPaths.AdminConfigFilePath);
    }

    /// <summary>
    /// The repair itself, over explicit paths so it can be exercised without
    /// install-scope state. Retires the per-user config only once settings have
    /// actually moved out of it, which is what makes the repair run once rather
    /// than on every load. A config with nothing left to contribute is left alone.
    /// </summary>
    /// <remarks>
    /// Promotion copies minus the credential keys rather than copying and then
    /// stripping, because copy-then-strip would publish a plaintext token to a
    /// file every local user can read for as long as the strip takes, and
    /// indefinitely if the strip fails.
    /// </remarks>
    internal static void RepairSplitAdminConfig(string userConfigPath, string machineConfigPath) {
        if (!File.Exists(userConfigPath))
            return;

        if (!File.Exists(machineConfigPath)) {
            if (!CopyConfigWithoutCredentialKeys(userConfigPath, machineConfigPath)) {
                ConfigurationDiagnostics.ReportWarning(
                    "Could not promote per-user config to the machine config: "
                    + userConfigPath);
                return;
            }

            FileAttributes attributes = File.GetAttributes(machineConfigPath);
            if ((attributes & FileAttributes.ReadOnly) != 0)
                File.SetAttributes(machineConfigPath, attributes & ~FileAttributes.ReadOnly);

            RetireSplitUserConfigIfSuperseded(userConfigPath, ContainsCredentialKeys(userConfigPath));
            return;
        }

        if (MergeAdminConfigFiles(userConfigPath, machineConfigPath, out bool credentialsLeftBehind))
            RetireSplitUserConfigIfSuperseded(userConfigPath, credentialsLeftBehind);
    }

    /// <summary>
    /// Renames the per-user config aside once the machine config has superseded
    /// everything in it.
    /// </summary>
    /// <remarks>
    /// <paramref name="stillHoldsCredentials"/> suppresses the rename. The
    /// per-user file is the only copy of a credential that is scoped to that
    /// user, so retiring it would destroy a working token and leave the user
    /// re-entering it. For those users the split layout stays, which is the
    /// correct trade and is not temporary: the credential outlives every
    /// subsequent merge.
    /// </remarks>
    private static void RetireSplitUserConfigIfSuperseded(
        string userConfigPath, bool stillHoldsCredentials) {
        if (stillHoldsCredentials) {
            ConfigurationDiagnostics.ReportInfo(
                "Kept the per-user config at " + userConfigPath
                + " because it still holds an extension credential. Credentials are never "
                + "copied to the machine config, so that file is the only remaining copy.");
            return;
        }

        RetireSplitUserConfig(userConfigPath);
    }

    /// <summary>
    /// Renames the per-user config aside once the machine config carries its
    /// settings. Without this the merge re-runs on every load, and a section
    /// deliberately removed from the machine config is restored from this file
    /// the next time pyRevit starts. A rename that fails leaves the file in place
    /// and the repair retries on a later load.
    /// </summary>
    private static void RetireSplitUserConfig(string userConfigPath) {
        string retiredPath = userConfigPath
            + ".split-admin." + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".bak";

        try {
            File.Move(userConfigPath, retiredPath);
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Merged the per-user config into the machine config but could not retire "
                + userConfigPath + ": " + ex.Message + ". The merge will run again on a later load.");
            return;
        }

        ConfigurationDiagnostics.ReportInfo(
            "Merged per-user config into the machine config; the original was kept at "
            + retiredPath + ".");
    }

    /// <summary>
    /// Copies the clone registry (when absent) and any per-extension sections the
    /// machine config is missing from the split per-user config. Credential keys
    /// are never copied and are stripped from the machine config, because a
    /// user-scope DPAPI blob is unreadable to every other user of the machine and
    /// a legacy plaintext token is readable by all of them.
    /// </summary>
    /// <param name="sourcePath">The split per-user config.</param>
    /// <param name="targetPath">The machine config.</param>
    /// <param name="credentialsLeftBehind">
    /// Set when the source held credential material that was deliberately not
    /// copied, which means the source is still the only place that credential
    /// exists and must not be retired.
    /// </param>
    /// <returns>
    /// Whether any setting was actually moved: only the source of a real copy has
    /// been superseded and may be retired. The merge carries the clone registry and
    /// extension sections alone, so a source that contributed nothing still holds
    /// the only copy of its other sections.
    /// </returns>
    internal static bool MergeAdminConfigFiles(
        string sourcePath, string targetPath, out bool credentialsLeftBehind) {
        credentialsLeftBehind = false;
        try {
            var source = IniConfiguration.Create(sourcePath);
            var target = IniConfiguration.Create(targetPath);
            bool changed = false;
            bool moved = false;

            if (CountRegisteredClones(target) == 0 && CountRegisteredClones(source) > 0) {
                string? clones = source.GetRawValueOrDefault(EnvironmentSectionName, ClonesKeyName, null);
                if (!string.IsNullOrEmpty(clones)) {
                    target.SetRawValue(EnvironmentSectionName, ClonesKeyName, clones!);
                    changed = moved = true;
                }
            }

            foreach (string section in source.GetSectionNames()) {
                if (!IsExtensionConfigSection(section))
                    continue;

                bool copyingSection = !target.HasSection(section);
                foreach (string key in source.GetSectionOptionNames(section)) {
                    if (IsCredentialKey(key)) {
                        if (source.GetRawValueOrDefault(section, key, null) is not null)
                            credentialsLeftBehind = true;
                        continue;
                    }

                    if (!copyingSection)
                        continue;

                    string? raw = source.GetRawValueOrDefault(section, key, null);
                    if (raw != null) {
                        target.SetRawValue(section, key, raw);
                        changed = moved = true;
                    }
                }
            }

            if (StripPlaintextCredentialKeys(target))
                changed = true;

            if (changed)
                target.SaveConfiguration();

            return moved;
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not merge split machine config: " + ex.Message);
            return false;
        }
    }

    /// <summary>
    /// Copies a config file, omitting every key that can hold extension credential
    /// material.
    /// </summary>
    /// <remarks>
    /// Used by the promote path so a machine-scope file is never, even briefly,
    /// holding credential material. The sealed key is omitted here even though it
    /// is unreadable to other users: an elevated <c>--persist-credentials</c> run
    /// on a machine install writes the token to ProgramData, so that file is the
    /// only copy and dropping it would silently break the extension.
    /// </remarks>
    /// <returns>Whether the copy was written.</returns>
    private static bool CopyConfigWithoutCredentialKeys(string sourcePath, string targetPath) {
        try {
            var source = IniConfiguration.Create(sourcePath);
            var target = IniConfiguration.Create(targetPath);

            foreach (string section in source.GetSectionNames()) {
                if (IsExtensionConfigSection(section))
                    target.AddSection(section);

                foreach (string key in source.GetSectionOptionNames(section)) {
                    if (IsCredentialKey(key))
                        continue;
                    string? raw = source.GetRawValueOrDefault(section, key, null);
                    if (raw != null)
                        target.SetRawValue(section, key, raw);
                }
            }

            target.SaveConfiguration();
            return true;
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not copy the per-user config to the machine config: " + ex.Message);
            return false;
        }
    }

    /// <summary>
    /// Whether a config key can hold extension credential material, sealed or
    /// plaintext.
    /// </summary>
    private static bool IsCredentialKey(string keyName) {
        foreach (string credentialKey in ExtensionCredentialProtector.AllConfigKeyNames) {
            if (string.Equals(keyName, credentialKey, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        return false;
    }

    /// <summary>
    /// Whether a config key holds a *plaintext* extension credential, i.e. one a
    /// machine-scope file must never carry.
    /// </summary>
    /// <remarks>
    /// Deliberately excludes the sealed key. A sealed blob is bound to the Windows
    /// profile that wrote it, so other users of the machine cannot read it, and
    /// for a machine install it is the only copy of the token.
    /// </remarks>
    private static bool IsPlaintextCredentialKey(string keyName) {
        if (string.Equals(
                keyName,
                ExtensionCredentialProtector.LegacyTokenKeyName,
                StringComparison.OrdinalIgnoreCase))
            return true;
        if (string.Equals(
                keyName,
                ExtensionCredentialProtector.LegacyPasswordKeyName,
                StringComparison.OrdinalIgnoreCase))
            return true;
        return string.Equals(
            keyName,
            ExtensionCredentialProtector.LegacyUsernameKeyName,
            StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>
    /// Removes every plaintext credential key from every extension section of a
    /// config.
    /// </summary>
    /// <remarks>
    /// Applied to the machine config, and to the per-user config that a fresh
    /// install seeds itself from, so a token that a pre-sealing build wrote in the
    /// clear does not keep being handed between the two.
    /// </remarks>
    /// <returns>Whether anything was removed.</returns>
    private static bool StripPlaintextCredentialKeys(IConfiguration configuration) {
        bool removed = false;
        foreach (string section in configuration.GetSectionNames()) {
            if (!IsExtensionConfigSection(section))
                continue;

            foreach (string key in configuration.GetSectionOptionNames(section)) {
                if (IsPlaintextCredentialKey(key) && configuration.RemoveOption(section, key)) {
                    removed = true;
                    ConfigurationDiagnostics.ReportWarning(
                        "Removed plaintext extension credential key \"" + key + "\" from the \""
                        + section + "\" config section. A config file is not a safe place for a "
                        + "token; it is sealed instead.");
                }
            }
        }
        return removed;
    }

    /// <summary>
    /// Removes plaintext credential keys from a config file, if it has any.
    /// </summary>
    private static bool StripPlaintextCredentialKeysFromFile(string configPath) {
        if (!File.Exists(configPath))
            return false;

        try {
            var configuration = IniConfiguration.Create(configPath);
            if (!StripPlaintextCredentialKeys(configuration))
                return false;
            configuration.SaveConfiguration();
            return true;
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not strip plaintext credential keys from " + configPath + ": " + ex.Message);
            return false;
        }
    }

    /// <summary>
    /// Whether a per-user config holds extension credential material of any kind.
    /// </summary>
    /// <remarks>
    /// A config that cannot be inspected counts as holding one: retiring a file
    /// we merely failed to read risks destroying a token we did not see.
    /// </remarks>
    private static bool ContainsCredentialKeys(string configPath) {
        if (!File.Exists(configPath))
            return false;

        try {
            var configuration = IniConfiguration.Create(configPath);
            foreach (string section in configuration.GetSectionNames()) {
                if (!IsExtensionConfigSection(section))
                    continue;
                foreach (string key in configuration.GetSectionOptionNames(section)) {
                    if (IsCredentialKey(key) && configuration.GetRawValueOrDefault(section, key, null) is not null)
                        return true;
                }
            }
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not inspect " + configPath + " for credentials: " + ex.Message);
            return true;
        }

        return false;
    }

    /// <summary>
    /// Number of clones the config records, or -1 when the value is present but
    /// will not decode. Unregistering the last clone leaves an empty map behind,
    /// so the key alone does not prove the registry survived; the -1 case keeps
    /// unreadable user data from being mistaken for an empty registry.
    /// </summary>
    private static int CountRegisteredClones(IConfiguration config) {
        if (!config.HasSectionKey(EnvironmentSectionName, ClonesKeyName))
            return 0;

        try {
            var clones = config.GetValue<Dictionary<string, string>>(
                EnvironmentSectionName, ClonesKeyName);
            return clones?.Count ?? 0;
        }
        catch {
            return -1;
        }
    }

    private static bool IsExtensionConfigSection(string sectionName) {
        return sectionName.EndsWith(ExtensionSectionSuffix, StringComparison.OrdinalIgnoreCase)
            || sectionName.EndsWith(LibrarySectionSuffix, StringComparison.OrdinalIgnoreCase);
    }

    private static void RunMigration(IConfigurationService service, string configPath) {
        ConfigurationMigrationResult migration;
        try {
            migration = ConfigurationMigrator.Migrate(service);
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Skipped config migration for " + configPath + ": " + ex.Message);
            return;
        }

        if (migration.BackupFailed) {
            ConfigurationDiagnostics.ReportWarning(
                "Skipped config migration for " + configPath +
                ": could not create a backup; will retry on a later load.");
            return;
        }

        if (migration.ConvertedKeys.Count > 0) {
            ConfigurationDiagnostics.ReportInfo(
                "Canonicalized " + migration.ConvertedKeys.Count + " legacy list value(s) in " +
                configPath + "; backup: " + migration.BackupPath);
            foreach (string key in migration.ConvertedKeys)
                ConfigurationDiagnostics.ReportInfo("Converted legacy list value: " + key);
        }
    }

    /// <summary>
    /// Copy the machine config to a per-user location, then drop the plaintext
    /// credential keys.
    /// </summary>
    /// <remarks>
    /// A machine config written by a pre-sealing build can still hold a plaintext
    /// token, which the copy would carry verbatim into this user's config. The
    /// sealed key is left alone: it is bound to the profile that wrote it and
    /// means nothing here, and it is the admin's own copy to remove, not ours.
    /// </remarks>
    private static void SeedToUserConfig(string sourceFile, string targetFile) {
        try {
            string? dir = Path.GetDirectoryName(targetFile);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);
            File.WriteAllText(targetFile, File.ReadAllText(sourceFile));
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not seed admin config to user config: " + ex.Message);
            return;
        }

        StripPlaintextCredentialKeysFromFile(targetFile);
    }

    private static IConfigurationService CreateConfiguration(string configPath, bool readOnly) {
        return new ConfigurationBuilder(readOnly)
            .AddIniConfiguration(configPath, readOnly)
            .Build();
    }
}
