"""Prints the IronPython sys.path paths."""

import os
import sys


__context__ = 'zerodoc'


folder = os.path.dirname(__file__)
print('Home directory of this script:\n{0}\n'.format(folder))

print('Printing sys.path directories:')
for p in sys.path:
    print(p)
