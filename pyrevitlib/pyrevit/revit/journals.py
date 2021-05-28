"""Provide access to Revit Journal Files."""
import re
import os.path as op

from pyrevit import HOST_APP


__all__ = ('get_journals_folder', 'get_current_journal_file',
           'get_current_session_id')


def get_journals_folder():
    return op.dirname(HOST_APP.app.RecordingJournalFilename)


def get_current_journal_file():
    return HOST_APP.app.RecordingJournalFilename


def get_current_session_id():
    re_finder = re.compile(r'.*>Session\s+(\$.{8}).*')
    journal_file = get_current_journal_file()
    with open(journal_file, "r") as jfile:
        for jline in reversed(jfile.readlines()):
            match = re_finder.match(jline)
            if match:
                return match.groups()[0]
