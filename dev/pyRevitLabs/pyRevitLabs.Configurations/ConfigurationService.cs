using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationService(IDictionary<string, IConfiguration> configurations) :  IConfigurationService
{
    public IEnumerable<string> ConfigurationNames => Configurations.Keys;
    public IDictionary<string, IConfiguration> Configurations => configurations;
    
    public static IConfigurationService Create(IDictionary<string, IConfiguration> configurations)
    {
        return new ConfigurationService(configurations);
    }
}