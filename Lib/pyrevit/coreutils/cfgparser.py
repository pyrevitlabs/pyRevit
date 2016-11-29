import ConfigParser
from ConfigParser import NoOptionError, NoSectionError

from pyrevit.core.exceptions import PyRevitException, PyRevitIOError

# noinspection PyUnresolvedReferences
from System.IO import IOException


class PyRevitConfigSectionParser(object):
    def __init__(self, config_parser, section_name):
        self._parser = config_parser
        self._section_name = section_name

    def __getattr__(self, param_name):
        try:
            return self._parser.get(self._section_name, param_name)
        except (NoOptionError, NoSectionError):
            raise AttributeError('Parameter does not exist in config file.')

    def __setattr__(self, param_name, value):
        if param_name in ['_parser', '_section_name']:
            super(PyRevitConfigSectionParser, self).__setattr__(param_name, value)
        else:
            try:
                return self._parser.set(self._section_name, param_name, value)
            except Exception as set_err:
                raise PyRevitException('Error setting parameter value. | {}'.format(set_err))


class PyRevitConfigParser(object):
    def __init__(self, cfg_file_path):
        self._parser = ConfigParser.ConfigParser()
        try:
            with open(cfg_file_path, 'r') as cfg_file:
                self._parser.readfp(cfg_file)
        except (OSError, IOError):
            raise PyRevitIOError()

    def __getattr__(self, section_name):
        if self._parser.has_section(section_name):
            return PyRevitConfigSectionParser(self._parser, section_name)
        else:
            raise AttributeError('Section does not exist in config file.')

    def add_section(self, section_name):
        self._parser.add_section(section_name)
        return PyRevitConfigSectionParser(self._parser, section_name)

    def save(self, cfg_file_path):
        try:
            with open(cfg_file_path, 'w') as cfg_file:
                self._parser.write(cfg_file)
        except (OSError, IOError):
            raise PyRevitIOError()
