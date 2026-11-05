namespace pyRevitLabs.Configurations.Exceptions;

/// <summary>
/// A section was requested that is not present in the configuration. Only the
/// strict readers throw this; the <c>*OrDefault</c> readers return their default
/// instead.
/// </summary>
/// <param name="message">Description of the failure.</param>
/// <param name="sectionName">Section that was not found.</param>
public sealed class ConfigurationSectionNotFoundException(string message, string sectionName)
    : ConfigurationException(message)
{
    /// <summary>Section that was not found.</summary>
    public string SectionName { get; } = sectionName;

    /// <summary>Initializes the exception with an empty message.</summary>
    /// <param name="sectionName">Section that was not found.</param>
    public ConfigurationSectionNotFoundException(string sectionName)
        : this("", sectionName)
    {

    }
}
