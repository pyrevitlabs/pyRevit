"""
Provides base class and standard filters to filter the usage records data,
provided by the pyrevit.usagelog module.

    Base filter class is:
        >>> RecordFilter()

    This module provides a function ``get_auto_filters()`` that looks into the provided
    records list and automatically creates useful filters for that data.
        >>> get_auto_filters(record_list)

"""

from collections import defaultdict

from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger
from pyrevit.usagelog.record import RESULT_DICT


logger = get_logger(__name__)


class RecordFilter(object):
    """Superclass of all UsageRecord filters. Use the subclasses for each of access to standard parameters.

    Attributes:
        filter_param (str): This is the parameter name of the UsageRecord object, filtered by this filter
        name_template (str): This template is used to create a human-readable name for the filter
        filter_value (str): Any UsageRecord object that object.filter_param == filter_value, will pass the filter
        filter_name (str): Human-readable name for this filter.
    """

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
        # less-than operator overload that causes the filter list to be sorted by name and then by value
        # if two filters are the same type, compare based on filter_value
        if type(self) == type(other):
            return self.filter_value < other.filter_value
        else:
            # if not, compare based on filter_name
            return self.filter_name < other.filter_name

    def filter_records(self, record_list, search_term=None):
        """Filters the input list of UsageRecord objects.

        Example:
            >>> filter = RecordCommandFilter('command name to filter')
            >>> filter.filter_records(all_records, search_term="some term")

        Args:
            record_list (list): List of UsageRecord object to be filtered
            search_term (str): If provided, filters all objects that pass object.has_term(search_term)

        Returns:
            list: Filtered list of UsageRecord objects.

        """

        filtered_list = []
        for record in record_list:
            # test for paraemter value
            if getattr(record, self.filter_param) == self.filter_value:
                # Passed filter value test:
                if search_term:
                    # check for search_term if provided
                    if record.has_term(search_term.lower()):
                        filtered_list.append(record)
                else:
                    # else add to filtered_list
                    filtered_list.append(record)

        return filtered_list


class RecordNoneFilter(RecordFilter):
    """RecordFilter that has no effect. All records pass this filter."""

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
    """Filters records based on bundle type (e.g. pushbutton)."""

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
    """
    Filters records based on result code (e.g. 0, 1, 2).
    Also overrides filter_name to convert the integer result code to human-readable code name.
    """

    filter_param = 'resultcode'
    name_template = 'Result Code: {}'

    def __init__(self, filter_value):
        RecordFilter.__init__(self, filter_value)
        # overrides filter_name to convert the integer result code to human-readable codename
        self.filter_name = self.name_template.format(RESULT_DICT[self.filter_value])


# lets find all subclasses of the RecordFilter class (all custom filters)
filter_types = get_all_subclasses([RecordFilter])
# and make a filter dictionary based on the filter parameter names
# so FILTERS_DICT['commandname'] returns a filter that filters the
# records based on their 'commandname' property
FILTERS_DICT = {f.filter_param:f for f in filter_types}


def get_auto_filters(record_list):
    """
    Returns a list of RecordFilter objects. This function works on the input list of usage records.
    This function traverses the usage records list, finds the parameters on each record object and
    creates a filter object for each (if a subclass of RecordFilter is available to that parameter)

    Any of the filter objects returned from this function, can be passed to the db.get_records() method
    to filter the usage record data.

        Example of typical use:
        >>> all_unfiltered_records = pyrevit.usagelog.db.get_records()
        >>> filter_list = pyrevit.usagelog.filters.get_auto_filters(all_unfiltered_records)
        >>> chosen_filter = filter_list[n]
        >>> filtered_records = pyrevit.usagelog.db.get_records(record_filter=chosen_filter)

    Args:
        record_list (list): list of UsageRecord objects

    Returns:
        list: returns a list of RecordFilter objects, sorted; Empty list if no filters could be created.
    """

    # make a filter list and add the `None` filter to it.
    auto_filters = set([RecordNoneFilter()])
    for record in record_list:
        # find parameters in the record object
        for param, value in record.__dict__.items():
            if param in FILTERS_DICT:
                # and if a filter is provided for that parameter, setup the filter and add to the list.
                logger.debug('Adding filter: param={} value={}'.format(param, value))
                auto_filters.add(FILTERS_DICT[param](value))

    # return a sorted list of filters for ease of use
    return sorted(auto_filters)
