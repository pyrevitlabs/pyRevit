namespace pyRevitLabs.Configurations.Json.Extensions;

public static class JsonConfigurationExtensions
{
    public static ConfigurationBuilder AddJsonConfiguration(this ConfigurationBuilder builder, string configurationPath, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));

        return builder.AddConfigurationSource(JsonConfiguration.Create(configurationPath, readOnly));
    }
}