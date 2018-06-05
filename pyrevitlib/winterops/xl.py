"""Read and Write Excel Files."""

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
    # create workbook
    xlwb = xlsxwriter.Workbook(xlfile)
    # bold = xlwb.add_format({'bold': True})
    for xlsheetname, xlsheetdata in datadict.items():
        xlsheet = xlwb.add_worksheet(xlsheetname)
        for idx, data in enumerate(xlsheetdata):
            xlsheet.write_row(idx, 0, data)
    xlwb.close()
