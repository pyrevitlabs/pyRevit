"""Module for managing keynotes using DeffrelDB."""
#pylint: disable=E0401,W0613
import re
import codecs
from collections import namedtuple, defaultdict

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit import framework
from pyrevit import revit

from pyrevit.labs import DeffrelDB as dfdb

from natsort import natsorted

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


CSI_REGEX = r' \d{2}(\s|[-_.])\d{2}(\s|[-_.])\d{2}'


class RKeynoteFilter(object):
    """Keynote smart filter."""

    def __init__(self, name, code):
        self.name = name
        self.code = code

    def format_term(self, exst_term):
        """Format existing search term for this filter"""
        # grab clearn existing
        exst_term = RKeynoteFilters.remove_filters(exst_term)
        # add space so user can type after
        return self.code + " " + exst_term


class RKeynoteRegexFilter(RKeynoteFilter):
    """Keynote smart regular expressions filter."""

    def __init__(self,
                 name="Regular Expression (Regex)",
                 regex=None,
                 negate=False):
        self.name = (name + "{}").format(" [Exclude]" if negate else "")
        self.code = ":notregex:" if negate else ":regex:"
        self.regex = regex or ""

    def format_term(self, exst_term):
        """Format existing search term for this filter"""
        # add space so user can type after
        return self.code + " " + self.regex


class RKeynoteViewFilter(RKeynoteFilter):
    """Keynote smart regular expressions filter."""

    def __init__(self):
        self.name = "Current View Only"
        self.code = ":view:"
        self.keys = []

    def __contains__(self, knote_key):
        return knote_key in self.keys

    def set_keys(self, valid_keys):
        self.keys = valid_keys


class RKeynoteFilters(object):
    """Custom filters for filtering keynotes."""

    UsedOnly = RKeynoteFilter(name="Used Only", code=":used:")
    UnusedOnly = RKeynoteFilter(name="Unused Only", code=":unused:")
    LockedOnly = RKeynoteFilter(name="Locked Only", code=":locked:")
    UnlockedOnly = RKeynoteFilter(name="Unlocked Only", code=":unlocked:")
    ViewOnly = RKeynoteViewFilter()
    UseRegex = RKeynoteRegexFilter()
    UseRegexNegate = RKeynoteRegexFilter(negate=True)
    UseCSI = RKeynoteRegexFilter(
        name="CSI MasterFormat Division No.",
        regex=CSI_REGEX
        )
    UseCSINegate = RKeynoteRegexFilter(
        name="CSI MasterFormat Division No.",
        regex=CSI_REGEX,
        negate=True
        )

    @classmethod
    def get_available_filters(cls):
        """Get available keynote filters."""
        return [cls.UsedOnly,
                cls.UnusedOnly,
                cls.LockedOnly,
                cls.UnlockedOnly,
                cls.ViewOnly,
                cls.UseRegex,
                cls.UseRegexNegate,
                cls.UseCSI,
                cls.UseCSINegate
                ]

    @classmethod
    def remove_filters(cls, source_string):
        """Get available keynote filters."""
        cleaned = source_string
        for code in [x.code for x in cls.get_available_filters()]:
            cleaned = cleaned.replace(code, '').strip()
        return cleaned


