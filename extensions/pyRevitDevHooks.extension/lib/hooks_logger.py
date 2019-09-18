# pylint: skip-file
import re
import os.path as op
import datetime
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')
HOOK_LOGS = op.join(USER_DESKTOP, 'hooks.log')


def _timestamp():
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")


def _write_record(record_str):
    with open(HOOK_LOGS, 'a') as f:
        f.write(record_str + '\n')


def _get_hook_parts(hook_script):
    # finds the two parts of the hook script name
    # e.g command-before-exec[ID_INPLACE_COMPONENT].py
    # ('command-before-exec', 'ID_INPLACE_COMPONENT')
    parts = re.findall(
        r'([a-z -]+)\[?([A-Z _]+)?\]?\..+',
        op.basename(hook_script)
        )
    if parts:
        return parts[0]
    else:
        return '', ''


def log_hook(hook_file, data, log_doc_access=False):
    hook_name, hook_target = _get_hook_parts(hook_file)
    # collect document element count as doc access test if requested
    doc = None
    if log_doc_access:
        from pyrevit import revit
        if revit.doc:
            doc = revit.doc
        elif hasattr(__eventargs__, 'GetDocument'):
            doc = __eventargs__.GetDocument()
    count = None
    if doc:
        count = len(revit.query.get_all_elements(doc=doc))

    # write log record with data
    record_str = "{} [{}] ".format(_timestamp(), hook_name)
    for k,v in data.items():
        record_str += '{}: "{}" '.format(k, v)
    record_str += 'count: {}'.format(str(count))
    _write_record(record_str)