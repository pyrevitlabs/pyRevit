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
open db
    db module: verifies db
    if db not ok, inform user
    db module: upgrade db
get ketnotes tree
get locked keynotes (collect locker)
get unused keynotes (collect info?)
build and show tree (color code locked and unused keynotes)



"""

# ================================================================ keynotesdb.py
#pylint: disable=W0703
from collections import namedtuple

from pyrevit.labs import DeffrelDB as kdb


RKeynote = namedtuple('RKeynote', ['key', 'text', 'parent_key'])

KEYNOTES_DB = 'keynotesdb'
KEYNOTES_DB_DESC = "pyRevit Keynotes Manager DB"

CATEGORIES_TABLE = 'categories'
CATEGORIES_TABLE_DESC = "Root Keynotes Table"
CATEGORY_KEY_FIELD = 'cat_key'
CATEGORY_TITLE_FIELD = 'cat_title'

KEYNOTES_TABLE = 'keynotes'
KEYNOTES_TABLE_DESC = "Keynotes Table"
KEYNOTES_KEY_FIELD = 'keynote_key'
KEYNOTES_TEXT_FIELD = 'keynote_text'


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


def get_keynotes_under_edit(conn):
    pass


def get_keynotes_tree(conn):
    keynote_records = conn.ReadAllRecords(KEYNOTES_DB, KEYNOTES_TABLE)
    return [RKeynote(key=x[KEYNOTES_KEY_FIELD],
                     text=x[KEYNOTES_TEXT_FIELD],
                     parent_key=x[CATEGORY_KEY_FIELD])
            for x in keynote_records]


def add_category(conn, key, text):
    # TODO: add category workflow
    # add record with key and empty text
    # lock the record
    conn.CreateRecord(
        KEYNOTES_DB,
        CATEGORIES_TABLE,
        {CATEGORY_KEY_FIELD: key,
         CATEGORY_TITLE_FIELD: text}
        )


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

def export_legacy_keynotes(target_legacy_keynotes_file):
    pass
# ==============================================================================


# ================================================================= revit.update
def update_linked_keynotes(doc=None):
    doc = doc or HOST_APP.doc
    ktable = DB.KeynoteTable.GetKeynoteTable(doc)
    ktable.Reload(None)
# ==============================================================================


class KeynoteManagerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._text_counter = 0
        self._lastcat = None
        self._last_kn = None

        # TODO: verify kfile
        self._kfile = revit.query.get_keynote_file(doc=revit.doc)
        self._conn = connect(self._kfile)
        # self._keynotes = revit.query.get_available_keynotes(doc=revit.doc)
        # self._ktree = revit.query.get_available_keynotes_tree(doc=revit.doc)
        self._update_ktree()

    @property
    def selected_keynote(self):
        return self.keynotes_tv.SelectedItem

    def _build_treeview_items(self):
        return []

    def _update_ktree(self, keynote_filter=None):
        # maybe some coloring on filter?
        # https://stackoverflow.com/questions/5442067/change-color-and-font-for-some-part-of-text-in-wpf-c-sharp
        if keynote_filter:
            clean_filter = keynote_filter.lower()
            self.keynotes_tv.ItemsSource = \
                [x for x in get_keynotes_tree(self._conn)
                 if clean_filter in x.key.lower()
                 or clean_filter in x.text.lower()]
        else:
            self.keynotes_tv.ItemsSource = get_keynotes_tree(self._conn)

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._update_ktree(keynote_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

    def add_category(self, sender, args):
        self._lastcat = 'S{}'.format(self._text_counter)
        add_category(self._conn, self._lastcat, 'Some value')
        self._text_counter += 1
        self._update_ktree()

    def add_keynote(self, sender, args):
        self._last_kn = 'SK{}'.format(self._text_counter)
        add_keynote(self._conn, self._last_kn, 'Some value', self._lastcat)
        self._text_counter += 1
        self._update_ktree()

    def remove_keynote(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            remove_keynote(self._conn, selected_keynote.key)
            self._update_ktree()

    def add_child_keynote(self, sender, args):
        # detect selected keynote
        self._last_kn = 'SK{}'.format(self._text_counter)
        add_keynote(self._conn, self._last_kn, 'Some value', self._lastcat)
        self._text_counter += 1
        self._update_ktree()

    def update_keynote_text(self, sender, args):
        selected_keynote = self.selected_keynote
        if selected_keynote:
            update_keynote_text(self._conn, selected_keynote.key, '-- New value --')
            self._update_ktree()

    def update_keynote_key(self, sender, args):
        # mark_keynote_under_edited(self._conn, self._last_kn)
        selected_keynote = self.selected_keynote
        if selected_keynote:
            update_keynote_key(self._conn, selected_keynote.key, selected_keynote.key + "-ED")
            self._update_ktree()

    def place_keynote(self, sender, args):
        self.Close()
        # figure out how to place a keynote

    def import_keynotes(self, sender, args):
        # verify existing keynotes when importing
        # maybe allow for merge conflict?
        kfile = forms.pick_file('txt')
        if kfile:
            import_legacy_keynotes(self._conn, kfile)
            self._update_ktree()

    def update_model(self, sender, args):
        self.Close()

    def window_closed(self, sender, args):
        with revit.Transaction("Update Keynotes"):
            update_linked_keynotes(doc=revit.doc)



KeynoteManagerWindow('KeynoteManagerWindow.xaml').show(modal=True)
