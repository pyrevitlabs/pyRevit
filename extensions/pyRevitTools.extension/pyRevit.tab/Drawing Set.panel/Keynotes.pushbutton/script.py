"""Manage project keynotes."""
#pylint: disable=E0401,W0613,C0111,C0103
import os
import os.path as op
import shutil

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.coreutils.loadertypes import UIDocUtils

__title__ = "Manage\nKeynotes"
__author__ = "{{author}}"
__context__ = ""

logger = script.get_logger()
output = script.get_output()

# TODO:
# manage lock errors
# manage timeout errors
# search needs to filter all subkeynotes as well
# take care of todo items here
# review and fine tune all functions for beta release

# ================================================================ keynotesdb.py
#pylint: disable=W0703
from collections import namedtuple, defaultdict

from pyrevit.labs import DeffrelDB as dfdb


RKeynote = namedtuple('RKeynote',
                      ['key', 'text', 'parent_key',
                       'locked', 'owner', 'children'])

KEYNOTES_DB = 'keynotesdb'
KEYNOTES_DB_DESC = 'pyRevit Keynotes Manager DB'

CATEGORIES_TABLE = 'categories'
CATEGORIES_TABLE_DESC = 'Root Keynotes Table'
CATEGORY_KEY_FIELD = 'cat_key'
CATEGORY_TITLE_FIELD = 'cat_title'

KEYNOTES_TABLE = 'keynotes'
KEYNOTES_TABLE_DESC = 'Keynotes Table'
KEYNOTES_KEY_FIELD = 'keynote_key'
KEYNOTES_TEXT_FIELD = 'keynote_text'
KEYNOTES_PARENTKEY_FIELD = 'parent_key'


EDIT_MODE_ADD_CATEG = 'add-category'
EDIT_MODE_EDIT_CATEG = 'edit-category'
EDIT_MODE_ADD_KEYNOTE = 'add-keynote'
EDIT_MODE_EDIT_KEYNOTE = 'edit-keynote'


def _verify_keynotesdb_def(conn):
    # verify db
    try:
        conn.ReadDB(KEYNOTES_DB)
    except Exception as dbex:
        logger.debug('Keynotes db read failed | %s', dbex)
        dbdef = dfdb.DatabaseDefinition()
        dbdef.Description = KEYNOTES_DB_DESC
        conn.CreateDB(KEYNOTES_DB, dbdef)

    # verify root categories table
    try:
        conn.ReadTable(KEYNOTES_DB, CATEGORIES_TABLE)
    except Exception as cattex:
        logger.debug('Category table read failed | %s', cattex)
        cat_key = dfdb.TextField(CATEGORY_KEY_FIELD)
        cat_title = dfdb.TextField(CATEGORY_TITLE_FIELD)
        cat_table_def = dfdb.TableDefinition()
        cat_table_def.SupportsTags = False
        cat_table_def.SupportsHistory = False
        cat_table_def.EncapsulateValues = False
        cat_table_def.SupportsHeaders = False
        cat_table_def.Fields = [cat_key, cat_title]
        cat_table_def.Description = CATEGORIES_TABLE_DESC
        conn.CreateTable(KEYNOTES_DB, CATEGORIES_TABLE, cat_table_def)


    # verify keynote table
    try:
        conn.ReadTable(KEYNOTES_DB, KEYNOTES_TABLE)
    except Exception as ktex:
        logger.debug('keynote table read failed | %s', ktex)
        keynote_key = dfdb.TextField(KEYNOTES_KEY_FIELD)
        keynote_text = dfdb.TextField(KEYNOTES_TEXT_FIELD)
        keynote_parent_key = dfdb.TPrimaryKeyField(KEYNOTES_PARENTKEY_FIELD)
        keynotes_table_def = dfdb.TableDefinition()
        keynotes_table_def.SupportsTags = False
        keynotes_table_def.SupportsHistory = False
        keynotes_table_def.EncapsulateValues = False
        keynotes_table_def.SupportsHeaders = False
        keynotes_table_def.Fields = \
            [keynote_key, keynote_text, keynote_parent_key]
        keynotes_table_def.Description = KEYNOTES_TABLE_DESC
        conn.CreateTable(KEYNOTES_DB, KEYNOTES_TABLE, keynotes_table_def)


def connect(keynotes_file, username=None):
    conn = dfdb.DataBase.Connect(keynotes_file, username or HOST_APP.username)
    logger.debug('verifying db schemas...')
    _verify_keynotesdb_def(conn)
    logger.debug('verifying db schemas completed.')
    return conn

