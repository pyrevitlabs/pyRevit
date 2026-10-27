"""Read and write Excel files on both Python engines.

CPython reads and writes ``.xlsx`` workbooks with openpyxl and reads legacy
``.xls`` workbooks with the vendored xlrd. IronPython keeps xlrd and
xlsxwriter for every workbook.
"""

import os.path as op

from pyrevit.compat import IRONPY


if IRONPY:
    import xlrd
    import xlsxwriter
else:
    import openpyxl


def _uses_openpyxl(xlfile):
    return not IRONPY and op.splitext(str(xlfile))[1].lower() != ".xls"


def _open_legacy_workbook(xlfile):
    """Open an ``.xls`` workbook with xlrd, which predates ``time.clock`` removal."""
    import xlrd
    import xlrd.book

    if not hasattr(xlrd.book.time, "clock"):
        import time
        import types

        xlrd.book.time = types.SimpleNamespace(clock=time.perf_counter, time=time.time)
    return xlrd.open_workbook(str(xlfile))


def _sheet_rows(xlsheet, openpyxl_sheet):
    if openpyxl_sheet:
        return [list(row) for row in xlsheet.iter_rows(values_only=True)]
    return [[cell.value for cell in row] for row in xlsheet.get_rows()]


def _read_xlsheet(xlsheet, openpyxl_sheet, columns=None, datatype=None, headers=True):
    columns = columns or []
    xlsheetrows = _sheet_rows(xlsheet, openpyxl_sheet)
    xlsheetheader = xlsheetrows[0] if headers and xlsheetrows else []
    xlsheetdata = []
    for drow in xlsheetrows[1 if headers else 0 :]:
        if columns:
            drow = dict([x for x in zip(columns, drow)])
        elif datatype:
            drow = datatype(drow)
        xlsheetdata.append(drow)
    return {"headers": xlsheetheader, "rows": xlsheetdata}


def load(xlfile, sheets=None, columns=None, datatype=None, headers=True):
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
    """
    sheets = sheets or []
    openpyxl_sheets = _uses_openpyxl(xlfile)
    if openpyxl_sheets:
        worksheets = [
            (sheet.title, sheet)
            for sheet in openpyxl.load_workbook(xlfile, data_only=True).worksheets
        ]
    elif IRONPY:
        worksheets = [
            (sheet.name, sheet) for sheet in xlrd.open_workbook(xlfile).sheets()
        ]
    else:
        worksheets = [
            (sheet.name, sheet) for sheet in _open_legacy_workbook(xlfile).sheets()
        ]
    xldata = {}
    for xlsheet_name, xlsheet in worksheets:
        if sheets and xlsheet_name not in sheets:
            continue
        xldata[xlsheet_name] = _read_xlsheet(
            xlsheet,
            openpyxl_sheets,
            columns=columns,
            datatype=datatype,
            headers=headers,
        )
    return xldata


def dump(xlfile, datadict):
    """Write data to Excel file.

    Creates a worksheet for each item of the input dictionary. An empty
    dictionary still produces a workbook with one empty worksheet.

    Args:
        xlfile (str): full path of the target excel file
        datadict (dict[str, list]): dictionary of worksheets names and data
    """
    if IRONPY:
        xlwb = xlsxwriter.Workbook(xlfile)
        for xlsheetname, xlsheetdata in datadict.items():
            xlsheet = xlwb.add_worksheet(xlsheetname)
            for idx, data in enumerate(xlsheetdata):
                xlsheet.write_row(idx, 0, data)
        xlwb.close()
        return
    xlwb = openpyxl.Workbook()
    if datadict:
        xlwb.remove(xlwb.active)
    for xlsheetname, xlsheetdata in datadict.items():
        xlsheet = xlwb.create_sheet(xlsheetname)
        for data in xlsheetdata:
            xlsheet.append(list(data))
    xlwb.save(xlfile)