class RKeynote(object):
    """Object representing a keynote entry in the databaseself.

    This object also has properties for the status of the keynote e.g.
    locked by another user or being used in the current model.
    """
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

        self.used = False
        self.used_count = 0
        self.tooltip = 'Referenced on views:'

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

    def has_children(self):
        return len(self.children)

    def filter(self, search_term):
        self._filter = search_term.lower()

        self_pass = False

        # use regex for string matching?
        use_regex = RKeynoteFilters.UseRegex.code in self._filter
        use_regex_not = RKeynoteFilters.UseRegexNegate.code in self._filter

        if RKeynoteFilters.ViewOnly.code in self._filter:
            self_pass = self.key in RKeynoteFilters.ViewOnly

        elif RKeynoteFilters.UsedOnly.code in self._filter:
            self_pass = self.used

        elif RKeynoteFilters.UnusedOnly.code in self._filter:
            self_pass = not self.used

        elif RKeynoteFilters.LockedOnly.code in self._filter:
            self_pass = self.locked

        elif RKeynoteFilters.UnlockedOnly.code in self._filter:
            self_pass = not self.locked

        cleaned_sfilter = RKeynoteFilters.remove_filters(self._filter)
        has_smart_filter = cleaned_sfilter != self._filter

        if cleaned_sfilter:
            sterm = self.key + ' ' + self.text + ' ' + self.owner
            sterm = sterm.lower()

            # here is where matching against the string happens
            if use_regex or use_regex_not:
                # check if pattern is valid
                try:
                    self_pass = re.search(
                        cleaned_sfilter,
                        sterm,
                        re.IGNORECASE
                        )
                except Exception:
                    self_pass = False
                if use_regex_not:
                    self_pass = not self_pass
            else:
                self_pass_keyword = \
                    coreutils.fuzzy_search_ratio(sterm, cleaned_sfilter) > 80

                if has_smart_filter:
                    self_pass = self_pass_keyword and self_pass
                else:
                    self_pass = self_pass_keyword

        # filter children now
        self._filtered_children = \
            [x for x in self._children if x.filter(self._filter)]

        return self_pass or self._filtered_children

    def update_used(self, used_keysdict, doc=None):
        doc = doc or HOST_APP.doc
        # update count, and tooltip
        if self.key in used_keysdict:
            self.used = True
            self.used_count = len(used_keysdict[self.key])
            for keyid in used_keysdict[self.key]:
                owner_view = doc.GetElement(doc.GetElement(keyid).OwnerViewId)
                view_name = revit.query.get_name(owner_view)
                self.tooltip += '\n' + view_name

        for crkey in self._children:
            crkey.update_used(used_keysdict)

    def collect_keys(self):
        keys = {self.key, self.parent_key}
        for crkey in self.children:
            keys.update(crkey.collect_keys())
        return keys


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
        keynote_parent_key = dfdb.TextField(KEYNOTES_PARENTKEY_FIELD)
        keynotes_table_def = dfdb.TableDefinition()
        keynotes_table_def.SupportsTags = False
        keynotes_table_def.SupportsHistory = False
        keynotes_table_def.EncapsulateValues = False
        keynotes_table_def.SupportsHeaders = False
        keynotes_table_def.Fields = \
            [keynote_key, keynote_text, keynote_parent_key]
        # wiring the keynotes primary key
        keynotes_table_def.Wires = [
            dfdb.Wire(KEYNOTES_PARENTKEY_FIELD, CATEGORY_KEY_FIELD),
            dfdb.Wire(KEYNOTES_PARENTKEY_FIELD, KEYNOTES_KEY_FIELD)
        ]
        keynotes_table_def.Description = KEYNOTES_TABLE_DESC
        conn.CreateTable(KEYNOTES_DB, KEYNOTES_TABLE, keynotes_table_def)


def connect(keynotes_file, username=None):
    # need to use UTF-16 (UCS-2 LE / utf_16_le) for Revit compatibility
    conn = dfdb.DataBase.Connect(
        keynotes_file,
        username or HOST_APP.username,
        sourceEncoding=framework.Encoding.GetEncoding('utf-16')
        )
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
    return natsorted(
        [RKeynote(
            key=x[CATEGORY_KEY_FIELD],
            text=x[CATEGORY_TITLE_FIELD] or '',
            parent_key='',
            locked=x[CATEGORY_KEY_FIELD] in locked_records.keys(),
            owner=locked_records.get(x[CATEGORY_KEY_FIELD], ''),
            children=[]
            )
         for x in cats_records], key=lambda x: x.key)