# query functions -------------------------------------------------------------

def get_locks(conn):
    return conn.ReadLocks()


def get_categories(conn):
    db_locks = get_locks(conn)
    locked_records = {x.LockTargetRecordKey: x.LockRequester
                      for x in db_locks if x.IsRecordLock}
    cats_records = conn.ReadAllRecords(KEYNOTES_DB, CATEGORIES_TABLE)
    return [RKeynote(key=x[CATEGORY_KEY_FIELD],
                     text=x[CATEGORY_TITLE_FIELD] or '',
                     parent_key='',
                     locked=x[CATEGORY_KEY_FIELD] in locked_records.keys(),
                     owner=locked_records.get(x[CATEGORY_KEY_FIELD], ''),
                     children=[])
            for x in cats_records]


def get_keynotes(conn):
    db_locks = get_locks(conn)
    locked_records = {x.LockTargetRecordKey: x.LockRequester
                      for x in db_locks if x.IsRecordLock}
    keynote_records = conn.ReadAllRecords(KEYNOTES_DB, KEYNOTES_TABLE)
    return [RKeynote(key=x[KEYNOTES_KEY_FIELD],
                     text=x[KEYNOTES_TEXT_FIELD] or '',
                     parent_key=x[KEYNOTES_PARENTKEY_FIELD],
                     locked=x[KEYNOTES_KEY_FIELD] in locked_records.keys(),
                     owner=locked_records.get(x[KEYNOTES_KEY_FIELD], ''),
                     children=[])
            for x in keynote_records]


def get_keynotes_tree(conn):
    keynote_records = get_keynotes(conn)
    parents = defaultdict(list)
    for rkey in keynote_records:
        parents[rkey.parent_key].append(rkey)
    roots = []
    for rkey in keynote_records:
        if rkey.key in parents:
            rkey.children.extend(parents[rkey.key])
        roots.append(rkey)
    return sorted(roots, key=lambda x: x.key)


def find(conn, key):
    for record in get_categories(conn) + get_keynotes(conn):
        if record.key == key:
            return record

# locking ---------------------------------------------------------------------

def begin_edit(conn, key, category=False):
    target_table = CATEGORIES_TABLE if category else KEYNOTES_TABLE
    conn.BEGIN(KEYNOTES_DB, target_table, key)


def end_edit(conn):
    conn.END()


def reserve_key(conn, key, category=False):
    target_table = CATEGORIES_TABLE if category else KEYNOTES_TABLE
    conn.BEGIN(KEYNOTES_DB, target_table, key)


def release_key(conn, key, category=False):
    conn.END()

# categories ------------------------------------------------------------------

def add_category(conn, key, text):
    conn.InsertRecord(KEYNOTES_DB,
                      CATEGORIES_TABLE,
                      key,
                      {CATEGORY_TITLE_FIELD: text})


def update_category_title(conn, key, new_title):
    conn.UpdateRecord(KEYNOTES_DB, CATEGORIES_TABLE, key,
                      {CATEGORY_TITLE_FIELD: new_title})


def remove_category(conn, key):
    conn.DropRecord(KEYNOTES_DB, CATEGORIES_TABLE, key)


def rekey_category(conn, key, new_key):
    # TODO: rekey_category
    pass
# keynotes --------------------------------------------------------------------

def add_keynote(conn, key, text, parent_key):
    conn.InsertRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key,
        {KEYNOTES_TEXT_FIELD: text,
         KEYNOTES_PARENTKEY_FIELD: parent_key}
        )


def remove_keynote(conn, key):
    conn.DropRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key
        )


def mark_category_under_edited(conn, key):
    conn.BEGIN(KEYNOTES_DB, CATEGORIES_TABLE, key)


def mark_keynote_under_edited(conn, key):
    conn.BEGIN(KEYNOTES_DB, KEYNOTES_TABLE, key)


def update_keynote_text(conn, key, text):
    conn.UpdateRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key,
        {KEYNOTES_TEXT_FIELD: text}
        )


def update_keynote_key(conn, key, new_key):
    conn.UpdateRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key,
        {KEYNOTES_KEY_FIELD: new_key}
        )


def move_keynote(conn, key, new_parent):
    conn.UpdateRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key,
        {KEYNOTES_PARENTKEY_FIELD: new_parent}
        )


def rekey_keynote(conn, key, new_key):
    # TODO: rekey_keynote
    pass


