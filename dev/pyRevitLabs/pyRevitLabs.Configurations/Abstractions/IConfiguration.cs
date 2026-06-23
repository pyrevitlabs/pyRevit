namespace pyRevitLabs.Configurations.Abstractions;

public interface IConfiguration
{
    string ConfigurationPath { get; }

    bool HasSection(string sectionName);
    bool HasSectionKey(string sectionName, string keyName);

    IEnumerable<string> GetSectionNames();
    IEnumerable<string> GetSectionOptionNames(string sectionName);

    T GetValue<T>(string sectionName, string keyName);
    T? GetValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default);

    internal object GetValue(Type typeObject, string sectionName, string keyName);
    internal object? GetValueOrDefault(Type typeObject, string sectionName, string keyName, object? defaultValue = default);

    // Raw access to the stored value text (canonical JSON). Lets a caller that
    // does its own (de)serialization round-trip a value with a single encode.
    string? GetRawValueOrDefault(string sectionName, string keyName, string? defaultValue = null);
    void SetRawValue(string sectionName, string keyName, string rawValue);

    bool RemoveSection(string sectionName);
    bool RemoveOption(string sectionName, string keyName);

    void SetValue<T>(string sectionName, string keyName, T? value);

    void SaveConfiguration();
    void SaveConfiguration(string configurationPath);
}
