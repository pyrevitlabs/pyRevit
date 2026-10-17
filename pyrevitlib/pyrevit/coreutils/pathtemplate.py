# -*- coding: utf-8 -*-
r"""Folder path templates with placeholders such as ``{date}`` and ``{time}``.

Lets a tool turn folder names a user types, like
``C:\Exports\{model}\{date}_{time}``, into one safe Windows path. Every
template accepts ``{date}`` (yymmdd) and ``{time}`` (HHMMSS); callers add
their own placeholders as values.

Important:
    This module imports only the standard library, so it loads without a
    Revit host and is tested on CPython outside Revit. It must stay
    source-compatible with IronPython 2.7, IronPython 3 and CPython 3.
    Paths follow Windows rules (``ntpath``) on every platform.

Note:
    Nothing here touches the filesystem; creating the folder is left to the
    caller. Error messages are plain English; tools that localize their UI
    should build their own text from the error attributes.

Examples:
    ```python
    from pyrevit.coreutils import pathtemplate
    pathtemplate.resolve_folder(
        "C:\\Exports\\{model}", "{date}", values={"model": "Tower"}
    )
    ```
    "C:\\Exports\\Tower\\261017"
"""

import datetime
import ntpath
import re

_WINDOWS_UNSAFE_CHARS = re.compile(r'[/:*?"<>|]')


class PathTemplateError(Exception):
    """A folder template cannot be turned into a usable path.

    Attributes:
        template (str): the template as the caller passed it.
    """

    def __init__(self, template, message):
        super(PathTemplateError, self).__init__(message)
        self.template = template


class InvalidTemplateError(PathTemplateError):
    """A template uses an unknown placeholder or has broken braces.

    Attributes:
        placeholders (list[str]): sorted placeholder names the template could use.
    """

    def __init__(self, template, placeholders):
        super(InvalidTemplateError, self).__init__(
            template,
            'Folder template "{}" can only use {}.'.format(
                template, ", ".join("{" + name + "}" for name in placeholders)
            ),
        )
        self.placeholders = placeholders


class NotFullPathError(PathTemplateError):
    """A root folder is relative or drive-relative once filled in."""

    def __init__(self, template):
        super(NotFullPathError, self).__init__(
            template,
            'Folder "{}" must be a full path, such as C:\\Exports '
            "or \\\\server\\share\\Exports.".format(template),
        )


def fill(template, values=None, now=None):
    r"""Fill a template's placeholders and return a safe relative path.

    Backslashes typed in the template create nested folders; backslashes
    inside values do not. Characters Windows rejects in folder names are
    removed, and empty or dot-only folder names are dropped.

    Args:
        template (str): folder template, such as ``{model}\{date}``.
        values (dict[str, str]): placeholder values; these override
            ``{date}`` and ``{time}`` when they use the same name.
        now (datetime.datetime): moment ``{date}`` and ``{time}`` describe;
            defaults to the current time.

    Returns:
        (str): relative path, or an empty string for an empty template.

    Raises:
        InvalidTemplateError: the template cannot be filled in.
    """
    return _safe_relative_path(_format(template.strip(), values, now))


def resolve_folder(root, subfolder="", values=None, now=None):
    r"""Resolve a root folder template and a subfolder template to one path.

    The root may also use ``~`` and ``%VARS%`` and must be a full path once
    filled in. Both templates are filled at the same ``now``.

    Args:
        root (str): root folder template, such as ``C:\Exports\{model}``.
        subfolder (str): template for folders under the root; empty means
            the root itself.
        values (dict[str, str]): placeholder values, as for `fill`.
        now (datetime.datetime): moment ``{date}`` and ``{time}`` describe;
            defaults to the current time.

    Returns:
        (str): full Windows path.

    Raises:
        NotFullPathError: the root is not a full path once filled in.
        InvalidTemplateError: either template cannot be filled in.
    """
    now = now or datetime.datetime.now()
    expanded = ntpath.expandvars(ntpath.expanduser(root.strip()))
    drive, rest = ntpath.splitdrive(_format(expanded, values, now))
    if not _is_full_path(drive, rest):
        raise NotFullPathError(root)
    full_root = drive + "\\" + _safe_relative_path(rest)
    relative_folder = fill(subfolder, values, now)
    if not relative_folder:
        return full_root
    return ntpath.join(full_root, relative_folder)


def _format(template, values, now):
    placeholders = _placeholder_values(values, now or datetime.datetime.now())
    try:
        return template.format(**placeholders)
    except (KeyError, ValueError, IndexError, AttributeError):
        raise InvalidTemplateError(template, sorted(placeholders))


def _placeholder_values(values, now):
    placeholders = {
        "date": now.strftime("%y%m%d"),
        "time": now.strftime("%H%M%S"),
    }
    for name, value in (values or {}).items():
        placeholders[name] = value.replace("\\", " ")
    return placeholders


def _is_full_path(drive, rest):
    is_unc_share = drive.startswith("\\\\")
    return bool(drive) and (is_unc_share or rest.startswith(("\\", "/")))


def _safe_relative_path(path):
    parts = [_safe_folder_part(part) for part in path.split("\\")]
    return "\\".join(part for part in parts if part)


def _safe_folder_part(part):
    return _WINDOWS_UNSAFE_CHARS.sub("", part).strip(" .")
