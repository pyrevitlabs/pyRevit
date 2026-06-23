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
    private static int _registered;

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
    /// Registers the INI-backed build factory with the store exactly once, so the
    /// first caller (loader or CLI) establishes the shared discovery.
    /// </summary>
    public static void EnsureRegistered()
    {
        if (Interlocked.Exchange(ref _registered, 1) == 0)
            PyRevitConfigStore.SetFactory(BuildConfigService);
    }

    private static IConfigurationService BuildConfigService(string configurationName)
    {
        // The per-user (%APPDATA%) config is the writable target and takes
        // priority. The all-users (%ProgramData%) config is used only when no
        // per-user config exists, and is opened read-only when this process
        // cannot write it.
        string userConfig = PyRevitConfigPaths.UserConfigFilePath;
        string adminConfig = PyRevitConfigPaths.AdminConfigFilePath;

        if (!File.Exists(userConfig) && File.Exists(adminConfig))
        {
            if (new FileInfo(adminConfig).IsReadOnly || !IsFileWritable(adminConfig))
            {
                ConfigurationDiagnostics.ReportInfo(
                    "Using read-only admin config " + adminConfig + "; user changes will not be saved.");
                return CreateConfiguration(adminConfig, true, configurationName);
            }

            SeedToUserConfig(adminConfig, userConfig);
        }

        var service = CreateConfiguration(userConfig, false, configurationName);
        RunMigration(service, userConfig);
        return service;
    }

    private static void RunMigration(IConfigurationService service, string configPath)
    {
        var migration = ConfigurationMigrator.Migrate(service);
        if (migration.BackupFailed)
        {
            ConfigurationDiagnostics.ReportWarning(
                "Skipped config migration for " + configPath +
                ": could not create a backup; will retry on a later load.");
        }
        else if (migration.ResetKeys.Count > 0)
        {
            ConfigurationDiagnostics.ReportInfo(
                "Repaired config " + configPath + ": reset " + migration.ResetKeys.Count +
                " invalid value(s); backup: " + migration.BackupPath);
            foreach (string key in migration.ResetKeys)
                ConfigurationDiagnostics.ReportWarning("Reset invalid config value: " + key);
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
