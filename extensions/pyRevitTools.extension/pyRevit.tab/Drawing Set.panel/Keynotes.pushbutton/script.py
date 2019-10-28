"""Manage project keynotes.

Shift+Click:
Reset window configurations and open.
"""
#pylint: disable=E0401,W0613,C0111,C0103,C0302,W0703
import os
import os.path as op
import shutil
import math
from collections import defaultdict

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit.framework import System
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.runtime.types import DocumentEventUtils

import keynotesdb as kdb


__title__ = "Manage\nKeynotes"
__author__ = "{{author}}"
__helpurl__ = "https://www.notion.so/pyrevitlabs/Manage-Keynotes-6f083d6f66fe43d68dc5d5407c8e19da"
__min_revit_ver__ = 2014


logger = script.get_logger()
output = script.get_output()


def get_keynote_pcommands():
    return list(reversed(
        [x for x in coreutils.get_enum_values(UI.PostableCommand)
         if str(x).endswith('Keynote')]))


class EditRecordWindow(forms.WPFWindow):
    def __init__(self,
                 owner,
                 conn, mode,
                 rkeynote=None,
                 rkey=None, text=None, pkey=None):
        forms.WPFWindow.__init__(self, 'EditRecord.xaml')
        self.Owner = owner
        self._res = None
        self._commited = False
        self._reserved_key = None

        # connection
        self._conn = conn
        self._mode = mode
        self._cat = False
        self._rkeynote = rkeynote
        self._rkey = rkey
        self._text = text
        self._pkey = pkey

        # prepare gui for various edit modes
        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = 'Add Category'
            self.recordKeyTitle.Text = 'Create Category Key'
            self.applyChanges.Content = 'Add Category'

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = 'Edit Category'
            self.recordKeyTitle.Text = 'Category Key'
            self.applyChanges.Content = 'Update Category'
            self.recordKey.IsEnabled = False
            if self._rkeynote:
                if self._rkeynote.key:
                    kdb.begin_edit(self._conn,
                                   self._rkeynote.key,
                                   category=True)

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Add Keynote'
            self.recordKeyTitle.Text = 'Create Keynote Key'
            self.applyChanges.Content = 'Add Keynote'

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Edit Keynote'
            self.recordKeyTitle.Text = 'Keynote Key'
            self.applyChanges.Content = 'Update Keynote'
            self.recordKey.IsEnabled = False
            if self._rkeynote:
                # start edit
                if self._rkeynote.key:
                    kdb.begin_edit(self._conn,
                                   self._rkeynote.key,
                                   category=False)

        # update gui with overrides if any
        if self._rkeynote:
            self.active_key = self._rkeynote.key
            self.active_text = self._rkeynote.text
            self.active_parent_key = self._rkeynote.parent_key

        if self._rkey:
            self.active_key = self._rkey
        if self._text:
            self.active_text = self._text
        if self._pkey:
            self.active_parent_key = self._pkey

        # select text in textbox for easy editing
        self.recordText.Focus()
        self.recordText.SelectAll()

    @property
    def active_key(self):
        if self.recordKey.Content and u'\u25CF' not in self.recordKey.Content:
            return self.recordKey.Content

    @active_key.setter
    def active_key(self, value):
        self.recordKey.Content = value

    @property
    def active_text(self):
        return self.recordText.Text

    @active_text.setter
    def active_text(self, value):
        self.recordText.Text = value.strip()

    @property
    def active_parent_key(self):
        return self.recordParent.Content

    @active_parent_key.setter
    def active_parent_key(self, value):
        self.recordParent.Content = value

    def commit(self):
        if self._mode == kdb.EDIT_MODE_ADD_CATEG:
            if not self.active_key:
                forms.alert('Category must have a unique key.')
                return False
            elif not self.active_text.strip():
                forms.alert('Category must have a title.')
                return False
            logger.debug('Adding category: {} {}'
                         .format(self.active_key, self.active_text))
            try:
                self._res = kdb.add_category(self._conn,
                                             self.active_key,
                                             self.active_text)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_CATEG:
            if not self.active_text:
                forms.alert('Existing title is removed. '
                            'Category must have a title.')
                return False
            try:
                # update category key if changed
                if self.active_key != self._rkeynote.key:
                    self._res = kdb.rekey_category(self._conn,
                                                   self._rkeynote.key,
                                                   self.active_key)
                # update category title if changed
                if self.active_text != self._rkeynote.text:
                    kdb.update_category_title(self._conn,
                                              self.active_key,
                                              self.active_text)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_ADD_KEYNOTE:
            if not self.active_key:
                forms.alert('Keynote must have a unique key.')
                return False
            elif not self.active_text:
                forms.alert('Keynote must have text.')
                return False
            elif not self.active_parent_key:
                forms.alert('Keynote must have a parent.')
                return False
            try:
                self._res = kdb.add_keynote(self._conn,
                                            self.active_key,
                                            self.active_text,
                                            self.active_parent_key)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        elif self._mode == kdb.EDIT_MODE_EDIT_KEYNOTE:
            if not self.active_text:
                forms.alert('Existing text is removed. Keynote must have text.')
                return False
            try:
                # update keynote key if changed
                if self.active_key != self._rkeynote.key:
                    self._res = kdb.rekey_keynote(self._conn,
                                                  self._rkeynote.key,
                                                  self.active_key)
                # update keynote title if changed
                if self.active_text != self._rkeynote.text:
                    kdb.update_keynote_text(self._conn,
                                            self.active_key,
                                            self.active_text)
                # update keynote parent
                if self.active_parent_key != self._rkeynote.parent_key:
                    kdb.move_keynote(self._conn,
                                     self.active_key,
                                     self.active_parent_key)
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return False

        return True

    def show(self):
        self.ShowDialog()
        return self._res

    def pick_key(self, sender, args):
        # remove previously reserved
        if self._reserved_key:
            try:
                kdb.release_key(self._conn,
                                self._reserved_key,
                                category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return

        try:
            categories = kdb.get_categories(self._conn)
            keynotes = kdb.get_keynotes(self._conn)
            locks = kdb.get_locks(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return

        # collect existing keys
        reserved_keys = [x.key for x in categories]
        reserved_keys.extend([x.key for x in keynotes])
        reserved_keys.extend([x.LockTargetRecordKey for x in locks])
        # ask for a unique new key
        new_key = forms.ask_for_unique_string(
            prompt='Enter a Unique Key',
            title=self.Title,
            reserved_values=reserved_keys,
            owner=self)
        if new_key:
            try:
                kdb.reserve_key(self._conn, new_key, category=self._cat)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                return
            self._reserved_key = new_key
            # set the key value on the button
            self.active_key = new_key

    def pick_parent(self, sender, args):
        # TODO: pick_parent
        # categories = get_categories(self._conn)
        # keynotes_tree = get_keynotes_tree(self._conn)
        forms.alert('Pick parent...')
        # remove self from that record if self is not none
        # prompt to select a record
        # apply the record key on the button

    def to_upper(self, sender, args):
        self.active_text = self.active_text.upper()

    def to_lower(self, sender, args):
        self.active_text = self.active_text.lower()

    def to_title(self, sender, args):
        self.active_text = self.active_text.title()

    def to_sentence(self, sender, args):
        self.active_text = self.active_text.capitalize()

    def select_template(self, sender, args):
        # TODO: get templates from config
        template = forms.SelectFromList.show(
            ["-- reserved for future use --", "!! do not use !! "],
            title='Select Template',
            owner=self)
        if template:
            self.active_text = template

    def translate(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def apply_changes(self, sender, args):
        logger.debug('Applying changes...')
        self._commited = self.commit()
        if self._commited:
            self.Close()

    def cancel_changes(self, sender, args):
        logger.debug('Cancelling changes...')
        self.Close()

    def window_closing(self, sender, args):
        if not self._commited:
            if self._reserved_key:
                try:
                    kdb.release_key(self._conn,
                                    self._reserved_key,
                                    category=self._cat)
                except System.TimeoutException as toutex:
                    forms.alert(toutex.Message)
                except Exception:
                    pass
            try:
                kdb.end_edit(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception:
                pass


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, reset_config=False):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # verify keynote file existence
        self._kfile = revit.query.get_keynote_file(doc=revit.doc)
        if not self._kfile or not op.exists(self._kfile):
            self._kfile = None
            forms.alert("Keynote file is not accessible. "
                        "Please select a keynote file.")
            self._change_kfile()

        # if a keynote file is still not set, return
        if not self._kfile:
            raise Exception('Keynote file is not setup.')

        # if a keynote file is still not set, return
        if not os.access(self._kfile, os.W_OK):
            raise Exception('Keynote file is read-only.')

        self._conn = None
        try:
            self._conn = kdb.connect(self._kfile)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message, exitscript=True)
        except Exception as ex:
            logger.debug('Connection failed | %s' % ex)
            res = forms.alert(
                "Existing keynote file needs to be converted to "
                "a format usable by this tool. The resulting keynote "
                "file is still readble by Revit and could be shared "
                "with other projects. Users should NOT be making changes to "
                "the existing keynote file during the conversion process.\n"
                "Are you sure you want to convert?",
                options=["Convert",
                         "Select a different keynote file",
                         "Give me more info"])
            if res:
                if res == "Convert":
                    try:
                        self._convert_existing()
                        forms.alert("Conversion completed!")
                        if not self._conn:
                            forms.alert(
                                "Launch the tool again to manage keynotes.",
                                exitscript=True
                                )
                    except Exception as convex:
                        logger.debug('Legacy conversion failed | %s' % convex)
                        forms.alert("Conversion failed! %s" % convex,
                                    exitscript=True)
                elif res == "Select a different keynote file":
                    self._change_kfile()
                elif res == "Give me more info":
                    script.open_url(__helpurl__)
                    script.exit()
            else:
                forms.alert("Keynote file is not yet converted.",
                            exitscript=True)

        self._cache = []
        self._allcat = kdb.RKeynote(key='', text='-- ALL CATEGORIES --',
                                    parent_key='',
                                    locked=False, owner='',
                                    children=None)

        self._needs_update = False
        self._config = script.get_config()
        self._used_keysdict = self.get_used_keynote_elements()
        self.load_config(reset_config)
        self.search_tb.Focus()

    @property
    def window_geom(self):
        return (self.Width, self.Height, self.Top, self.Left)

    @window_geom.setter
    def window_geom(self, geom_tuple):
        width, height, top, left = geom_tuple
        self.Width = self.Width if math.isnan(width) else width #pylint: disable=W0201
        self.Height = self.Height if math.isnan(height) else height #pylint: disable=W0201
        self.Top = self.Top if math.isnan(top) else top #pylint: disable=W0201
        self.Left = self.Left if math.isnan(left) else left #pylint: disable=W0201

    @property
    def target_id(self):
        return hash(self._kfile)

    @property
    def search_term(self):
        return self.search_tb.Text

    @search_term.setter
    def search_term(self, value):
        self.search_tb.Text = value

    @property
    def postable_keynote_command(self):
        # order must match the order in GUI
        return get_keynote_pcommands()[self.postcmd_idx]

    @property
    def postcmd_options(self):
        return [self.userknote_rb, self.materialknote_rb, self.elementknote_rb]

    @property
    def postcmd_idx(self):
        # return self.keynotetype_cb.SelectedIndex
        for idx, postcmd_op in enumerate(self.postcmd_options):
            if postcmd_op.IsChecked:
                return idx

    @postcmd_idx.setter
    def postcmd_idx(self, index):
        # self.keynotetype_cb.ItemsSource = \
        #     [str(x).replace('UI.PostableCommand', '')
        #      for x in get_keynote_pcommands()]
        # self.keynotetype_cb.SelectedIndex = index
        postcmd_op = self.postcmd_options[index]
        postcmd_op.IsChecked = True

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    @property
    def selected_category(self):
        # grab selected category
        cat = self.categories_tv.SelectedItem
        if cat:
            # verify category is not all-categories item
            if cat != self._allcat:
                return cat
            # grab category from keynote list
            elif self.selected_keynote \
                    and not self.selected_keynote.parent_key:
                return self.selected_keynote

    @selected_category.setter
    def selected_category(self, cat_key):
        self._update_ktree(active_catkey=cat_key)

    @property
    def all_categories(self):
        try:
            return kdb.get_categories(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    @property
    def all_keynotes(self):
        try:
            return kdb.get_keynotes(self._conn)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
            return []

    @property
    def current_keynotes(self):
        return self.keynotes_tv.ItemsSource

    @property
    def keynote_text_with(self):
        return 200

    def get_used_keynote_elements(self):
        used_keys = defaultdict(list)
        for knote in revit.query.get_used_keynotes(doc=revit.doc):
            key = knote.Parameter[DB.BuiltInParameter.KEY_VALUE].AsString()
            used_keys[key].append(knote.Id)
        return used_keys

    def save_config(self):
        # save self.window_geom
        new_window_geom_dict = {}
        # cleanup removed keynote files
        for kfile, wgeom_value in self._config.get_option('last_window_geom',
                                                          {}).items():
            if op.exists(kfile):
                new_window_geom_dict[kfile] = wgeom_value
        new_window_geom_dict[self._kfile] = self.window_geom
        self._config.set_option('last_window_geom', new_window_geom_dict)

        # save self.postable_keynote_command
        new_postcmd_dict = {}
        # cleanup removed keynote files
        for kfile, lpc_value in self._config.get_option('last_postcmd_idx',
                                                        {}).items():
            if op.exists(kfile):
                new_postcmd_dict[kfile] = lpc_value
        new_postcmd_dict[self._kfile] = self.postcmd_idx
        self._config.set_option('last_postcmd_idx', new_postcmd_dict)

        # save self.selected_category
        new_category_dict = {}
        # cleanup removed keynote files
        for kfile, lc_value in self._config.get_option('last_category',
                                                       {}).items():
            if op.exists(kfile):
                new_category_dict[kfile] = lc_value
        new_category_dict[self._kfile] = ''
        if self.selected_category:
            new_category_dict[self._kfile] = self.selected_category.key
        self._config.set_option('last_category', new_category_dict)

        # save self.search_term
        new_category_dict = {}
        if self.search_term:
            new_category_dict[self._kfile] = self.search_term
        self._config.set_option('last_search_term', new_category_dict)

        script.save_config()

    def load_config(self, reset_config):
        # load last window geom
        if reset_config:
            last_window_geom_dict = {}
        else:
            last_window_geom_dict = \
                self._config.get_option('last_window_geom', {})
        if last_window_geom_dict and self._kfile in last_window_geom_dict:
            width, height, top, left = last_window_geom_dict[self._kfile]
        else:
            width, height, top, left = (None, None, None, None)
        # update window geom
        if all([width, height, top, left]) \
                and coreutils.is_box_visible_on_screens(
                        left, top, width, height):
            self.window_geom = (width, height, top, left)
        else:
            self.WindowStartupLocation = \
                framework.Windows.WindowStartupLocation.CenterScreen

        # load last postable commands id
        if reset_config:
            last_postcmd_dict = {}
        else:
            last_postcmd_dict = \
                self._config.get_option('last_postcmd_idx', {})
        if last_postcmd_dict and self._kfile in last_postcmd_dict:
            self.postcmd_idx = last_postcmd_dict[self._kfile]
        else:
            self.postcmd_idx = 0

        # load last category
        if reset_config:
            last_category_dict = {}
        else:
            last_category_dict = \
                self._config.get_option('last_category', {})
        if last_category_dict and self._kfile in last_category_dict:
            self._update_ktree(active_catkey=last_category_dict[self._kfile])
        else:
            self.selected_category = self._allcat

        # load last search term
        if reset_config:
            last_searchterm_dict = {}
        else:
            last_searchterm_dict = \
                self._config.get_option('last_search_term', {})
        if last_searchterm_dict and self._kfile in last_searchterm_dict:
            self.search_term = last_searchterm_dict[self._kfile]
        else:
            self.search_term = ""

    def _convert_existing(self):
        # make a copy of exsing
        temp_kfile = op.join(op.dirname(self._kfile),
                             op.basename(self._kfile) + '.bak')
        shutil.copy(self._kfile, temp_kfile)
        os.remove(self._kfile)
        try:
            self._conn = kdb.connect(self._kfile)
            kdb.import_legacy_keynotes(self._conn, temp_kfile, skip_dup=True)
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message, exitscript=True)

    def _change_kfile(self):
        kfile = forms.pick_file('txt')
        if kfile:
            logger.debug('Setting keynote file: %s' % kfile)
            try:
                with revit.Transaction("Set Keynote File"):
                    revit.update.set_keynote_file(kfile, doc=revit.doc)
                self._kfile = revit.query.get_keynote_file(doc=revit.doc)

                # attempt at opening the selected file.
                try:
                    self._conn = kdb.connect(self._kfile)
                except Exception as ckf_ex:
                    forms.alert(
                        "Error opening seleced keynote file.",
                        sub_msg=str(ckf_ex)
                    )

                return self._kfile
            except Exception as skex:
                forms.alert(str(skex))

    def _update_ktree(self, active_catkey=None):
        categories = [self._allcat]
        categories.extend(self.all_categories)

        last_idx = 0
        if active_catkey:
            cat_keys = [x.key for x in categories]
            if active_catkey in cat_keys:
                last_idx = cat_keys.index(active_catkey)
        else:
            if self.categories_tv.ItemsSource:
                last_idx = self.categories_tv.SelectedIndex

        self.categories_tv.ItemsSource = categories
        self.categories_tv.SelectedIndex = last_idx

    def _update_ktree_knotes(self, fast=False):
        keynote_filter = self.search_term if self.search_term else None

        # update the visible keys in active view if filter is ViewOnly
        if keynote_filter \
                and kdb.RKeynoteFilters.ViewOnly.code in keynote_filter:
            visible_keys = \
                [x.TagText for x in
                 revit.query.get_visible_keynotes(revit.active_view)]
            kdb.RKeynoteFilters.ViewOnly.set_keys(visible_keys)

        if fast and keynote_filter:
            # fast filtering using already loaded content
            active_tree = list(self._cache)
        else:
            # get the keynote trees (not categories)
            try:
                active_tree = kdb.get_keynotes_tree(self._conn)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
                active_tree = []

            selected_cat = self.selected_category
            # if the is a category selected, list its children
            if selected_cat:
                if selected_cat.key:
                    active_tree = \
                        [x for x in active_tree
                         if x.parent_key == self.selected_category.key]
            # otherwise list categories as roots witn children
            else:
                parents = defaultdict(list)
                for rkey in active_tree:
                    parents[rkey.parent_key].append(rkey)
                categories = self.all_categories
                for crkey in categories:
                    if crkey.key in parents:
                        crkey.children.extend(parents[crkey.key])
                active_tree = categories

        # mark used keynotes
        for knote in active_tree:
            knote.update_used(self._used_keysdict)

        # filter keynotes
        self._cache = list(active_tree)
        if keynote_filter:
            clean_filter = keynote_filter.lower()
            filtered_keynotes = []
            for rkey in active_tree:
                if rkey.filter(clean_filter):
                    filtered_keynotes.append(rkey)
        else:
            filtered_keynotes = active_tree

        # show keynotes
        self.keynotes_tv.ItemsSource = filtered_keynotes

    def _update_catedit_buttons(self):
        self.catEditButtons.IsEnabled = \
            self.selected_category and not self.selected_category.locked

    def _update_knoteedit_buttons(self):
        if self.selected_keynote \
                and not self.selected_keynote.locked:
            self.keynoteEditButtons.IsEnabled = \
                bool(self.selected_keynote.parent_key)
            self.catEditButtons.IsEnabled = \
                not self.keynoteEditButtons.IsEnabled
        else:
            self.keynoteEditButtons.IsEnabled = False

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        logger.debug('New search term: %s', self.search_term)
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._update_ktree_knotes(fast=True)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

    def custom_filter(self, sender, args):
        sfilter = forms.SelectFromList.show(
            kdb.RKeynoteFilters.get_available_filters(),
            title='Select Filter',
            owner=self)
        if sfilter:
            self.search_term = sfilter.format_term(self.search_term)

    def selected_category_changed(self, sender, args):
        logger.debug('New category selected: %s', self.selected_category)
        self._update_catedit_buttons()
        self._update_ktree_knotes()

    def selected_keynote_changed(self, sender, args):
        logger.debug('New keynote selected: %s', self.selected_keynote)
        self._update_catedit_buttons()
        self._update_knoteedit_buttons()

    def refresh(self, sender, args):
        if self._conn:
            self._update_ktree()
            self._update_ktree_knotes()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        try:
            new_cat = \
                EditRecordWindow(self, self._conn,
                                 kdb.EDIT_MODE_ADD_CATEG).show()
            if new_cat:
                self.selected_category = new_cat.key
                # make sure to relaod on close
                self._needs_update = True
        except System.TimeoutException as toutex:
            forms.alert(toutex.Message)
        except Exception as ex:
            forms.alert(str(ex))

    def edit_category(self, sender, args):
        selected_category = self.selected_category
        selected_keynote = self.selected_keynote
        # determine where the category is coming from
        # selected category in drop-down
        if selected_category:
            target_keynote = selected_category
        # or selected category in keynotes list
        elif selected_keynote and not selected_keynote.parent_key:
            target_keynote = selected_keynote
        if target_keynote:
            if target_keynote.locked:
                forms.alert('Category is locked and is being edited by {}. '
                            'Wait until their changes are committed. '
                            'Meanwhile you can use or modify the keynotes '
                            'under this category.'
                            .format('\"%s\"' % target_keynote.owner
                                    if target_keynote.owner
                                    else 'and unknown user'))
            else:
                try:
                    EditRecordWindow(self, self._conn,
                                     kdb.EDIT_MODE_EDIT_CATEG,
                                     rkeynote=target_keynote).show()
                    # make sure to relaod on close
                    self._needs_update = True
                except System.TimeoutException as toutex:
                    forms.alert(toutex.Message)
                except Exception as ex:
                    forms.alert(str(ex))
                finally:
                    self._update_ktree()
                    if selected_keynote:
                        self._update_ktree_knotes()

    def rekey_category(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def remove_category(self, sender, args):
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_category = self.selected_category
        if selected_category:
            if selected_category.has_children():
                forms.alert("Category \"%s\" is not empty. "
                            "Delete all its keynotes first."
                            % selected_category.key)
            elif selected_category.used:
                forms.alert("Category \"%s\" is used in the model. "
                            "Can not delete."
                            % selected_category.key)
            else:
                if forms.alert("Are you sure you want to delete category "
                               "\"%s\"?" % selected_category.key,
                               yes=True, no=True):
                    try:
                        kdb.remove_category(self._conn, selected_category.key)
                        # make sure to relaod on close
                        self._needs_update = True
                    except System.TimeoutException as toutex:
                        forms.alert(toutex.Message)
                    except Exception as ex:
                        forms.alert(str(ex))
                    finally:
                        self._update_ktree(active_catkey=self._allcat)

    def add_keynote(self, sender, args):
        # try to get parent key from selected keynote or category
        parent_key = None
        if self.selected_keynote:
            parent_key = self.selected_keynote.parent_key
        elif self.selected_category:
            parent_key = self.selected_category.key
        # otherwise ask to select a parent category
        if not parent_key:
            cat = forms.SelectFromList.show(self.all_categories,
                                            title="Select Parent Category",
                                            name_attr='text',
                                            owner=self)
            if cat:
                parent_key = cat.key
        # if parent key is available proceed to create keynote
        if parent_key:
            try:
                EditRecordWindow(self, self._conn,
                                 kdb.EDIT_MODE_ADD_KEYNOTE,
                                 pkey=parent_key).show()
                # make sure to relaod on close
                self._needs_update = True
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_ktree_knotes()

    def add_sub_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                EditRecordWindow(self, self._conn,
                                 kdb.EDIT_MODE_ADD_KEYNOTE,
                                 pkey=selected_keynote.key).show()
                # make sure to relaod on close
                self._needs_update = True
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_ktree_knotes()

    def duplicate_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    kdb.EDIT_MODE_ADD_KEYNOTE,
                    text=self.selected_keynote.text,
                    pkey=self.selected_keynote.parent_key).show()
                # make sure to relaod on close
                self._needs_update = True
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_ktree_knotes()

    def remove_keynote(self, sender, args):
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_keynote = self.selected_keynote
        if selected_keynote:
            if selected_keynote.children:
                forms.alert("Keynote \"%s\" has sub-keynotes. "
                            "Delete all its sub-keynotes first."
                            % selected_keynote.key)
            elif selected_keynote.used:
                forms.alert("Keynote \"%s\" is used in the model. "
                            "Can not delete."
                            % selected_keynote.key)
            else:
                if forms.alert("Are you sure you want to delete keynote "
                               "\"%s\"?" % selected_keynote.key,
                               yes=True, no=True):
                    try:
                        kdb.remove_keynote(self._conn, selected_keynote.key)
                        # make sure to relaod on close
                        self._needs_update = True
                    except System.TimeoutException as toutex:
                        forms.alert(toutex.Message)
                    except Exception as ex:
                        forms.alert(str(ex))
                    finally:
                        self._update_ktree_knotes()

    def edit_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    kdb.EDIT_MODE_EDIT_KEYNOTE,
                    rkeynote=self.selected_keynote).show()
                # make sure to relaod on close
                self._needs_update = True
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_ktree_knotes()

    def rekey_keynote(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def show_keynote(self, sender, args):
        if self.selected_keynote:
            self.Close()
            kids = self.get_used_keynote_elements() \
                       .get(self.selected_keynote.key, [])
            for kid in kids:
                source = viewname = ''
                kel = revit.doc.GetElement(kid)
                ehist = revit.query.get_history(kel)
                if kel:
                    source = kel.Parameter[
                        DB.BuiltInParameter.KEY_SOURCE_PARAM].AsString()
                    vel = revit.doc.GetElement(kel.OwnerViewId)
                    if vel:
                        viewname = revit.query.get_name(vel)
                # prepare report
                report = \
                    '{} \"{}\" Keynote @ \"{}\"'.format(
                        output.linkify(kid),
                        source,
                        viewname
                        )

                if ehist:
                    report += \
                        ' - Last Edited By \"{}\"'.format(ehist.last_changed_by)

                print(report)

    def place_keynote(self, sender, args):
        self.Close()
        keynotes_cat = \
            revit.query.get_category(DB.BuiltInCategory.OST_KeynoteTags)
        if keynotes_cat and self.selected_keynote:
            knote_key = self.selected_keynote.key
            def_kn_typeid = revit.doc.GetDefaultFamilyTypeId(keynotes_cat.Id)
            kn_type = revit.doc.GetElement(def_kn_typeid)
            if kn_type:
                try:
                    # place keynotes and get placed keynote elements
                    DocumentEventUtils.PostCommandAndUpdateNewElementProperties(
                        HOST_APP.uiapp,
                        revit.doc,
                        self.postable_keynote_command,
                        "Update Keynotes",
                        DB.BuiltInParameter.KEY_VALUE,
                        knote_key
                        )
                except Exception as ex:
                    forms.alert(str(ex))

    def enable_history(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def show_category_history(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def show_keynote_history(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def change_keynote_file(self, sender, args):
        if self._change_kfile():
            # make sure to relaod on close
            self._needs_update = True
            self.Close()

    def show_keynote_file(self, sender, args):
        coreutils.show_entry_in_explorer(self._kfile)

    def import_keynotes(self, sender, args):
        # verify existing keynotes when importing
        # maybe allow for merge conflict?
        kfile = forms.pick_file('txt')
        if kfile:
            logger.debug('Importing keynotes from: %s' % kfile)
            res = forms.alert("Do you want me to skip duplicates if any?",
                              yes=True, no=True)
            try:
                kdb.import_legacy_keynotes(self._conn, kfile, skip_dup=res)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)
            except Exception as ex:
                logger.debug('Importing legacy keynotes failed | %s' % ex)
                forms.alert(str(ex))
            finally:
                self._update_ktree(active_catkey=self._allcat)
                self._update_ktree_knotes()

    def export_keynotes(self, sender, args):
        kfile = forms.save_file('txt')
        if kfile:
            logger.debug('Exporting keynotes to: %s' % kfile)
            try:
                kdb.export_legacy_keynotes(self._conn, kfile)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)

    def export_visible_keynotes(self, sender, args):
        kfile = forms.save_file('txt')
        if kfile:
            logger.debug('Exporting visible keynotes to: %s' % kfile)
            include_list = set()
            for rkey in self.current_keynotes:
                include_list.update(rkey.collect_keys())
            try:
                kdb.export_legacy_keynotes(self._conn,
                                           kfile,
                                           include_keys=include_list)
            except System.TimeoutException as toutex:
                forms.alert(toutex.Message)

    def update_model(self, sender, args):
        self.Close()

    def window_closing(self, sender, args):
        if self._needs_update:
            with revit.Transaction('Update Keynotes'):
                revit.update.update_linked_keynotes(doc=revit.doc)

        try:
            self.save_config()
        except Exception as saveex:
            logger.debug('Saving configuration failed | %s' % saveex)
            forms.alert(str(saveex))

        if self._conn:
            # manuall call dispose to release locks
            try:
                self._conn.Dispose()
            except Exception:
                pass


try:
    KeynoteManagerWindow(
        xaml_file_name='KeynoteManagerWindow.xaml',
        reset_config=__shiftclick__ #pylint: disable=undefined-variable
        ).show(modal=True)
except Exception as kmex:
    forms.alert(str(kmex))
