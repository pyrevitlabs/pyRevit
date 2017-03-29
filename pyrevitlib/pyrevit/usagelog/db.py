import os
import os.path as op
import json

from pyrevit import PyRevitException
from pyrevit.coreutils import calculate_dir_hash
from pyrevit.coreutils.logger import get_logger

from pyrevit.usagelog import FILE_LOG_EXT, get_current_usage_logpath
from pyrevit.usagelog.record import UsageRecord
from pyrevit.usagelog.filters import *


logger = get_logger(__name__)


def logobj_decoder(logobj):
    if 'revit' in logobj:
        new_rec = UsageRecord()
        new_rec.update(logobj)
        return new_rec
    else:
        return logobj


def _collect_records_from_file(usagelog_file):
    try:
        logger.debug('Reading usage log for: {}'.format(usagelog_file))
        with open(usagelog_file, 'r') as ulogf:
            return json.load(ulogf, object_hook=logobj_decoder)
    except Exception as err:
        raise PyRevitException('Error reading usage log for: {} | {}'.format(usagelog_file, err))


_records = []
_current_path_hash = None


def _is_record_info_current(source_path):
    dir_hash = calculate_dir_hash(source_path, '', FILE_LOG_EXT)
    if dir_hash == _current_path_hash:
        return True
    return False


def _get_all_usagelogfiles(usagelog_path=None):
    usagelog_file_list = []
    for usagelog_file in os.listdir(usagelog_path):
        if usagelog_file.endswith(FILE_LOG_EXT):
            usagelog_file_list.append(op.join(usagelog_path, usagelog_file))
    return usagelog_file_list


def _collect_all_records(source_path):
    global _records
    current_log_path = get_current_usage_logpath() if not source_path else source_path

    if current_log_path:
        if _is_record_info_current(current_log_path):
            return _records
        else:
            _records = []
            for usagelog_file in _get_all_usagelogfiles(current_log_path):
                _records.extend(_collect_records_from_file(usagelog_file))
            return _records
    else:
        return None


def get_records(source_path=None, recordfilter=None, search_term=None, reverse=True):
    all_records = _collect_all_records(source_path)

    if all_records:
        if recordfilter:
            return sorted(recordfilter.filter_records(all_records, search_term=search_term), reverse=reverse)
        else:
            return sorted(all_records, reverse=reverse)
    else:
        return None
