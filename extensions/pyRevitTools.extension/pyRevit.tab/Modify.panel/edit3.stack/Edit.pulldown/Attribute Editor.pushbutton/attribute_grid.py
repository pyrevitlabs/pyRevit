# -*- coding: utf-8 -*-
"""Reads a source into the rows and columns the Attribute Editor page shows."""

import itertools

from pyrevit import DB, script

from attribute_columns import SCOPE_TYPE, ColumnSpec, id_value
from attribute_strings import t
from attribute_values import ValueCodec

logger = script.get_logger()

DESCRIBE_LIMIT = 300


def _read_cell(codec, column, element):
    parameter = column.find(element)
    if parameter is None:
        return "", False
    try:
        return codec.read(column, parameter), not parameter.IsReadOnly
    except Exception as ex:
        logger.debug("Cannot read %s: %s", column.key, ex)
        return "", False


def _cell(codec, column, element, type_cache):
    if column.scope != SCOPE_TYPE or isinstance(element, DB.ElementType):
        return _read_cell(codec, column, element)
    cache_key = (column.key, id_value(element.GetTypeId()))
    if cache_key not in type_cache:
        type_cache[cache_key] = _read_cell(codec, column, element)
    return type_cache[cache_key]


def _choices(codec, column):
    if column.is_yesno:
        return [codec.yes_label, codec.no_label]
    if column.is_workset:
        return sorted(codec.worksets())
    return None


def make_codec(doc, unit_mode):
    return ValueCodec(doc, unit_mode, t("ui_yes"), t("ui_no"))


def build_grid(doc, source, column_keys, unit_mode):
    """Read ``source`` into a JSON-ready grid.

    Args:
        doc (DB.Document): document the source belongs to.
        source: a ``ScheduleSource`` or ``ScratchSource``.
        column_keys (list | None): column keys in display order; None takes the
            source's own columns.
        unit_mode (str): one of the ``attribute_values.UNIT_MODES``.

    Returns:
        (dict): ``source``, ``title``, ``unitMode``, ``columns``, ``rows`` and
        ``sort``. A row is ``{id, t, c, v, x}``: element id, type id, category
        name, cell texts and the indexes of cells that cannot be edited.
    """
    defaults = source.default_columns()
    if column_keys is None:
        columns = defaults
    else:
        headings = dict((column.key, column.heading) for column in defaults)
        columns = [ColumnSpec(key, headings.get(key)) for key in column_keys]
    elements = source.elements()
    units = doc.GetUnits()
    for column in columns:
        for element in itertools.islice(elements, DESCRIBE_LIMIT):
            parameter = column.find(element)
            if parameter is not None:
                column.describe(parameter, units)
                break
    codec = make_codec(doc, unit_mode)
    type_cache = {}
    rows = []
    for element in elements:
        values = []
        locked = []
        for index, column in enumerate(columns):
            text, editable = _cell(codec, column, element, type_cache)
            values.append(text)
            if not editable:
                locked.append(index)
        category = element.Category
        rows.append(
            {
                "id": id_value(element.Id),
                "t": id_value(element.GetTypeId()),
                "c": category.Name if category is not None else "",
                "v": values,
                "x": locked,
            }
        )
    return {
        "source": source.to_json(),
        "title": source.title,
        "unitMode": codec.unit_mode,
        "columns": [column.to_json(_choices(codec, column)) for column in columns],
        "rows": rows,
        "sort": source.sort_hints([column.key for column in columns]),
    }
