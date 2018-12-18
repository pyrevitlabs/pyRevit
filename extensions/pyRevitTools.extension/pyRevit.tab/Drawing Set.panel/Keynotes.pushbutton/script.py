"""Manage project keynotes."""
#pylint: disable=E0401,W0613,C0111,C0103
from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

from pyrevit.coreutils.loadertypes import UIDocUtils

__title__ = "Manage\nKeynotes"
__author__ = "{{author}}"
__context__ = ""

logger = script.get_logger()
output = script.get_output()

# ================================================================ keynotesdb.py
#pylint: disable=W0703
from collections import namedtuple

from pyrevit.labs import DeffrelDB as kdb


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
        logger.debug('db exception: %s', dbex)
        dbdef = kdb.DatabaseDefinition()
        dbdef.Description = KEYNOTES_DB_DESC
        conn.CreateDB(KEYNOTES_DB, dbdef)

    # verify root categories table
    try:
        conn.ReadTable(KEYNOTES_DB, CATEGORIES_TABLE)
    except Exception as cattex:
        logger.debug('category table exception: %s', cattex)
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

    # verify keynote table
    try:
        conn.ReadTable(KEYNOTES_DB, KEYNOTES_TABLE)
    except Exception as ktex:
        logger.debug('keynote table exception: %s', ktex)
        keynote_key = kdb.TextField(KEYNOTES_KEY_FIELD)
        keynote_text = kdb.TextField(KEYNOTES_TEXT_FIELD)
        keynote_parent_key = kdb.TPrimaryKeyField(KEYNOTES_PARENTKEY_FIELD)
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
    rkey_dict = {x.key: x for x in keynote_records}
    to_be_removed = []
    for rkey in keynote_records:
        parent = rkey_dict.get(rkey.parent_key, None)
        if parent:
            logger.debug('adding parent-child: %s --> %s', parent.key, rkey.key)
            parent.children.append(rkey)
            parent.children.sort()
            to_be_removed.append(rkey.key)
    return sorted([x for x in keynote_records if x.key not in to_be_removed],
                  key=lambda x: x.key)


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
    target_table = CATEGORIES_TABLE if category else KEYNOTES_TABLE
    conn.END(KEYNOTES_DB, target_table, key)

# categories ------------------------------------------------------------------

