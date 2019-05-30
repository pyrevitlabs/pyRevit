"""Apply tag to selected elements."""
#pylint: disable=C0111,E0401,C0103,W0613
import os.path as op

from pyrevit import revit
from pyrevit import forms
from pyrevit import script

import tagscfg
import tagsmgr


__title__ = 'Tag\nSelected'
__author__ = '{{author}}'
__helpurl__ = '{{docpath}}FYNDSAypWlg'


logger = script.get_logger()
output = script.get_output()


class ApplyTagWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        # make sure there is selection
        forms.check_selection(exitscript=True)
        # now setup window
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._tag_cache = \
            script.get_document_data_file(file_id='tagcache',
                                          file_ext='cache')
        if op.isfile(self._tag_cache):
            self._read_sow_cache()

        selection = revit.get_selection()
        sel_cnt = len(selection)
        self._target_elements = selection.elements
        self.Title += ' (for {} Selected Elements)'.format(sel_cnt) #pylint: disable=E1101

        self.tags_tb.Focus()
        self.tags_tb.SelectAll()

    @property
    def tags(self):
        return tagsmgr.extract_tags_from_str(self.tags_tb.Text)

    def _ensure_tag_validity(self):
        valid = all([x.is_valid() for x in self.tags])
        if not valid:
            forms.alert('At least one tag is not valid.')
            return False
        else:
            return True

    def _read_sow_cache(self):
        with open(self._tag_cache, 'r') as cache_file:
            self.tags_tb.Text = cache_file.read()

    def _write_sow_cache(self):
        with open(self._tag_cache, 'w') as cache_file:
            cache_file.write(self.tags_tb.Text)

    def _apply_tags(self, title='Apply Tags', append=True):
        self.Close()
        cfg = tagsmgr.ApplyTagsConfig(append=append,
                                      circuits=self.circuits_cb.IsChecked)
        with revit.Transaction(title, log_errors=False):
            if self._ensure_tag_validity():
                for el in self._target_elements:
                    tagsmgr.apply_tags(el, self.tags, config=cfg)

        self._write_sow_cache()

    def overwrite_tags(self, sender, args):
        self._apply_tags(title='OverWrite Tags', append=False)

    def append_tags(self, sender, args):
        self._apply_tags()


# make sure doc is not family
forms.check_modeldoc(doc=revit.doc, exitscript=True)

if tagscfg.verify_tags_configs():
    ApplyTagWindow('ApplyTagWindow.xaml').ShowDialog()
else:
    forms.alert('Tags tools need to be configured before using. '
                'Click on the Tags Settings button to setup.')
