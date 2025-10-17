"""Base module for pyRevit config parsing."""
import json

from pyrevit import coreutils
from pyrevit.labs import ConfigurationService


class ConfigSection(object):
    def __init__(self, section_name, configuration):
        self.__section_name = section_name
        self.__configuration = configuration

    def __iter__(self):
        for option_name in self.__configuration.GetSectionOptionNames(self.__section_name):
            yield option_name

    def __str__(self):
        return self.__section_name

    def __repr__(self):
        return '<PyRevitConfigSectionParser object '    \
               'at 0x{0:016x} '                         \
               'config section \'{1}\'>'                \
               .format(id(self), self.__section_name)

    def __getattr__(self, param_name):
        return self.get_option(param_name)

    def __setattr__(self, param_name, value):
        return self.set_option(param_name, value)

    @property
    def header(self):
        return self.__section_name

    @property
    def subheader(self):
        return coreutils.get_canonical_parts(self.header)[-1]

    def has_option(self, option_name):
        return self.__configuration.HasSectionKey(self.__section_name, option_name)

    def get_option(self, op_name, default_value=None):
        value = self.__configuration.GetValueOrDefault(op_name, "")
        return json.load(value) if value else default_value

    def set_option(self, op_name, value):
        self.__configuration.SetValue(self.__section_name, op_name,
                                      json.dumps(value, separators=(',', ':'), ensure_ascii=False))

    def remove_option(self, option_name):
        return self.__configuration.RemoveOption(self.__section_name, option_name)

    def has_subsection(self, section_name):
        """Check if section has any subsections."""
        return True if self.get_subsection(section_name) else False

    def add_subsection(self, section_name):
        """Add subsection to section."""
        return self._parser.add_section(
            coreutils.make_canonical_name(self._section_name, section_name)
        )

    def get_subsections(self):
        subsections = []
        for section_name in self.__configuration.GetSectionNames():
            if section_name.startswith(self._section_name + '.'):
                subsec = ConfigSection(self._parser, section_name)
                subsections.append(subsec)

        return subsections

    def get_subsection(self, section_name):
        for subsection in self.get_subsections():
            if subsection.subheader == section_name:
                return subsection


class ConfigSections(object):
    def __init__(self, configuration_service):
        self.__configuration_service = configuration_service

    def __iter__(self):
        for section_name in self.__get_default_config().GetSectionNames():
            yield section_name

    def __getattr__(self, section_name):
        return self.get_section(section_name)

    def has_section(self, section_name):
        return self.__get_default_config().HasSection(section_name)

    def add_section(self, section_name):
        return ConfigSection(section_name, self.__get_default_config())

    def get_section(self, section_name):
        return ConfigSection(section_name, self.__get_default_config())

    def remove_section(self, section_name):
        self.__get_default_config().RemoveSection(section_name)

    def __get_default_config(self):
        return self.__configuration_service[ConfigurationService.DefaultConfigurationName]
