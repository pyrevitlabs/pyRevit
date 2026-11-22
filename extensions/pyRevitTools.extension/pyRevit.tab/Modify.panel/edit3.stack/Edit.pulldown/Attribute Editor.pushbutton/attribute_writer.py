# -*- coding: utf-8 -*-
"""Writes grid edits and schedule layout changes back to the Revit model."""

from pyrevit import DB, framework, revit, script
from pyrevit.compat import get_elementid_from_value_func, safe_strtype

from attribute_columns import SCOPE_TYPE, ColumnSpec, id_value
from attribute_grid import make_codec
from attribute_strings import t
from attribute_values import EditError

logger = script.get_logger()

get_elementid_from_value = get_elementid_from_value_func()


def _failure(edit, message, conflict=False, current=None):
    result = {
        "row": edit["row"],
        "key": edit["key"],
        "ok": False,
        "message": message,
    }
    if conflict:
        result["conflict"] = True
        result["current"] = current
    return result


def _apply_edit(doc, edit, codec, columns, type_edits, force):
    key = edit["key"]
    column = columns.get(key)
    if column is None:
        column = columns[key] = ColumnSpec(key)
    element = doc.GetElement(get_elementid_from_value(int(edit["row"])))
    if element is None:
        return _failure(edit, t("err_element_missing"))
    parameter = column.find(element)
    if parameter is None:
        return _failure(edit, t("err_not_found"))
    if not column.available:
        column.describe(parameter, doc.GetUnits())
    if parameter.IsReadOnly:
        return _failure(edit, t("err_read_only"))
    text = edit["text"]
    type_key = None
    if column.scope == SCOPE_TYPE:
        type_key = (key, id_value(column.target(element).Id))
        earlier = type_edits.get(type_key)
        if earlier is not None:
            if earlier["text"] != text:
                return _failure(edit, t("err_type_mixed"))
            return dict(earlier["result"], row=edit["row"])
    if not force and "base" in edit:
        current = codec.read(column, parameter)
        if current != edit["base"]:
            return _failure(edit, t("err_conflict"), conflict=True, current=current)
    try:
        codec.write(column, parameter, text)
    except EditError as ex:
        return _failure(edit, safe_strtype(ex))
    except Exception as ex:
        logger.debug("Writing %s failed: %s", key, ex)
        return _failure(edit, safe_strtype(ex))
    result = {
        "row": edit["row"],
        "key": key,
        "ok": True,
        "value": codec.read(column, parameter),
        "typeId": id_value(column.target(element).Id) if type_key else None,
    }
    if type_key:
        type_edits[type_key] = {"text": text, "result": result}
    return result


def apply_edits(doc, edits, unit_mode, force=False, dry=False):
    """Write ``edits`` in one transaction and report the outcome per cell.

    Args:
        doc (DB.Document): document that owns the elements.
        edits (list[dict]): ``{row, key, text, base}``: element id, column key,
            new text and the text last read from Revit for conflict detection.
        unit_mode (str): how number texts are parsed.
        force (bool): write even where Revit's value changed since ``base``.
        dry (bool): validate by writing inside a transaction that is rolled
            back, so nothing in the model changes.

    Returns:
        (list[dict]): one result per edit: ``{row, key, ok, message}`` for a
        failure (plus ``conflict`` and ``current`` for a conflict) or
        ``{row, key, ok, value, typeId}`` where ``value`` is Revit's text after
        the commit and ``typeId`` is set when a type was changed.

    Important:
        A failing cell does not stop the others, and the cells that succeeded
        are committed as one undo step. When Revit refuses the commit, every
        cell is reported as failed.
    """
    codec = make_codec(doc, unit_mode)
    columns = {}
    type_edits = {}
    results = []

    def write_all():
        for edit in edits:
            results.append(_apply_edit(doc, edit, codec, columns, type_edits, force))

    if dry:
        with revit.DryTransaction(t("transaction_push"), doc):
            write_all()
        return results
    if not _commit(doc, t("transaction_push"), write_all):
        return [
            _failure(edit, t("err_not_committed")) if result["ok"] else result
            for edit, result in zip(edits, results)
        ]
    for edit, result in zip(edits, results):
        if result["ok"]:
            _refresh_value(doc, edit, result, codec, columns)
    return results


