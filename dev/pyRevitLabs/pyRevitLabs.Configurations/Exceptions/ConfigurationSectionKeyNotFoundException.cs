namespace pyRevitLabs.Configurations.Exceptions;

public sealed class ConfigurationSectionKeyNotFoundException(string message, string keyName, string sectionName)
    : ConfigurationException(message)
{
    public string KeyName { get; } = keyName;
    public string SectionName { get; } = sectionName;

    public ConfigurationSectionKeyNotFoundException(string keyName, string sectionName)
        : this("", keyName, sectionName)
    {
    }
}