def get_keynotes(conn):
    db_locks = get_locks(conn)
    locked_records = {x.LockTargetRecordKey: x.LockRequester
                      for x in db_locks if x.IsRecordLock}
    keynote_records = conn.ReadAllRecords(KEYNOTES_DB, KEYNOTES_TABLE)
    return natsorted(
        [RKeynote(
            key=x[KEYNOTES_KEY_FIELD],
            text=x[KEYNOTES_TEXT_FIELD] or '',
            parent_key=x[KEYNOTES_PARENTKEY_FIELD],
            locked=x[KEYNOTES_KEY_FIELD] in locked_records.keys(),
            owner=locked_records.get(x[KEYNOTES_KEY_FIELD], ''),
            children=[])
         for x in keynote_records], key=lambda x: x.key)


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
            catroot_rkey.children.extend(
                natsorted(
                    parents[catroot_rkey.key],
                    key=lambda x: x.key
                )
            )

    return natsorted(cat_roots, key=lambda x: x.key)


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


# import export ---------------------------------------------------------------


def _import_keynotes_from_lines(conn, lines, skip_dup=False):
    for line in lines:
        clean_line = line.strip()
        if not clean_line.startswith('#'):
            fields = clean_line.split('\t')
            if len(fields) == 1:
                # add category with empty title
                if fields[0]:
                    try:
                        add_category(conn, fields[0], "")
                    except Exception as cataddex:
                        if skip_dup:
                            pass
                        else:
                            raise cataddex
            elif len(fields) == 2 \
                    or (len(fields) == 3 and not fields[2]):
                # add category
                if fields[0]:
                    try:
                        add_category(conn, fields[0], fields[1])
                    except Exception as cataddex:
                        if skip_dup:
                            pass
                        else:
                            raise cataddex
            elif len(fields) == 3:
                # add keynote
                if fields[0]:
                    try:
                        add_keynote(conn, fields[0], fields[1], fields[2])
                    except Exception as cataddex:
                        if skip_dup:
                            pass
                        else:
                            raise cataddex


def import_legacy_keynotes(conn, src_legacy_keynotes_file, skip_dup=False):
    knote_lines = None
    try:
        mlogger.debug('Attempt opening file with utf-16 encoding...')
        legacy_kfile = codecs.open(src_legacy_keynotes_file, 'r', 'utf_16')
        knote_lines = legacy_kfile.readlines()
    except Exception:
        mlogger.debug('Failed opening with utf-16 encoding : %s',
                      src_legacy_keynotes_file)
        try:
            mlogger.debug('Attempt opening file with utf-8 encoding...')
            legacy_kfile = codecs.open(src_legacy_keynotes_file, 'r', 'utf_8')
            knote_lines = legacy_kfile.readlines()
        except Exception:
            mlogger.debug('Failed opening with utf-8 encoding : %s',
                          src_legacy_keynotes_file)
            raise Exception('Unknown file encoding. Supported encodings are '
                            'UTF-8 and UTF-16 (UCS-2 LE)')

    if legacy_kfile:
        conn.BEGIN(KEYNOTES_DB)
        try:
            mlogger.debug('Importing categories and keynotes...')
            _import_keynotes_from_lines(conn, knote_lines, skip_dup=skip_dup)
        finally:
            conn.END()


def export_legacy_keynotes(conn, dest_legacy_keynotes_file, include_keys=None):
    include_keys = include_keys or []
    categories = get_categories(conn)
    keynotes = get_keynotes(conn)

    if include_keys:
        with codecs.open(dest_legacy_keynotes_file, 'w', 'utf_16') as lkfile:
            for cat in categories:
                if cat.key in include_keys:
                    lkfile.write('{}\t{}\n'.format(cat.key, cat.text))
            for knote in keynotes:
                if knote.key in include_keys:
                    lkfile.write('{}\t{}\t{}\n'
                                 .format(knote.key,
                                         knote.text,
                                         knote.parent_key))

    else:
        with codecs.open(dest_legacy_keynotes_file, 'w', 'utf_16') as lkfile:
            for cat in categories:
                lkfile.write('{}\t{}\n'.format(cat.key, cat.text))
            for knote in keynotes:
                lkfile.write('{}\t{}\t{}\n'
                             .format(knote.key, knote.text, knote.parent_key))