def import_legacy_keynotes(conn, legacy_keynotes_file, skip_dup=False):
    conn.BEGIN(KEYNOTES_DB)
    try:
        with open(legacy_keynotes_file, 'r') as lkf:
            for line in lkf.readlines():
                clean_line = line.strip()
                if not clean_line.startswith('#'):
                    fields = clean_line.split('\t')
                    if len(fields) == 2 \
                            or (len(fields) == 3 and not fields[2]):
                        # add category
                        try:
                            add_category(conn, fields[0], fields[1])
                        except Exception as cataddex:
                            if skip_dup:
                                pass
                            else:
                                raise cataddex
                    elif len(fields) == 3:
                        # add keynote
                        try:
                            add_keynote(conn, fields[0], fields[1], fields[2])
                        except Exception as cataddex:
                            if skip_dup:
                                pass
                            else:
                                raise cataddex
    finally:
        conn.END()


def export_legacy_keynotes(conn, target_legacy_keynotes_file):
    categories = get_categories(conn)
    keynotes = get_keynotes(conn)
    with open(target_legacy_keynotes_file, 'w') as lkfile:
        for cat in categories:
            lkfile.write('{}\t{}\n'.format(cat.key, cat.text))
        for knote in keynotes:
            lkfile.write('{}\t{}\t{}\n'
                         .format(knote.key, knote.text, knote.parent_key))

# =================================================================

