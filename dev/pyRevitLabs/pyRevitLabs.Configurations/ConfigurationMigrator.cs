using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Outcome of a <see cref="ConfigurationMigrator.Migrate"/> call. Carries the
/// reset keys and the backup path so the caller can log the repair (the
/// Configurations assembly has no logging dependency of its own).
/// </summary>
public sealed class ConfigurationMigrationResult
{
    public bool Migrated { get; }
    public bool BackupFailed { get; }
    public int FromVersion { get; }
    public string? BackupPath { get; }
    public IReadOnlyList<string> ResetKeys { get; }

    internal ConfigurationMigrationResult(
        bool migrated, bool backupFailed, int fromVersion,
        string? backupPath, IReadOnlyList<string> resetKeys)
    {
        Migrated = migrated;
        BackupFailed = backupFailed;
        FromVersion = fromVersion;
        BackupPath = backupPath;
        ResetKeys = resetKeys;
    }
}

/// <summary>
/// Version-gated, one-time repair of an existing configuration. Removes
/// typed-section values that no longer parse to their declared type and
/// telemetry fields blown up by escape-doubling, then stamps the schema
/// version so the migration does not run again.
/// </summary>
public static class ConfigurationMigrator
{
    public const int CurrentVersion = 1;

    private const string VersionSection = "core";
    private const string VersionKey = "config_version";
    private const int MaxFieldLength = 8192;

    private static readonly ConfigurationMigrationResult NotMigrated =
        new(false, false, 0, null, Array.Empty<string>());

    private static readonly Type[] KnownSections =
    {
        typeof(CoreSection), typeof(RoutesSection),
        typeof(TelemetrySection), typeof(EnvironmentSection),
    };

    private static readonly (string Section, string Key)[] BloatFields =
    {
        ("telemetry", "telemetry_file_dir"),
        ("telemetry", "telemetry_server_url"),
        ("telemetry", "apptelemetry_server_url"),
    };

    /// <summary>
    /// Migrates the service's default configuration when its stamped version is
    /// older than <see cref="CurrentVersion"/>.
    /// </summary>
    public static ConfigurationMigrationResult Migrate(IConfigurationService service)
    {
        if (service is null)
            throw new ArgumentNullException(nameof(service));

        IConfiguration config = service[ConfigurationService.DefaultConfigurationName];
        int version = ReadVersion(config);
        if (version >= CurrentVersion)
            return NotMigrated;

        // Back up before mutating. If the file exists but cannot be backed up,
        // skip this run so a recoverable copy is preserved; the migration
        // retries on a later load once the cause (disk, ACLs) is resolved.
        bool hasFile = !string.IsNullOrEmpty(config.ConfigurationPath)
                       && File.Exists(config.ConfigurationPath);
        string? backupPath = TryBackup(config.ConfigurationPath);
        if (hasFile && backupPath is null)
            return new ConfigurationMigrationResult(false, true, version, null, Array.Empty<string>());

        var resetKeys = new List<string>();

        // Drop typed-section values that no longer parse to their declared type;
        // reads then fall back to the section default.
        foreach (Type sectionType in KnownSections)
        {
            string section = SectionName(sectionType);
            foreach (PropertyInfo property in GetProperties(sectionType))
            {
                string key = KeyName(property);
                if (!config.HasSectionKey(section, key))
                    continue;

                try
                {
                    config.GetValue(property.PropertyType, section, key);
                }
                catch
                {
                    config.RemoveOption(section, key);
                    resetKeys.Add(section + "." + key);
                }
            }
        }

        // Drop telemetry fields whose length indicates an escape-doubling blow-up.
        foreach ((string section, string key) in BloatFields)
        {
            string? raw = config.GetRawValueOrDefault(section, key);
            if (raw != null && raw.Length > MaxFieldLength)
            {
                config.RemoveOption(section, key);
                resetKeys.Add(section + "." + key);
            }
        }

        config.SetValue(VersionSection, VersionKey, CurrentVersion);
        config.SaveConfiguration();
        return new ConfigurationMigrationResult(true, false, version, backupPath, resetKeys);
    }

    private static int ReadVersion(IConfiguration config)
    {
        string? raw = config.GetRawValueOrDefault(VersionSection, VersionKey);
        if (string.IsNullOrEmpty(raw))
            return 0;

        return int.TryParse(raw!.Trim().Trim('"'), out int version) ? version : 0;
    }

    private static string? TryBackup(string path)
    {
        try
        {
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
                return null;

            string backup = path + ".v0." + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".bak";
            if (!File.Exists(backup))
                File.Copy(path, backup);
            return backup;
        }
        catch
        {
            return null;
        }
    }

    private static IEnumerable<PropertyInfo> GetProperties(Type sectionType) =>
        sectionType.GetProperties(BindingFlags.Public | BindingFlags.Instance)
            .Where(p => p.CanRead && p.CanWrite);

    private static string SectionName(Type sectionType) =>
        (sectionType.GetCustomAttributes(typeof(SectionNameAttribute), false)
            .FirstOrDefault() as SectionNameAttribute)?.SectionName ?? sectionType.Name;

    private static string KeyName(PropertyInfo property) =>
        (property.GetCustomAttributes(typeof(KeyNameAttribute), false)
            .FirstOrDefault() as KeyNameAttribute)?.KeyName ?? property.Name;
}
