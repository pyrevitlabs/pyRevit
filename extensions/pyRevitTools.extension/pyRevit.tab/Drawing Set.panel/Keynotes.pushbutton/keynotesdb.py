"""Module for managing keynotes using DeffrelDB."""
#pylint: disable=E0401
from collections import namedtuple, defaultdict

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit.labs import DeffrelDB as dfdb


#pylint: disable=W0703,C0302
mlogger = logger.get_logger(__name__)  #pylint: disable=C0103


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



class RKeynote:
    def __init__(self, key, text, parent_key=None,
                 locked=False, owner=None, children=None):
        self.key = key
        self.text = text
        self.parent_key = parent_key or ''
        self.locked = locked
        self.owner = owner or ''
        self._children = children or []
        self._filtered_children = []
        self._filter = None

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '<%s key:%s childs:%s>' % (self.__class__.__name__,
                                          self.key,
                                          len(self.children))
    @property
    def children(self):
        if self._filter:
            return self._filtered_children
        return self._children

    def filter(self, search_term):
        sterm = self.key +' '+ self.text +' '+ self.owner
        self._filter = search_term.lower()
        # here is where matching against the string happens
        self_pass = \
            coreutils.fuzzy_search_ratio(sterm.lower(), self._filter) > 80
        self._filtered_children = \
            [x for x in self._children if x.filter(self._filter)]
        return self_pass or self._filtered_children


def _verify_keynotesdb_def(conn):
    # verify db
    try:
        conn.ReadDB(KEYNOTES_DB)
    except Exception as dbex:
        mlogger.debug('Keynotes db read failed | %s', dbex)
        dbdef = dfdb.DatabaseDefinition()
        dbdef.Description = KEYNOTES_DB_DESC
        conn.CreateDB(KEYNOTES_DB, dbdef)

    # verify root categories table
    try:
        conn.ReadTable(KEYNOTES_DB, CATEGORIES_TABLE)
    except Exception as cattex:
        mlogger.debug('Category table read failed | %s', cattex)
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
        mlogger.debug('keynote table read failed | %s', ktex)
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
    mlogger.debug('verifying db schemas...')
    _verify_keynotesdb_def(conn)
    mlogger.debug('verifying db schemas completed.')
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
    category_keys = [x.key for x in get_categories(conn)]
    keynote_records = get_keynotes(conn)
    cat_roots = [x for x in keynote_records if x.parent_key in category_keys]

    parents = defaultdict(list)
    for rkey in keynote_records:
        if rkey.parent_key:
            parents[rkey.parent_key].append(rkey)

    for catroot_rkey in keynote_records:
        if catroot_rkey.key in parents:
            catroot_rkey.children.extend(parents[catroot_rkey.key])

    return sorted(cat_roots, key=lambda x: x.key)


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
    return RKeynote(key=key, text=text)


def update_category_title(conn, key, new_title):
    conn.UpdateRecord(KEYNOTES_DB, CATEGORIES_TABLE, key,
                      {CATEGORY_TITLE_FIELD: new_title})


def mark_category_under_edited(conn, key):
    conn.BEGIN(KEYNOTES_DB, CATEGORIES_TABLE, key)


def remove_category(conn, key):
    conn.DropRecord(KEYNOTES_DB, CATEGORIES_TABLE, key)


def rekey_category(conn, key, new_key):
    raise NotImplementedError()


# keynotes --------------------------------------------------------------------


def add_keynote(conn, key, text, parent_key):
    conn.InsertRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key,
        {KEYNOTES_TEXT_FIELD: text,
         KEYNOTES_PARENTKEY_FIELD: parent_key}
        )
    return RKeynote(key=key, text=text, parent_key=parent_key)


def remove_keynote(conn, key):
    conn.DropRecord(
        KEYNOTES_DB,
        KEYNOTES_TABLE,
        key
        )


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
    raise NotImplementedError()


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
