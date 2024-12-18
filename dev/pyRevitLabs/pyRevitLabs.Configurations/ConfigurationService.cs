using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationService(List<IConfiguration> configurations) : IConfiguration
{
    public List<IConfiguration> Configurations { get; } = configurations;
    public IEnumerable<IConfiguration> ReverseConfigurations => ((IEnumerable<IConfiguration>)Configurations).Reverse();

    public static IConfiguration Create(List<IConfiguration> configurations)
    {
        return new ConfigurationService(configurations);
    }

    public bool HasSection(string sectionName)
    {
        foreach (IConfiguration configuration in Configurations)
        {
            if (configuration.HasSection(sectionName))
            {
                return true;
            }
        }

        return false;
    }

    public bool HasSectionKey(string sectionName, string keyName)
    {
        foreach (IConfiguration configuration in ReverseConfigurations)
        {
            if (configuration.HasSectionKey(sectionName, keyName))
            {
                return true;
            }
        }

        return false;
    }

    public T GetValue<T>(string sectionName, string keyName)
    {
        foreach (IConfiguration configuration in ReverseConfigurations)
        {
            if (configuration.HasSectionKey(sectionName, keyName))
            {
                return configuration.GetValue<T>(sectionName, keyName);
            }
        }

        throw new ConfigurationException("Section not found");
    }

    public T? GetValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default)
    {
        foreach (IConfiguration configuration in ReverseConfigurations)
        {
            if (configuration.HasSectionKey(sectionName, keyName))
            {
                return configuration.GetValueOrDefault(sectionName, keyName, defaultValue);
            }
        }

        return defaultValue;
    }

    public bool RemoveValue(string sectionName, string keyName)
    {
        foreach (IConfiguration configuration in ReverseConfigurations)
        {
            if (configuration.HasSectionKey(sectionName, keyName))
            {
                return configuration.RemoveValue(sectionName, keyName);
            }
        }

        return false;
    }

    public void SetValue<T>(string sectionName, string keyName, T? value)
    {
        // default save in main config
        foreach (IConfiguration configuration in Configurations)
        {
            if (configuration.HasSectionKey(sectionName, keyName))
            {
                configuration.SetValue(sectionName, keyName, value);
                return;
            }
        }

        Configurations[0].SetValue(sectionName, keyName, value);
    }
}