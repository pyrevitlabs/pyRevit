import sys
import os.path as op
print '\n'.join(sys.path)
sys.path.append(op.dirname(__file__))

from pyrevit.loader.sessionmgr import load_session

load_session()
