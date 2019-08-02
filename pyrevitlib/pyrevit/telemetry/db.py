"""
This module is used to access the telemetry records saved in telemetry
files. It is not used to access the telemetry records sent to a
remote logging server.

    It has only one public function:
        >>> get_records()
        This function accepts, source directory, filters, and search terms
        and returns sorted results. See more on function documentation.

"""

import os
import os.path as op
import json

#pylint: disable=W0703,C0302,C0103,W0614,W0401,W0603
from pyrevit import PyRevitException
from pyrevit.coreutils import calculate_dir_hash
from pyrevit.coreutils.logger import get_logger


from pyrevit import telemetry
from pyrevit.telemetry.record import TelemetryRecord
from pyrevit.telemetry.filters import *


mlogger = get_logger(__name__)


def _logobj_decoder(logobj):
    # decoder function that receives object dictionary from json.load method
    # and returns the object that owns that data
    if 'revit' in logobj:
        # if 'revit' is in the keys, it means its a TelemetryRecord object.
        new_rec = TelemetryRecord()
        new_rec.update(logobj)
        return new_rec
    else:
        # else it is not TelemetryRecord. It could be the command results
        # dictionary or other dictionaries, saved in command results.
        return logobj


def _collect_records_from_file(telemetry_file):
    # collect all telemetry records from the provided file
    try:
        mlogger.debug('Reading telemetry for: %s', telemetry_file)
        with open(telemetry_file, 'r') as ulogf:
            record_list = json.load(ulogf, object_hook=_logobj_decoder)
            for record in record_list:
                record.logfilename = telemetry_file
            return record_list
    except Exception as err:
        raise PyRevitException('Error reading telemetry for: {} | {}'
                               .format(telemetry_file, err))


_records = []
_current_path_hash = None


def _is_record_info_current(source_path):
    # calculates a hash from the log files in the directory and compares it
    # with the _current_path_hash
    # (to determine if the current _records list is up-to-date)
    dir_hash = calculate_dir_hash(source_path, '', telemetry.FILE_LOG_EXT)
    if dir_hash == _current_path_hash:
        return True
    return False


def _get_all_telemetry_files(telemetry_path=None):
    # returns a list of all telemetry files in the
    # default or provided directory
    telemetry_file_list = []
    for telemetry_file in os.listdir(telemetry_path):
        if telemetry_file.endswith(telemetry.FILE_LOG_EXT):
            telemetry_file_list.append(op.join(telemetry_path, telemetry_file))
    return telemetry_file_list


def _collect_all_records(source_path=None):
    # collects all log records in all the telemetry files
    global _records

    # use the default telemetry file path if source_path is not provided
    current_log_path = telemetry.get_telemetry_file_dir() \
        if not source_path else source_path

    if current_log_path:
        # TODO: implement per file hash check to improve performance
        # check to make sure the data held in _records is up-to-date
        if _is_record_info_current(current_log_path):
            # return loaded data if it is up-to-date
            return _records
        else:
            # if not, let's read the data again
            _records = []
            for telemetry_file in _get_all_telemetry_files(current_log_path):
                _records.extend(_collect_records_from_file(telemetry_file))
            return _records
    else:
        return None


def get_records(source_path=None, record_filter=None,
                search_term=None, reverse=True):
    """
    Returns a list of TelemetryRecord objects. Each TelemetryRecord object represents
    a telemetry entry. if record_filter argument is provided with a
    RecordFilter (or any of the subclasses) object, this function will filter
    the records as well. Filter objects are provided in
    pyrevit.telemetry.filters module.

    Returned record list is sorterd using sorted() function.
    The TelemetryRecord object provides necessary methods to allow sorting
    based on time and date. So the result will be sorted by date:time.

    Args:
        source_path (str): Directory address of telemetry file locations.
        record_filter (RecordFilter): RecordFilter object or its subclasses.
        search_term (str): Only return the results that include this string.
        reverse (bool): Reverse the result list order.

    Returns:
        list: returns a list of TelemetryRecord objects, sorted by date:time;
              Empty list if no records
    """

    all_records = _collect_all_records(source_path)

    if all_records:
        if record_filter:
            return sorted(record_filter.filter_records(all_records,
                                                       search_term=search_term),
                          reverse=reverse)
        else:
            return sorted(all_records, reverse=reverse)
    else:
        return None
