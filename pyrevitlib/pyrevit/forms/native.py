"""Engine-independent Revit task dialogs and native file pickers."""

import sys

from pyrevit import EXEC_PARAMS, UI, coreutils, versionmgr
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import Forms, CPDialogs, System
from . import _backend

mlogger = get_logger(__name__)


def alert(
    msg,
    title=None,
    sub_msg=None,
    expanded=None,
    footer="",
    ok=True,
    cancel=False,
    yes=False,
    no=False,
    retry=False,
    warn_icon=True,
    icon="",
    options=None,
    exitscript=False,
):
    r"""Show a task dialog with given message.

    Args:
        msg (str): message to be displayed
        title (str, optional): task dialog title
        sub_msg (str, optional): sub message, use html to create clickable links
        expanded (str, optional): expanded area message
        footer (str, optional): footer text
        ok (bool, optional): show OK button, defaults to True
        cancel (bool, optional): show Cancel button, defaults to False
        yes (bool, optional): show Yes button, defaults to False
        no (bool, optional): show NO button, defaults to False
        retry (bool, optional): show Retry button, defaults to False
        warn_icon (bool, optional): show "warning" icon. Ignored if `icon` is used. Defaults to True
        icon (str, optional): icon to show, from one of "warning", "shield", "information", "error".
            When provided (non-empty), this takes full precedence over `warn_icon` and `warn_icon` is ignored.
        options (list[str], optional): list of command link titles in order
        exitscript (bool, optional): exit if cancel or no, defaults to False

    Returns:
        (bool): True if okay, yes, or retry, otherwise False

    Examples:
        ```python
        from pyrevit import forms
        forms.alert('Are you sure?',
                    sub_msg='<a href=\"https://discourse.pyrevitlabs.io/ \">Click here if you are not sure and want to go to the pyRevit Forum</a>',
                    ok=False, yes=True, no=True, exitscript=True)
        ```
    """
    # BUILD DIALOG
    cmd_name = EXEC_PARAMS.command_name
    if not title:
        title = cmd_name if cmd_name else "pyRevit"
    tdlg = UI.TaskDialog(title)

    # process input types
    just_ok = ok and not any([cancel, yes, no, retry])

    options = options or []
    # add command links if any
    if options:
        clinks = coreutils.get_enum_values(UI.TaskDialogCommandLinkId)
        max_clinks = len(clinks)
        for idx, cmd in enumerate(options):
            if idx < max_clinks:
                tdlg.AddCommandLink(clinks[idx], cmd)
    # otherwise add buttons
    else:
        buttons = coreutils.get_enum_none(UI.TaskDialogCommonButtons)
        if yes:
            buttons |= UI.TaskDialogCommonButtons.Yes
        elif ok:
            buttons |= UI.TaskDialogCommonButtons.Ok

        if cancel:
            buttons |= UI.TaskDialogCommonButtons.Cancel
        if no:
            buttons |= UI.TaskDialogCommonButtons.No
        if retry:
            buttons |= UI.TaskDialogCommonButtons.Retry
        tdlg.CommonButtons = buttons

    # set texts
    tdlg.MainInstruction = msg
    tdlg.MainContent = sub_msg
    tdlg.ExpandedContent = expanded
    if footer:
        footer = footer.strip() + "\n"
    tdlg.FooterText = footer + "pyRevit {}".format(
        versionmgr.get_pyrevit_version().get_formatted()
    )
    tdlg.TitleAutoPrefix = False

    # set icon
    icon_map = {
        "warning": UI.TaskDialogIcon.TaskDialogIconWarning,
        "shield": UI.TaskDialogIcon.TaskDialogIconShield,
        "information": UI.TaskDialogIcon.TaskDialogIconInformation,
        "error": UI.TaskDialogIcon.TaskDialogIconError,
    }

    if icon:
        # `icon` takes precedence if provided
        key = icon.lower()
        if key not in icon_map:
            mlogger.warning(
                "Unknown icon %r; falling back to no icon. Valid icons: %s",
                icon,
                ", ".join(sorted(icon_map)),
            )
        tdlg.MainIcon = icon_map.get(key, UI.TaskDialogIcon.TaskDialogIconNone)
    else:
        # else fall back to legacy `warn_icon` behavior to prevent breaking of existing scripts
        tdlg.MainIcon = (
            UI.TaskDialogIcon.TaskDialogIconWarning
            if warn_icon
            else UI.TaskDialogIcon.TaskDialogIconNone
        )

    # tdlg.VerificationText = 'verif'

    # SHOW DIALOG
    res = tdlg.Show()

    # PROCESS REPONSES
    # positive response
    mlogger.debug("alert result: %s", res)
    if (
        res == UI.TaskDialogResult.Ok
        or res == UI.TaskDialogResult.Yes
        or res == UI.TaskDialogResult.Retry
    ):
        if just_ok and exitscript:
            sys.exit()
        return True
    # negative response
    elif (
        res == coreutils.get_enum_none(UI.TaskDialogResult)
        or res == UI.TaskDialogResult.Cancel
        or res == UI.TaskDialogResult.No
    ):
        if exitscript:
            sys.exit()
        else:
            return False

    # command link response
    elif "CommandLink" in str(res):
        tdresults = sorted(
            [
                x
                for x in coreutils.get_enum_values(UI.TaskDialogResult)
                if "CommandLink" in str(x)
            ],
            key=System.Convert.ToInt32,
        )
        residx = tdresults.index(res)
        return options[residx]
    elif exitscript:
        sys.exit()
    else:
        return False


