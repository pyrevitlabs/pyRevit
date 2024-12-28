# -*- coding: utf-8 -*-
"""Base module for pushing toast messages on Win 10.

This module is a port of `https://github.com/kolide/toast`
"""

import os.path
import subprocess

from pyrevit import ROOT_BIN_DIR
from pyrevit.coreutils.logger import get_logger

SCRIPT_TEMPLATE = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$APP_ID = "{app_id}"

$template = @"
<toast activationType="protocol" {launch}>
    <visual>
        <binding template="ToastGeneric">
            {image}
            {title}
            {message}
        </binding>
    </visual>
    {actions}
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
"""

LAUNCH_TEMPLATE = "launch=\"{}\""
TEXT_TEMPLATE = "<text><![CDATA[{}]]></text>"
IMAGE_TEMPLATE = "<image placement=\"appLogoOverride\" src=\"{}\"/>"
ACTION_ITEM_TEMPLATE = "<action activationType=\"protocol\" content=\"{}\" arguments=\"{}\" />"
ACTIONS_TEMPLATE = "<actions>{}</actions>"


def toast(
    message,
    title="pyRevit",
    appid="pyRevit",
    icon=None,
    click=None,
    actions=None,
):
    """Show a toast notificaton.

    Args:
        message (str): notification message
        title (str): notification title. Defaults to "pyRevit".
        appid (str): application unique id. Defaults to "pyRevit".
        icon (str): notification icon. Defaults to pyRevit icon.
        click (str): optional click action.
        actions (dict[str, str]): optional dictionary of button names and actions.

    Examples:
        ```python
        toast(
            "🚀 PyRevit Rocks!",
            click="https://www.pyrevitlabs.io",
            actions={
                "Donate": "https://opencollective.com/pyrevitlabs/donate", 
                "Docs": "https://docs.pyrevitlabs.io/"
            }
        )
        ```
    """
    mlogger = get_logger(__name__)
    icon = icon or os.path.join(ROOT_BIN_DIR, 'pyRevit.ico')
    if not actions:
        actions_content = ""
    else:
        actions_items = (
            ACTION_ITEM_TEMPLATE.format(content, arguments)
            for content, arguments in actions.items()
        )
        actions_content = ACTIONS_TEMPLATE.format("".join(actions_items))
    script = SCRIPT_TEMPLATE.format(
        app_id=appid,
        launch=LAUNCH_TEMPLATE.format(click) if click else "",
        title=TEXT_TEMPLATE.format(title) if title else "",
        message=TEXT_TEMPLATE.format(message) if message else "",
        image=IMAGE_TEMPLATE.format(icon) if icon else "",
        actions=actions_content,
    )

    CREATE_NO_WINDOW = 0x08000000
    mlogger.debug("sending toast with script %s...", script)
    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            creationflags=CREATE_NO_WINDOW,
        )
        mlogger.debug("toast sent.")
    except subprocess.CalledProcessError as e:
        mlogger.error("Error sending notification: %s" % str(e.output))