def add_category(conn, key, text):
    conn.InsertRecord(KEYNOTES_DB, CATEGORIES_TABLE,
                      {CATEGORY_KEY_FIELD: key,
                       CATEGORY_TITLE_FIELD: text})


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
    # TODO: add keynote workflow
    # add record with key and empty text
    # lock the record
    conn.InsertRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        {KEYNOTES_KEY_FIELD: key,
         KEYNOTES_TEXT_FIELD: text,
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


# ================================================================= revit.update
def update_linked_keynotes(doc=None):
    doc = doc or HOST_APP.doc
    ktable = DB.KeynoteTable.GetKeynoteTable(doc)
    ktable.Reload(None)

# =================================================================

class EditRecordWindow(forms.WPFWindow):
    def __init__(self,
                 conn, mode,
                 rkeynote=None,
                 rkey=None, text=None, pkey=None):
        forms.WPFWindow.__init__(self, 'EditRecord.xaml')
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
            self.recordKeyTitle.Text = 'Change Category Key'
            self.applyChanges.Content = 'Update Category'
            if self._rkeynote:
                if self._rkeynote.key:
                    try:
                        begin_edit(self._conn,
                                   self._rkeynote.key,
                                   category=True)
                    except Exception as ex:
                        forms.alert(str(ex))
                        return
                self.active_key = str(self._rkeynote.key)
                self.active_text = self._rkeynote.text

        elif self._mode == EDIT_MODE_ADD_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Add Keynote'
            self.recordKeyTitle.Text = 'Create Keynote Key'
            self.applyChanges.Content = 'Add Keynote'

        elif self._mode == EDIT_MODE_EDIT_KEYNOTE:
            self.show_element(self.recordParentInput)
            self.Title = 'Edit Keynote'
            self.recordKeyTitle.Text = 'Change Keynote Key'
            self.applyChanges.Content = 'Update Keynote'
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
                self.active_key = rkey or str(self._rkeynote.key)
                self.active_text = text or self._rkeynote.text
                self.active_parent_key = pkey or str(self._rkeynote.parent_key)

        # update gui with overrides if any
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
        return self.recordKey.Content

    @active_key.setter
    def active_key(self, value):
        self.recordKey.Content = value

    @property
    def active_text(self):
        return self.recordText.Text

    @active_text.setter
    def active_text(self, value):
        self.recordText.Text = value

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
            elif not self.active_text:
                forms.alert('Category must have a title.')
                return False
            add_category(self._conn, self.active_key, self.active_text)

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

    def apply_changes(self, sender, args):
        self._commited = self.commit()
        if self._commited:
            self.Close()

    def window_closed(self, sender, args):
        if not self._commited:
            if self._reserved_key:
                release_key(self._conn, self._reserved_key, category=self._cat)
            end_edit(self._conn)


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
                                parent_key='',
                                locked=False, owner='',
                                children=None)

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
        last_idx = 0
        if self.categories_tv.ItemsSource:
            last_idx = self.categories_tv.SelectedIndex

        categories = [self._allcat]
        categories.extend(get_categories(self._conn))
        self.categories_tv.ItemsSource = categories
        self.categories_tv.SelectedIndex = last_idx
        self._update_ktree_knotes()

    def _update_ktree_knotes(self):
        active_keynotes = get_keynotes_tree(self._conn)
        selected_cat = self.selected_category
        if selected_cat:
            if selected_cat.key:
                active_keynotes = \
                    [x for x in active_keynotes
                     if x.parent_key == self.selected_category.key]

        keynote_filter = self.search_term if self.search_term else None
        if keynote_filter:
            clean_filter = keynote_filter.lower()
            self.keynotes_tv.ItemsSource = \
                [x for x in active_keynotes
                 if clean_filter in x.key.lower()
                 + x.text.lower()
                 + x.owner.lower()]
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
        if self.selected_category != self._allcat:
            self.catEditButtons.IsEnabled = True
        else:
            self.catEditButtons.IsEnabled = False
        self._update_ktree_knotes()

    def refresh(self, sender, args):
        if self._conn:
            self._update_ktree()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        try:
            EditRecordWindow(self._conn, EDIT_MODE_ADD_CATEG).show()
            self._update_ktree()
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
                    EditRecordWindow(self._conn,
                                     EDIT_MODE_EDIT_CATEG,
                                     rkeynote=selected_category).show()
                    self._update_ktree()
                except Exception as ex:
                    forms.alert(str(ex))

    def remove_category(self, sender, args):
        # TODO: make sure noone owns any sub keynotes
        # TODO: ask user if they're sure
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_category = self.selected_category
        if selected_category and selected_category.text != self._allcat.text:
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
            EditRecordWindow(self._conn,
                             EDIT_MODE_ADD_KEYNOTE,
                             pkey=parent_key).show()
            self._update_ktree()
        except Exception as ex:
            forms.alert(str(ex))

    def duplicate_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self._conn,
                    EDIT_MODE_ADD_KEYNOTE,
                    text=self.selected_keynote.text,
                    pkey=self.selected_keynote.parent_key).show()
                self._update_ktree_knotes()
            except Exception as ex:
                forms.alert(str(ex))

    def remove_keynote(self, sender, args):
        # TODO: make sure noone owns any sub keynotes
        # TODO: ask user if they're sure
        # TODO: ask user which category to move the subkeynotes or delete?
        selected_keynote = self.selected_keynote
        if selected_keynote:
            try:
                remove_keynote(self._conn, selected_keynote.key)
                self._update_ktree()
            except Exception as ex:
                forms.alert(str(ex))

    def edit_keynote(self, sender, args):
        if self.selected_keynote:
            try:
                EditRecordWindow(
                    self._conn,
                    EDIT_MODE_EDIT_KEYNOTE,
                    rkey=self.selected_keynote).show()
                self._update_ktree_knotes()
            except Exception as ex:
                forms.alert(str(ex))

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
                    # TODO: add combobox to select keynote type
                    # UI.PostableCommand.UserKeynote
                    # UI.PostableCommand.ElementKeynote
                    # UI.PostableCommand.MaterialKeynote
                    uidoc_utils.PostCommandAndUpdateNewElementProperties(
                        revit.doc,
                        UI.PostableCommand.UserKeynote,
                        "Update Keynotes",
                        DB.BuiltInParameter.KEY_VALUE,
                        knote_key
                        )
                except Exception as ex:
                    forms.alert(str(ex))

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