import os
import os.path as op

from pyrevit.coreutils import appdata

__doc__ = 'Deletes all the temporary selection data files from user temp'\
          ' folder. This will clear all selection memories. '\
          'This is a project-dependent (Revit *.rvt) memory. '\
          'Every project has its own memory saved in user temp folder '\
          'as *.pym files.'


for pymemfile in appdata.list_data_files('.pym'):
    print('Removing: {}'.format(pymemfile))
    os.remove(pymemfile)
