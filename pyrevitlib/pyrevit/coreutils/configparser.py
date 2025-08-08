"""Base module for pyRevit config parsing."""
import json
import codecs
from pyrevit.compat import configparser

from pyrevit import PyRevitException, PyRevitIOError
from pyrevit import coreutils

#pylint: disable=W0703,C0302
KEY_VALUE_TRUE = "True"
KEY_VALUE_FALSE = "False"


class PyRevitConfigSectionParser(object):
    """Config section parser object. Handle section options."""
    def __init__(self, config_parser, section_name):
        self._parser = config_parser
        self._section_name = section_name

    def __iter__(self):
        return iter(self._parser.options(self._section_name))

    def __str__(self):
        return self._section_name

    def __repr__(self):
        return '<PyRevitConfigSectionParser object '    \
               'at 0x{0:016x} '                         \
               'config section \'{1}\'>'                \
               .format(id(self), self._section_name)

    def __getattr__(self, param_name):
        try:
            value = self._parser.get(self._section_name, param_name)
            try:
                try:
                    return json.loads(value)  #pylint: disable=W0123
                except Exception:
                    # try fix legacy formats
                    # cleanup python style true, false values
                    if value == KEY_VALUE_TRUE:
                        value = json.dumps(True)
                    elif value == KEY_VALUE_FALSE:
                        value = json.dumps(False)
                    # cleanup string representations
                    value = value.replace('\'', '"').encode('string-escape')
                    # try parsing again
                    try:
                        return json.loads(value)  #pylint: disable=W0123
                    except Exception:
                        # if failed again then the value is a string
                        # but is not encapsulated in quotes
                        # e.g. option = C:\Users\Desktop
                        value = value.strip()
                        if (not value.startswith('(')
                                and not value.startswith('[')
                                and not value.startswith('{')):
                            value = "\"%s\"" % value
                        return json.loads(value)  #pylint: disable=W0123
            except Exception:
                return value
        except (configparser.NoOptionError, configparser.NoSectionError):
            raise AttributeError('Parameter does not exist in config file: {}'
                                 .format(param_name))

    def __setattr__(self, param_name, value):
        # check agaist used attribute names
        if param_name in ['_parser', '_section_name']:
            super(PyRevitConfigSectionParser, self).__setattr__(param_name,
                                                                value)
        else:
            # if not used by this object, then set a config section
            try:
                return self._parser.set(self._section_name,
                                        param_name,
                                        json.dumps(value,
                                                   separators=(',', ':'),
                                                   ensure_ascii=False))
            except Exception as set_err:
                raise PyRevitException('Error setting parameter value. '
                                       '| {}'.format(set_err))

    @property
    def header(self):
        """Section header."""
        return self._section_name

    @property
    def subheader(self):
        """Section sub-header e.g. Section.SubSection."""
        return coreutils.get_canonical_parts(self.header)[-1]

    def has_option(self, option_name):
        """Check if section contains given option."""
        return self._parser.has_option(self._section_name, option_name)

    def get_option(self, op_name, default_value=None):
        """Get option value or return default."""
        try:
            return self.__getattr__(op_name)
        except Exception as opt_get_err:
            if default_value is not None:
                return default_value
            else:
                raise opt_get_err

    def set_option(self, op_name, value):
        """Set value of given option."""
        self.__setattr__(op_name, value)

    def remove_option(self, option_name):
        """Remove given option from section."""
        return self._parser.remove_option(self._section_name, option_name)

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
                subsec = PyRevitConfigSectionParser(self._parser, section_name)
                subsections.append(subsec)
        return subsections

    def get_subsection(self, section_name):
        """Get subsection with given name."""
        for subsection in self.get_subsections():
            if subsection.subheader == section_name:
                return subsection


class PyRevitConfigParser(object):
    """Config parser object. Handle config sections and io."""
    def __init__(self, cfg_file_path=None):
        self._cfg_file_path = cfg_file_path
        self._parser = configparser.ConfigParser()
        if self._cfg_file_path:
            try:
                with codecs.open(self._cfg_file_path, 'r', 'utf-8') as cfg_file:
                    try:
                        self._parser.readfp(cfg_file)
                    except AttributeError:
                        self._parser.read_file(cfg_file)
            except (OSError, IOError):
                raise PyRevitIOError()
            except Exception as read_err:
                raise PyRevitException(read_err)

    def __iter__(self):
        return iter([self.get_section(x) for x in self._parser.sections()])

    def __getattr__(self, section_name):
        if self._parser.has_section(section_name):
            # build a section parser object and return
            return PyRevitConfigSectionParser(self._parser, section_name)
        else:
            raise AttributeError(
                'Section \"{}\" does not exist in config file.'
                .format(section_name))

    def get_config_file_hash(self):
        """Get calculated unique hash for this config.

        Returns:
            (str): hash of the config.
        """
        with codecs.open(self._cfg_file_path, 'r', 'utf-8') as cfg_file:
            cfg_hash = coreutils.get_str_hash(cfg_file.read())

        return cfg_hash

    def has_section(self, section_name):
        """Check if config contains given section."""
        try:
            self.get_section(section_name)
            return True
        except Exception:
            return False

    def add_section(self, section_name):
        """Add section with given name to config."""
        self._parser.add_section(section_name)
        return PyRevitConfigSectionParser(self._parser, section_name)

    def get_section(self, section_name):
        """Get section with given name.

        Raises:
            AttributeError: if section is missing
        """
        # check is section with full name is available
        if self._parser.has_section(section_name):
            return PyRevitConfigSectionParser(self._parser, section_name)

        # if not try to match with section_name.subsection
        # if there is a section_name.subsection defined, that should be
        # the sign that the section exists
        # section obj then supports getting all subsections
        for cfg_section_name in self._parser.sections():
            master_section = coreutils.get_canonical_parts(cfg_section_name)[0]
            if section_name == master_section:
                return PyRevitConfigSectionParser(self._parser,
                                                  master_section)

        # if no match happened then raise exception
        raise AttributeError('Section does not exist in config file.')

    def remove_section(self, section_name):
        """Remove section from config."""
        cfg_section = self.get_section(section_name)
        for cfg_subsection in cfg_section.get_subsections():
            self._parser.remove_section(cfg_subsection.header)
        self._parser.remove_section(cfg_section.header)

    def reload(self, cfg_file_path=None):
        """Reload config from original or given file."""
        try:
            with codecs.open(cfg_file_path \
                    or self._cfg_file_path, 'r', 'utf-8') as cfg_file:
                try:
                    self._parser.readfp(cfg_file)
                except AttributeError:
                    self._parser.read_file(cfg_file)
        except (OSError, IOError):
            raise PyRevitIOError()

    def save(self, cfg_file_path=None):
        """Save config to original or given file."""
        try:
            with codecs.open(cfg_file_path \
                    or self._cfg_file_path, 'w', 'utf-8') as cfg_file:
                self._parser.write(cfg_file)
        except (OSError, IOError):
            raise PyRevitIOError()
