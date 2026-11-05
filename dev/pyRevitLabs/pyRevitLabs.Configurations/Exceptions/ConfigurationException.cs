namespace pyRevitLabs.Configurations.Exceptions;

/// <summary>
/// Base type for configuration failures: a value that cannot be decoded, a
/// missing section or key, or a write aimed at a read-only configuration. Catch
/// this to handle any of them uniformly.
/// </summary>
/// <param name="message">Description of the failure.</param>
public class ConfigurationException(string message) : Exception(message)
{
    /// <summary>Initializes the exception with an empty message.</summary>
    public ConfigurationException() : this("")
    {

    }
}
