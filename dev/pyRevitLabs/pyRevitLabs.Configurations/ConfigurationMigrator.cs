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
    /// <summary>True when the configuration was changed and written.</summary>
    public bool Migrated { get; }

    /// <summary>
    /// True when a repair was needed but skipped because the existing file could
    /// not be backed up. Nothing was changed; the repair retries on a later load.
    /// </summary>
    public bool BackupFailed { get; }

    /// <summary>
    /// Schema version found before the repair. Zero for a configuration that
    /// carries no version stamp.
    /// </summary>
    public int FromVersion { get; }

    /// <summary>
    /// Path of the backup taken before mutating, or null when there was no
    /// existing file to back up.
    /// </summary>
    public string? BackupPath { get; }

    /// <summary>
    /// Keys removed because their stored value could not be read. The affected
    /// settings revert to their defaults, so a caller should surface these.
    /// </summary>
    public IReadOnlyList<string> ResetKeys { get; }

    /// <summary>Keys rewritten from a legacy encoding to the canonical form.</summary>
    public IReadOnlyList<string> ConvertedKeys { get; }

    internal ConfigurationMigrationResult(
        bool migrated, bool backupFailed, int fromVersion,
        string? backupPath, IReadOnlyList<string> resetKeys, IReadOnlyList<string> convertedKeys)
    {
        Migrated = migrated;
        BackupFailed = backupFailed;
        FromVersion = fromVersion;
        BackupPath = backupPath;
        ResetKeys = resetKeys;
        ConvertedKeys = convertedKeys;
    }
}

/// <summary>
/// Repairs a configuration on load: drops typed-section values that no longer
/// parse to their declared type and telemetry fields blown up by
/// escape-doubling, and stamps a schema version. The repair runs whenever such
/// a value is present on a writable config (so corruption introduced after the
/// first run still self-heals); a config with nothing to fix is a no-op.
/// </summary>
public static class ConfigurationMigrator
{
    /// <summary>
    /// Schema version this build writes. A configuration stamped with it is not
    /// rescanned for version reasons, though corruption is still repaired.
    /// </summary>
    public const int CurrentVersion = 1;

    private const string VersionSection = "core";
    private const string VersionKey = "config_version";
    private const int MaxFieldLength = 8192;

    private static readonly ConfigurationMigrationResult NotMigrated =
        new(false, false, 0, null, Array.Empty<string>(), Array.Empty<string>());

    private static readonly Type[] KnownSections =
    {
        typeof(CoreSection), typeof(RoutesSection),
        typeof(TelemetrySection), typeof(EnvironmentSection),
    };

    /// <summary>
    /// Telemetry fields that escape-doubling degraded, paired with whether a
    /// forward slash counts as an artifact in that field rather than content.
    /// It does for the URLs, whose wreckage retains the separator slashes; in a
    /// directory path a slash is part of the value.
    /// </summary>
    private static readonly (string Section, string Key, bool SlashIsArtifact)[] BloatFields =
    {
        ("telemetry", "telemetry_file_dir", false),
        ("telemetry", "telemetry_server_url", true),
        ("telemetry", "apptelemetry_server_url", true),
    };

    /// <summary>
    /// Repairs the service's default configuration and stamps the schema version
    /// when needed. A clean, already-stamped config performs no write. Legacy
    /// single-quoted containers are rewritten as canonical JSON, which keeps the
    /// rewrite idempotent since the canonical form is no longer detected as
    /// legacy on a later load.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="service"/> is null.</exception>
    public static ConfigurationMigrationResult Migrate(IConfigurationService service)
    {
        if (service is null)
            throw new ArgumentNullException(nameof(service));

        IConfiguration config = service.Configuration;
        int version = ReadVersion(config);

        var badKeys = FindUnreadableKeys(config);
        var legacyLists = FindLegacyListKeys(config);
        var legacyDicts = FindLegacyDictKeys(config);
        bool needsVersionStamp = version < CurrentVersion;
        if (badKeys.Count == 0 && legacyLists.Count == 0 && legacyDicts.Count == 0 && !needsVersionStamp)
            return NotMigrated;

        bool hasFile = !string.IsNullOrEmpty(config.ConfigurationPath)
                       && File.Exists(config.ConfigurationPath);
        string? backupPath = TryBackup(config.ConfigurationPath);
        if (hasFile && backupPath is null)
            return new ConfigurationMigrationResult(
                false, true, version, null, Array.Empty<string>(), Array.Empty<string>());

        var resetKeys = new List<string>();
        foreach ((string section, string key) in badKeys)
        {
            config.RemoveOption(section, key);
            resetKeys.Add(section + "." + key);
        }

        var convertedKeys = new List<string>();
        foreach ((string section, string key, List<string> value) in legacyLists)
        {
            config.SetValue(section, key, value);
            convertedKeys.Add(section + "." + key);
        }

        foreach ((string section, string key, Dictionary<string, string> value) in legacyDicts)
        {
            config.SetValue(section, key, value);
            convertedKeys.Add(section + "." + key);
        }

        if (needsVersionStamp)
            config.SetValue(VersionSection, VersionKey, CurrentVersion);

        config.SaveConfiguration();
        return new ConfigurationMigrationResult(true, false, version, backupPath, resetKeys, convertedKeys);
    }

