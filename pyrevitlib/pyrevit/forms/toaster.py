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
$xml.LoadXml('{xml_content}')

$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($APP_ID).Show($toast)
"""

# Mapping for audio friendly names to ms-winsoundevent strings
AUDIO_MAPPING = {
    "default": "ms-winsoundevent:Notification.Default",
    "im": "ms-winsoundevent:Notification.IM",
    "mail": "ms-winsoundevent:Notification.Mail",
    "reminder": "ms-winsoundevent:Notification.Reminder",
    "sms": "ms-winsoundevent:Notification.SMS",
    "silent": "silent",
    "looping_alarm": "ms-winsoundevent:Notification.Looping.Alarm",
    "looping_call": "ms-winsoundevent:Notification.Looping.Call"
}


def send_toast(
    message,
    title="pyRevit",
    appid="pyRevit",
    icon=None,
    click=None,
    actions=None,
    audio="default",
    duration="short",
    activation_type="protocol",
    loop=False,
):
    """Send toast notificaton.

    Args:
        message (str): notification message
        title (str): notification title
        appid (str): application unique id
        icon (str): notification icon
        click (str): click action
        actions (dict[str, str]): list of actions
        audio (str): notification audio to play
        duration (str): notification duration
        activation_type (str): notification activation type
        loop (bool): notification loop
    """
    mlogger = get_logger(__name__)
    icon = icon or os.path.join(ROOT_BIN_DIR, 'pyRevit.ico')
    xml_content = _build_toast_xml(
        title, message, icon, activation_type, click, actions, audio, loop, duration
    )
    script = SCRIPT_TEMPLATE.format(app_id=appid, xml_content=xml_content)
    mlogger.debug("sending toast with script %s...", script)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            mlogger.error("Error sending notification: %s", result.stderr)
        else:
            mlogger.debug("toast sent.")
    except subprocess.CalledProcessError as e:
        mlogger.error("Error sending notification: %s" % str(e))
    except subprocess.TimeoutExpired:
        mlogger.error("Notification script timed out.")


def _build_toast_xml(
    title,
    message,
    icon=None,
    activation_type="protocol", 
    activation_arguments=None,
    actions=None,
    audio="default", 
    loop=False,
    duration="short"
):
    if duration not in {"short", "long"}:
        raise ValueError("Invalid duration: must be 'short' or 'long'")
    audio = AUDIO_MAPPING.get(audio.lower(), AUDIO_MAPPING["default"])
    toast = Element("toast", {
        "activationType": activation_type,
        "launch": activation_arguments or "",
        "duration": duration
    })
    visual = SubElement(toast, "visual")
    binding = SubElement(visual, "binding", {"template": "ToastGeneric"})
    if icon:
        SubElement(binding, "image", {"placement": "appLogoOverride", "src": icon})
    if title:
        SubElement(binding, "text").text = title
    if message:
        SubElement(binding, "text").text = message
    audio_element = (
        {"silent": "true"} if audio == "silent"
        else {"src": audio, "loop": "true" if loop else "false"}
    )
    SubElement(toast, "audio", audio_element)
    if actions:
        actions_element = SubElement(toast, "actions")
        for action in actions:
            SubElement(actions_element, "action", {
                "activationType": action.get("type", ""),
                "content": action.get("label", ""),
                "arguments": action.get("arguments", "")
            })
    return tostring(toast, encoding="unicode")
