using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Outcome of a <see cref="ConfigurationMigrator.Migrate"/> call. Carries the
/// reset keys and the backup path so the caller can log the repair (the
/// Configurations assembly has no logging dependency of its own).
/// </summary>
public sealed class ConfigurationMigrationResult {
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
        string? backupPath, IReadOnlyList<string> resetKeys, IReadOnlyList<string> convertedKeys) {
        Migrated = migrated;
        BackupFailed = backupFailed;
        FromVersion = fromVersion;
        BackupPath = backupPath;
        ResetKeys = resetKeys;
        ConvertedKeys = convertedKeys;
    }
}

/// <summary>
/// Canonicalizes legacy configuration values and stamps the schema version.
/// </summary>
public static class ConfigurationMigrator {
    /// <summary>
    /// Schema version this build writes. A configuration stamped with it is not
    /// rescanned for version reasons, though corruption is still repaired.
    /// </summary>
    public const int CurrentVersion = 1;

    private const string VersionSection = "core";
    private const string VersionKey = "config_version";
    private static readonly ConfigurationMigrationResult NotMigrated =
        new(false, false, 0, null, Array.Empty<string>(), Array.Empty<string>());

    /// <summary>
    /// Repairs the service's default configuration and stamps the schema version
    /// when needed. A clean, already-stamped config performs no write. Legacy
    /// single-quoted containers are rewritten as canonical JSON, which keeps the
    /// rewrite idempotent since the canonical form is no longer detected as
    /// legacy on a later load.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="service"/> is null.</exception>
    public static ConfigurationMigrationResult Migrate(IConfigurationService service) {
        if (service is null)
            throw new ArgumentNullException(nameof(service));

        IConfiguration config = service.Configuration;
        int version = ReadVersion(config);

        var legacyLists = FindLegacyListKeys(config);
        var legacyDicts = FindLegacyDictKeys(config);
        bool needsVersionStamp = version < CurrentVersion;
        if (legacyLists.Count == 0 && legacyDicts.Count == 0 && !needsVersionStamp)
            return NotMigrated;

        bool hasFile = !string.IsNullOrEmpty(config.ConfigurationPath)
                       && File.Exists(config.ConfigurationPath);
        string? backupPath = TryBackup(config.ConfigurationPath);
        if (hasFile && backupPath is null)
            return new ConfigurationMigrationResult(
                false, true, version, null, Array.Empty<string>(), Array.Empty<string>());

        var convertedKeys = new List<string>();
        foreach ((string section, string key, List<string> value) in legacyLists) {
            config.SetValue(section, key, value);
            convertedKeys.Add(section + "." + key);
        }

        foreach ((string section, string key, Dictionary<string, string> value) in legacyDicts) {
            config.SetValue(section, key, value);
            convertedKeys.Add(section + "." + key);
        }

        if (needsVersionStamp)
            config.SetValue(VersionSection, VersionKey, CurrentVersion);

        config.SaveConfiguration();
        return new ConfigurationMigrationResult(
            true, false, version, backupPath, Array.Empty<string>(), convertedKeys);
    }

    /// <summary>
    /// Finds List&lt;string&gt; keys stored in the legacy Python single-quoted form,
    /// returning the parsed value so migration can rewrite them as canonical JSON.
    /// Scans every section the file has, not just the built-in ones, so a
    /// custom/extension section carrying the same legacy form is repaired too.
    /// Reads raw (never decoded), so this scan alone does not report a legacy read.
    /// </summary>
    private static List<(string Section, string Key, List<string> Value)> FindLegacyListKeys(IConfiguration config) {
        var legacy = new List<(string, string, List<string>)>();

        foreach (string section in config.GetSectionNames()) {
            foreach (string key in config.GetSectionOptionNames(section)) {
                string? raw = config.GetRawValueOrDefault(section, key);
                if (raw != null
                    && LegacyListFormat.TryParseSingleQuoted(raw.Trim(), out List<string>? value)
                    && value != null) {
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
        IConfiguration config) {
        var legacy = new List<(string, string, Dictionary<string, string>)>();

        foreach (string section in config.GetSectionNames()) {
            foreach (string key in config.GetSectionOptionNames(section)) {
                string? raw = config.GetRawValueOrDefault(section, key);
                if (raw != null
                    && LegacyDictFormat.TryParseSingleQuoted(raw.Trim(), out Dictionary<string, string>? value)
                    && value != null) {
                    legacy.Add((section, key, value));
                }
            }
        }

        return legacy;
    }

    private static int ReadVersion(IConfiguration config) {
        string? raw = config.GetRawValueOrDefault(VersionSection, VersionKey);
        if (string.IsNullOrEmpty(raw))
            return 0;

        return int.TryParse(raw!.Trim().Trim('"'), out int version) ? version : 0;
    }

    private static string? TryBackup(string path) {
        try {
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
                return null;

            string backup = path + ".v0." + DateTime.Now.ToString("yyyyMMdd-HHmmss") + ".bak";
            if (!File.Exists(backup))
                File.Copy(path, backup);
            return backup;
        }
        catch {
            return null;
        }
    }

}
