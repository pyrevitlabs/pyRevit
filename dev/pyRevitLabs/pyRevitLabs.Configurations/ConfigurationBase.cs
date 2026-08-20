using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Format-independent half of <see cref="IConfiguration"/>: argument validation,
/// read-only enforcement, revision tracking, and the tolerant-read fallback. A
/// backend derives from this and implements the <c>*Impl</c> members against its
/// own file format, and can rely on every <c>*Impl</c> call having been
/// validated first.
/// </summary>
public abstract class ConfigurationBase : IConfiguration
{
    /// <summary>Path to the backing file, as supplied to the constructor.</summary>
    protected readonly string _configurationPath;

    /// <summary>
    /// Initializes the shared state for a backend.
    /// </summary>
    /// <param name="configurationPath">Path to the backing file. It need not exist yet.</param>
    /// <param name="readOnly">
    /// True to make <see cref="SaveConfiguration()"/> discard changes instead of
    /// writing them, used for an admin-locked configuration.
    /// </param>
    protected ConfigurationBase(string configurationPath, bool readOnly)
    {
        _configurationPath = configurationPath;
        ReadOnly = readOnly;
    }

    /// <inheritdoc />
    public bool ReadOnly { get; }

    /// <inheritdoc />
    public string ConfigurationPath => _configurationPath;

    private long _revision;

    /// <inheritdoc />
    public long Revision => Interlocked.Read(ref _revision);

    private void MarkChanged() => Interlocked.Increment(ref _revision);

    /// <inheritdoc />
    public void SaveConfiguration()
    {
        if (ReadOnly)
        {
            return;
        }

        SaveConfigurationImpl();
    }

    /// <inheritdoc />
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

    /// <inheritdoc />
    public IEnumerable<string> GetSectionNames()
    {
        return GetSectionNamesImpl();
    }

    /// <inheritdoc />
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

    /// <inheritdoc />
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
            ConfigurationDiagnostics.ReportFallback(sectionName, keyName, error);
            return defaultValue;
        }
    }

    /// <inheritdoc />
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

    /// <summary>Writes the current state to <see cref="ConfigurationPath"/>. Called only when writable.</summary>
    protected abstract void SaveConfigurationImpl();

    /// <summary>Writes the current state to an explicit path, creating the directory if needed.</summary>
    protected abstract void SaveConfigurationImpl(string configurationPath);

    /// <summary>Whether the section exists in the backing store.</summary>
    protected abstract bool HasSectionImpl(string sectionName);

    /// <summary>Whether the key exists in the section. Called without a prior section-existence check.</summary>
    protected abstract bool HasSectionKeyImpl(string sectionName, string keyName);

    /// <summary>Every section name in the backing store.</summary>
    protected abstract IEnumerable<string> GetSectionNamesImpl();

    /// <summary>Key names in a section that is known to exist.</summary>
    protected abstract IEnumerable<string> GetSectionOptionNamesImpl(string sectionName);

    /// <summary>Adds a section that is known not to exist. Returns false when the backend declines.</summary>
    protected abstract bool AddSectionImpl(string sectionName);

    /// <summary>Removes a section that is known to exist. Returns false when the backend declines.</summary>
    protected abstract bool RemoveSectionImpl(string sectionName);

    /// <summary>Removes a key that is known to exist. Returns false when the backend declines.</summary>
    protected abstract bool RemoveOptionImpl(string sectionName, string keyName);

    /// <summary>
    /// Encodes and stores a non-null value, creating the section and key as
    /// needed. The encoding must round-trip through <see cref="GetValueImpl"/>.
    /// </summary>
    protected abstract void SetValueImpl<T>(string sectionName, string keyName, T value);

    /// <summary>
    /// Decodes a stored value that is known to be present, to the requested
    /// type. Throws when the value cannot be decoded; the caller turns that into
    /// either a thrown exception or a default, depending on the entry point.
    /// </summary>
    protected abstract object GetValueImpl(Type typeObject, string sectionName, string keyName);

    /// <summary>Returns the stored value text for a key that is known to be present, undecoded.</summary>
    protected abstract string GetRawValueImpl(string sectionName, string keyName);

    /// <summary>Stores value text verbatim, creating the section and key as needed.</summary>
    protected abstract void SetRawValueImpl(string sectionName, string keyName, string rawValue);
}
