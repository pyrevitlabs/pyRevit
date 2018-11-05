""""Utility methods for reporting Revit data uniformly."""

from pyrevit import DB
from pyrevit.output import PyRevitOutputWindow
from pyrevit.revit import db


def print_revision(rev, prefix='', print_id=True):
    wrev = db.ElementWrapper(rev)
    outstr = 'SEQ#: {} REV#: {} DATE: {} TYPE: {} DESC: {} ' \
             .format(rev.SequenceNumber,
                     str(wrev.safe_get_param('RevisionNumber', '')).ljust(5),
                     str(rev.RevisionDate).ljust(10),
                     str(rev.NumberType.ToString()).ljust(15),
                     str(rev.Description).replace('\n', '').replace('\r', ''))
    if print_id:
        outstr = PyRevitOutputWindow.linkify(rev.Id) + '\t' + outstr
    print(prefix + outstr)


def print_sheet(sht, prefix='', print_id=True):
    outstr = '{}\t{}'.format(
        sht.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
        sht.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()
        )
    if print_id:
        outstr = PyRevitOutputWindow.linkify(sht.Id) + '\t' + outstr
    print(prefix + outstr)
