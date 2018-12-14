"""Manage project keynotes."""
#pylint: disable=E0401,W0613,C0111,C0103
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__title__ = "Manage\nKeynotes"
__author__ = "{{author}}"
__context__ = ""

logger = script.get_logger()
output = script.get_output()

"""
startup:
get ketnotes tree
get locked keynotes (collect locker)
get unused keynotes (collect info?)
build and show tree (color code locked and unused keynotes)



"""

# ================================================================ keynotesdb.py
#pylint: disable=W0703
from collections import namedtuple

from pyrevit.labs import DeffrelDB as kdb


RKeynote = namedtuple('RKeynote',
                      ['key', 'text', 'parent_key', 'locked', 'owner'])

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

RESERVERD_TEXT_FIELD_VALUE = '-------------- reserved by keynote manager -----------------'


def _verify_keynotesdb_def(conn):
    keynotesdb_ok = True
    keynotes_table_ok = True
    categories_table_ok = True

    # verify db
    try:
        conn.ReadDB(KEYNOTES_DB)
    except Exception:
        keynotesdb_ok = False

    if not keynotesdb_ok:
        dbdef = kdb.DatabaseDefinition()
        dbdef.Description = KEYNOTES_DB_DESC
        conn.CreateDB(KEYNOTES_DB, dbdef)

    # verify root categories table
    try:
        conn.ReadTable(KEYNOTES_DB, CATEGORIES_TABLE)
    except Exception:
        categories_table_ok = False

    if not categories_table_ok:
        cat_key = kdb.TextField(CATEGORY_KEY_FIELD)
        cat_title = kdb.TextField(CATEGORY_TITLE_FIELD)
        cat_table_def = kdb.TableDefinition()
        cat_table_def.SupportsTags = False
        cat_table_def.SupportsHistory = False
        cat_table_def.EncapsulateValues = False
        cat_table_def.SupportsHeaders = False
        cat_table_def.Fields = [cat_key, cat_title]
        cat_table_def.Description = CATEGORIES_TABLE_DESC
        conn.CreateTable(KEYNOTES_DB, CATEGORIES_TABLE, cat_table_def)

    try:
        conn.ReadTable(KEYNOTES_DB, KEYNOTES_TABLE)
    except Exception:
        keynotes_table_ok = False

    if not keynotes_table_ok:
        keynote_key = kdb.TextField(KEYNOTES_KEY_FIELD)
        keynote_text = kdb.TextField(KEYNOTES_TEXT_FIELD)
        keynote_parent_key = kdb.TPrimaryKeyField(CATEGORY_KEY_FIELD)
        keynotes_table_def = kdb.TableDefinition()
        keynotes_table_def.SupportsTags = False
        keynotes_table_def.SupportsHistory = False
        keynotes_table_def.EncapsulateValues = False
        keynotes_table_def.SupportsHeaders = False
        keynotes_table_def.Fields = \
            [keynote_key, keynote_text, keynote_parent_key]
        keynotes_table_def.Description = KEYNOTES_TABLE_DESC
        conn.CreateTable(KEYNOTES_DB, KEYNOTES_TABLE, keynotes_table_def)


def connect(keynotes_file, username=None):
    conn = kdb.DataBase.Connect(keynotes_file, username or HOST_APP.username)
    _verify_keynotesdb_def(conn)
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
                     owner=locked_records.get(x[CATEGORY_KEY_FIELD], ''))
            for x in cats_records]


def get_keynotes(conn):
    db_locks = get_locks(conn)
    locked_records = {x.LockTargetRecordKey: x.LockRequester
                      for x in db_locks if x.IsRecordLock}
    keynote_records = conn.ReadAllRecords(KEYNOTES_DB, KEYNOTES_TABLE)
    return [RKeynote(key=x[KEYNOTES_KEY_FIELD],
                     text=x[KEYNOTES_TEXT_FIELD] or '',
                     parent_key=x[CATEGORY_KEY_FIELD],
                     locked=x[KEYNOTES_KEY_FIELD] in locked_records.keys(),
                     owner=locked_records.get(x[KEYNOTES_KEY_FIELD], ''))
            for x in keynote_records]

# locking ---------------------------------------------------------------------

def begin_edit(conn, key, category=False):
    target_table = CATEGORIES_TABLE if category else KEYNOTES_TABLE
    conn.BEGIN(KEYNOTES_DB, target_table, key)


def end_edit(conn):
    conn.END()


def reserve_key(conn, key, category=False):
    if category:
        conn.CreateRecord(KEYNOTES_DB, CATEGORIES_TABLE,
                          {CATEGORY_KEY_FIELD: key,
                           CATEGORY_TITLE_FIELD: None})
    else:
        conn.CreateRecord(KEYNOTES_DB, KEYNOTES_TABLE,
                          {KEYNOTES_KEY_FIELD: key,
                           KEYNOTES_TEXT_FIELD: None,
                           CATEGORY_KEY_FIELD: None})

# categories ------------------------------------------------------------------

def add_category(conn, key, text):
    conn.CreateRecord(KEYNOTES_DB, CATEGORIES_TABLE,
                      {CATEGORY_KEY_FIELD: key,
                       CATEGORY_TITLE_FIELD: text})


