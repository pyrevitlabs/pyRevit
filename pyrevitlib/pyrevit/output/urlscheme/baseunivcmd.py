import json


SCHEME_PREFIX = 'revit://'
COMMAND_KEY = 'command'
DATA_KEY = 'data'


class GenericUniversalCommand(object):
    type_id = None

    def __init__(self, args):
        self._args = args

    @property
    def url_data(self):
        return json.dumps({COMMAND_KEY: self.type_id,
                           DATA_KEY: self.get_elements()},
                          separators=(',', ':'))

    @property
    def url_title(self):
        title_str = unicode(self.get_elements())
        title_str = title_str.replace('[', '').replace(']', '')
        return title_str

    def make_command_url(self):
        raise NotImplementedError()

    def get_elements(self):
        raise NotImplementedError()

    def execute(self):
        raise NotImplementedError()
