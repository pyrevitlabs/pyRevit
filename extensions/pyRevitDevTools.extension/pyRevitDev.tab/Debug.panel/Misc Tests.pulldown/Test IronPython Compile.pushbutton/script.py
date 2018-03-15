import sys
import os.path as op
import clr

from pyrevit import USER_SYS_TEMP
from pyrevit import script

# compile
source = script.get_bundle_file('ipycompiletest.py')
dest = op.join(USER_SYS_TEMP, 'compiledipytest.dll')
clr.CompileModules(dest, source)

# import test
sys.path.append(USER_SYS_TEMP)
clr.AddReference("compiledipytest")

import ipycompiletest

ipycompiletest.compile_test('Compiled function works.')

ipycompiletest.CompiledType('Compiled type works.')
