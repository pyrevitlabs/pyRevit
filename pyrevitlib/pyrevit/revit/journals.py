"""Provide access to Revit Journal Files."""

import os.path as op

from pyrevit import HOST_APP


__all__ = ['get_journals_folder', 'get_current_journal_file']


def get_journals_folder():
    return op.dirname(HOST_APP.app.RecordingJournalFilename)


def get_current_journal_file():
    return HOST_APP.app.RecordingJournalFilename
