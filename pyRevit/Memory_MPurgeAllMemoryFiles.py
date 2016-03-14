__doc__ = 'Deletes all the temporary selection data files from user temp folder. This will clear all selection memories. This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in user temp folder as *.pym files.'

# __window__.Close()

import os
import os.path as op

usertemp = os.getenv('Temp')
files = os.listdir( usertemp )
files = [ fi for fi in files if fi.endswith(".pym") ]
for f in files:
	print( f )
	os.remove( op.join( usertemp, f) )