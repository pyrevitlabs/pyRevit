import os
import os.path as op

from pyrevit.coreutils import appdata

__doc__ = 'Deletes all the temporary selection data files folder. '\
          'This will clear all selection memories.'


for pymemfile in appdata.list_data_files('.pym'):
    print('Removing: {}'.format(pymemfile))
    os.remove(pymemfile)
