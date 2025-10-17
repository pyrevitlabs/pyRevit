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

    void ReloadLoadConfigurations();

    T GetSection<T>();
    void SaveSection<T>(string configurationName, T sectionValue);

    void SetSectionKeyValue<T>(string configurationName, string sectionName, string keyName, T keyValue);
    T? GetSectionKeyValueOrDefault<T>(string configurationName, string sectionName, string keyName, T? defaultValue = default);
}