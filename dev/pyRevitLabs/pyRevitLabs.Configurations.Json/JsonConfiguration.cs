using System.Text;
using System.Xml;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using Formatting = pyRevitLabs.Json.Formatting;

namespace pyRevitLabs.Configurations.Json;

public sealed class JsonConfiguration : ConfigurationBase
{
    public static readonly string DefaultFileExtension = ".json";
    public static readonly Encoding DefaultFileEncoding = Encoding.UTF8;

    private readonly JObject _jsonObject;

    /// <summary>
    /// Create json configuration instance.
    /// </summary>
    /// <param name="configurationPath">Configuration path.</param>
    /// <param name="readOnly">Readonly configurations </param>
    private JsonConfiguration(string configurationPath, bool readOnly)
        : base(configurationPath, readOnly)
    {
        _jsonObject = !File.Exists(configurationPath)
            ? new JObject()
            : JObject.Parse(File.ReadAllText(_configurationPath, DefaultFileEncoding));
    }

    /// <summary>
    /// Creates JsonConfiguration.
    /// </summary>
    /// <param name="configurationPath">Configuration file path.</param>
    /// <param name="readOnly">Mark file is readonly.</param>
    /// <returns>Return new JsonConfiguration.</returns>
    /// <exception cref="ArgumentNullException">When configurationPath is null.</exception>
    public static IConfiguration Create(string configurationPath, bool readOnly = default)
    {
        if (configurationPath is null)
            throw new ArgumentNullException(nameof(configurationPath));

        return new JsonConfiguration(configurationPath, readOnly);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl()
    {
        SaveConfigurationImpl(_configurationPath);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl(string configurationPath)
    {
        string jsonString = JsonConvert.SerializeObject(_jsonObject,
            new JsonSerializerSettings() {Formatting = Formatting.Indented});
        File.WriteAllText(configurationPath, jsonString, DefaultFileEncoding);
    }

    /// <inheritdoc />
    protected override bool HasSectionImpl(string sectionName)
    {
        return _jsonObject.ContainsKey(sectionName);
    }

    /// <inheritdoc />
    protected override bool HasSectionKeyImpl(string sectionName, string keyName)
    {
        JObject? sectionObject = _jsonObject[sectionName] as JObject;
        return sectionObject?.ContainsKey(keyName) == true;
    }

    protected override IEnumerable<string> GetSectionNamesImpl()
    {
        return _jsonObject.Properties().Select(x => x.Name);
    }

    protected override IEnumerable<string> GetSectionOptionNamesImpl(string sectionName)
    {
        JObject? sectionObject = _jsonObject[sectionName] as JObject;
        return sectionObject?.Properties().Select(x => x.Name) ?? Enumerable.Empty<string>();
    }

    protected override bool RemoveSectionImpl(string sectionName)
    {
        return _jsonObject.Remove(sectionName);
    }

    protected override bool RemoveOptionImpl(string sectionName, string keyName)
    {
        _jsonObject[sectionName]![keyName] = null;
        return true;
    }

    /// <inheritdoc />
    protected override void SetValueImpl<T>(string sectionName, string keyName, T value)
    {
        if (!HasSection(sectionName))
        {
            JObject fromObject = new();
            fromObject.Add(keyName, JToken.FromObject(value!));
            
            _jsonObject.Add(sectionName, fromObject);

            return;
        }
        
        if (!HasSectionKey(sectionName, keyName))
        {
            JObject fromObject = new();
            fromObject.Add(keyName, JToken.FromObject(value!));

            JObject? sectionObject = (JObject?)_jsonObject[sectionName];
            sectionObject?.Add(keyName, fromObject);
            
            return;
        }
        
        _jsonObject[sectionName]![keyName] = JToken.FromObject(value!);
    }
    
    /// <inheritdoc />
    protected override object GetValueImpl(Type typeObject, string sectionName, string keyName)
    {
        JToken? token = _jsonObject[sectionName]?[keyName];
        return token is null
            ? throw new ConfigurationException($"Section {sectionName} or keyName {keyName} not found.")
            : token.ToObject(typeObject)
              ?? throw new ConfigurationException($"Cannot deserialize value with {sectionName} and {keyName}.");
    }
}