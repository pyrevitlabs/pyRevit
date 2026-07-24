using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

public abstract class ConfigurationBase : IConfiguration
{
    protected readonly string _configurationPath;

    protected ConfigurationBase(string configurationPath, bool readOnly)
    {
        _configurationPath = configurationPath;
        ReadOnly = readOnly;
    }

    public bool ReadOnly { get; }
    public string ConfigurationPath => _configurationPath;

    private long _revision;

    /// <inheritdoc />
    public long Revision => Interlocked.Read(ref _revision);

    private void MarkChanged() => Interlocked.Increment(ref _revision);

    public void SaveConfiguration()
    {
        if (ReadOnly)
        {
            return;
        }

        SaveConfigurationImpl();
    }

    public void SaveConfiguration(string configurationPath)
    {
        if (configurationPath == null)
            throw new ArgumentNullException(nameof(configurationPath));

        SaveConfigurationImpl(configurationPath);
    }

    /// <inheritdoc />
    public bool HasSection(string sectionName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        return HasSectionImpl(sectionName);
    }

    /// <inheritdoc />
    public bool HasSectionKey(string sectionName, string keyName)
    {
        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        return HasSectionKeyImpl(sectionName, keyName);
    }

    public IEnumerable<string> GetSectionNames()
    {
        return GetSectionNamesImpl();
    }

    public IEnumerable<string> GetSectionOptionNames(string sectionName)
    {
        if (!HasSection(sectionName))
        {
            return Enumerable.Empty<string>();
        }

        return GetSectionOptionNamesImpl(sectionName);
    }

    /// <inheritdoc />
    public bool AddSection(string sectionName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (HasSection(sectionName) || !AddSectionImpl(sectionName))
            return false;

        MarkChanged();
        return true;
    }

    public bool RemoveSection(string sectionName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));


        bool result = HasSection(sectionName)
                      && RemoveSectionImpl(sectionName);

        if (result)
            MarkChanged();

        return result;
    }

    /// <inheritdoc />
    public bool RemoveOption(string sectionName, string keyName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        bool result = HasSection(sectionName)
                      && HasSectionKey(sectionName, keyName)
                      && RemoveOptionImpl(sectionName, keyName);

        if (result)
            MarkChanged();

        return result;
    }

    /// <inheritdoc />
    public T GetValue<T>(string sectionName, string keyName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        if (!HasSection(sectionName))
            throw new ConfigurationSectionNotFoundException(sectionName);

        if (!HasSectionKey(sectionName, keyName))
            throw new ConfigurationSectionKeyNotFoundException(keyName, sectionName);

        return (T) GetValueImpl(typeof(T), sectionName, keyName);
    }

    /// <inheritdoc />
    public T? GetValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        if (!HasSection(sectionName))
            return defaultValue;

        if (!HasSectionKey(sectionName, keyName))
            return defaultValue;

        try
        {
            return (T) GetValueImpl(typeof(T), sectionName, keyName);
        }
        catch (Exception error)
        {
            // Return the default when the stored value cannot be deserialized,
            // so a single malformed value does not fail the whole section load.
            ConfigurationDiagnostics.ReportFallback(sectionName, keyName, error);
            return defaultValue;
        }
    }

    public object? GetValueOrDefault(Type typeObject, string sectionName, string keyName, object? defaultValue = default)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        if (!HasSection(sectionName))
            return defaultValue;

        if (!HasSectionKey(sectionName, keyName))
            return defaultValue;

        try
        {
            return GetValueImpl(typeObject, sectionName, keyName);
        }
        catch (Exception error)
        {
            // Return the default when the stored value cannot be deserialized.
            ConfigurationDiagnostics.ReportFallback(sectionName, keyName, error);
            return defaultValue;
        }
    }

    /// <inheritdoc />
    public object GetValue(Type typeObject, string sectionName, string keyName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        if (!HasSection(sectionName))
            throw new ConfigurationSectionNotFoundException(sectionName);

        if (!HasSectionKey(sectionName, keyName))
            throw new ConfigurationSectionKeyNotFoundException(keyName, sectionName);

        return GetValueImpl(typeObject, sectionName, keyName);
    }

    /// <inheritdoc />
    public void SetValue<T>(string sectionName, string keyName, T? value)
    {
        if (value == null)
            throw new ArgumentNullException(nameof(value));

        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        SetValueImpl<T>(sectionName, keyName, value);
        MarkChanged();
    }

    /// <inheritdoc />
    public string? GetRawValueOrDefault(string sectionName, string keyName, string? defaultValue = null)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        if (!HasSection(sectionName) || !HasSectionKey(sectionName, keyName))
            return defaultValue;

        return GetRawValueImpl(sectionName, keyName);
    }

    /// <inheritdoc />
    public void SetRawValue(string sectionName, string keyName, string rawValue)
    {
        if (rawValue is null)
            throw new ArgumentNullException(nameof(rawValue));

        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));

        if (string.IsNullOrWhiteSpace(keyName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(keyName));

        SetRawValueImpl(sectionName, keyName, rawValue);
        MarkChanged();
    }

    protected abstract void SaveConfigurationImpl();
    protected abstract void SaveConfigurationImpl(string configurationPath);

    protected abstract bool HasSectionImpl(string sectionName);
    protected abstract bool HasSectionKeyImpl(string sectionName, string keyName);

    protected abstract IEnumerable<string> GetSectionNamesImpl();
    protected abstract IEnumerable<string> GetSectionOptionNamesImpl(string sectionName);

    protected abstract bool AddSectionImpl(string sectionName);
    protected abstract bool RemoveSectionImpl(string sectionName);
    protected abstract bool RemoveOptionImpl(string sectionName, string keyName);

    protected abstract void SetValueImpl<T>(string sectionName, string keyName, T value);
    protected abstract object GetValueImpl(Type typeObject, string sectionName, string keyName);

    protected abstract string GetRawValueImpl(string sectionName, string keyName);
    protected abstract void SetRawValueImpl(string sectionName, string keyName, string rawValue);
}
