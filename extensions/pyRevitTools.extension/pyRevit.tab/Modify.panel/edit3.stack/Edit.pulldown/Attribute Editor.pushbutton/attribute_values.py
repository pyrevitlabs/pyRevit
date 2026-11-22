# -*- coding: utf-8 -*-
"""Converts between Revit parameter values and the text shown in the grid.

Three unit modes decide how numbers with units appear and are parsed:
``display`` is Revit's own text with the unit symbol, written back with
``Parameter.SetValueString`` (so it accepts what the Revit UI accepts);
``number`` is the bare number in the project display unit; ``internal`` is the
raw Revit value.
"""

from pyrevit import DB, script
from pyrevit.compat import safe_strtype

from attribute_strings import t

logger = script.get_logger()

UNIT_DISPLAY = "display"
UNIT_NUMBER = "number"
UNIT_INTERNAL = "internal"
UNIT_MODES = (UNIT_DISPLAY, UNIT_NUMBER, UNIT_INTERNAL)

YES_TOKENS = frozenset(("yes", "y", "true", "1", "x"))
NO_TOKENS = frozenset(("no", "n", "false", "0"))


class EditError(Exception):
    """A pasted or typed value that cannot be written; the message is for the user."""


def format_number(value):
    return "%.10g" % value


def parse_number(text):
    cleaned = "".join(text.split())
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        raise EditError(t("err_number"))


class ValueCodec(object):
    """Reads and writes parameter values as grid text for one unit mode."""

    def __init__(self, doc, unit_mode, yes_label, no_label):
        self.doc = doc
        self.unit_mode = unit_mode if unit_mode in UNIT_MODES else UNIT_DISPLAY
        self.yes_label = yes_label
        self.no_label = no_label
        self._worksets = None
        self._named_elements = {}

    def worksets(self):
        if self._worksets is None:
            collector = DB.FilteredWorksetCollector(self.doc).OfKind(
                DB.WorksetKind.UserWorkset
            )
            self._worksets = dict(
                (workset.Name, int(workset.Id.IntegerValue)) for workset in collector
            )
        return self._worksets

    def read(self, column, parameter):
        storage = parameter.StorageType
        if storage == DB.StorageType.String:
            return parameter.AsString() or ""
        if storage == DB.StorageType.Double:
            return self._read_double(column, parameter)
        if storage == DB.StorageType.Integer:
            if column.is_yesno:
                return self.yes_label if parameter.AsInteger() else self.no_label
            return parameter.AsValueString() or safe_strtype(parameter.AsInteger())
        if storage == DB.StorageType.ElementId:
            return parameter.AsValueString() or ""
        return ""

    def _read_double(self, column, parameter):
        if self.unit_mode == UNIT_DISPLAY or (
            self.unit_mode == UNIT_NUMBER and column.unit_id is None
        ):
            return parameter.AsValueString() or format_number(parameter.AsDouble())
        value = parameter.AsDouble()
        if self.unit_mode == UNIT_NUMBER:
            value = DB.UnitUtils.ConvertFromInternalUnits(value, column.unit_id)
        return format_number(value)

    def write(self, column, parameter, text):
        storage = parameter.StorageType
        if storage == DB.StorageType.String:
            self._require(parameter.Set(text))
        elif storage == DB.StorageType.Double:
            self._write_double(column, parameter, text)
        elif storage == DB.StorageType.Integer:
            self._write_integer(column, parameter, text)
        elif storage == DB.StorageType.ElementId:
            self._write_reference(parameter, text)
        else:
            raise EditError(t("err_unsupported"))

    @staticmethod
    def _require(accepted):
        if accepted is False:
            raise EditError(t("err_rejected"))

    def _write_double(self, column, parameter, text):
        text = text.strip()
        if not text:
            raise EditError(t("err_empty"))
        if self.unit_mode == UNIT_DISPLAY or (
            self.unit_mode == UNIT_NUMBER and column.unit_id is None
        ):
            self._require(parameter.SetValueString(text))
            return
        value = parse_number(text)
        if self.unit_mode == UNIT_NUMBER:
            value = DB.UnitUtils.ConvertToInternalUnits(value, column.unit_id)
        self._require(parameter.Set(value))

    def _write_integer(self, column, parameter, text):
        token = text.strip()
        if not token:
            raise EditError(t("err_empty"))
        if column.is_yesno:
            lowered = token.lower()
            if lowered in YES_TOKENS or lowered == self.yes_label.lower():
                self._require(parameter.Set(1))
            elif lowered in NO_TOKENS or lowered == self.no_label.lower():
                self._require(parameter.Set(0))
            else:
                raise EditError(t("err_yes_no"))
            return
        if column.is_workset:
            workset_id = self.worksets().get(token)
            if workset_id is None:
                raise EditError(t("err_workset"))
            self._require(parameter.Set(workset_id))
            return
        try:
            number = int(token)
        except ValueError:
            self._require(parameter.SetValueString(token))
            return
        self._require(parameter.Set(number))

    def _write_reference(self, parameter, text):
        name = text.strip()
        if not name:
            self._require(parameter.Set(DB.ElementId.InvalidElementId))
            return
        current = self.doc.GetElement(parameter.AsElementId())
        if current is None:
            raise EditError(t("err_reference"))
        matches = self._named_elements_of(current).get(name.lower(), [])
        if not matches:
            raise EditError(t("err_reference"))
        if len(matches) > 1:
            raise EditError(t("err_ambiguous"))
        self._require(parameter.Set(matches[0]))

    def _named_elements_of(self, sample):
        element_class = sample.GetType()
        cache_key = element_class.FullName
        if cache_key not in self._named_elements:
            by_name = {}
            collector = DB.FilteredElementCollector(self.doc).OfClass(element_class)
            for element in collector:
                for label in self._labels_of(element):
                    by_name.setdefault(label.lower(), []).append(element.Id)
            self._named_elements[cache_key] = by_name
        return self._named_elements[cache_key]

    @staticmethod
    def _labels_of(element):
        labels = [element.Name]
        if isinstance(element, DB.FamilySymbol):
            labels.append(element.FamilyName + " : " + element.Name)
        return labels
