using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationBuilder
{
    private readonly Dictionary<string, IConfiguration> _configurations = [];

    public ConfigurationBuilder AddConfigurationSource(string configurationName, IConfiguration configuration)
    {
        if (configuration == null)
            throw new ArgumentNullException(nameof(configuration));

        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));

        _configurations.Add(configurationName, configuration);
        return this;
    }

    public ConfigurationService Build()
    {
        return ConfigurationService.Create(_configurations);
    }
}