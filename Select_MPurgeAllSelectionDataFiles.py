__window__.Close()

import os
import os.path as op

usertemp = os.getenv('Temp')
files = os.listdir( usertemp )
files = [ fi for fi in files if fi.endswith(".sel") ]
for f in files:
	os.remove( op.join( usertemp, f) )