    /// <summary>
    /// Finds present keys whose stored value cannot be read: typed-section
    /// values that fail to parse to their declared type, and telemetry fields
    /// left as escape-doubling wreckage.
    /// </summary>
    private static List<(string Section, string Key)> FindUnreadableKeys(IConfiguration config)
    {
        var bad = new List<(string, string)>();

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
                    bad.Add((section, key));
                }
            }
        }

        foreach ((string section, string key, bool slashIsArtifact) in BloatFields)
        {
            string? raw = config.GetRawValueOrDefault(section, key);
            if (raw != null && IsTelemetryWreckage(raw, slashIsArtifact))
                bad.Add((section, key));
        }

        return bad;
    }

    /// <summary>
    /// Whether a stored telemetry value is escape-doubling wreckage rather than a
    /// setting. Extreme length is one shape of it. The other is a value made up
    /// entirely of quote and escape artifacts, which is what an empty field
    /// degrades into after repeated re-encoding: it stays far below any length
    /// threshold and carries nothing recoverable. An absent or canonical-empty
    /// value is never wreckage, and neither is a value with no quote at all,
    /// which is a legacy bare path or URL stored unencoded.
    /// </summary>
    private static bool IsTelemetryWreckage(string raw, bool slashIsArtifact)
    {
        if (raw.Length > MaxFieldLength)
            return true;

        string compact = new(raw.Where(c => !char.IsWhiteSpace(c)).ToArray());

        if (compact.Length == 0 || compact == "\"\"")
            return false;

        if (compact.IndexOf('"') < 0 && compact.IndexOf('\'') < 0)
            return false;

        return compact.All(c => IsArtifact(c, slashIsArtifact));
    }

    private static bool IsArtifact(char value, bool slashIsArtifact) =>
        value is '"' or '\'' or '\\' || (slashIsArtifact && value == '/');

    /// <summary>
    /// Finds List&lt;string&gt; keys stored in the legacy Python single-quoted form,
    /// returning the parsed value so migration can rewrite them as canonical JSON.
    /// Scans every section the file has, not just the built-in ones, so a
    /// custom/extension section carrying the same legacy form is repaired too.
    /// Reads raw (never decoded), so this scan alone does not report a legacy read.
    /// </summary>
    private static List<(string Section, string Key, List<string> Value)> FindLegacyListKeys(IConfiguration config)
    {
        var legacy = new List<(string, string, List<string>)>();

        foreach (string section in config.GetSectionNames())
        {
            foreach (string key in config.GetSectionOptionNames(section))
            {
                string? raw = config.GetRawValueOrDefault(section, key);
                if (raw != null
                    && LegacyListFormat.TryParseSingleQuoted(raw.Trim(), out List<string>? value)
                    && value != null)
                {
                    legacy.Add((section, key, value));
                }
            }
        }

        return legacy;
    }

    /// <summary>
    /// Finds Dictionary&lt;string,string&gt; keys stored in the legacy Python
    /// single-quoted form, returning the parsed value so migration can rewrite
    /// them as canonical JSON. Scans every section the file has, not just the
    /// built-in ones, so a custom/extension section carrying the same legacy form
    /// is repaired too. Reads raw (never decoded), so this scan alone does not
    /// report a legacy read.
    /// </summary>
    private static List<(string Section, string Key, Dictionary<string, string> Value)> FindLegacyDictKeys(
        IConfiguration config)
    {
        var legacy = new List<(string, string, Dictionary<string, string>)>();

        foreach (string section in config.GetSectionNames())
        {
            foreach (string key in config.GetSectionOptionNames(section))
            {
                string? raw = config.GetRawValueOrDefault(section, key);
                if (raw != null
                    && LegacyDictFormat.TryParseSingleQuoted(raw.Trim(), out Dictionary<string, string>? value)
                    && value != null)
                {
                    legacy.Add((section, key, value));
                }
            }
        }

        return legacy;
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
