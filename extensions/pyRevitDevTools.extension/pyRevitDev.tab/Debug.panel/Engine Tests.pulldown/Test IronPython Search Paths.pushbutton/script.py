"""Prints the IronPython sys.path paths."""

import os
import sys


__context__ = 'zero-doc'


folder = os.path.dirname(__file__)
print('Home directory of this script:\n{0}'.format(folder))

print('\n\nPrinting sys.path directories:')
for p in sys.path:
    print(p)

print('\n\nSys args:')
print(', '.join(sys.argv))
