# -*- coding: utf-8 -*-
"""Where a Print Sheets run writes its files.

Turns the folder and subfolder templates typed in the window into one
Windows path. Has no Revit or pyRevit dependency so it can be tested
outside Revit, and stays source-compatible with IronPython 2.7 and
CPython 3. Paths follow Windows rules (``ntpath``) on every platform.
Creating the folder is left to the caller.
"""

import ntpath
import re
from collections import namedtuple

PrintRun = namedtuple("PrintRun", ["model", "sheet_index", "started_at"])

_WINDOWS_UNSAFE_CHARS = re.compile(r'[/:*?"<>|]')


class OutputFolderError(Exception):
    """The typed output folder cannot be used; the message is user-facing."""


class InvalidOutputRoot(OutputFolderError):
    """The output folder is not a full Windows path once filled in."""


class InvalidFolderTemplate(OutputFolderError):
    """A folder template has unknown placeholders or broken braces."""


class OutputFolder(object):
    """The output folder and subfolder templates the user chose.

    Both templates accept ``{date}`` (yymmdd), ``{time}`` (HHMMSS),
    ``{model}`` and ``{sheet_index}``. Backslashes typed in a template
    create nested folders; backslashes inside placeholder values do not.
    The output folder may also use ``~`` and ``%VARS%``, and must be a
    full path once filled in. An empty subfolder template means files go
    straight into the output folder.
    """

    def __init__(self, root, subfolder_template):
        self._root = root.strip()
        self._subfolder_template = subfolder_template.strip()

    def path_for(self, run):
        """Return the folder this run writes into.

        Args:
            run (PrintRun): values for the template placeholders.

        Raises:
            InvalidOutputRoot: the output folder is relative or drive-relative.
            InvalidFolderTemplate: a template cannot be filled in.
        """
        root = self._root_for(run)
        subfolder = _safe_relative_path(_fill(self._subfolder_template, run))
        if not subfolder:
            return root
        return ntpath.join(root, subfolder)

    def _root_for(self, run):
        expanded = ntpath.expandvars(ntpath.expanduser(self._root))
        drive, rest = ntpath.splitdrive(_fill(expanded, run))
        if not _is_full_path(drive, rest):
            raise InvalidOutputRoot(
                'The output folder "{}" must be a full path, '
                "such as C:\\Prints or \\\\server\\share\\Prints.".format(self._root)
            )
        return drive + "\\" + _safe_relative_path(rest)


def _is_full_path(drive, rest):
    is_unc_share = drive.startswith("\\\\")
    return bool(drive) and (is_unc_share or rest.startswith(("\\", "/")))


def _fill(template, run):
    try:
        return template.format(
            date=run.started_at.strftime("%y%m%d"),
            time=run.started_at.strftime("%H%M%S"),
            model=_single_folder_name(run.model),
            sheet_index=_single_folder_name(run.sheet_index),
        )
    except (KeyError, ValueError, IndexError, AttributeError):
        raise InvalidFolderTemplate(
            "The folder name is not valid. Use {date}, {time}, "
            "{model} and {sheet_index} only."
        )


def _single_folder_name(value):
    return value.replace("\\", " ")


def _safe_relative_path(path):
    parts = [_safe_folder_part(part) for part in path.split("\\")]
    return "\\".join(part for part in parts if part)


def _safe_folder_part(part):
    return _WINDOWS_UNSAFE_CHARS.sub("", part).strip(" .")
