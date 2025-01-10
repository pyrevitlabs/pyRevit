using System.Text;
using IniParser;
using IniParser.Model;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Json;

namespace pyRevitLabs.Configurations.Ini;

public sealed class IniConfiguration : ConfigurationBase
{
    public static readonly string DefaultFileExtension = ".ini";
    public static readonly Encoding DefaultFileEncoding = new UTF8Encoding(false);

    private readonly IniData _iniFile;
    private readonly FileIniDataParser _parser;

    /// <summary>
    /// Create ini configuration instance.
    /// </summary>
    /// <param name="configurationPath">Configuration path.</param>
    /// <param name="readOnly">Admin configurations </param>
    private IniConfiguration(string configurationPath, bool readOnly)
        : base(configurationPath, readOnly)
    {
        _parser = new FileIniDataParser();
        _iniFile = !File.Exists(configurationPath)
            ? new IniData()
            : _parser.ReadFile(_configurationPath, DefaultFileEncoding);
    }

    /// <summary>
    /// Creates IniConfiguration.
    /// </summary>
    /// <param name="configurationPath">Configuration file path.</param>
    /// <param name="readOnly">Mark file is readonly.</param>
    /// <returns>Return new IniConfiguration.</returns>
    /// <exception cref="ArgumentNullException">When configurationPath is null.</exception>
    public static IConfiguration Create(string configurationPath, bool readOnly = default)
    {
        if (configurationPath is null)
            throw new ArgumentNullException(nameof(configurationPath));

        return new IniConfiguration(configurationPath, readOnly);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl()
    {
        SaveConfigurationImpl(_configurationPath);
    }
    
    /// <inheritdoc />
    protected override void SaveConfigurationImpl(string configurationPath)
    {
        _parser.WriteFile(configurationPath, _iniFile, DefaultFileEncoding);
    }

    /// <inheritdoc />
    protected override bool HasSectionImpl(string sectionName)
    {
        return _iniFile.Sections.ContainsSection(sectionName);
    }

    /// <inheritdoc />
    protected override bool HasSectionKeyImpl(string sectionName, string keyName)
    {
        return HasSection(sectionName)
               && _iniFile.Sections[sectionName].ContainsKey(keyName);
    }

    /// <inheritdoc />
    protected override bool RemoveSectionImpl(string sectionName)
    {
        return _iniFile.Sections.RemoveSection(sectionName);
    }

    /// <inheritdoc />
    protected override bool RemoveOptionImpl(string sectionName, string keyName)
    {
        return _iniFile[sectionName].RemoveKey(keyName);
    }

    /// <inheritdoc />
    protected override void SetValueImpl<T>(string sectionName, string keyName, T value)
    {
        if (!HasSection(sectionName))
        {
            _iniFile.Sections.AddSection(sectionName);
        }

        if (!HasSectionKey(sectionName, keyName))
        {
            _iniFile[sectionName].AddKey(keyName);
        }

        _iniFile[sectionName][keyName] = JsonConvert.SerializeObject(value);
    }
    
    /// <inheritdoc />
    protected override object GetValueImpl(Type typeObject, string sectionName, string keyName)
    {
        return JsonConvert.DeserializeObject(_iniFile[sectionName][keyName], typeObject)
               ?? throw new ConfigurationException("Cannot deserialize value using the specified key.");
    }
}