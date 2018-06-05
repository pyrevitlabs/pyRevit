# pylama:ignore=E402,W0611
from winterops import clr, System

clr.AddReferenceByName('YamlDotNet')

import YamlDotNet as libyaml


def load(yaml_file):
    with open(yaml_file, 'r') as yamlfile:
        yamlstr = libyaml.RepresentationModel.YamlStream()
        yamlstr.Load(System.IO.StringReader(yamlfile.read()))
        if yamlstr.Documents.Count >= 1:
            return yamlstr.Documents[0].RootNode
