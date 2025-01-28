using System.Collections;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public sealed class ConfigurationService : IConfigurationService
{
    private readonly List<ConfigurationName> _names;
    private readonly IDictionary<string, IConfiguration> _configurations;

    public const string DefaultConfigurationName = "Default";

    internal ConfigurationService(bool readOnly,
        List<ConfigurationName> names,
        IDictionary<string, IConfiguration> configurations)
    {
        _names = names;
        _configurations = configurations;

        ReadOnly = readOnly;

        // TODO: Change behavior
        ReloadLoadConfigurations();
    }

    internal static IConfigurationService Create(bool readOnly, List<ConfigurationName> names,
        IDictionary<string, IConfiguration> configurations)
    {
        return new ConfigurationService(readOnly, names, configurations);
    }

    public bool ReadOnly { get; }

    public IEnumerable<string> ConfigurationNames => _configurations.Keys;

    public IEnumerable<IConfiguration> Configurations => _names
        .Select(item => _configurations[item.Name!])
        .ToArray();

    public IConfiguration this[string configurationName]
    {
        get
        {
            if (string.IsNullOrWhiteSpace(configurationName))
                throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationName));
            
            if (!_configurations.TryGetValue(configurationName, out IConfiguration? configuration))
                throw new InvalidOperationException($"Configuration {configurationName} not found");

            return configuration;
        }
    }

    public CoreSection Core { get; private set; } = new();
    public RoutesSection Routes { get; private set; } = new();
    public TelemetrySection Telemetry { get; private set; } = new();
    public EnvironmentSection Environment { get; private set; } = new();
    
    public void ReloadLoadConfigurations()
    {
        Core = GetSection<CoreSection>();
        Routes = GetSection<RoutesSection>();
        Telemetry = GetSection<TelemetrySection>();
        Environment = GetSection<EnvironmentSection>();
    }

    public T GetSection<T>()
    {
        Type configurationType = typeof(T);
        return (T) CreateSection(configurationType, Configurations.Reverse().ToArray());
    }

    public void SaveSection<T>(string configurationName, T sectionValue)
    {
        if (sectionValue is null)
            throw new ArgumentNullException(nameof(sectionValue));

        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationName));

        if (!_configurations.TryGetValue(configurationName, out IConfiguration? configuration))
            throw new ArgumentException($"Configuration with name {configurationName} not found");
        
        Type configurationType = typeof(T);
        SaveSection(configurationType, sectionValue, configuration);
    }

    public void SetSectionKeyValue<T>(string configurationName, string sectionName, string keyName, T keyValue)
    {
        if (keyValue == null)
            throw new ArgumentNullException(nameof(keyValue));
        
        if (string.IsNullOrEmpty(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));
        
        if (string.IsNullOrEmpty(sectionName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(sectionName));
       
        if (string.IsNullOrEmpty(keyName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(keyName));
        
        if (!_configurations.TryGetValue(configurationName, out IConfiguration? configuration))
            throw new ArgumentException($"Configuration with name {configurationName} not found");
        
        configuration.SetValue(sectionName, keyName, keyValue);
    }

    public T? GetSectionKeyValueOrDefault<T>(
        string configurationName,
        string sectionName,
        string keyName,
        T? defaultValue = default)
    {
        if (string.IsNullOrEmpty(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));

        if (string.IsNullOrEmpty(sectionName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(sectionName));

        if (string.IsNullOrEmpty(keyName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(keyName));

        if (!_configurations.TryGetValue(configurationName, out IConfiguration? configuration))
            throw new ArgumentException($"Configuration with name {configurationName} not found");

        return configuration.GetValue<T>(sectionName, keyName);
    }

    private static void SaveSection(Type configurationType, object? sectionValue, IConfiguration configuration)
    {
        string sectionName =
            GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName ?? configurationType.Name;
        
        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;
            object? keyValue = propertyInfo.GetValue(sectionValue);
            
            if (keyValue is null)
                configuration.RemoveOption(sectionName, keyName);
            else
                configuration.SetValue(sectionName, keyName, keyValue);
        }
        
        configuration.SaveConfiguration();
    }

    private static object CreateSection(Type configurationType, params IConfiguration[] configurations)
    {
        string sectionName =
            GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName ?? configurationType.Name;

        var sectionConfiguration = Activator.CreateInstance(configurationType);

        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;

            object? keyValue = GetKeyValue(configurations, propertyInfo, sectionName, keyName);
            propertyInfo.SetValue(sectionConfiguration, keyValue ?? propertyInfo.GetValue(sectionConfiguration));
        }

        return sectionConfiguration!;
    }

    private static object? GetKeyValue(
        IEnumerable<IConfiguration> configurations,
        PropertyInfo propertyInfo,
        string sectionName, string keyName)
    {
        return configurations
            .Select(item=> item.GetValueOrDefault(propertyInfo.PropertyType, sectionName, keyName))
            .FirstOrDefault(item => item != default);
    }
    
    private static IEnumerable<PropertyInfo> GetProperties(Type configurationType)
    {
        var flags = BindingFlags.Instance | BindingFlags.Public;
        return configurationType.GetProperties(flags)
            .Where(item => item.CanWrite && item.CanRead);
    }

    private static T? GetCustomAttribute<T>(MemberInfo memberInfo) where T : Attribute
    {
        return memberInfo.GetCustomAttributes(typeof(T), false).FirstOrDefault() as T;
    }
}