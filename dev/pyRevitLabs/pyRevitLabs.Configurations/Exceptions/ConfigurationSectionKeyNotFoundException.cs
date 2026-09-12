namespace pyRevitLabs.Configurations.Exceptions;

/// <summary>
/// A key was requested from a section that exists but does not contain it. Only
/// the strict readers throw this; the <c>*OrDefault</c> readers return their
/// default instead.
/// </summary>
/// <param name="message">Description of the failure.</param>
/// <param name="keyName">Key that was not found.</param>
/// <param name="sectionName">Section that was searched.</param>
public sealed class ConfigurationSectionKeyNotFoundException(string message, string keyName, string sectionName)
    : ConfigurationException(message)
{
    /// <summary>Key that was not found.</summary>
    public string KeyName { get; } = keyName;

    /// <summary>Section that was searched.</summary>
    public string SectionName { get; } = sectionName;

    /// <summary>Initializes the exception with an empty message.</summary>
    /// <param name="keyName">Key that was not found.</param>
    /// <param name="sectionName">Section that was searched.</param>
    public ConfigurationSectionKeyNotFoundException(string keyName, string sectionName)
        : this("", keyName, sectionName)
    {
    }
}