def update_category_title(conn, key, new_title):
    conn.UpdateRecord(KEYNOTES_DB, CATEGORIES_TABLE, key,
                      {CATEGORY_TITLE_FIELD: new_title})


def remove_category(conn, key):
    conn.DropRecord(KEYNOTES_DB, CATEGORIES_TABLE, key)

# keynotes --------------------------------------------------------------------

def add_keynote(conn, key, text, parent=None):
    # TODO: add keynote workflow
    # add record with key and empty text
    # lock the record
    conn.CreateRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        {KEYNOTES_KEY_FIELD: key,
         KEYNOTES_TEXT_FIELD: text,
         CATEGORY_KEY_FIELD: parent}
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


def move_keynote(conn, current_parent, new_parent):
    pass


def import_legacy_keynotes(conn, legacy_keynotes_file):
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
                        add_category(conn, fields[0], fields[1])
                    elif len(fields) == 3:
                        # add keynote
                        add_keynote(conn, fields[0], fields[1], fields[2])
    finally:
        conn.END()


def export_legacy_keynotes(target_legacy_keynotes_file):
    pass
# ==============================================================================


# ================================================================= revit.update
def update_linked_keynotes(doc=None):
    doc = doc or HOST_APP.doc
    ktable = DB.KeynoteTable.GetKeynoteTable(doc)
    ktable.Reload(None)
# ==============================================================================


