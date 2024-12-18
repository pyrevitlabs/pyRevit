using System.Text;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;
using System.Collections;
using YamlDotNet.Core;
using YamlDotNet.RepresentationModel;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace pyRevitLabs.Configurations.Yaml;

public sealed class YamlConfiguration : ConfigurationBase
{
    public static readonly string DefaultFileExtension = ".yml";
    public static readonly Encoding DefaultFileEncoding = Encoding.UTF8;

    private readonly YamlStream _yamlStream;
    private readonly YamlMappingNode _rootNode;

    /// <summary>
    /// Create yaml configuration instance.
    /// </summary>
    /// <param name="configurationPath">Configuration path.</param>
    /// <param name="readOnly">Admin configurations </param>
    private YamlConfiguration(string configurationPath, bool readOnly)
        : base(configurationPath, readOnly)
    {
        _yamlStream = [];
        if (File.Exists(configurationPath))
        {
            _yamlStream.Load(new StringReader(File.ReadAllText(_configurationPath, DefaultFileEncoding)));
        }

        if (_yamlStream.Documents.Count == 0)
        {
            _yamlStream.Documents.Add(new YamlDocument(new YamlMappingNode()));
        }

        _rootNode = (YamlMappingNode)_yamlStream.Documents[0].RootNode;
    }

    /// <summary>
    /// Creates YamlConfiguration.
    /// </summary>
    /// <param name="configurationPath">Configuration file path.</param>
    /// <param name="readOnly">Mark file is readonly.</param>
    /// <returns>Return new YamlConfiguration.</returns>
    /// <exception cref="ArgumentNullException">When configurationPath is null.</exception>
    public static IConfiguration Create(string configurationPath, bool readOnly = default)
    {
        if (configurationPath is null)
            throw new ArgumentNullException(nameof(configurationPath));

        return new YamlConfiguration(configurationPath, readOnly);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl()
    {
        SaveConfigurationImpl(_configurationPath);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl(string configurationPath)
    {
        ISerializer serializer = CreateSerializer();
        string yamlString = serializer.Serialize(_yamlStream);
        File.WriteAllText(configurationPath, yamlString, DefaultFileEncoding);
    }

    protected override bool HasSectionImpl(string sectionName)
    {
        return _rootNode.Children.ContainsKey(sectionName)
               && _rootNode.Children[sectionName].NodeType == YamlNodeType.Mapping;
    }

    protected override bool HasSectionKeyImpl(string sectionName, string keyName)
    {
        if (!HasSection(sectionName))
        {
            return false;
        }

        YamlMappingNode sectionNode = (YamlMappingNode)_rootNode.Children[sectionName];
        if (!sectionNode.Children.ContainsKey(keyName))
        {
            return false;
        }

        YamlNodeType? yamlNodeType = sectionNode.Children[keyName].NodeType;
        return yamlNodeType is YamlNodeType.Scalar or YamlNodeType.Sequence or YamlNodeType.Mapping;
    }

    protected override bool RemoveValueImpl(string sectionName, string keyName)
    {
        YamlMappingNode yamlNode = (YamlMappingNode)_rootNode[sectionName];
        return yamlNode.Children.Remove(keyName);
    }

    protected override T GetValueImpl<T>(string sectionName, string keyName)
    {
        YamlNode yamlNode = _rootNode[sectionName][keyName];
        return CreateDeserializer().Deserialize<T>(yamlNode.ToString());
    }

    protected override void SetValueImpl<T>(string sectionName, string keyName, T value)
    {
        if (_yamlStream.Documents.Count == 0)
            _yamlStream.Documents.Add(new YamlDocument(new YamlMappingNode()));

        if (value is string stringValue)
        {
            if (string.IsNullOrEmpty(stringValue))
            {
                return;
            }
        }

        if (!HasSection(sectionName))
        {
            _rootNode.Add(sectionName,
                new YamlMappingNode(
                    new KeyValuePair<YamlNode, YamlNode>(keyName, YamlMappingNode.FromObject(value!))));
        }

        if (!HasSectionKey(sectionName, keyName))
        {
            YamlMappingNode sectionNode = (YamlMappingNode)_rootNode[sectionName];
            sectionNode.Add(keyName, YamlMappingNode.FromObject(value!));
        }

        RemoveValue(sectionName, keyName);

        YamlMappingNode sectionNode1 = (YamlMappingNode)_rootNode[sectionName];
        sectionNode1.Add(keyName, YamlMappingNode.FromObject(value!));
    }

    private static ISerializer CreateSerializer()
    {
        return new SerializerBuilder()
            .WithNamingConvention(CamelCaseNamingConvention.Instance)
            .Build();
    }

    private static IDeserializer CreateDeserializer()
    {
        return new DeserializerBuilder()
            .WithNamingConvention(CamelCaseNamingConvention.Instance)
            .Build();
    }
}