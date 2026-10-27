"""Read and write Excel files on both Python engines."""

from pyrevit.compat import PY3


if PY3:
    import openpyxl
else:
    import xlrd
    import xlsxwriter


def _read_xlsheet(xlsheet, columns=None, datatype=None, headers=True):
    columns = columns or []
    xlsheetdata = []
    xlsheetrows = (
        list(xlsheet.iter_rows(values_only=True)) if PY3 else list(xlsheet.get_rows())
    )
    skip = 1 if headers else 0
    xlsheetheader = list(xlsheetrows[0]) if PY3 and headers else []
    if not PY3 and headers:
        xlsheetheader = [cell.value for cell in xlsheetrows[0]]
    for xlsheetrow in xlsheetrows[skip:]:
        drow = list(xlsheetrow) if PY3 else [cell.value for cell in xlsheetrow]
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
    xldata = {}
    sheets = sheets or []
    xlwb = (
        openpyxl.load_workbook(xlfile, data_only=True)
        if PY3
        else xlrd.open_workbook(xlfile)
    )
    worksheets = xlwb.worksheets if PY3 else xlwb.sheets()
    for xlsheet in worksheets:
        xlsheet_name = xlsheet.title if PY3 else xlsheet.name
        if sheets:
            if xlsheet_name in sheets:
                xldata[xlsheet_name] = _read_xlsheet(
                    xlsheet, columns=columns, datatype=datatype, headers=headers
                )
        else:
            xldata[xlsheet_name] = _read_xlsheet(
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
    xlwb = openpyxl.Workbook() if PY3 else xlsxwriter.Workbook(xlfile)
    if PY3:
        xlwb.remove(xlwb.active)
    for xlsheetname, xlsheetdata in datadict.items():
        xlsheet = (
            xlwb.create_sheet(xlsheetname) if PY3 else xlwb.add_worksheet(xlsheetname)
        )
        for idx, data in enumerate(xlsheetdata):
            if PY3:
                xlsheet.append(list(data))
            else:
                xlsheet.write_row(idx, 0, data)
    if PY3:
        xlwb.save(xlfile)
    else:
        xlwb.close()
