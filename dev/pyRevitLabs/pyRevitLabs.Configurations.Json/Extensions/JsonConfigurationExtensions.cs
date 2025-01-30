namespace pyRevitLabs.Configurations.Json.Extensions;

public static class JsonConfigurationExtensions
{
    public static ConfigurationBuilder AddJsonConfiguration(
        this ConfigurationBuilder builder, string configurationPath, string conigurationName, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));
        
        if (string.IsNullOrWhiteSpace(conigurationName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(conigurationName));

        return builder.AddConfigurationSource(conigurationName, JsonConfiguration.Create(configurationPath, readOnly));
    }
}