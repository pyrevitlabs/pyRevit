namespace pyRevitLabs.Configurations.Exceptions;

/// <inheritdoc />
public class ConfigurationException(string message) : Exception(message)
{
    public ConfigurationException() : this("")
    {

    }
}