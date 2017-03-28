from collections import defaultdict

from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger
from pyrevit.usagelog.record import RESULT_DICT


logger = get_logger(__name__)


class RecordFilter(object):
    filter_param = ''
    name_template = ''

    def __init__(self, filter_value):
        self.filter_value = filter_value
        self.filter_name = self.name_template.format(self.filter_value)

    def __eq__(self, other):
        return self.filter_value == other.filter_value

    def __ne__(self, other):
        return self.filter_value != other.filter_value

    def __hash__(self):
        return hash(self.filter_value)

    def __lt__(self, other):
        if type(self) == type(other):
            return self.filter_value < other.filter_value
        else:
            return self.filter_name < other.filter_name

    def filter_records(self, record_list, search_term=None):
        filtered_list = []
        for record in record_list:
            if getattr(record, self.filter_param) == self.filter_value:
                if search_term:
                    if record.has_term(search_term.lower()):
                        filtered_list.append(record)
                else:
                    filtered_list.append(record)
        return filtered_list


class RecordNoneFilter(RecordFilter):
    type_id = ''

    def __init__(self):
        self.filter_value = 'None'
        self.filter_name = 'No Filter'

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return type(self) != type(other)

    def __hash__(self):
        return hash(0)

    def __lt__(self, other):
        return True

    def filter_records(self, record_list, search_term=None):
        if search_term:
            filtered_list = []
            for record in record_list:
                if record.has_term(search_term.lower()):
                    filtered_list.append(record)

            return filtered_list
        else:
            return record_list


class RecordDateFilter(RecordFilter):
    filter_param = 'date'
    name_template = 'Date: {}'


# class RecordTimeFilter:
#     filter_param = 'time'


class RecordUsernameFilter(RecordFilter):
    filter_param = 'username'
    name_template = 'User: {}'


class RecordRevitVersionFilter(RecordFilter):
    filter_param = 'revit'
    name_template = 'Revit Version: {}'


class RecordRevitBuildFilter(RecordFilter):
    filter_param = 'revitbuild'
    name_template = 'Revit Build: {}'


class RecordSessionFilter(RecordFilter):
    filter_param = 'sessionid'
    name_template = 'Session Id: {}'


class RecordPyRevitVersionFilter(RecordFilter):
    filter_param = 'pyrevit'
    name_template = 'pyRevit Version: {}'


class RecordDebugModeFilter(RecordFilter):
    filter_param = 'debug'
    name_template = 'Debug Mode: {}'


class RecordAltScriptFilter(RecordFilter):
    filter_param = 'alternate'
    name_template = 'Alternate Mode: {}'


class RecordCommandFilter(RecordFilter):
    filter_param = 'commandname'
    name_template = 'Command Name: {}'


# class RecordBundleFilter(RecordFilter):
#     filter_param = 'commandbundle'
#     name_template = 'Bundle: {}'


class RecordBundleTypeFilter(RecordFilter):
    filter_param = 'commandbundle'
    name_template = 'Bundle Type: {}'

    def __init__(self, filter_value):
        RecordFilter.__init__(self, filter_value)
        self.filter_value = filter_value.split('.')[1]
        self.filter_name = self.name_template.format(self.filter_value)

    def filter_records(self, record_list, search_term=None):
        filtered_list = []
        for record in record_list:
            if getattr(record, self.filter_param).endswith(self.filter_value):
                if search_term:
                    if record.has_term(search_term.lower()):
                        filtered_list.append(record)
                else:
                    filtered_list.append(record)
        return filtered_list


class RecordExtensionFilter(RecordFilter):
    filter_param = 'commandextension'
    name_template = 'Extension: {}'


class RecordResultFilter(RecordFilter):
    filter_param = 'resultcode'
    name_template = 'Result Code: {}'

    def __init__(self, filter_value):
        RecordFilter.__init__(self, filter_value)
        self.filter_name = self.name_template.format(RESULT_DICT[self.filter_value])


filter_types = get_all_subclasses([RecordFilter])
FILTERS_DICT = {f.filter_param:f for f in filter_types}


def get_auto_filters(record_list):
    auto_filters = set([RecordNoneFilter()])
    for record in record_list:
        for param, value in record.__dict__.items():
            if param in FILTERS_DICT:
                logger.debug('Adding filter: param={} value={}'.format(param, value))
                auto_filters.add(FILTERS_DICT[param](value))

    return sorted(auto_filters)
