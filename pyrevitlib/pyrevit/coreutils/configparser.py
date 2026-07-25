"""Base module for pyRevit config parsing."""
import json

from pyrevit import coreutils
from pyrevit.labs import ConfigurationService


class ConfigSection(object):
    """Read/write access to the options of a single config section.

    Options can be accessed either as attributes (``section.option``) or
    through the explicit ``get_option``/``set_option`` methods. Values are
    stored as JSON and decoded tolerantly on read.
    """

    def __init__(self, section_name, configuration):
        self.__section_name = section_name
        self.__configuration = configuration

    def __iter__(self):
        for option_name in self.__configuration.GetSectionOptionNames(self.__section_name):
            yield option_name

    def __str__(self):
        return self.__section_name

    def __repr__(self):
        return '<ConfigSection object '                 \
               'at 0x{0:016x} '                         \
               'config section \'{1}\'>'                \
               .format(id(self), self.__section_name)

    def __getattr__(self, param_name):
        if not self.has_option(param_name):
            raise AttributeError(
                'Parameter does not exist in config file: {}'.format(param_name))
        return self.get_option(param_name)

    def __setattr__(self, param_name, value):
        # Skip internal storage so __init__ can set __section_name and __configuration
        if param_name in ('_ConfigSection__section_name', '_ConfigSection__configuration'):
            object.__setattr__(self, param_name, value)
        else:
            return self.set_option(param_name, value)

    @property
    def header(self):
        """str: Full canonical name of this section."""
        return self.__section_name

    @property
    def subheader(self):
        """str: Last component of the section's canonical name."""
        return coreutils.get_canonical_parts(self.header)[-1]

    def has_option(self, option_name):
        """Check if this section contains the given option.

        Args:
            option_name (str): name of the option

        Returns:
            (bool): whether the option exists
        """
        return self.__configuration.HasSectionKey(self.__section_name, option_name)

    def get_option(self, op_name, default_value=None):
        """Get the value of an option, decoding it tolerantly.

        A missing key returns ``default_value``; an explicitly stored empty
        string is treated as a real value. Values that are not valid JSON
        (legacy single-quoted strings, bare paths, Python bools) are returned
        as-is rather than raising.

        Args:
            op_name (str): name of the option
            default_value: value to return when the option is not set

        Returns:
            the decoded option value, or ``default_value`` when unset
        """
        value = self.__configuration.GetRawValueOrDefault(self.__section_name, op_name, None)
        # Only a missing key is "unset"; an explicitly stored empty string is a
        # real value and must not fall back to the default.
        if value is None:
            return default_value
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            try:
                # Legacy configs stored Python-style single-quoted strings/lists.
                return json.loads(value.replace("'", '"'))
            except (ValueError, TypeError):
                # Bare values (Windows paths, Python bools) are returned as-is.
                return value

    def set_option(self, op_name, value):
        """Set the value of an option, encoding it as JSON.

        Args:
            op_name (str): name of the option
            value: value to store
        """
        self.__configuration.SetRawValue(
            self.__section_name, op_name,
            json.dumps(value, separators=(',', ':'), ensure_ascii=False))

    def remove_option(self, option_name):
        """Remove an option from this section.

        Args:
            option_name (str): name of the option

        Returns:
            (bool): whether an option was removed
        """
        return self.__configuration.RemoveOption(self.__section_name, option_name)

    def has_subsection(self, section_name):
        """Check if section has any subsections."""
        return True if self.get_subsection(section_name) else False

    def add_subsection(self, section_name):
        """Add subsection to section."""
        canonical_name = coreutils.make_canonical_name(
            self.__section_name, section_name)
        self.__configuration.AddSection(canonical_name)
        return ConfigSection(canonical_name, self.__configuration)

    def get_subsections(self):
        """Return all subsections nested under this section.

        Returns:
            (list[ConfigSection]): the nested subsections
        """
        subsections = []
        for section_name in self.__configuration.GetSectionNames():
            if section_name.startswith(self.__section_name + '.'):
                subsec = ConfigSection(section_name, self.__configuration)
                subsections.append(subsec)
        return subsections

    def get_subsection(self, section_name):
        """Return the named subsection nested under this section.

        Args:
            section_name (str): short name of the subsection

        Returns:
            (ConfigSection): the subsection, or None if not found
        """
        for subsection in self.get_subsections():
            if subsection.subheader == section_name:
                return subsection
        return None


class ConfigSections(object):
    """Access the sections of the default configuration.

    Sections can be reached either as attributes (``sections.core``) or
    through the explicit section methods. Iterating yields section names.
    """

    def __init__(self, configuration_service):
        self.__configuration_service = configuration_service

    def __iter__(self):
        for section_name in self.__get_default_config().GetSectionNames():
            yield section_name

    def __getattr__(self, section_name):
        return self.get_section(section_name)

    def has_section(self, section_name):
        """Check if the config contains the given section.

        Args:
            section_name (str): name of the section

        Returns:
            (bool): whether the section exists
        """
        return self.__get_default_config().HasSection(section_name)

    def add_section(self, section_name):
        """Add a new section to the config.

        Args:
            section_name (str): name of the section

        Returns:
            (ConfigSection): the added section
        """
        configuration = self.__get_default_config()
        configuration.AddSection(section_name)
        return ConfigSection(section_name, configuration)

    def get_section(self, section_name):
        """Get the named config section.

        Args:
            section_name (str): name of the section

        Returns:
            (ConfigSection): the requested section

        Raises:
            AttributeError: if the section does not exist
        """
        configuration = self.__get_default_config()
        if not configuration.HasSection(section_name):
            raise AttributeError(
                'Section "{}" does not exist in config file.'.format(section_name))
        return ConfigSection(section_name, configuration)

    def remove_section(self, section_name):
        """Remove the named section from the config.

        Args:
            section_name (str): name of the section
        """
        self.__get_default_config().RemoveSection(section_name)

    def __get_default_config(self):
        return self.__configuration_service[ConfigurationService.DefaultConfigurationName]
