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

    public bool RemoveSection(string sectionName)
    {
        if (string.IsNullOrWhiteSpace(sectionName))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(sectionName));


        bool result = HasSection(sectionName)
                      && RemoveSectionImpl(sectionName);

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
            throw new ConfigurationSectionKeyNotFoundException(sectionName, keyName);

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

        return (T) GetValueImpl(typeof(T), sectionName, keyName);
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

        return GetValueImpl(typeObject, sectionName, keyName);
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
            throw new ConfigurationSectionKeyNotFoundException(sectionName, keyName);
        
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
    }

    protected abstract void SaveConfigurationImpl();
    protected abstract void SaveConfigurationImpl(string configurationPath);
    
    protected abstract bool HasSectionImpl(string sectionName);
    protected abstract bool HasSectionKeyImpl(string sectionName, string keyName);
    
    protected abstract IEnumerable<string> GetSectionNamesImpl();
    protected abstract IEnumerable<string> GetSectionOptionNamesImpl(string sectionName);

    protected abstract bool RemoveSectionImpl(string sectionName);
    protected abstract bool RemoveOptionImpl(string sectionName, string keyName);
    
    protected abstract void SetValueImpl<T>(string sectionName, string keyName, T value);
    protected abstract object GetValueImpl(Type typeObject, string sectionName, string keyName);
}