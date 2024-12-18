using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationService(IDictionary<string, IConfiguration> configurations)
{
    public IDictionary<string, IConfiguration> Configurations { get; } = configurations;

    public static ConfigurationService Create(IDictionary<string, IConfiguration> configurations)
    {
        return new ConfigurationService(configurations);
    }
}