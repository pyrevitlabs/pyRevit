""" Standard IO Dialogs

Original code by github.com/pyrevitlabs/pyRevit

"""  #

from rpw.ui.forms.resources import *

def select_folder():
    """
    Selects a Folder Path using the standard OS Dialog.
    Uses Forms.FolderBrowserDialog(). For more information see:
    https://msdn.microsoft.com/en-us/library/system.windows.forms.openfiledialog.

    >>> from rpw.ui.forms import select_folder
    >>> folderpath = select_folder()
    'C:\\folder\\path'
    """

    form = Forms.FolderBrowserDialog()
    if form.ShowDialog() == Forms.DialogResult.OK:
        return form.SelectedPath


def select_file(extensions='All Files (*.*)|*.*',
                title="Select File",
                multiple=False,
                restore_directory=True):
    """
    Selects a File Path using the standard OS Dialog.
    Uses Forms.OpenFileDialog
    https://msdn.microsoft.com/en-us/library/system.windows.forms.filedialog.filter

    >>> from rpw.ui.forms import select_file
    >>> filepath = select_file('Revit Model (*.rvt)|*.rvt')
    'C:\\folder\\file.rvt'

    Args:
        extensions (str, optional): File Extensions Filtering options. Default is All Files (*.*)|*.*
        title (str, optional): File Extensions Filtering options
        multiple (bool): Allow selection of multiple files. Default is `False`
        restore_directory (bool): Restores the directory to the previously selected directory before closing

    Returns:
        filepath (list, string): filepath string if ``multiple=False`` otherwise list of filepath strings

    """
    form = Forms.OpenFileDialog()
    form.Filter = extensions
    form.Title = title
    form.Multiselect = multiple
    form.RestoreDirectory = restore_directory
    if form.ShowDialog() == Forms.DialogResult.OK:
        return form.FileName if not multiple else list(form.FileNames)

# Tests
if __name__ == '__main__':
    # print(select_folder())
    # print(select_file('Python Files|*.py'))
    print(select_file('Python Files|*.py', multiple=False))
    print(select_file('Python Files|*.py', multiple=True))
