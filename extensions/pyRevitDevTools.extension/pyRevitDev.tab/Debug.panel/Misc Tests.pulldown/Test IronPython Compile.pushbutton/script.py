import sys
import os.path as op
import clr

from pyrevit import USER_SYS_TEMP
from pyrevit import script
from pyrevit.framework import IO

# compile
try:
    source = script.get_bundle_file('ipycompiletest.py')
    dest = op.join(USER_SYS_TEMP, 'compiledipytest.dll')
    clr.CompileModules(dest, source)
except IO.IOException as ioerr:
    print('DLL file already exists...')
except Exception as cerr:
    print('Compilation failed: {}'.format(cerr))

# import test
sys.path.append(USER_SYS_TEMP)
clr.AddReferenceToFileAndPath(dest)

import ipycompiletest

ipycompiletest.compile_test('Compiled function works.')

ipycompiletest.CompiledType('Compiled type works.')
