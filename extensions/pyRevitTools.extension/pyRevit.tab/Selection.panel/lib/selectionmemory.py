# -*- coding: utf-8 -*-
"""Selection memory shared by the MAppend, MRead, MWrite, MDeduct, MClear, Next, Prev and Save Memory as Selection buttons.

Each document keeps its memory in the document data file ``SelList``, a pickled set
of element id strings, and the position of Next and Prev in ``SelListPrevNextIndex``.
Older pyRevit releases read and write the same files, so the formats must not change.
Next and Prev also store the id of the element they selected last in
``SelListPrevNextLastId``, which older releases ignore.
All of these files are written with pickle protocol 2, so that every engine can read them.
"""

import bisect
import os.path as op
import pickle

from pyrevit import forms, script
from pyrevit import revit
from pyrevit.compat import get_elementid_from_value_func, get_elementid_value_func
from pyrevit.coreutils import applocales

logger = script.get_logger()

RESOURCES = op.join(op.dirname(__file__), "selectionmemory.xaml")
MEMORY_ID = "SelList"
INDEX_ID = "SelListPrevNextIndex"
LAST_VISITED_ID = "SelListPrevNextLastId"
DATA_FILE_EXTENSION = "pym"


def text(key):
    """Return the localized string of the selection memory buttons for ``key``."""
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def _memory_file():
    return script.get_document_data_file(MEMORY_ID, DATA_FILE_EXTENSION)


def _index_file():
    return script.get_document_data_file(INDEX_ID, DATA_FILE_EXTENSION)


def _last_visited_file():
    return script.get_document_data_file(LAST_VISITED_ID, DATA_FILE_EXTENSION)


def _load(path, report_failure):
    if not op.exists(path):
        return None
    try:
        with open(path, "rb") as data_file:
            return pickle.load(data_file)
    except Exception as load_err:
        report_failure("{} could not be read. | {}".format(path, load_err))
        return None


def _dump(path, data):
    with open(path, "wb") as data_file:
        pickle.dump(data, data_file, 2)


def read_memory():
    """Return the element ids in the memory of the active document as a set of strings.

    A missing or unreadable memory file reads as an empty memory. An unreadable file
    is logged. Memories written as a list by older releases are read as well.
    """
    stored = _load(_memory_file(), logger.exception)
    return set(stored) if stored else set()


def write_memory(element_id_strings):
    """Replace the memory of the active document with ``element_id_strings``."""
    _dump(_memory_file(), set(element_id_strings))


def selected_ids():
    """Return the ids of the selected host elements as a set of strings."""
    get_elementid_value = get_elementid_value_func()
    return {
        str(get_elementid_value(element_id))
        for element_id in revit.get_selection().element_ids
    }


def memory_element_ids():
    """Return the memorized ids of elements that still exist, in ascending id order."""
    get_elementid_from_value = get_elementid_from_value_func()
    element_ids = [
        get_elementid_from_value(int(element_id))
        for element_id in sorted(read_memory(), key=int)
    ]
    return [
        element_id
        for element_id in element_ids
        if revit.doc.GetElement(element_id) is not None
    ]


def require_memory_element_ids():
    """Return `memory_element_ids`, or tell the user and exit when there are none."""
    if not read_memory():
        forms.alert(text("memory_empty"), exitscript=True)
    element_ids = memory_element_ids()
    if not element_ids:
        forms.alert(text("memory_stale"), exitscript=True)
    return element_ids


def _stepped_index(element_id_values, last_value, direction, step_size):
    if last_value in element_id_values:
        return element_id_values.index(last_value) + direction * step_size
    insertion_point = bisect.bisect_left(element_id_values, last_value)
    if direction > 0:
        return insertion_point + step_size - 1
    return insertion_point - step_size


def step_through_memory(direction, step_size=1):
    """Select the element ``step_size`` places after (``direction`` 1) or before (-1) the last one.

    The last element is remembered per document by its id, so the walk continues from
    it when elements are added to or removed from the memory or deleted from the
    document. If the last element is gone, the walk continues with its neighbour in
    id order. It wraps around at both ends. The first call in a document selects the
    first element of the memory.
    """
    element_ids = require_memory_element_ids()
    get_elementid_value = get_elementid_value_func()
    element_id_values = [get_elementid_value(element_id) for element_id in element_ids]
    last_value = _load(_last_visited_file(), logger.debug)
    if last_value is not None:
        index = _stepped_index(element_id_values, last_value, direction, step_size)
    else:
        stored_index = _load(_index_file(), logger.debug)
        index = 0 if stored_index is None else stored_index + direction * step_size
    index %= len(element_ids)
    revit.get_selection().set_to([element_ids[index]])
    _dump(_index_file(), index)
    _dump(_last_visited_file(), element_id_values[index])
