""""Utility methods for reporting Revit data uniformly."""

from pyrevit import DB
from pyrevit.output import PyRevitOutputWindow
from pyrevit.revit import query


def print_revision(rev, prefix='', print_id=True):
    """Print a revision.

    Args:
        rev (DB.Revision): revision to output
        prefix (str, optional): prefix to add to the output text. Defaults to empty string.
        print_id (bool, optional): whether to print the revision id. Defaults to True.
    """
    outstr = 'SEQ#: {} REV#: {} DATE: {} TYPE: {} DESC: {} ' \
             .format(rev.SequenceNumber,
                     str(query.get_param(rev, 'RevisionNumber', '')).ljust(5),
                     str(rev.RevisionDate).ljust(10),
                     str(rev.NumberType if rev.NumberType else "").ljust(15),
                     str(rev.Description).replace('\n', '').replace('\r', ''))
    if print_id:
        outstr = PyRevitOutputWindow.linkify(rev.Id) + '\t' + outstr
    print(prefix + outstr)


def print_sheet(sht, prefix='', print_id=True):
    """Print the name of a sheet.

    Args:
        sht (DB.ViewSheet): sheet to output
        prefix (str, optional): prefix to add to the output text. Defaults to empty string.
        print_id (bool, optional): whether to print the sheet id. Defaults to True.
    """
    outstr = '{}\t{}'.format(
        sht.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
        sht.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()
        )
    if print_id:
        outstr = PyRevitOutputWindow.linkify(sht.Id) + '\t' + outstr
    print(prefix + outstr)


def print_view(view, prefix='', print_id=True):
    """Print the name of a view.

    Args:
        view (DB.View): view to output
        prefix (str, optional): prefix to add to the output text. Defaults to empty string.
        print_id (bool, optional): whether to print the view id. Defaults to True.
    """
    outstr = query.get_name(view)
    if print_id:
        outstr = PyRevitOutputWindow.linkify(view.Id) + '\t' + outstr
    print(prefix + outstr)
