# pylint: skip-file
import os.path as op
from pyrevit import revit, USER_DESKTOP

count = 0
if revit.doc:
    count = len(revit.query.get_all_elements(doc=revit.doc))

with open(op.join(USER_DESKTOP, 'hooks.txt'), 'a') as f:
    f.write('\n'.join([
        'View Activated '.ljust(80, '-'),
        'Cancellable? ' + str(__eventargs__.Cancellable),
        'CurrentActiveView: ' + str(__eventargs__.CurrentActiveView),
        'Document: ' + str(__eventargs__.Document),
        'PreviousActiveView: ' + str(__eventargs__.PreviousActiveView),
        'Status: ' + str(__eventargs__.Status),
        'Element Count: ' + str(count)]) + '\n')
