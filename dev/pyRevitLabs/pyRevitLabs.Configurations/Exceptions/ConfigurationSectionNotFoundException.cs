namespace pyRevitLabs.Configurations.Exceptions;

public sealed class ConfigurationSectionNotFoundException(string message, string sectionName)
    : ConfigurationException(message)
{
    public string SectionName { get; } = sectionName;

    public ConfigurationSectionNotFoundException(string sectionName)
        : this("", sectionName)
    {

    }
}