def _commit(doc, name, body):
    """Run ``body`` in one transaction; return whether Revit kept its changes.

    ``revit.Transaction`` logs a failed commit and carries on, so it cannot tell
    the caller that nothing was saved.
    """
    transaction = DB.Transaction(doc, name)
    transaction.Start()
    try:
        body()
    except Exception:
        transaction.RollBack()
        raise
    try:
        return transaction.Commit() == DB.TransactionStatus.Committed
    except Exception as ex:
        logger.debug("Commit failed: %s", ex)
        if transaction.HasStarted():
            transaction.RollBack()
        return False


def _refresh_value(doc, edit, result, codec, columns):
    element = doc.GetElement(get_elementid_from_value(int(edit["row"])))
    column = columns[edit["key"]]
    parameter = column.find(element) if element is not None else None
    if parameter is not None:
        result["value"] = codec.read(column, parameter)


def apply_layout(doc, source, ordered_keys):
    """Make the schedule show ``ordered_keys`` as its visible columns, in that order.

    Adds missing fields, removes the visible supported fields that are no longer
    wanted and reorders. Hidden fields, calculated fields and unsupported fields
    stay where they are.

    Args:
        doc (DB.Document): the document.
        source (ScheduleSource): the schedule to change.
        ordered_keys (list[str]): wanted column keys in display order.

    Returns:
        (dict): ``{added, removed, failed}`` where ``failed`` lists
        ``{key, message}`` for fields Revit refused to add or remove.
    """
    definition = source.schedule.Definition
    existing = source.field_ids_by_key()
    schedulable = source.schedulable_fields()
    summary = {"added": 0, "removed": 0, "failed": []}
    with revit.Transaction(t("transaction_layout"), doc):
        for key, field_id in existing.items():
            if key in ordered_keys:
                continue
            try:
                definition.RemoveField(field_id)
                summary["removed"] += 1
            except Exception as ex:
                logger.debug("RemoveField failed for %s: %s", key, ex)
                summary["failed"].append({"key": key, "message": safe_strtype(ex)})
        field_ids = dict(
            (key, field_id) for key, field_id in existing.items() if key in ordered_keys
        )
        for key in ordered_keys:
            if key in field_ids:
                continue
            if key not in schedulable:
                summary["failed"].append(
                    {"key": key, "message": t("err_not_schedulable")}
                )
                continue
            try:
                field_ids[key] = definition.AddField(schedulable[key]).FieldId
                summary["added"] += 1
            except Exception as ex:
                logger.debug("AddField failed for %s: %s", key, ex)
                summary["failed"].append({"key": key, "message": safe_strtype(ex)})
        wanted = [field_ids[key] for key in ordered_keys if key in field_ids]
        definition.SetFieldOrder(
            framework.to_clr_list(
                DB.ScheduleFieldId,
                _order_keeping_unmanaged_fields(definition.GetFieldOrder(), wanted),
            )
        )
    after = set(source.field_ids_by_key())
    summary["added"] = len(after - set(existing))
    summary["removed"] = len(set(existing) - after)
    if set(ordered_keys) - after - set(item["key"] for item in summary["failed"]):
        summary["failed"].append({"key": "", "message": t("err_not_committed")})
    return summary


def _order_keeping_unmanaged_fields(current_order, wanted):
    """Place ``wanted`` in order; every other field stays after the managed field it followed."""
    managed = set(int(field_id.IntegerValue) for field_id in wanted)
    unmanaged_after = {}
    previous = None
    for field_id in current_order:
        if int(field_id.IntegerValue) not in managed:
            unmanaged_after.setdefault(previous, []).append(field_id)
        else:
            previous = int(field_id.IntegerValue)
    order = list(unmanaged_after.get(None, []))
    for field_id in wanted:
        order.append(field_id)
        order.extend(unmanaged_after.get(int(field_id.IntegerValue), []))
    return order
