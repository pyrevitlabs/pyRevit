"""Read and Write Excel Files.

The vendored xlrd reads both .xlsx and .xls workbooks and xlsxwriter writes
them, on IronPython and CPython alike, so both engines return the same values.
"""

# pylint: disable=import-error
import time
import types

import xlrd
import xlsxwriter


def _give_xlrd_a_clock():
    """Restore the ``time.clock`` xlrd's .xls reader needs on Python 3.8+.

    xlrd 1.1.0 times every .xls parse with ``time.clock``, which Python 3.8
    removed, so each .xls load fails on CPython without it. Only
    ``xlrd.book`` sees the replacement; the standard ``time`` module is left
    untouched. A no-op on IronPython, which still has ``time.clock``.
    """
    if not hasattr(xlrd.book.time, "clock"):
        xlrd.book.time = types.SimpleNamespace(clock=time.perf_counter, time=time.time)


_give_xlrd_a_clock()


def _read_xlsheet(xlsheet, columns=[], datatype=None, headers=True):
    xlsheetdata = []
    xlsheetrows = list(xlsheet.get_rows())
    skip = 1 if headers else 0
    xlsheetheader = [x.value for x in xlsheetrows[0]] if headers else []
    for xlsheetrow in xlsheetrows[skip:]:
        drow = list([x.value for x in xlsheetrow])
        if columns:
            drow = dict([x for x in zip(columns, drow)])
        elif datatype:
            drow = datatype(drow)
        xlsheetdata.append(drow)
    return {"headers": xlsheetheader, "rows": xlsheetdata}


def load(xlfile, sheets=[], columns=[], datatype=None, headers=True):
    """Read data from Excel file.

    Args:
        xlfile (str): full path of the excel file to read
        sheets (list, optional): worksheets to read. Defaults to all the sheets.
        columns (list, optional): Names to give to the columns.
            It builds a dictionary for each row with the column name and value.
            If none given (default), it returns a simple list of values.
        datatype (type, optional): Type of the data. Defaults to None.
        headers (bool, optional): Whether to use the first row as headers.
            Defaults to True.

    Returns:
        (dict[str, dict[str, Any]]): Excel data grouped by worksheet.
            Each worksheet is a dictionary with `headers` and `rows`.

    Note:
        The file is read into memory and closed before parsing, so it can be
        renamed or deleted as soon as this returns. Opening it by path would
        leave xlrd's zip handle on .xlsx files open until IronPython's GC runs.
    """
    xldata = {}
    with open(xlfile, "rb") as xlstream:
        xlcontents = xlstream.read()
    xlwb = xlrd.open_workbook(file_contents=xlcontents)
    for xlsheet in xlwb.sheets():
        if sheets:
            if xlsheet.name in sheets:
                xldata[xlsheet.name] = _read_xlsheet(
                    xlsheet, columns=columns, datatype=datatype, headers=headers
                )
        else:
            xldata[xlsheet.name] = _read_xlsheet(
                xlsheet, columns=columns, datatype=datatype, headers=headers
            )
    return xldata


def dump(xlfile, datadict):
    """Write data to Excel file.

    Creates a worksheet for each item of the input dictionary.

    Args:
        xlfile (str): full path of the target excel file
        datadict (dict[str, list]): dictionary of worksheets names and data
    """
    xlwb = xlsxwriter.Workbook(xlfile)
    # bold = xlwb.add_format({'bold': True})
    for xlsheetname, xlsheetdata in datadict.items():
        xlsheet = xlwb.add_worksheet(xlsheetname)
        for idx, data in enumerate(xlsheetdata):
            xlsheet.write_row(idx, 0, data)
    xlwb.close()
