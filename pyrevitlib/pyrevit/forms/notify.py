"""User notifications through Revit InfoCenter and Windows toast helpers."""

from pyrevit.forms import toaster


def result_item_result_clicked(sender, e, debug=False):
    """Callback for a result item click event."""
    if debug:
        print("Result clicked")  # using print_md here will break the script
    pass


def show_balloon(
    header,
    text,
    tooltip="",
    group="",
    is_favourite=False,
    is_new=False,
    timestamp=None,
    click_result=result_item_result_clicked,
):
    r"""Show ballon in the info center section.

    Args:
        header (str): Category section (Bold)
        text (str): Title section (Regular)
        tooltip (str): Tooltip
        group (str): Group
        is_favourite (bool): Add a blue star before header
        is_new (bool): Flag to new
        timestamp (str): Set timestamp
        click_result (def): Executed after a click event

    Examples:
        ```python
        from pyrevit import forms
        date = '2019-01-01 00:00:00'
        date = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        forms.show_balloon("my header", "Lorem ipsum", tooltip='tooltip',   group='group', is_favourite=True, is_new=True, timestamp = date, click_result = forms.result_item_result_clicked)
        ```
    """
    import Autodesk.Internal.InfoCenter
    import Autodesk.Windows.ComponentManager

    result_item = Autodesk.Internal.InfoCenter.ResultItem()
    result_item.Category = header
    result_item.Title = text
    result_item.TooltipText = tooltip
    result_item.Group = group
    result_item.IsFavorite = is_favourite
    result_item.IsNew = is_new
    if timestamp:
        result_item.Timestamp = timestamp
    result_item.ResultClicked += click_result
    balloon = Autodesk.Windows.ComponentManager.InfoCenterPaletteManager.ShowBalloon(
        result_item
    )
    return balloon


def toast(
    message, title="pyRevit", appid="pyRevit", icon=None, click=None, actions=None
):
    """Show a Windows 10 notification.

    Args:
        message (str): notification message
        title (str): notification title
        appid (str): app name (will show under message)
        icon (str): file path to icon .ico file (defaults to pyRevit icon)
        click (str): click action commands string
        actions (dict): dictionary of button names and action strings

    Examples:
        ```python
        script.toast("Hello World!",
                     title="My Script",
                     appid="MyAPP",
                     click="https://pyrevitlabs.github.io/pyRevit/",
                     actions={
                         "Open Google":"https://google.com",
                         "Open Toast64":"https://github.com/go-toast/toast"
                         })
        ```
    """
    toaster.send_toast(
        message, title=title, appid=appid, icon=icon, click=click, actions=actions
    )
