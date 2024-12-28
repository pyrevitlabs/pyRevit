# -*- coding: utf-8 -*-
"""Base module for pushing toast messages on Win 10.

This module is a port of `https://github.com/kolide/toast`
"""

import os.path
import subprocess
from xml.etree.ElementTree import Element, SubElement, tostring

from pyrevit import ROOT_BIN_DIR
from pyrevit.coreutils.logger import get_logger

SCRIPT_TEMPLATE = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$APP_ID = "{app_id}"

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("{xml_content}")

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
"""


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
    xml_content = _build_toast_xml(
        title, message, icon=icon, click=click, actions=actions
    )
    script = SCRIPT_TEMPLATE.format(app_id=appid, xml_content=xml_content)
    mlogger.debug("sending toast with script %s...", script)
    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
        )
        mlogger.debug("toast sent.")
    except subprocess.CalledProcessError as e:
        mlogger.error("Error sending notification: %s" % str(e.output))


def _build_toast_xml(title, message, icon=None, click=None, actions=None):
    toast_props = {"activationType": "protocol", "launch": click or ""}
    toast = Element("toast", toast_props)
    visual = SubElement(toast, "visual")
    binding = SubElement(visual, "binding", {"template": "ToastGeneric"})
    if icon:
        SubElement(binding, "image", {"placement": "appLogoOverride", "src": icon})
    if title:
        SubElement(binding, "text").text = title
    if message:
        SubElement(binding, "text").text = message
    SubElement(toast, "audio")
    if actions:
        actions_element = SubElement(toast, "actions")
        for content, arguments in actions.items():
            SubElement(actions_element, "action", {
                "activationType": "protocol",
                "content": content,
                "arguments": arguments
            })
    return tostring(toast, encoding="UTF-8").replace("\"", "`\"")
