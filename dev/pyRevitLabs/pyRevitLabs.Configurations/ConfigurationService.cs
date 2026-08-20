using System.Collections;
using System.ComponentModel;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Default <see cref="IConfigurationService"/>: materializes typed section
/// records from the backing configuration by reflecting over the section
/// attributes, and caches those records until a write advances the store.
/// Build one with <see cref="ConfigurationBuilder"/>.
/// </summary>
public sealed class ConfigurationService : IConfigurationService
{
    private readonly IConfiguration _configuration;

    internal ConfigurationService(bool readOnly, IConfiguration configuration)
    {
        _configuration = configuration;

        ReadOnly = readOnly;
    }

    internal static IConfigurationService Create(bool readOnly, IConfiguration configuration)
    {
        return new ConfigurationService(readOnly, configuration);
    }

    /// <inheritdoc />
    public bool ReadOnly { get; }

    /// <inheritdoc />
    public IConfiguration Configuration => _configuration;

    /// <summary>
    /// Guards every read (snapshot rebuild) and write against the backing
    /// <see cref="IConfiguration"/>, which is not itself thread-safe.
    /// </summary>
    private readonly object _syncLock = new();
    private long _snapshotRevision = -1;
    private CoreSection _core = new();
    private RoutesSection _routes = new();
    private TelemetrySection _telemetry = new();
    private EnvironmentSection _environment = new();

    /// <inheritdoc />
    public CoreSection Core { get { EnsureSnapshots(); return _core; } }

    /// <inheritdoc />
    public RoutesSection Routes { get { EnsureSnapshots(); return _routes; } }

    /// <inheritdoc />
    public TelemetrySection Telemetry { get { EnsureSnapshots(); return _telemetry; } }

    /// <inheritdoc />
    public EnvironmentSection Environment { get { EnsureSnapshots(); return _environment; } }

    /// <inheritdoc />
    public void ReloadLoadConfigurations()
    {
        lock (_syncLock)
            _snapshotRevision = -1;
    }

    /// <summary>
    /// Rebuilds the typed snapshots when the backing store has moved on, so a
    /// reader never observes state older than the last write. The revision only
    /// ever increases, so any write changes it.
    /// </summary>
    private void EnsureSnapshots()
    {
        lock (_syncLock)
        {
            long revision = _configuration.Revision;
            if (revision == _snapshotRevision)
                return;

            _core = GetSection<CoreSection>();
            _routes = GetSection<RoutesSection>();
            _telemetry = GetSection<TelemetrySection>();
            _environment = GetSection<EnvironmentSection>();
            _snapshotRevision = revision;
        }
    }

    /// <inheritdoc />
    public T GetSection<T>()
    {
        Type configurationType = typeof(T);
        return (T) CreateSection(configurationType, null, _configuration);
    }

    /// <summary>
    /// Suffixes of the per-extension section an extension's settings may live
    /// in, in precedence order: the .extension form wins over .lib.
    /// </summary>
    private static readonly string[] ExtensionSectionSuffixes = { ".extension", ".lib" };

