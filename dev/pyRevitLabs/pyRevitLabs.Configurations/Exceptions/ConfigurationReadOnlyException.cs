namespace pyRevitLabs.Configurations.Exceptions;

/// <summary>
/// A write was attempted against a read-only (e.g. admin-locked) configuration.
/// Callers that want to treat this differently from other configuration
/// failures — for example, reporting it as a benign no-op rather than a hard
/// error — can catch this subtype specifically.
/// </summary>
/// <param name="message">Description of the failure.</param>
public sealed class ConfigurationReadOnlyException(string message) : ConfigurationException(message)
{
    /// <summary>Initializes the exception with an empty message.</summary>
    public ConfigurationReadOnlyException() : this("")
    {

    }
}
