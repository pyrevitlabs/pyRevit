import os
import os.path as op
import re

def cleanup_backups(main_revitfile):
    file_dir = op.dirname(main_revitfile)
    fname, fext = op.splitext(op.basename(main_revitfile))
    backup_fname = re.compile('{}\.\d\d\d\d\.{}'.format(fname,
                                                        fext.replace('.', '')))
    for f in os.listdir(file_dir):
        if backup_fname.findall(f):
            try:
                os.remove(op.join(file_dir, f))
            except Exception as osremove_err:
                logger.error('Error backup file cleanup on: {} | {}'
                             .format(file_path, osremove_err))
