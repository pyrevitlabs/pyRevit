using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Builds and shares the pyRevit configuration service backed by the per-user
/// INI file. Discovery, all-users fallback, seeding, and one-time migration live
/// here (not in the heavier pyRevit libraries) so the loader, CLI, and script
/// engines resolve and share one in-process instance via
/// <see cref="PyRevitConfigStore"/>. Diagnostics route through
/// <see cref="ConfigurationDiagnostics"/>; a host wires those to its logger.
/// </summary>
public static class PyRevitConfigService
{
    /// <summary>
    /// Returns the shared service, building it on first request and caching it
    /// for the process.
    /// </summary>
    public static IConfigurationService GetShared()
    {
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
    public static void EnsureRegistered()
    {
        if (!PyRevitConfigStore.HasFactory)
            PyRevitConfigStore.SetFactory(BuildConfigService);
    }

    /// <summary>
    /// The configuration tier selected for the current install.
    /// </summary>
    public enum ConfigSelection
    {
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
        bool adminExists, bool adminLocked, bool userExists)
    {
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
    private static IConfigurationService BuildConfigService()
    {
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

        switch (selection)
        {
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

    private static IConfigurationService BuildWritable(string configPath)
    {
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
    internal static void MigrateSplitAdminConfigIfNeeded()
    {
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
    internal static void RepairSplitAdminConfig(string userConfigPath, string machineConfigPath)
    {
        if (!File.Exists(userConfigPath))
            return;

        if (!File.Exists(machineConfigPath))
        {
            try
            {
                string? dir = Path.GetDirectoryName(machineConfigPath);
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);
                File.Copy(userConfigPath, machineConfigPath);
            }
            catch (Exception ex)
            {
                ConfigurationDiagnostics.ReportWarning(
                    "Could not promote per-user config to the machine config: " + ex.Message);
                return;
            }

            RetireSplitUserConfig(userConfigPath);
            return;
        }

        if (MergeAdminConfigFiles(userConfigPath, machineConfigPath))
            RetireSplitUserConfig(userConfigPath);
    }

    /// <summary>
    /// Renames the per-user config aside once the machine config carries its
    /// settings. Without this the merge re-runs on every load, and a section
    /// deliberately removed from the machine config is restored from this file
    /// the next time pyRevit starts. A rename that fails leaves the file in place
    /// and the repair retries on a later load.
    /// </summary>
    private static void RetireSplitUserConfig(string userConfigPath)
    {
        string retiredPath = userConfigPath
            + ".split-admin." + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".bak";

        try
        {
            File.Move(userConfigPath, retiredPath);
        }
        catch (Exception ex)
        {
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
    /// machine config is missing from the split per-user config. Returns whether any
    /// setting was actually moved: only the source of a real copy has been superseded
    /// and may be retired. The merge carries the clone registry and extension
    /// sections alone, so a source that contributed nothing still holds the only copy
    /// of its other sections.
    /// </summary>
    internal static bool MergeAdminConfigFiles(string sourcePath, string targetPath)
    {
        try
        {
            var source = IniConfiguration.Create(sourcePath);
            var target = IniConfiguration.Create(targetPath);
            bool changed = false;

            if (CountRegisteredClones(target) == 0 && CountRegisteredClones(source) > 0)
            {
                string? clones = source.GetRawValueOrDefault(EnvironmentSectionName, ClonesKeyName, null);
                if (!string.IsNullOrEmpty(clones))
                {
                    target.SetRawValue(EnvironmentSectionName, ClonesKeyName, clones!);
                    changed = true;
                }
            }

            foreach (string section in source.GetSectionNames())
            {
                if (!IsExtensionConfigSection(section) || target.HasSection(section))
                    continue;

                foreach (string key in source.GetSectionOptionNames(section))
                {
                    string? raw = source.GetRawValueOrDefault(section, key, null);
                    if (raw != null)
                    {
                        target.SetRawValue(section, key, raw);
                        changed = true;
                    }
                }
            }

            if (changed)
                target.SaveConfiguration();

            return changed;
        }
        catch (Exception ex)
        {
            ConfigurationDiagnostics.ReportWarning(
                "Could not merge split machine config: " + ex.Message);
            return false;
        }
    }

    /// <summary>
    /// Number of clones the config records, or -1 when the value is present but
    /// will not decode. Unregistering the last clone leaves an empty map behind,
    /// so the key alone does not prove the registry survived; the -1 case keeps
    /// unreadable user data from being mistaken for an empty registry.
    /// </summary>
    private static int CountRegisteredClones(IConfiguration config)
    {
        if (!config.HasSectionKey(EnvironmentSectionName, ClonesKeyName))
            return 0;

        try
        {
            var clones = config.GetValue<Dictionary<string, string>>(
                EnvironmentSectionName, ClonesKeyName);
            return clones?.Count ?? 0;
        }
        catch
        {
            return -1;
        }
    }

    private static bool IsExtensionConfigSection(string sectionName)
    {
        return sectionName.EndsWith(ExtensionSectionSuffix, StringComparison.OrdinalIgnoreCase)
            || sectionName.EndsWith(LibrarySectionSuffix, StringComparison.OrdinalIgnoreCase);
    }

    private static void RunMigration(IConfigurationService service, string configPath)
    {
        var migration = ConfigurationMigrator.Migrate(service);
        if (migration.BackupFailed)
        {
            ConfigurationDiagnostics.ReportWarning(
                "Skipped config migration for " + configPath +
                ": could not create a backup; will retry on a later load.");
            return;
        }

        if (migration.ResetKeys.Count > 0)
        {
            ConfigurationDiagnostics.ReportInfo(
                "Repaired config " + configPath + ": reset " + migration.ResetKeys.Count +
                " invalid value(s); backup: " + migration.BackupPath);
            foreach (string key in migration.ResetKeys)
                ConfigurationDiagnostics.ReportWarning("Reset invalid config value: " + key);
        }

        if (migration.ConvertedKeys.Count > 0)
        {
            ConfigurationDiagnostics.ReportInfo(
                "Canonicalized " + migration.ConvertedKeys.Count + " legacy list value(s) in " +
                configPath + "; backup: " + migration.BackupPath);
            foreach (string key in migration.ConvertedKeys)
                ConfigurationDiagnostics.ReportInfo("Converted legacy list value: " + key);
        }
    }

    private static void SeedToUserConfig(string sourceFile, string targetFile)
    {
        try
        {
            string? dir = Path.GetDirectoryName(targetFile);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);
            File.WriteAllText(targetFile, File.ReadAllText(sourceFile));
        }
        catch (Exception ex)
        {
            ConfigurationDiagnostics.ReportWarning(
                "Could not seed admin config to user config: " + ex.Message);
        }
    }

    private static IConfigurationService CreateConfiguration(string configPath, bool readOnly)
    {
        return new ConfigurationBuilder(readOnly)
            .AddIniConfiguration(configPath, readOnly)
            .Build();
    }
}
