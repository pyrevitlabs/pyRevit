# coding: utf8

import clr
clr.AddReferenceByName('Microsoft.Office.Interop.Excel, Version=11.0.0.0, Culture=neutral, PublicKeyToken=71e9bce111e9429c')
from Microsoft.Office.Interop import Excel
from Microsoft.Office.Interop.Excel import XlListObjectSourceType, Worksheet, Range, XlYesNoGuess
from System.Runtime.InteropServices import Marshal


class ExcelApp:
    def __init__(self, app=None, workbook=None):
        self.app = app
        self.workbook = workbook


def initialise():
    """Get active Excel.Application COM object if available or create a new one"""
    # If Excel is open, get it
    try:
        return Marshal.GetActiveObject("Excel.Application")
    # Else open it
    except EnvironmentError:
        return Excel.ApplicationClass()

def release(com_object):
    """Release given Excel.Application COM Object"""
    Marshal.ReleaseComObject(com_object)


def table_style(worksheet, xl_range):
    """
    Apply TableStyle to given Range on given Worksheet
    :type xl_range: Range
    :type worksheet: Worksheet
    """
    worksheet.ListObjects.Add(SourceType=XlListObjectSourceType.xlSrcRange,
                              Source=xl_range,
                              XlListObjectHasHeaders=XlYesNoGuess.xlYes,
                              TableStyleName="TableStyleMedium15")


def workbook_by_name(app, name):
    for workbook in app.Workbooks:
        if workbook.Name == name:
            return workbook


def none():
    try:
        workbook = app.ActiveWorkbook
    except AttributeError:
        workbook = app.Workbooks.Add()


def worksheet_by_name(workbook, name):
    for worksheet in workbook.Sheets:
        if worksheet.Name == name:
            return worksheet
