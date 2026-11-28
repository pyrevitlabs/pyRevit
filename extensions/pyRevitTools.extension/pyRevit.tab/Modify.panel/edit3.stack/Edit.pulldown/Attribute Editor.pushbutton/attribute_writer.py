# -*- coding: utf-8 -*-
"""Writes grid edits and schedule layout changes back to the Revit model."""

from pyrevit import DB, framework, revit, script
from pyrevit.compat import get_elementid_from_value_func, safe_strtype

from attribute_columns import SCOPE_TYPE, ColumnSpec, id_value
from attribute_sources import id_value_of_field
from attribute_strings import t
from attribute_values import EditError, make_codec

logger = script.get_logger()

get_elementid_from_value = get_elementid_from_value_func()

MAX_COMMIT_ATTEMPTS = 4


class FailureCollector(DB.IFailuresPreprocessor):
    """Collects the errors Revit raises at commit and rolls the transaction back.

    Without it Revit opens its modal failure dialog from inside the external
    event, where the user can pick a resolution such as Delete Element(s).
    Warnings are left to Revit.

    Attributes:
        failures (list): ``(element ids, description)`` per error message.
    """

    __namespace__ = "pyrevit.attribute_editor.writer"

    def __init__(self):
        self.failures = []

    def PreprocessFailures(self, failuresAccessor):
        """Required IFailuresPreprocessor interface method."""
        severities = (DB.FailureSeverity.Error, DB.FailureSeverity.DocumentCorruption)
        errors = [
            message
            for message in failuresAccessor.GetFailureMessages()
            if message.GetSeverity() in severities
        ]
        if not errors:
            return DB.FailureProcessingResult.Continue
        for message in errors:
            ids = set(
                id_value(element_id) for element_id in message.GetFailingElementIds()
            )
            self.failures.append((ids, message.GetDescriptionText()))
        return DB.FailureProcessingResult.ProceedWithRollBack

    def message_for(self, element_ids):
        """Return the description of the first error that names one of ``element_ids``."""
        for failing_ids, description in self.failures:
            if failing_ids & set(element_ids):
                return description
        return None

    def first_message(self):
        """Return the description of the first error, or None."""
        return self.failures[0][1] if self.failures else None


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


def _refused(description):
    if description:
        return t("err_refused").format(description)
    return t("err_not_committed")


def _worksharing_problem(doc, element_id):
    status = DB.WorksharingUtils.GetCheckoutStatus(doc, element_id)
    if status == DB.CheckoutStatus.OwnedByOtherUser:
        owner = DB.WorksharingUtils.GetWorksharingTooltipInfo(doc, element_id).Owner
        return t("err_owned_by").format(owner)
    updates = DB.WorksharingUtils.GetModelUpdatesStatus(doc, element_id)
    if updates in (
        DB.ModelUpdatesStatus.UpdatedInCentral,
        DB.ModelUpdatesStatus.DeletedInCentral,
    ):
        return t("err_out_of_date")
    return None


def _edited_element_id(doc, edit):
    element = doc.GetElement(get_elementid_from_value(int(edit["row"])))
    if element is None:
        return None
    if edit["key"].endswith("|" + SCOPE_TYPE) and not isinstance(
        element, DB.ElementType
    ):
        return element.GetTypeId()
    return element.Id


def _worksharing_blocks(doc, edits):
    """Return ``{element id: message}`` for edited elements the user cannot change.

    A workshared model refuses an edit on an element another user owns, or one
    changed in the central model since the last reload. Asking up front lets
    those cells carry their own reason instead of failing the whole commit.
    """
    if not doc.IsWorkshared:
        return {}
    blocked = {}
    checked = set()
    for edit in edits:
        element_id = _edited_element_id(doc, edit)
        if element_id is None or id_value(element_id) in checked:
            continue
        checked.add(id_value(element_id))
        problem = _worksharing_problem(doc, element_id)
        if problem:
            blocked[id_value(element_id)] = problem
    return blocked


def _apply_edit(doc, edit, codec, columns, type_edits, force, blocked):
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
        codec.describe(column, parameter)
    if parameter.IsReadOnly:
        return _failure(edit, t("err_read_only"))
    target_id = id_value(column.target(element).Id)
    if target_id in blocked:
        return _failure(edit, blocked[target_id])
    text = edit["text"]
    type_key = None
    if column.scope == SCOPE_TYPE:
        type_key = (key, target_id)
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
        "typeId": target_id if type_key else None,
        "touched": [id_value(element.Id), target_id],
    }
    if type_key:
        type_edits[type_key] = {"text": text, "result": result}
    return result


def _push_once(doc, batch, codec, columns, force, blocked):
    """Write ``batch`` in one transaction; return ``(results, collector or None)``.

    The collector is returned only when Revit did not keep the changes.
    """
    collector = FailureCollector()
    type_edits = {}
    results = []
    with revit.Transaction(
        t("transaction_push"),
        doc,
        clear_after_rollback=True,
        failures_preprocessor=collector,
    ) as action:
        for edit in batch:
            results.append(
                _apply_edit(doc, edit, codec, columns, type_edits, force, blocked)
            )
    return results, (None if action.committed else collector)


