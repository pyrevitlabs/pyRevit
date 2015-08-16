__window__.Close()
import os
import os.path as op
folder = op.dirname(__file__)
print(folder)
os.startfile( op.join( folder, '__py__simpleInOutList.py' ))