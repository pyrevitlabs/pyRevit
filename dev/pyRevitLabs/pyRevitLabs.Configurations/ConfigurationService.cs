using System.Collections;
using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationService : IConfigurationService
{
    private readonly List<ConfigurationName> _names;
    private readonly IDictionary<string, IConfiguration> _configurations;

    public static readonly string DefaultConfigurationName = "Default";

    internal ConfigurationService(
        List<ConfigurationName> names,
        IDictionary<string, IConfiguration> configurations)
    {
        _names = names;
        _configurations = configurations;
    }

    internal static IConfigurationService Create(
        List<ConfigurationName> names,
        IDictionary<string, IConfiguration> configurations)
    {
        return new ConfigurationService(names, configurations);
    }

    public IEnumerable<string> ConfigurationNames => _configurations.Keys;
    public IEnumerable<IConfiguration> Configurations => _configurations.Values;

    public CoreSection? Core { get; private set; }
    public RoutesSection? Routes { get; private set; }
    public TelemetrySection? Telemetry { get; private set; }

    public void LoadConfigurations()
    {
        Core = GetConfiguration<CoreSection>();
        Routes = GetConfiguration<RoutesSection>();
        Telemetry = GetConfiguration<TelemetrySection>();
    }

    internal T GetConfiguration<T>()
    {
        return GetConfigurationImpl<T>(DefaultConfigurationName);
    }

    internal T GetConfiguration<T>(string configurationName)
    {
        return GetConfigurationImpl<T>(configurationName);
    }

    internal T? GetConfigurationOrDefault<T>(T? defaultValue = default)
    {
        return GetConfigurationOrDefault(DefaultConfigurationName, defaultValue);
    }

    internal T? GetConfigurationOrDefault<T>(string configurationName, T? defaultValue = default)
    {
        try
        {
            return GetConfigurationImpl<T>(configurationName);
        }
        catch
        {
            return defaultValue;
        }
    }

    private T GetConfigurationImpl<T>(string configurationName)
    {
        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationName));

        if (!_configurations.TryGetValue(configurationName, out var configuration))
            throw new ArgumentException($"Configuration with name {configurationName} not found");

        Type configurationType = typeof(T);

        string sectionName =
            GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName ?? configurationType.Name;

        var sectionConfiguration = Activator.CreateInstance<T>();
        foreach (var propertyInfo in configurationType.GetProperties(BindingFlags.Instance | BindingFlags.Public))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;

            object? keyValue = configuration.GetValueOrDefault(
                propertyInfo.PropertyType, sectionName, keyName, propertyInfo.GetValue(sectionConfiguration));

            propertyInfo.SetValue(sectionConfiguration, keyValue);
        }

        return sectionConfiguration;
    }

    private static T? GetCustomAttribute<T>(MemberInfo memberInfo) where T : Attribute
    {
        return memberInfo.GetCustomAttributes(typeof(T), false).FirstOrDefault() as T;
    }
}