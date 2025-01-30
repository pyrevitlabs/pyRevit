"""Base module for pyRevit config parsing."""
import json
import codecs
from pyrevit.compat import configparser

from pyrevit import PyRevitException, PyRevitIOError
from pyrevit import coreutils

#pylint: disable=W0703,C0302
KEY_VALUE_TRUE = "True"
KEY_VALUE_FALSE = "False"


class ConfigSection(object):
    def __init__(self, section_name, configuration):
        self.section_name = section_name
        self.configuration = configuration

    def __iter__(self):
        return list(self.configuration.GetSectionOptionNames(self.section_name))

    def __str__(self):
        return self.section_name

    def __repr__(self):
        return '<PyRevitConfigSectionParser object '    \
               'at 0x{0:016x} '                         \
               'config section \'{1}\'>'                \
               .format(id(self), self.section_name)

    def __getattr__(self, param_name):
        return self.get_option(param_name)

    def __setattr__(self, param_name, value):
        return self.set_option(param_name, value)

    @property
    def header(self):
        """Section header."""
        return self.section_name

    @property
    def subheader(self):
        """Section sub-header e.g. Section.SubSection."""
        return coreutils.get_canonical_parts(self.header)[-1]

    def has_option(self, option_name):
        pass

    def get_option(self, op_name, default_value=None):
        value = self.configuration.GetValueOrDefault(op_name, "")
        return json.load(value) if value else None

    def set_option(self, op_name, value):
        self.configuration.SetValue(self.section_name, op_name,
                                    json.dumps(value, separators=(',', ':'), ensure_ascii=False))

    def remove_option(self, option_name):
        self.configuration.RemoveOption(self.section_name, option_name)

    def has_subsection(self, section_name):
        """Check if section has any subsections."""
        return True if self.get_subsection(section_name) else False

    def add_subsection(self, section_name):
        """Add subsection to section."""
        return self._parser.add_section(
            coreutils.make_canonical_name(self._section_name, section_name)
        )

    def get_subsections(self):
        """Get all subsections."""
        subsections = []
        for section_name in self._parser.sections():
            if section_name.startswith(self._section_name + '.'):
                subsec = ConfigSection(self._parser, section_name)
                subsections.append(subsec)
        return subsections

    def get_subsection(self, section_name):
        """Get subsection with given name."""
        for subsection in self.get_subsections():
            if subsection.subheader == section_name:
                return subsection


class ConfigSections(object):
    def __init__(self, configuration):
        self.configuration = configuration

    def __iter__(self):
        return list(self.configuration.GetSectionNames())

    def __getattr__(self, section_name):
        return self.get_section(section_name)

    def has_section(self, section_name):
        return self.configuration.HasSection(section_name)

    def add_section(self, section_name):
        return ConfigSection(section_name, self.configuration)

    def get_section(self, section_name):
        return ConfigSection(section_name, self.configuration)

    def remove_section(self, section_name):
        self.configuration.RemoveSection(section_name)