def alert_ifnot(condition, msg, *args, **kwargs):
    """Show a task dialog with given message if condition is NOT met.

    Args:
        condition (bool): condition to test
        msg (str): message to be displayed
        *args (Any): additional arguments
        **kwargs (Any): additional keyword arguments

    Keyword Args:
        title (str, optional): task dialog title
        ok (bool, optional): show OK button, defaults to True
        cancel (bool, optional): show Cancel button, defaults to False
        yes (bool, optional): show Yes button, defaults to False
        no (bool, optional): show NO button, defaults to False
        retry (bool, optional): show Retry button, defaults to False
        exitscript (bool, optional): exit if cancel or no, defaults to False

    Returns:
        (bool): True if okay, yes, or retry, otherwise False

    Examples:
        ```python
        from pyrevit import forms
        forms.alert_ifnot(value > 12,
                          'Are you sure?',
                           ok=False, yes=True, no=True, exitscript=True)
        ```
    """
    if not condition:
        return alert(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """Show a warning-styled task dialog.

    Args:
        msg (str): Message shown to the user.
        *args: Positional arguments accepted by :func:`alert`.
        **kwargs: Keyword arguments accepted by :func:`alert`.

    Returns:
        bool: The selected task-dialog response.
    """
    kwargs.setdefault("warn_icon", True)
    return alert(msg, *args, **kwargs)


def pick_folder(title=None, owner=None, init_dir=""):
    """Show standard windows pick folder dialog.

    Args:
        title (str, optional): title for the window
        owner (object, optional): owner of the dialog
        init_dir (str, optional): initial directory

    Returns:
        (str): folder path
    """
    if CPDialogs:
        fb_dlg = CPDialogs.CommonOpenFileDialog()
        fb_dlg.IsFolderPicker = True
        if title:
            fb_dlg.Title = title
        if init_dir:
            fb_dlg.InitialDirectory = init_dir

        res = CPDialogs.CommonFileDialogResult.Cancel
        if owner:
            res = fb_dlg.ShowDialog(_backend.unwrap(owner))
        else:
            res = fb_dlg.ShowDialog()

        if res == CPDialogs.CommonFileDialogResult.Ok:
            return fb_dlg.FileName
    else:
        fb_dlg = Forms.FolderBrowserDialog()
        if title:
            fb_dlg.Description = title
        if init_dir:
            fb_dlg.SelectedPath = init_dir
        if fb_dlg.ShowDialog() == Forms.DialogResult.OK:
            return fb_dlg.SelectedPath


def pick_file(
    file_ext="*",
    files_filter="",
    init_dir="",
    restore_dir=True,
    multi_file=False,
    unc_paths=False,
    title=None,
):
    r"""Pick file dialog to select a destination file.

    Args:
        file_ext (str): file extension
        files_filter (str): file filter
        init_dir (str): initial directory
        restore_dir (bool): restore last directory
        multi_file (bool): allow select multiple files
        unc_paths (bool): return unc paths
        title (str): text to show in the title bar

    Returns:
        (str | System.String[] | list[str]): file path. With ``multi_file=True``,
            the dialog's .NET ``String[]`` of paths on both engines, or a Python
            list of UNC paths when ``unc_paths=True``.

    Examples:
        ```python
        from pyrevit import forms
        forms.pick_file(file_ext='csv')
        r'C:\output\somefile.csv'
        ```

        ```python
        forms.pick_file(file_ext='csv', multi_file=True)
        [r'C:\output\somefile1.csv', r'C:\output\somefile2.csv']
        ```

        ```python
        forms.pick_file(files_filter='All Files (*.*)|*.*|'
                                         'Excel Workbook (*.xlsx)|*.xlsx|'
                                         'Excel 97-2003 Workbook|*.xls',
                            multi_file=True)
        [r'C:\output\somefile1.xlsx', r'C:\output\somefile2.xls']
        ```
    """
    of_dlg = Forms.OpenFileDialog()
    if files_filter:
        of_dlg.Filter = files_filter
    else:
        of_dlg.Filter = "|*.{}".format(file_ext)
    of_dlg.RestoreDirectory = restore_dir
    of_dlg.Multiselect = multi_file
    if init_dir:
        of_dlg.InitialDirectory = init_dir
    if title:
        of_dlg.Title = title
    if of_dlg.ShowDialog() == Forms.DialogResult.OK:
        if multi_file:
            if unc_paths:
                return [coreutils.dletter_to_unc(x) for x in of_dlg.FileNames]
            return of_dlg.FileNames
        else:
            if unc_paths:
                return coreutils.dletter_to_unc(of_dlg.FileName)
            return of_dlg.FileName


def save_file(
    file_ext="",
    files_filter="",
    init_dir="",
    default_name="",
    restore_dir=True,
    unc_paths=False,
    title=None,
):
    r"""Save file dialog to select a destination file for data.

    Args:
        file_ext (str): file extension
        files_filter (str): file filter
        init_dir (str): initial directory
        default_name (str): default file name
        restore_dir (bool): restore last directory
        unc_paths (bool): return unc paths
        title (str): text to show in the title bar

    Returns:
        (str): file path

    Examples:
        ```python
        from pyrevit import forms
        forms.save_file(file_ext='csv')
        r'C:\output\somefile.csv'
        ```
    """
    sf_dlg = Forms.SaveFileDialog()
    if files_filter:
        sf_dlg.Filter = files_filter
    else:
        sf_dlg.Filter = "|*.{}".format(file_ext)
    sf_dlg.RestoreDirectory = restore_dir
    if init_dir:
        sf_dlg.InitialDirectory = init_dir
    if title:
        sf_dlg.Title = title

    # setting default filename
    sf_dlg.FileName = default_name

    if sf_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(sf_dlg.FileName)
        return sf_dlg.FileName


def pick_excel_file(save=False, title=None):
    """File pick/save dialog for an excel file.

    Args:
        save (bool): show file save dialog, instead of file pick dialog
        title (str): text to show in the title bar

    Returns:
        (str): file path
    """
    if save:
        return save_file(file_ext="xlsx")
    return pick_file(
        files_filter="Excel Workbook (*.xlsx)|*.xlsx|Excel 97-2003 Workbook|*.xls",
        title=title,
    )


def save_excel_file(title=None):
    """File save dialog for an excel file.

    Args:
        title (str): text to show in the title bar

    Returns:
        (str): file path
    """
    return pick_excel_file(save=True, title=title)


def ask_for_color(default=None):
    """Show system color picker and ask for color.

    Args:
        default (str): default color in HEX ARGB e.g. #ff808080

    Returns:
        (str): selected color in HEX ARGB e.g. #ff808080, or None if cancelled

    Examples:
        ```python
        forms.ask_for_color()
        '#ff808080'
        ```
    """
    # colorDlg.Color
    color_picker = Forms.ColorDialog()
    if default:
        default = default.replace("#", "")
        color_picker.Color = System.Drawing.Color.FromArgb(
            int(default[:2], 16),
            int(default[2:4], 16),
            int(default[4:6], 16),
            int(default[6:8], 16),
        )
    color_picker.FullOpen = True
    if color_picker.ShowDialog() == Forms.DialogResult.OK:
        c = color_picker.Color
        c_hex = "".join("{:02X}".format(int(x)) for x in [c.A, c.R, c.G, c.B])
        return "#" + c_hex