class EditRecordWindow(forms.WPFWindow):
    def __init__(self, conn, rkey=None, category=False):
        forms.WPFWindow.__init__(self, 'EditRecord.xaml')
        self.response = (None, None)

        # connection
        self._conn = conn
        # category or keynote?
        self._cat = category
        if self._cat:
            self.hide_element(self.selectParentRow)
            self.Title = 'Edit Category'
            self.selectKeyTitle.Text = 'Category Key'

        # target keynote
        self._rkey = rkey

        if self._rkey:
            self.selectKey.Content = str(self._rkey.key)
            self.selectParent.Content = str(self._rkey.parent_key)
            self.recordText.Text = self._rkey.text
        else:
            self.applyChanges.Content = \
                'Create {}'.format('Category' if self._cat else 'Keynote')
        # select text in textbox for easy editing
        self.recordText.Focus()
        self.recordText.SelectAll()

    def show(self):
        self.ShowDialog()
        return self.response

    def pick_key(self, sender, args):
        # read button content for existing key
        # verify that record is not a temporary record
            # if it is, remove it and release any locks
        # collect existing keys
        reserved_keys = [x.key for x in get_categories(self._conn)]
        reserved_keys.extend([x.key for x in get_keynotes(self._conn)])
        # ask for a unique new key
        new_key = forms.ask_for_unique_string(
            prompt='Enter Unique Key',
            title=self.Title,
            reserved_values=reserved_keys)
        # create empty record with that key
        try:
            reserve_key(self._conn, new_key, category=True)
        except Exception as ex:
            forms.alert('reserve_key' + str(ex))
            return
        # place a lock on that key
        try:
            begin_edit(self._conn, new_key, category=True)
        except Exception as ex:
            forms.alert('begin_edit' + str(ex))
            return
        # set the key value on the button
        self.selectKey.Content = new_key

    def pick_parent(self, sender, args):
        forms.alert('Picking a new parent...')
        # read all records
        # remove self from that record if self is not none
        # prompt to select a record
        # apply the record key on the button

    def apply_changes(self, sender, args):
        self.Close()
        # are we editing an existing record?
        if self._rkey:
            self.response = ('nochange', None)
            if self.recordText.Text != self._rkey.text:
                self.response = ('text', self.recordText.Text)
        # or creating a new record?
        else:
            new_key = self.selectKey.Content
            new_parent_key = '' if self._cat else self.selectParent.Content
            self.response = ('new',
                             RKeynote(key=new_key,
                                      text=self.recordText.Text,
                                      parent_key=new_parent_key,
                                      locked=False,
                                      owner=''))


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # TODO: verify kfile
        self._kfile = revit.query.get_keynote_file(doc=revit.doc)
        self._conn = None
        try:
            self._conn = connect(self._kfile)
        except Exception as ex:
            forms.alert(str(ex), exitscript=True)

        self._allcat = RKeynote(key='', text='-- ALL CATEGORIES --',
                                parent_key='', locked=False, owner='')
        
        self.refresh(None, None)

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    @property
    def search_term(self):
        return self.search_tb.Text

    @property
    def selected_category(self):
        return self.categories_tv.SelectedItem

    @property
    def all_keynotes(self):
        return get_keynotes(self._conn)

    @property
    def current_keynotes(self):
        return self.keynotes_tv.ItemsSource

    def _update_ktree(self):
        # maybe some coloring on filter?
        # https://stackoverflow.com/questions/5442067/change-color-and-font-for-some-part-of-text-in-wpf-c-sharp
        categories = [self._allcat]
        categories.extend(get_categories(self._conn))
        self.categories_tv.ItemsSource = categories
        self.categories_tv.SelectedIndex = 0
        self._update_ktree_knotes()

    def _update_ktree_knotes(self):
        active_keynotes = get_keynotes(self._conn)
        selected_cat = self.selected_category
        if selected_cat:
            if selected_cat.key == '':
                active_keynotes = \
                    sorted([x for x in active_keynotes], key=lambda x: x.key)
            else:
                active_keynotes = \
                    sorted([x for x in active_keynotes
                            if x.parent_key == self.selected_category.key],
                           key=lambda x: x.key)

        keynote_filter = self.search_term if self.search_term else None
        if keynote_filter:
            clean_filter = keynote_filter.lower()
            self.keynotes_tv.ItemsSource = \
                [x for x in active_keynotes
                 if clean_filter in x.key.lower()
                 or clean_filter in x.text.lower()
                 or clean_filter in x.owner.lower()]
        else:
            self.keynotes_tv.ItemsSource = active_keynotes

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._update_ktree_knotes()

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

    def selected_category_changed(self, sender, args):
        self._update_ktree_knotes()

    def refresh(self, sender, args):
        if self._conn:
            self._update_ktree()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        try:
            edit_type, new_rkey = \
                EditRecordWindow(self._conn, category=True).show()
            if edit_type == 'new':
                update_category_title(self._conn, new_rkey.key, new_rkey.text)
            self._update_ktree()
            self._conn.END()
        except Exception as ex:
            forms.alert(str(ex))

    def edit_category(self, sender, args):
        selected_category = self.selected_category
        if selected_category and selected_category.text != self._allcat.text:
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
                    # start edit
                    begin_edit(self._conn,
                               selected_category.key, category=True)
                    # get updated value
                    edit_type, updated_value = \
                        EditRecordWindow(self._conn,
                                         rkey=selected_category,
                                         category=True).show()
                    # process and apply the updated value
                    if edit_type == 'text':
                        update_category_title(self._conn,
                                              selected_category.key,
                                              updated_value)
                    elif edit_type == 'key':
                        # TODO: rekey category
                        forms.alert('Rekeying category...')
                except Exception as ex:
                    forms.alert(str(ex))
                finally:
                    end_edit(self._conn)
                    self._update_ktree()

    def remove_category(self, sender, args):
        selected_category = self.selected_category
        if selected_category and selected_category.text != self._allcat.text:
            try:
                remove_category(self._conn, selected_category.key)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._update_ktree()

    def add_keynote(self, sender, args):
        self._last_kn = 'SK{}'.format(self._text_counter)
        try:
            add_keynote(self._conn, self._last_kn, 'Some value', self._lastcat)
            self._text_counter += 1
            self._update_ktree()
        except Exception as ex:
            forms.alert(str(ex))

    def duplicate_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                add_keynote(self._conn, selected_keynote.key + '-DUP', 'Some value', self._lastcat)
                self._update_ktree()
            except Exception as ex:
                forms.alert(str(ex))

    def remove_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                remove_keynote(self._conn, selected_keynote.key)
                self._update_ktree()
            except Exception as ex:
                forms.alert(str(ex))

    def add_child_keynote(self, sender, args):
        # detect selected keynote
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                add_keynote(self._conn, selected_keynote.key + str(self._text_counter), 'Some value', self._lastcat)
                self._text_counter += 1
                self._update_ktree()
            except Exception as ex:
                forms.alert(str(ex))

    def edit_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                self._conn.BEGIN(KEYNOTES_DB,
                                 KEYNOTES_TABLE,
                                 selected_keynote.key)
                edit_type, updated_value = \
                    EditRecordWindow(selected_keynote,
                                      self.all_keynotes).show()
                if edit_type == 'text':
                    update_keynote_text(self._conn,
                                        selected_keynote.key,
                                        updated_value)
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._conn.END()
                self._update_ktree_knotes()

    def update_keynote_key(self, sender, args):
        # mark_keynote_under_edited(self._conn, self._last_kn)
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                self._conn.BEGIN(KEYNOTES_DB, KEYNOTES_TABLE, selected_keynote.key)
                forms.alert('Click OK When finished editing...', ok=True)
                update_keynote_key(self._conn, selected_keynote.key, selected_keynote.key + '-ED')
            except Exception as ex:
                forms.alert(str(ex))
            finally:
                self._conn.END()
                self._update_ktree()

    def place_keynote(self, sender, args):
        self.Close()
        # TODO: figure out how to place a keynote

    def import_keynotes(self, sender, args):
        # verify existing keynotes when importing
        # maybe allow for merge conflict?
        kfile = forms.pick_file('txt')
        if kfile:
            try:
                import_legacy_keynotes(self._conn, kfile)
                self._update_ktree()
            except Exception as ex:
                forms.alert(str(ex))

    def update_model(self, sender, args):
        self.Close()

    def window_closed(self, sender, args):
        if self._conn:
            del self._conn
            with revit.Transaction('Update Keynotes'):
                update_linked_keynotes(doc=revit.doc)



KeynoteManagerWindow('KeynoteManagerWindow.xaml').show(modal=True)
