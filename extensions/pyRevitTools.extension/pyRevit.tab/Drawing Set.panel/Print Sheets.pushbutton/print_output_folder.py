# -*- coding: utf-8 -*-
"""Where a Print Sheets run writes its files.

Turns the folder and subfolder template typed in the window into one
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
    """The output folder is not a full Windows path."""


class InvalidSubfolderTemplate(OutputFolderError):
    """The subfolder template has unknown placeholders or broken braces."""


class OutputFolder(object):
    """The output folder and subfolder template the user chose.

    Supported placeholders are ``{date}`` (yymmdd), ``{time}`` (HHMMSS),
    ``{model}`` and ``{sheet_index}``. Backslashes typed in the template
    create nested folders; backslashes inside placeholder values do not.
    An empty template means files go straight into the root.
    """

    def __init__(self, root, subfolder_template):
        self._root = root.strip()
        self._subfolder_template = subfolder_template.strip()

    def path_for(self, run):
        """Return the folder this run writes into.

        Args:
            run (PrintRun): values for the template placeholders.

        Raises:
            InvalidOutputRoot: the root is relative or drive-relative.
            InvalidSubfolderTemplate: the template cannot be filled in.
        """
        root = self._expanded_root()
        subfolder = self._subfolder_for(run)
        if not subfolder:
            return root
        return ntpath.join(root, subfolder)

    def _expanded_root(self):
        root = ntpath.expandvars(ntpath.expanduser(self._root))
        if ntpath.isabs(root) and ntpath.splitdrive(root)[0]:
            return root
        raise InvalidOutputRoot(
            "The output folder must be a full path, "
            "such as C:\\Prints or \\\\server\\share\\Prints."
        )

    def _subfolder_for(self, run):
        try:
            subfolder = self._subfolder_template.format(
                date=run.started_at.strftime("%y%m%d"),
                time=run.started_at.strftime("%H%M%S"),
                model=_single_folder_name(run.model),
                sheet_index=_single_folder_name(run.sheet_index),
            )
        except (KeyError, ValueError, IndexError, AttributeError):
            raise InvalidSubfolderTemplate(
                "The subfolder name is not valid. Use {date}, {time}, "
                "{model} and {sheet_index} only."
            )
        parts = [_safe_folder_part(part) for part in subfolder.split("\\")]
        return "\\".join(part for part in parts if part)


def _single_folder_name(value):
    return value.replace("\\", " ")


def _safe_folder_part(part):
    return _WINDOWS_UNSAFE_CHARS.sub("", part).strip(" .")