    /// <inheritdoc />
    public ExtensionSection? GetExtensionSection(string extensionName)
    {
        if (string.IsNullOrWhiteSpace(extensionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(extensionName));

        foreach (string suffix in ExtensionSectionSuffixes)
        {
            string sectionName = extensionName + suffix;
            if (_configuration.HasSection(sectionName))
                return (ExtensionSection) CreateSection(typeof(ExtensionSection), sectionName, _configuration);
        }

        return null;
    }

    /// <inheritdoc />
    public void SaveSection<T>(T sectionValue)
    {
        EnsureWritable(sectionValue);
        lock (_syncLock)
        {
            ApplySection(typeof(T), sectionValue!, _configuration);
            _configuration.SaveConfiguration();
        }
    }

    /// <inheritdoc />
    public void ApplySection<T>(T sectionValue)
    {
        EnsureWritable(sectionValue);
        lock (_syncLock)
            ApplySection(typeof(T), sectionValue!, _configuration);
    }

    private void EnsureWritable(object? sectionValue)
    {
        if (sectionValue is null)
            throw new ArgumentNullException(nameof(sectionValue));

        EnsureWritable();
    }

    /// <summary>
    /// Refuses a write before anything is mutated. A read-only configuration
    /// silently discards its flush, so allowing the mutation through would leave
    /// the caller reporting success while the in-memory state disagrees with the
    /// file.
    /// </summary>
    private void EnsureWritable()
    {
        if (ReadOnly || _configuration.ReadOnly)
            throw new ConfigurationReadOnlyException(
                $"Configuration {_configuration.ConfigurationPath} is read-only; changes cannot be saved.");
    }

    /// <inheritdoc />
    public void SetSectionKeyValue<T>(string sectionName, string keyName, T keyValue)
    {
        if (keyValue == null)
            throw new ArgumentNullException(nameof(keyValue));

        if (string.IsNullOrEmpty(sectionName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(sectionName));

        if (string.IsNullOrEmpty(keyName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(keyName));

        EnsureWritable();

        lock (_syncLock)
        {
            _configuration.SetValue(sectionName, keyName, keyValue);
            _configuration.SaveConfiguration();
        }
    }

    /// <inheritdoc />
    public T? GetSectionKeyValueOrDefault<T>(
        string sectionName,
        string keyName,
        T? defaultValue = default)
    {
        if (string.IsNullOrEmpty(sectionName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(sectionName));

        if (string.IsNullOrEmpty(keyName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(keyName));

        return _configuration.GetValueOrDefault<T>(sectionName, keyName, defaultValue);
    }

    /// <summary>
    /// Writes changed, non-default properties into the store without flushing.
    /// The public <see cref="SaveSection{T}"/> adds the
    /// <see cref="IConfiguration.SaveConfiguration()"/> call; <see cref="ApplySection{T}"/>
    /// omits it so an in-process caller can batch edits behind one flush.
    /// </summary>
    private static void ApplySection(Type configurationType, object sectionValue, IConfiguration configuration)
    {
        string sectionName =
            GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName ?? configurationType.Name;

        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;

            object? storedValue = GetKeyValue(configuration, propertyInfo, sectionName, keyName);

            object? keyValue = propertyInfo.GetValue(sectionValue);
            if (keyValue is null)
                continue;
            if (storedValue is null && ValuesEqual(keyValue, GetPropertyDefault(propertyInfo)))
                continue;
            if (!ValuesEqual(keyValue, storedValue))
                configuration.SetValue(sectionName, keyName, keyValue);
        }
    }

    /// <summary>
    /// Compares two section-property values for the purpose of skipping an
    /// unchanged write. <see cref="object.Equals(object, object)"/> is reference
    /// equality for <c>List&lt;string&gt;</c>/<c>Dictionary&lt;string,string&gt;</c>
    /// section properties, so a byte-identical container value would otherwise
    /// always look "changed" and always be written: dictionaries are compared by
    /// key/value content (order-independent), other enumerables by element
    /// sequence, and everything else falls back to ordinary equality.
    /// </summary>
    private static bool ValuesEqual(object? left, object? right)
    {
        if (left is IDictionary leftDict && right is IDictionary rightDict)
            return DictionariesEqual(leftDict, rightDict);

        if (left is IEnumerable leftEnumerable && right is IEnumerable rightEnumerable
            && left is not string && right is not string)
            return leftEnumerable.Cast<object>().SequenceEqual(rightEnumerable.Cast<object>());

        return Equals(left, right);
    }

    private static bool DictionariesEqual(IDictionary left, IDictionary right)
    {
        if (left.Count != right.Count)
            return false;

        foreach (DictionaryEntry entry in left)
        {
            if (!right.Contains(entry.Key) || !Equals(right[entry.Key], entry.Value))
                return false;
        }

        return true;
    }

    private static object CreateSection(
        Type configurationType, string? sectionNameOverride, IConfiguration configuration)
    {
        string sectionName = sectionNameOverride
            ?? GetCustomAttribute<SectionNameAttribute>(configurationType)?.SectionName
            ?? configurationType.Name;

        var sectionConfiguration = Activator.CreateInstance(configurationType);

        foreach (var propertyInfo in GetProperties(configurationType))
        {
            string keyName = GetCustomAttribute<KeyNameAttribute>(propertyInfo)?.KeyName ?? propertyInfo.Name;

            object? keyValue = GetKeyValue(configuration, propertyInfo, sectionName, keyName);

            if (keyValue is null && GetCustomAttribute<LegacyKeyNameAttribute>(propertyInfo) is { } legacyKeyName)
                keyValue = GetKeyValue(configuration, propertyInfo, sectionName, legacyKeyName.KeyName);

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
        IConfiguration configuration,
        PropertyInfo propertyInfo,
        string sectionName, string keyName)
    {
        return configuration.GetValueOrDefault(propertyInfo.PropertyType, sectionName, keyName);
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