class EditRecordWindow(forms.WPFWindow):
    def __init__(self,
                 owner,
                 conn, mode,
                 rkeynote=None,
                 rkey=None, text=None, pkey=None):
        forms.WPFWindow.__init__(self, 'EditRecord.xaml')
        self.Owner = owner
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
        if self._mode == EDIT_MODE_ADD_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = 'Add Category'
            self.recordKeyTitle.Text = 'Create Category Key'
            self.applyChanges.Content = 'Add Category'

        elif self._mode == EDIT_MODE_EDIT_CATEG:
            self._cat = True
            self.hide_element(self.recordParentInput)
            self.Title = 'Edit Category'
            self.recordKeyTitle.Text = 'Category Key'
            self.applyChanges.Content = 'Update Category'
            self.recordKey.IsEnabled = False
            if self._rkeynote:
                if self._rkeynote.key:
                    try:
                        begin_edit(self._conn,
                                   self._rkeynote.key,
                                   category=True)
                    except Exception as ex:
                        forms.alert(str(ex))
                        return

        elif self._mode == EDIT_MODE_ADD_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Add Keynote'
            self.recordKeyTitle.Text = 'Create Keynote Key'
            self.applyChanges.Content = 'Add Keynote'

        elif self._mode == EDIT_MODE_EDIT_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Edit Keynote'
            self.recordKeyTitle.Text = 'Keynote Key'
            self.applyChanges.Content = 'Update Keynote'
            self.recordKey.IsEnabled = False
            if self._rkeynote:
                # start edit
                if self._rkeynote.key:
                    try:
                        begin_edit(self._conn,
                                   self._rkeynote.key,
                                   category=False)
                    except Exception as ex:
                        forms.alert(str(ex))
                        return

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
        if isinstance(self.recordKey.Content, str):
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
        if self._mode == EDIT_MODE_ADD_CATEG:
            if not self.active_key:
                forms.alert('Category must have a unique key.')
                return False
            elif not self.active_text.strip():
                forms.alert('Category must have a title.')
                return False
            logger.debug('Adding category: {} {}'
                         .format(self.active_key, self.active_text))
            add_category(self._conn, self.active_key, self.active_text)
            end_edit(self._conn)

        elif self._mode == EDIT_MODE_EDIT_CATEG:
            if not self.active_text:
                forms.alert('Existing title is removed. '
                            'Category must have a title.')
                return False
            # update category key if changed
            if self.active_key != self._rkeynote.key:
                rekey_category(self._conn, self._rkeynote.key, self.active_key)
            # update category title if changed
            if self.active_text != self._rkeynote.text:
                update_category_title(self._conn,
                                      self.active_key,
                                      self.active_text)
            end_edit(self._conn)

        elif self._mode == EDIT_MODE_ADD_KEYNOTE:
            if not self.active_key:
                forms.alert('Keynote must have a unique key.')
                return False
            elif not self.active_text:
                forms.alert('Keynote must have text.')
                return False
            elif not self.active_parent_key:
                forms.alert('Keynote must have a parent.')
                return False
            add_keynote(self._conn,
                        self.active_key,
                        self.active_text,
                        self.active_parent_key)
            end_edit(self._conn)

        elif self._mode == EDIT_MODE_EDIT_KEYNOTE:
            if not self.active_text:
                forms.alert('Existing text is removed. Keynote must have text.')
                return False
            # update keynote key if changed
            if self.active_key != self._rkeynote.key:
                rekey_keynote(self._conn, self._rkeynote.key, self.active_key)
            # update keynote title if changed
            if self.active_text != self._rkeynote.text:
                update_keynote_text(self._conn,
                                    self.active_key,
                                    self.active_text)
            # update keynote parent
            if self.active_parent_key != self._rkeynote.parent_key:
                move_keynote(self._conn,
                             self.active_key,
                             self.active_parent_key)
            end_edit(self._conn)

        return True

    def show(self):
        self.ShowDialog()

    def pick_key(self, sender, args):
        # remove previously reserved
        if self._reserved_key:
            release_key(self._conn, self._reserved_key, category=self._cat)
        # collect existing keys
        reserved_keys = [x.key for x in get_categories(self._conn)]
        reserved_keys.extend([x.key for x in get_keynotes(self._conn)])
        reserved_keys.extend(
            [x.LockTargetRecordKey for x in get_locks(self._conn)]
            )
        # ask for a unique new key
        new_key = forms.ask_for_unique_string(
            prompt='Enter a Unique Key',
            title=self.Title,
            reserved_values=reserved_keys)
        if new_key:
            try:
                reserve_key(self._conn, new_key, category=self._cat)
                self._reserved_key = new_key
                # set the key value on the button
                self.active_key = new_key
            except Exception as ex:
                forms.alert(str(ex))
                return

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
                release_key(self._conn, self._reserved_key, category=self._cat)
            end_edit(self._conn)


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # verify keynote file existence
        self._kfile = revit.query.get_keynote_file(doc=revit.doc)
        if not self._kfile or not op.exists(self._kfile):
            self._kfile = None
            forms.alert("Keynote file is not accessible. "
                        "I'll ask you to select a keynote file.")
            kfile = forms.pick_file('txt')
            if kfile:
                logger.debug('Setting keynote file: %s' % kfile)
                try:
                    with revit.Transaction("Set Keynote File"):
                        revit.update.set_keynote_file(kfile, doc=revit.doc)
                    self._kfile = revit.query.get_keynote_file(doc=revit.doc)
                except Exception as skex:
                    forms.alert(str(skex))
                    return

        # if a keynote file is still not set, return
        if not self._kfile:
            raise Exception('Keynote file is not setup.')

        self._conn = None
        try:
            self._conn = connect(self._kfile)
        except Exception as ex:
            logger.debug('Connection failed | %s' % ex)
            res = forms.alert(
                "Existing keynote file needs to be converted to "
                "a format usable by this tool. The resulting keynote "
                "file is still readble by Revit and could be shared "
                "with other projects. Users should be making changes to "
                "the existing keynote file during the conversion process.\n"
                "Are you sure you want to convert?",
                options=["Convert", "Give me more info"])
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
                elif res == "Give me more info":
                    script.open_url('https://eirannejad.github.io/pyRevit')
                    script.exit()
            else:
                forms.alert("Keynote file is not yet converted.",
                            exitscript=True)


        self._allcat = RKeynote(key='', text='-- ALL CATEGORIES --',
                                parent_key='',
                                locked=False, owner='',
                                children=None)

        self._config = script.get_config()
        self._update_postable_commands()
        self._update_window_geom()

        self.refresh(None, None)

    @property
    def window_geom(self):
        return (self.Width, self.Height, self.Top, self.Left)

    @window_geom.setter
    def window_geom(self, geom_tuple):
        self.Width, self.Height, self.Top, self.Left = geom_tuple   #pylint: disable=W0201

    @property
    def target_id(self):
        return hash(self._kfile)

    @property
    def search_term(self):
        return self.search_tb.Text

    @property
    def postable_keynote_command(self):
        # order must match the order in GUI
        return [UI.PostableCommand.UserKeynote,
                UI.PostableCommand.ElementKeynote,
                UI.PostableCommand.MaterialKeynote][self.postcmd_idx]

    @property
    def postcmd_idx(self):
        return self.keynotetype_cb.SelectedIndex

    @postcmd_idx.setter
    def postcmd_idx(self, index):
        self.keynotetype_cb.SelectedIndex = index

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    @property
    def selected_category(self):
        cat = self.categories_tv.SelectedItem
        if cat and cat != self._allcat:
            return cat

    @property
    def all_keynotes(self):
        return get_keynotes(self._conn)

    @property
    def current_keynotes(self):
        return self.keynotes_tv.ItemsSource

    @property
    def keynote_text_with(self):
        return 200

    def get_last_category_key(self):
        last_category_dict = self._config.get_option('last_category', {})
        if last_category_dict and self._kfile in last_category_dict:
            return last_category_dict[self._kfile]

    def get_last_postcmd_idx(self):
        last_postcmd_dict = self._config.get_option('last_postcmd_idx', {})
        if last_postcmd_dict and self._kfile in last_postcmd_dict:
            return last_postcmd_dict[self._kfile]
        else:
            return 0

    def get_last_window_geom(self):
        last_window_geom_dict = \
            self._config.get_option('last_window_geom', {})
        if last_window_geom_dict and self._kfile in last_window_geom_dict:
            return last_window_geom_dict[self._kfile]
        else:
            return self.window_geom

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
        script.save_config()

    def _convert_existing(self):
        # make a copy of exsing
        temp_kfile = op.join(op.dirname(self._kfile), 'backup.txt')
        shutil.copy(self._kfile, temp_kfile)
        os.remove(self._kfile)
        self._conn = connect(self._kfile)
        import_legacy_keynotes(self._conn, temp_kfile, skip_dup=True)

    def _update_postable_commands(self):
        self.postcmd_idx = self.get_last_postcmd_idx()

    def _update_window_geom(self):
        width, height, top, left = self.get_last_window_geom()
        if coreutils.is_box_visible_on_screens(left, top, width, height):
            self.window_geom = (width, height, top, left)
        else:
            self.WindowStartupLocation = \
                framework.Windows.WindowStartupLocation.CenterScreen

    def _update_ktree(self):
        categories = [self._allcat]
        categories.extend(get_categories(self._conn))

        last_idx = 0
        last_cat_key = self.get_last_category_key()
        if last_cat_key:
            cat_keys = [x.key for x in categories]
            if last_cat_key in cat_keys:
                last_idx = cat_keys.index(last_cat_key)
        else:
            if self.categories_tv.ItemsSource:
                last_idx = self.categories_tv.SelectedIndex

        self.categories_tv.ItemsSource = categories
        self.categories_tv.SelectedIndex = last_idx
        self._update_ktree_knotes()

    def _update_ktree_knotes(self, fast=False):
        keynote_filter = self.search_term if self.search_term else None
        if fast and keynote_filter:
            active_keynotes = self.keynotes_tv.ItemsSource
        else:
            active_keynotes = get_keynotes_tree(self._conn)
            selected_cat = self.selected_category
            if selected_cat:
                if selected_cat.key:
                    active_keynotes = \
                        [x for x in active_keynotes
                        if x.parent_key == self.selected_category.key]

        if keynote_filter:
            clean_filter = keynote_filter.lower()
            filtered_keynotes = \
                [x for x in active_keynotes
                 if clean_filter in x.key.lower()
                 + x.text.lower()
                 + x.owner.lower()]
        else:
            filtered_keynotes = active_keynotes

        self.keynotes_tv.ItemsSource = filtered_keynotes

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
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

    def selected_category_changed(self, sender, args):
        if self.selected_category and not self.selected_category.locked:
            self.catEditButtons.IsEnabled = True
        else:
            self.catEditButtons.IsEnabled = False
        self._update_ktree_knotes()

    def selected_keynote_changed(self, sender, args):
        if self.selected_keynote and not self.selected_keynote.locked:
            self.keynoteEditButtons.IsEnabled = True
        else:
            self.keynoteEditButtons.IsEnabled = False

    def refresh(self, sender, args):
        if self._conn:
            self._update_ktree()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        try:
            EditRecordWindow(self, self._conn, EDIT_MODE_ADD_CATEG).show()
            self._update_ktree()
        except Exception as ex:
            forms.alert(str(ex))

    def edit_category(self, sender, args):
        selected_category = self.selected_category
        if selected_category:
            if selected_category.locked:
                forms.alert('Category is locked and is being edited by {}. '
                            'Wait until their changes are committed. '
                            'Meanwhile you can use or modify the keynotes '
                            'under this category.'
                            .format('\"%s\"' % selected_category.owner
                                    if selected_category.owner
                                    else 'and unknown user'))
            else:
                try:
                    EditRecordWindow(self, self._conn,
                                     EDIT_MODE_EDIT_CATEG,
                                     rkeynote=selected_category).show()
                    self._update_ktree()
                except Exception as ex:
                    forms.alert(str(ex))

    def rekey_category(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def remove_category(self, sender, args):
        # TODO: make sure noone owns any sub keynotes
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_category = self.selected_category
        if selected_category:
            if forms.alert(
                    "Are you sure about deleting %s?" % selected_category.key,
                    yes=True, no=True):
                try:
                    remove_category(self._conn, selected_category.key)
                except Exception as ex:
                    forms.alert(str(ex))
                finally:
                    self._update_ktree()

    def add_keynote(self, sender, args):
        parent_key = None
        if self.selected_keynote:
            parent_key = self.selected_keynote.parent_key
        elif self.selected_category:
            parent_key = self.selected_category.key

        try:
            EditRecordWindow(self, self._conn,
                             EDIT_MODE_ADD_KEYNOTE,
                             pkey=parent_key).show()
            self._update_ktree_knotes()
        except Exception as ex:
            forms.alert(str(ex))

    def add_sub_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                EditRecordWindow(self, self._conn,
                                 EDIT_MODE_ADD_KEYNOTE,
                                 pkey=selected_keynote.key).show()
                self._update_ktree_knotes()
            except Exception as ex:
                forms.alert(str(ex))

    def duplicate_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    EDIT_MODE_ADD_KEYNOTE,
                    text=self.selected_keynote.text,
                    pkey=self.selected_keynote.parent_key).show()
                self._update_ktree_knotes()
            except Exception as ex:
                forms.alert(str(ex))

    def remove_keynote(self, sender, args):
        # TODO: make sure noone owns any sub keynotes
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_keynote = self.selected_keynote
        if selected_keynote:
            if forms.alert(
                    "Are you sure about deleting %s?" % selected_keynote.key,
                    yes=True, no=True):
                try:
                    remove_keynote(self._conn, selected_keynote.key)
                    self._update_ktree_knotes()
                except Exception as ex:
                    forms.alert(str(ex))

    def edit_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self,
                    self._conn,
                    EDIT_MODE_EDIT_KEYNOTE,
                    rkeynote=self.selected_keynote).show()
                self._update_ktree_knotes()
            except Exception as ex:
                forms.alert(str(ex))

    def rekey_keynote(self, sender, args):
        forms.alert("Not yet implemented. Coming soon.")

    def place_keynote(self, sender, args):
        self.Close()
        keynotes_cat = \
            revit.query.get_category(DB.BuiltInCategory.OST_KeynoteTags)
        if keynotes_cat and self.selected_keynote:
            knote_key = self.selected_keynote.key
            def_kn_typeid = revit.doc.GetDefaultFamilyTypeId(keynotes_cat.Id)
            kn_type = revit.doc.GetElement(def_kn_typeid)
            if kn_type:
                uidoc_utils = UIDocUtils(HOST_APP.uiapp)
                # place keynotes and get placed keynote elements
                try:
                    uidoc_utils.PostCommandAndUpdateNewElementProperties(
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

    def import_keynotes(self, sender, args):
        # verify existing keynotes when importing
        # maybe allow for merge conflict?
        kfile = forms.pick_file('txt')
        logger.debug('Importing keynotes from: %s' % kfile)
        if kfile:
            res = forms.alert("Do you want me to skip duplicates if any?",
                              yes=True, no=True)
            try:
                import_legacy_keynotes(self._conn,
                                       kfile,
                                       skip_dup=res)
                self._update_ktree()
            except Exception as ex:
                logger.debug('Importing legacy keynotes failed | %s' % ex)
                forms.alert(str(ex))

    def export_keynotes(self, sender, args):
        kfile = forms.save_file('txt')
        logger.debug('Exporting keynotes from: %s' % kfile)
        if kfile:
            export_legacy_keynotes(self._conn, kfile)

    def update_model(self, sender, args):
        self.Close()

    def window_closed(self, sender, args):
        try:
            self.save_config()
        except Exception as saveex:
            logger.debug('Saving configuration failed | %s' % saveex)
            forms.alert(str(saveex))
        if self._conn:
            # manuall call dispose to release locks
            self._conn.Dispose()
            with revit.Transaction('Update Keynotes'):
                revit.update.update_linked_keynotes(doc=revit.doc)


try:
    # forms.alert("This tool is in beta testing stage. "
    #             "Please only use for testing purposes.")
    KeynoteManagerWindow('KeynoteManagerWindow.xaml').show(modal=True)
except Exception as kmex:
    forms.alert(str(kmex))
