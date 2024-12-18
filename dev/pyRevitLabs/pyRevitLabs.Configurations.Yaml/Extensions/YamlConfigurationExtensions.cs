namespace pyRevitLabs.Configurations.Yaml.Extensions;

public static class YamlConfigurationExtensions
{
    public static ConfigurationBuilder AddYamlConfiguration(this ConfigurationBuilder builder, string configurationPath, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));

        return builder.AddConfigurationSource(YamlConfiguration.Create(configurationPath, readOnly));
    }
}