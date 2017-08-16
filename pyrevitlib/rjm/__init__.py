import os.path as op
from datetime import datetime

from rjm import templates
from rjm import entries


class JournalMaker(object):
    def __init__(self, permissive=True):
        self._journal_contents = ''
        self._init_journal(permissive=permissive)

    def _add_entry(self, entry_string):
        self._journal_contents += entry_string

    def _init_journal(self, permissive=True):
        self._add_entry(templates.INIT.format(time_stamp=datetime.now().strftime("%d-%b-%Y %H:%M:%S.%f")[:-3]))
        if permissive:
            self._add_entry(templates.INIT_DEBUG)

    def open_workshared_model(self, model_path, central=False, detached=False, keep_worksets=True, audit=False):
        if detached:
            if audit:
                if keep_worksets:
                    self._add_entry(templates.CENTRAL_OPEN_DETACH_AUDIT \
                                             .format(journal_model_path=model_path))
                else:
                    self._add_entry(templates.CENTRAL_OPEN_DETACH_AUDIT_DISCARD \
                                             .format(journal_model_path=model_path))
            else:
                if keep_worksets:
                    self._add_entry(templates.CENTRAL_OPEN_DETACH \
                                             .format(journal_model_path=model_path))
                else:
                    self._add_entry(templates.CENTRAL_OPEN_DETACH_DISCARD \
                                             .format(journal_model_path=model_path))
        elif central:
            if audit:
                self._add_entry(templates.CENTRAL_OPEN_AUDIT \
                                         .format(journal_model_path=model_path))
            else:
                self._add_entry(templates.CENTRAL_OPEN \
                                         .format(journal_model_path=model_path))
        else:
            if audit:
                self._add_entry(templates.WORKSHARED_OPEN_AUDIT \
                                         .format(journal_model_path=model_path))
            else:
                self._add_entry(templates.WORKSHARED_OPEN \
                                         .format(journal_model_path=model_path))

    def open_model(self, model_path, audit=False):
        if audit:
            self._add_entry(templates.FILE_OPEN_AUDIT \
                                     .format(journal_model_path=model_path))
        else:
            self._add_entry(templates.FILE_OPEN \
                                     .format(journal_model_path=model_path))

    def ignore_missing_links(self):
        self._add_entry(templates.IGNORE_MISSING_LINKS)

    def execute_command(self, tab_name, panel_name, command_module, command_class, command_data={}):
        self._add_entry(templates.EXTERNAL_COMMAND.format(external_command_tab=tab_name,
                                                          external_command_panel=panel_name,
                                                          command_class_name=command_class,
                                                          command_class='{}.{}'.format(command_module, command_class)))

        data_count = len(command_data.keys())

        if data_count > 0:
            data_str_list = []
            for k, v in command_data.items():
                data_str_list.append(' "{}" , "{}"'.format(k, v))

            data_str = '_\n    ,'.join(data_str_list)
            self._add_entry(templates.EXTERNAL_COMMANDDATA.format(data_count=data_count, data_string=data_str))

    def add_custom_entry(self, entry_string):
        self._add_entry(entry_string)

    def export_warnings(self, export_file):
        warnings_file_path = op.dirname(export_file)
        warnings_file_name = op.splitext(op.basename(export_file))[0]
        self._add_entry(templates.EXPORT_WARNINGS.format(warnings_export_path=warnings_file_path,
                                                         warnings_export_file=warnings_file_name))

    def purge_unused(self, pass_count=3):
        for purge_count in range(0, pass_count):
            self._add_entry(templates.PROJECT_PURGE)

    def close_model(self):
        self._add_entry(templates.FILE_CLOSE)

    def save_model(self):
        self._add_entry(templates.FILE_SAVE)

    def sync_model(self, comment='', compact_central=False,
                   release_borrowed=True, release_workset=True, save_local=False):
        self._add_entry(templates.FILE_SYNC_START)

        if compact_central:
            self._add_entry(templates.FILE_SYNC_COMPACT)
        if release_borrowed:
            self._add_entry(templates.FILE_SYNC_RELEASE_BORROWED)
        if release_workset:
            self._add_entry(templates.FILE_SYNC_RELEASE_USERWORKSETS)
        if save_local:
            self._add_entry(templates.FILE_SYNC_RELEASE_SAVELOCAL)

        self._add_entry(templates.FILE_SYNC_COMMENT_OK.format(journal_sync_comment=comment))

    def write_journal(self, journal_file_path):
        with open(journal_file_path, "w") as jrn_file:
            jrn_file.write(self._journal_contents)


class JournalReader(object):
    def __init__(self, journal_file):
        self._jrnl_file = journal_file

    def _read_journal(self):
        with open(self._jrnl_file, 'r') as jrn_file:
            return jrn_file.read()

    def endswith(self, search_str):
        for entry in reversed(list(open(self._jrnl_file, 'r'))[-5:]):
            if search_str in entry:
                return True

        return False

    def is_stopped(self):
        return self.endswith(entries.MODAL_OPEN)
