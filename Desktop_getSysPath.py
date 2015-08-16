import sys, os
folder = os.path.dirname(__file__)
print('Home directory of this script:\n{0}\n'.format( folder ))

sys.path.append(folder)

import pyRevit
print('pyRevit import successful\n')

print('Printing sys.path addresses:')
for p in sys.path:
	print(p)