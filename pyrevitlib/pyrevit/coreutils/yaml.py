"""Wrapper for YamlDotNet."""
from collections import OrderedDict
import codecs

from pyrevit.framework import StringReader, KeyValuePair
from pyrevit.labs import libyaml
from pyrevit.compat import PY3, PY2


def _convert_yamldotnet_to_dict(ynode, level=0):
    if isinstance(ynode, libyaml.RepresentationModel.YamlMappingNode):
        d = OrderedDict()
        for child in ynode.Children:
            if isinstance(child, KeyValuePair[libyaml.RepresentationModel.YamlNode, libyaml.RepresentationModel.YamlNode]):
                d[child.Key.Value] = _convert_yamldotnet_to_dict(child.Value, level=level+1)
        return d
    elif isinstance(ynode, libyaml.RepresentationModel.YamlSequenceNode):
        v = []
        for child in ynode.Children:
            v.append(_convert_yamldotnet_to_dict(child, level=level+1))
        return v
    elif isinstance(ynode, libyaml.RepresentationModel.YamlScalarNode):
        return ynode.Value


def load(yaml_file):
    """Load Yaml file into YamlDotNet object.

    Args:
        yaml_file (str): file path to yaml file

    Returns:
        (YamlDotNet.RepresentationModel.YamlMappingNode): yaml node
    """
    if PY3:
        with open(yaml_file, 'r', encoding="utf8") as yamlfile:
            yamlstr = libyaml.RepresentationModel.YamlStream()
            yamldata = yamlfile.read()
            yamlstr.Load(StringReader(yamldata))
            if yamlstr.Documents.Count >= 1:
                return yamlstr.Documents[0].RootNode
    else:
        with open(yaml_file, 'r') as yamlfile:
            yamlstr = libyaml.RepresentationModel.YamlStream()
            yamldata = yamlfile.read().decode('utf-8')
            yamlstr.Load(StringReader(yamldata))
            if yamlstr.Documents.Count >= 1:
                return yamlstr.Documents[0].RootNode


def load_as_dict(yaml_file):
    """Load Yaml file into python dict object.

    Args:
        yaml_file (str): file path to yaml file

    Returns:
        (dict[str, Any]): dictionary representing yaml data
    """
    return _convert_yamldotnet_to_dict(load(yaml_file))


def dump_dict(dict_object, yaml_file):
    """Save YamlDotNet object to Yaml file.

    Args:
        dict_object (dict): dict object to be serialized into yaml
        yaml_file (str): file path to yaml file
    """
    ybuilder = libyaml.Serialization.SerializerBuilder().Build()
    serialized_yaml = ybuilder.Serialize(dict_object)
    with codecs.open(yaml_file, 'w', 'utf-8') as yamlfile:
        yamlfile.write(serialized_yaml.replace('\r\n', '\n'))
