"""Read and Write Excel Files."""
# pylint: disable=import-error
import xlrd
import xlsxwriter


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
    return {'headers': xlsheetheader, 'rows': xlsheetdata}


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
    """
    xldata = {}
    xlwb = xlrd.open_workbook(xlfile)
    for xlsheet in xlwb.sheets():
        if sheets:
            if xlsheet.name in sheets:
                xldata[xlsheet.name] = _read_xlsheet(xlsheet,
                                                     columns=columns,
                                                     datatype=datatype,
                                                     headers=headers)
        else:
            xldata[xlsheet.name] = _read_xlsheet(xlsheet,
                                                 columns=columns,
                                                 datatype=datatype,
                                                 headers=headers)
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
