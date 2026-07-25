using System.Collections;
using System.ComponentModel;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Configurations.Sections;

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

    private readonly object _snapshotLock = new();
    private long _snapshotRevision = -1;
    private CoreSection _core = new();
    private RoutesSection _routes = new();
    private TelemetrySection _telemetry = new();
    private EnvironmentSection _environment = new();

    public CoreSection Core { get { EnsureSnapshots(); return _core; } }
    public RoutesSection Routes { get { EnsureSnapshots(); return _routes; } }
    public TelemetrySection Telemetry { get { EnsureSnapshots(); return _telemetry; } }
    public EnvironmentSection Environment { get { EnsureSnapshots(); return _environment; } }

    /// <summary>
    /// Forces the typed section snapshots to be rebuilt on next access. Writes
    /// made through this service or its configurations are picked up on their
    /// own, so this is only needed when a configuration is replaced wholesale.
    /// </summary>
    public void ReloadLoadConfigurations()
    {
        lock (_snapshotLock)
            _snapshotRevision = -1;
    }

    // Sum of per-configuration revisions: each only ever increases, so any write
    // to any backing configuration changes the total.
    private long CurrentRevision()
    {
        long total = 0;
        foreach (IConfiguration configuration in Configurations)
            total += configuration.Revision;

        return total;
    }

    // Rebuilds the typed snapshots when the backing store has moved on, so a
    // reader never observes state older than the last write.
    private void EnsureSnapshots()
    {
        lock (_snapshotLock)
        {
            long revision = CurrentRevision();
            if (revision == _snapshotRevision)
                return;

            _core = GetSection<CoreSection>();
            _routes = GetSection<RoutesSection>();
            _telemetry = GetSection<TelemetrySection>();
            _environment = GetSection<EnvironmentSection>();
            _snapshotRevision = revision;
        }
    }

    public T GetSection<T>()
    {
        Type configurationType = typeof(T);
        return (T) CreateSection(configurationType, null, Configurations.Reverse().ToArray());
    }

    // Extension settings live in a per-extension section named for the extension
    // plus its type suffix; the .extension form takes precedence over .lib.
    private static readonly string[] ExtensionSectionSuffixes = { ".extension", ".lib" };

    public ExtensionSection? GetExtensionSection(string extensionName)
    {
        if (string.IsNullOrWhiteSpace(extensionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(extensionName));

        foreach (string suffix in ExtensionSectionSuffixes)
        {
            string sectionName = extensionName + suffix;
            if (Configurations.Any(configuration => configuration.HasSection(sectionName)))
                return (ExtensionSection) CreateSection(
                    typeof(ExtensionSection), sectionName, Configurations.Reverse().ToArray());
        }

        return null;
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
        configuration.SaveConfiguration();
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

        return configuration.GetValueOrDefault<T>(sectionName, keyName, defaultValue);
    }

    private void SaveSection(Type configurationType, object sectionValue, IConfiguration configuration)
    {
        string sectionName =
            GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName ?? configurationType.Name;

        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;
            object? storedValue = GetKeyValue(Configurations, propertyInfo, sectionName, keyName);

            object? keyValue = propertyInfo.GetValue(sectionValue);
            // A null property is treated as "not set by this caller": its
            // existing stored value is left untouched. Only non-null properties
            // are written.
            if (keyValue is null)
                continue;
            // Don't materialize a section's declared default that isn't already
            // stored: it resolves from the default on read, and writing it would
            // pin the user to today's default. Fully-defaulted snapshots (e.g.
            // the Python save path) would otherwise persist every default key.
            if (storedValue is null && keyValue.Equals(GetPropertyDefault(propertyInfo)))
                continue;
            if (!keyValue.Equals(storedValue))
                configuration.SetValue(sectionName, keyName, keyValue);
        }

        configuration.SaveConfiguration();
    }

    private static object CreateSection(
        Type configurationType, string? sectionNameOverride, params IConfiguration[] configurations)
    {
        string sectionName = sectionNameOverride
            ?? GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName
            ?? configurationType.Name;

        var sectionConfiguration = Activator.CreateInstance(configurationType);

        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;

            object? keyValue = GetKeyValue(configurations, propertyInfo, sectionName, keyName);
            // Apply the declared default for keys absent from every config, so a
            // section's defaults live on the read path rather than as field
            // initializers (which would otherwise be written back on a sparse save).
            propertyInfo.SetValue(sectionConfiguration,
                keyValue ?? GetPropertyDefault(propertyInfo) ?? propertyInfo.GetValue(sectionConfiguration));
        }

        return sectionConfiguration!;
    }

    private static object? GetPropertyDefault(PropertyInfo propertyInfo)
    {
        if (GetCustomAttribute<DefaultValueAttribute>(propertyInfo) is { } defaultAttr)
            return defaultAttr.Value;

        Type type = propertyInfo.PropertyType;
        if (type.IsGenericType)
        {
            Type definition = type.GetGenericTypeDefinition();
            if (definition == typeof(List<>) || definition == typeof(Dictionary<,>))
                return Activator.CreateInstance(type);
        }

        return null;
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
