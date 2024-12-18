using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationBuilder
{
    private readonly List<IConfiguration> _configurations = [];
    
    public ConfigurationBuilder AddConfigurationSource(IConfiguration configuration)
    {
        if (configuration == null) 
            throw new ArgumentNullException(nameof(configuration));
        
        _configurations.Add(configuration);
        return this;
    }

    public IConfiguration Build()
    {
        return ConfigurationService.Create(_configurations);
    }
}