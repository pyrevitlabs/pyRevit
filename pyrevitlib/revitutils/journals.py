import os
import os.path as op


def get_journals_folder():
    return op.dirname(__revit__.Application.RecordingJournalFilename)


def get_current_journal_file():
    return __revit__.Application.RecordingJournalFilename
