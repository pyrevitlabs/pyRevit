"""Wrapper for YamlDotNet."""
# pylama:ignore=E402,W0611
from winterops import clr, System

clr.AddReferenceByName('YamlDotNet')

import YamlDotNet as libyaml


def _convert_yamldotnet_to_dict(ynode, level=0):
    # logger.debug('{}* Processing: {}'.format(' '*level, type(ynode)))
    if hasattr(ynode, 'Children'):
        d = dict()
        value_childs = []
        for child in ynode.Children:
            # logger.debug('{}+ Child: {}'.format(' '*level, child))
            if hasattr(child, 'Key') and hasattr(child, 'Value'):
                d[child.Key.Value] = \
                    _convert_yamldotnet_to_dict(child.Value, level=level+1)
            else:
                value_childs.append(child.Value)
        return value_childs or d
    else:
        # logger.debug('{}- Child: {}'.format(' '*level, ynode.Value))
        return ynode.Value


def load(yaml_file):
    """Load Yaml file into YamlDotNet object.

    Args:
        yaml_file (str): fiel path to yaml file

    Returns:
        obj`YamlDotNet.RepresentationModel.YamlMappingNode`: yaml node
    """
    with open(yaml_file, 'r') as yamlfile:
        yamlstr = libyaml.RepresentationModel.YamlStream()
        yamlstr.Load(System.IO.StringReader(yamlfile.read()))
        if yamlstr.Documents.Count >= 1:
            return yamlstr.Documents[0].RootNode


def load_as_dict(yaml_file):
    """Load Yaml file into python dict object.

    Args:
        yaml_file (str): fiel path to yaml file

    Returns:
        obj`dict`: dictionary representing yaml data
    """
    return _convert_yamldotnet_to_dict(load(yaml_file))
