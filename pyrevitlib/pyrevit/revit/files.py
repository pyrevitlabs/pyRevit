import os
import os.path as op
import re

from pyrevit.coreutils.logger import get_logger


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def cleanup_backups(main_revitfile):
    file_dir = op.dirname(main_revitfile)
    fname, fext = op.splitext(op.basename(main_revitfile))
    backup_fname = re.compile(r'{}\.\d\d\d\d\.{}'.format(fname,
                                                         fext.replace('.', '')))
    for f in os.listdir(file_dir):
        if backup_fname.findall(f):
            file_path = op.join(file_dir, f)
            try:
                os.remove(file_path)
            except Exception as osremove_err:
                mlogger.error('Error backup file cleanup on: %s | %s',
                              file_path, osremove_err)
