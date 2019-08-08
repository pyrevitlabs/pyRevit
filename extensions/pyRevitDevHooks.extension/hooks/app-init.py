# python3
# pylint: skip-file

import os.path as op
import datetime
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')
HOOK_LOGS = op.join(USER_DESKTOP, 'hooks.log')


def _timestamp():
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")


def _write_record(record_str):
    with open(HOOK_LOGS, 'a') as f:
        f.write(record_str + '\n')


def log_hook():
    # collect document element count as doc access test if requested
    # write log record with data
    record_str = "{} [app-init] cpython".format(_timestamp())
    _write_record(record_str)


log_hook()