namespace pyRevitLabs.Configurations.Yaml.Extensions;

public static class YamlConfigurationExtensions
{
    public static ConfigurationBuilder AddYamlConfiguration(
        this ConfigurationBuilder builder, string configurationPath, string conigurationName, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));
        
        if (string.IsNullOrWhiteSpace(conigurationName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(conigurationName));

        return builder.AddConfigurationSource(conigurationName, YamlConfiguration.Create(configurationPath, readOnly));
    }
}