def _push(doc, edits, codec, columns, force, blocked):
    """Write ``edits`` and return one result per edit, in order.

    When Revit refuses the commit, the edits whose element it names get its
    reason and the rest are written again without them, so one bad cell does
    not take the others down. When the refusal names none of the edited
    elements (a dependent element failed), every written cell shows the reason
    and nothing is kept.
    """
    outcomes = {}
    active = list(range(len(edits)))
    for _ in range(MAX_COMMIT_ATTEMPTS):
        batch = [edits[index] for index in active]
        results, collector = _push_once(doc, batch, codec, columns, force, blocked)
        if collector is None:
            outcomes.update(zip(active, results))
            break
        blamed = {}
        for index, result in zip(active, results):
            if not result["ok"]:
                outcomes[index] = result
                continue
            description = collector.message_for(result["touched"])
            if description:
                blamed[index] = description
        if not blamed:
            for index, result in zip(active, results):
                if result["ok"]:
                    result = _failure(edits[index], _refused(collector.first_message()))
                outcomes[index] = result
            break
        for index, description in blamed.items():
            outcomes[index] = _failure(edits[index], _refused(description))
        active = [
            index
            for index, result in zip(active, results)
            if result["ok"] and index not in blamed
        ]
        if not active:
            break
    else:
        for index in active:
            outcomes[index] = _failure(edits[index], t("err_not_committed"))
    ordered = [outcomes[index] for index in range(len(edits))]
    for result in ordered:
        result.pop("touched", None)
    return ordered


def apply_edits(doc, edits, unit_mode, force=False, dry=False, column_formats=None):
    """Write ``edits`` in one transaction and report the outcome per cell.

    Args:
        doc (DB.Document): document that owns the elements.
        edits (list[dict]): ``{row, key, text, base}``: element id, column key,
            new text and the text last read from Revit for conflict detection.
        unit_mode (str): how number texts are parsed.
        force (bool): write even where Revit's value changed since ``base``.
        dry (bool): validate by writing and committing inside a transaction
            group that is rolled back, so Revit's commit-time checks run but
            nothing in the model changes.
        column_formats (dict | None): ``{column key: DB.FormatOptions}`` of the
            schedule fields that override the project's number format. The
            grid read its texts with them, so comparing and parsing must too.

    Returns:
        (list[dict]): one result per edit: ``{row, key, ok, message}`` for a
        failure (plus ``conflict`` and ``current`` for a conflict) or
        ``{row, key, ok, value, typeId}`` where ``value`` is Revit's text after
        the commit and ``typeId`` is set when a type was changed.

    Important:
        A failing cell does not stop the others, and the cells that succeeded
        are committed as one undo step. Revit's own commit-time errors never
        open a dialog: they are attributed to the cells that caused them.
        Elements another user owns in a workshared model fail up front.
    """
    codec = make_codec(doc, unit_mode)
    columns = dict(
        (key, ColumnSpec(key, field_format=field_format))
        for key, field_format in (column_formats or {}).items()
    )
    blocked = _worksharing_blocks(doc, edits)
    if dry:
        with revit.DryTransactionGroup(t("transaction_push"), doc):
            return _push(doc, edits, codec, columns, force, blocked)
    results = _push(doc, edits, codec, columns, force, blocked)
    for edit, result in zip(edits, results):
        if result["ok"]:
            _refresh_value(doc, edit, result, codec, columns)
    return results


def _refresh_value(doc, edit, result, codec, columns):
    element = doc.GetElement(get_elementid_from_value(int(edit["row"])))
    column = columns[edit["key"]]
    parameter = column.find(element) if element is not None else None
    if parameter is not None:
        result["value"] = codec.read(column, parameter)


def apply_layout(doc, source, ordered_keys):
    """Make the schedule show ``ordered_keys`` as its visible columns, in that order.

    Adds missing fields (showing a hidden field again instead of adding it
    twice), removes the visible supported fields that are no longer wanted and
    reorders. Calculated fields and unsupported fields stay where they are, and
    so do filters and sorting: a field one of them refers to is hidden rather
    than removed.

    Args:
        doc (DB.Document): the document.
        source (ScheduleSource): the schedule to change.
        ordered_keys (list[str]): wanted column keys in display order.

    Returns:
        (dict): ``{added, removed, failed}`` where ``failed`` lists
        ``{key, message}`` for fields Revit refused to add or remove. When
        Revit refuses the whole change, nothing is kept and ``failed`` holds
        one entry with an empty key.
    """
    definition = source.schedule.Definition
    existing = source.field_ids_by_key()
    hidden = source.field_ids_by_key(hidden=True)
    schedulable = source.schedulable_fields()
    summary = {"added": 0, "removed": 0, "failed": []}
    in_use = source.fields_in_use()
    collector = FailureCollector()
    with revit.Transaction(
        t("transaction_layout"),
        doc,
        clear_after_rollback=True,
        failures_preprocessor=collector,
    ) as action:
        for key, field_id in existing.items():
            if key in ordered_keys:
                continue
            try:
                if id_value_of_field(field_id) in in_use:
                    definition.GetField(field_id).IsHidden = True
                else:
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
            if key in hidden:
                definition.GetField(hidden[key]).IsHidden = False
                field_ids[key] = hidden[key]
                summary["added"] += 1
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
    if not action.committed:
        return {
            "added": 0,
            "removed": 0,
            "failed": [{"key": "", "message": _refused(collector.first_message())}],
        }
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
