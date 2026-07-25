using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Abstractions;

public interface IConfigurationService
{
    bool ReadOnly { get; }

    IEnumerable<string> ConfigurationNames { get; }
    IEnumerable<IConfiguration> Configurations { get; }
    IConfiguration this[string configurationName] { get; }

    CoreSection Core { get; }
    RoutesSection Routes { get; }
    TelemetrySection Telemetry { get; }
    EnvironmentSection Environment { get; }

    /// <summary>
    /// Reads the settings for a single extension from its dynamic
    /// "{name}.extension" or "{name}.lib" section, or null when neither section is
    /// present. Section names are resolved without the type suffix (e.g. pass
    /// "pyRevitCore", not "pyRevitCore.extension").
    /// </summary>
    ExtensionSection? GetExtensionSection(string extensionName);

    void ReloadLoadConfigurations();

    T GetSection<T>();
    void SaveSection<T>(string configurationName, T sectionValue);

    /// <summary>
    /// Writes a section's non-null properties into the backing store using the
    /// same key-mapping and default-skip rules as <see cref="SaveSection{T}"/>,
    /// but does not flush to disk. Lets an in-process caller batch many edits
    /// behind a single <see cref="IConfiguration.SaveConfiguration()"/>. CLI-style
    /// callers that must persist per command should keep using SaveSection.
    /// </summary>
    void ApplySection<T>(string configurationName, T sectionValue);

    void SetSectionKeyValue<T>(string configurationName, string sectionName, string keyName, T keyValue);
    T? GetSectionKeyValueOrDefault<T>(string configurationName, string sectionName, string keyName, T? defaultValue = default);
}
