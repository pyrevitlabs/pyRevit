"""Test standard input in pyRevit console window."""
# pylint: disable-all
__context__ = 'zero-doc'
__fullframeengine__ = True

import pdb
pdb.set_trace()

def debug_test(value):
    i = 12
    print(value)
    print(i)

for idx in range(2):
    debug_test(idx)
