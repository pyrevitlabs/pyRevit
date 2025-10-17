using System.Collections.Specialized;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationBuilder
{
    private readonly bool _readOnly;
    private readonly List<ConfigurationName> _names = [];
    private readonly Dictionary<string, IConfiguration> _configurations = [];

    public ConfigurationBuilder(bool readOnly)
    {
        _readOnly = readOnly;
    }

    public ConfigurationBuilder AddConfigurationSource(string configurationName, IConfiguration configuration)
    {
        if (configuration == null)
            throw new ArgumentNullException(nameof(configuration));

        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));

        _names.Add(new ConfigurationName() {Index = _configurations.Count, Name = configurationName});
        _configurations.Add(configurationName, configuration);
        
        return this;
    }

    public IConfigurationService Build()
    {
        return ConfigurationService.Create(_readOnly, _names, _configurations);
    }
}