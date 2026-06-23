using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations;

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
    /// older than <see cref="CurrentVersion"/>. Returns true when a migration ran.
    /// </summary>
    public static bool Migrate(IConfigurationService service)
    {
        if (service is null)
            throw new ArgumentNullException(nameof(service));

        IConfiguration config = service[ConfigurationService.DefaultConfigurationName];
        if (ReadVersion(config) >= CurrentVersion)
            return false;

        TryBackup(config.ConfigurationPath);

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
                }
            }
        }

        // Drop telemetry fields whose length indicates an escape-doubling blow-up.
        foreach ((string section, string key) in BloatFields)
        {
            string? raw = config.GetRawValueOrDefault(section, key);
            if (raw != null && raw.Length > MaxFieldLength)
                config.RemoveOption(section, key);
        }

        config.SetValue(VersionSection, VersionKey, CurrentVersion);
        config.SaveConfiguration();
        return true;
    }

    private static int ReadVersion(IConfiguration config)
    {
        string? raw = config.GetRawValueOrDefault(VersionSection, VersionKey);
        if (string.IsNullOrEmpty(raw))
            return 0;

        return int.TryParse(raw!.Trim().Trim('"'), out int version) ? version : 0;
    }

    private static void TryBackup(string path)
    {
        try
        {
            if (!string.IsNullOrEmpty(path) && File.Exists(path))
            {
                string backup = path + ".v0." + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".bak";
                if (!File.Exists(backup))
                    File.Copy(path, backup);
            }
        }
        catch
        {
            // best effort: a missing backup must not block migration
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
