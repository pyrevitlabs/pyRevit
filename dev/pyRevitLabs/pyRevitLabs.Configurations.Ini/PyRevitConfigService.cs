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
    /// Returns the shared service for the given configuration name, building it on
    /// first request and caching it for the process.
    /// </summary>
    public static IConfigurationService GetShared(string? configurationName = null)
    {
        EnsureRegistered();
        return PyRevitConfigStore.GetShared(configurationName);
    }

    /// <summary>
    /// Drops the cached service(s) so the next access re-reads from disk.
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
        /// <summary>Machine-wide install: the writable %ProgramData% config is authoritative.</summary>
        AdminInstall,
        /// <summary>A read-only admin config: used directly, user changes are not saved.</summary>
        AdminLockdown,
        /// <summary>A writable admin config with no user config yet: copy it to the user, then use the copy.</summary>
        Seed,
        /// <summary>An existing per-user config.</summary>
        User,
        /// <summary>Nothing found: create a fresh per-user config.</summary>
        New,
    }

    /// <summary>
    /// Pure selection of the config tier from the observed facts, so the ladder is
    /// unit-testable without touching real machine directories. Order mirrors the
    /// documented Python precedence: Local, all-users install, admin seed/lockdown,
    /// user, new.
    /// </summary>
    public static ConfigSelection SelectConfig(
        bool localExists, bool isAllUsers, bool adminExists, bool adminWritable, bool userExists)
    {
        if (localExists)
            return ConfigSelection.Local;

        if (isAllUsers)
            return adminExists && !adminWritable ? ConfigSelection.AdminLockdown : ConfigSelection.AdminInstall;

        if (adminExists && adminWritable && !userExists)
            return ConfigSelection.Seed;

        if (adminExists && !adminWritable)
            return ConfigSelection.AdminLockdown;

        return userExists ? ConfigSelection.User : ConfigSelection.New;
    }

    private static IConfigurationService BuildConfigService(string configurationName)
    {
        // Repair a machine install whose settings are split across %APPDATA% and
        // %ProgramData%.
        MigrateSplitAdminConfigIfNeeded();

        string localConfig = PyRevitInstallScope.GetLocalConfigFilePath();
        string userConfig = PyRevitConfigPaths.UserConfigFilePath;
        string adminConfig = PyRevitConfigPaths.AdminConfigFilePath;

        bool adminExists = File.Exists(adminConfig);
        bool adminWritable = adminExists
            && !new FileInfo(adminConfig).IsReadOnly
            && IsFileWritable(adminConfig);

        var selection = SelectConfig(
            localExists: !string.IsNullOrEmpty(localConfig) && File.Exists(localConfig),
            isAllUsers: PyRevitInstallScope.IsAllUsersInstall(),
            adminExists: adminExists,
            adminWritable: adminWritable,
            userExists: File.Exists(userConfig));

        switch (selection)
        {
            case ConfigSelection.Local:
                return BuildWritable(localConfig, configurationName);

            case ConfigSelection.AdminInstall:
                // Machine-wide install: the %ProgramData% config is authoritative
                // and writable. Resolve through the shared scope helper so the CLI
                // and loader target the same file. No per-user seed in this mode.
                return BuildWritable(PyRevitInstallScope.GetActiveConfigFilePath(), configurationName);

            case ConfigSelection.AdminLockdown:
                ConfigurationDiagnostics.ReportInfo(
                    "Using read-only admin config " + adminConfig + "; user changes will not be saved.");
                return CreateConfiguration(adminConfig, true, configurationName);

            case ConfigSelection.Seed:
                SeedToUserConfig(adminConfig, userConfig);
                break;
        }

        // Seed, User, and New all resolve to the writable per-user config.
        return BuildWritable(userConfig, configurationName);
    }

    private static IConfigurationService BuildWritable(string configPath, string configurationName)
    {
        var service = CreateConfiguration(configPath, false, configurationName);
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
    /// </summary>
    internal static void MigrateSplitAdminConfigIfNeeded()
    {
        if (!PyRevitInstallScope.IsAllUsersInstall())
            return;

        string appDataConfig = PyRevitConfigPaths.UserConfigFilePath;
        if (!File.Exists(appDataConfig))
            return;

        string programDataConfig = PyRevitConfigPaths.AdminConfigFilePath;

        if (!File.Exists(programDataConfig))
        {
            try
            {
                string? dir = Path.GetDirectoryName(programDataConfig);
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);
                File.Copy(appDataConfig, programDataConfig);
            }
            catch (Exception ex)
            {
                ConfigurationDiagnostics.ReportWarning(
                    "Could not promote per-user config to the machine config: " + ex.Message);
            }
            return;
        }

        MergeAdminConfigFiles(appDataConfig, programDataConfig);
    }

    // Copies the clone registry (when absent) and any per-extension sections the
    // machine config is missing from the split per-user config.
    internal static void MergeAdminConfigFiles(string sourcePath, string targetPath)
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
        }
        catch (Exception ex)
        {
            ConfigurationDiagnostics.ReportWarning(
                "Could not merge split machine config: " + ex.Message);
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

    // Reports whether the current process can write the file by opening it for
    // read/write; the read-only attribute alone does not reflect ACL denials.
    private static bool IsFileWritable(string filePath)
    {
        try
        {
            using (new FileStream(filePath, FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite))
                return true;
        }
        catch
        {
            return false;
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

    private static IConfigurationService CreateConfiguration(string configPath, bool readOnly, string configurationName)
    {
        var builder = new ConfigurationBuilder(readOnly)
            .AddIniConfiguration(configPath, ConfigurationService.DefaultConfigurationName, readOnly);

        if (!string.IsNullOrEmpty(configurationName)
            && !string.Equals(configurationName, ConfigurationService.DefaultConfigurationName, StringComparison.Ordinal))
        {
            builder.AddIniConfiguration(
                Path.ChangeExtension(configPath, configurationName + IniConfiguration.DefaultFileExtension),
                configurationName, readOnly);
        }

        return builder.Build();
    }
}
