# pylint: skip-file
import os.path as op
from pyrevit import revit, USER_DESKTOP

count = 0
doc = revit.doc if revit.doc else __eventargs__.GetDocument()
count = len(revit.query.get_all_elements(doc=doc))

with open(op.join(USER_DESKTOP, 'hooks.txt'), 'a') as f:
    f.write('\n'.join([
        'Document Changed '.ljust(80, '-'),
        'Cancellable? ' + str(__eventargs__.Cancellable),
        'Operation: ' + str(__eventargs__.Operation),
        'Element Count: ' + str(count)]) + '\n')