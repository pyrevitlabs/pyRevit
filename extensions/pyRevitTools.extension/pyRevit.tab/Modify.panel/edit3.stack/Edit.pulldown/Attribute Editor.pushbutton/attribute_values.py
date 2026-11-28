# -*- coding: utf-8 -*-
"""Converts between Revit parameter values and the text shown in the grid.

Three unit modes decide how numbers with units appear and are parsed:
``display`` is Revit's own text with the unit symbol, written back with
``Parameter.SetValueString`` (so it accepts what the Revit UI accepts);
``number`` is the bare number in the project display unit; ``internal`` is the
raw Revit value. The two bare-number modes use the project's decimal symbol.
"""

import math
import re

from pyrevit import DB, script
from pyrevit.compat import safe_strtype
from pyrevit.revit import query

from attribute_columns import read_traits
from attribute_strings import t, token_set, translations

logger = script.get_logger()

UNIT_DISPLAY = "display"
UNIT_NUMBER = "number"
UNIT_INTERNAL = "internal"
UNIT_MODES = (UNIT_DISPLAY, UNIT_NUMBER, UNIT_INTERNAL)

INTEGER_TEXT = re.compile(r"^[+-]?[0-9]+$")


class EditError(Exception):
    """A pasted or typed value that cannot be written; the message is for the user."""


def _expand_exponent(text):
    mantissa, exponent = text.lower().split("e")
    sign = "-" if mantissa.startswith("-") else ""
    whole, _, fraction = mantissa.lstrip("-").partition(".")
    digits = whole + fraction
    point = len(whole) + int(exponent)
    if point <= 0:
        return sign + "0." + "0" * (-point) + digits
    if point >= len(digits):
        return sign + digits + "0" * (point - len(digits))
    return sign + digits[:point] + "." + digits[point:]


def _shortest_text(value):
    """Return the shortest ``%g`` text that reads back as exactly ``value``.

    ``repr`` is not used because IronPython 3 does not shorten it the way
    CPython and IronPython 2 do.
    """
    for digits in (15, 16, 17):
        text = "%.*g" % (digits, value)
        if float(text) == value:
            return text
    return repr(value)


def format_number(value, decimal="."):
    """Return ``value`` as plain text that ``parse_number`` reads back exactly.

    Never uses exponent notation and keeps every significant digit, so a value
    that is converted and written back does not drift.
    """
    text = _shortest_text(float(value))
    if "e" in text or "E" in text:
        text = _expand_exponent(text)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if decimal == "." else text.replace(".", decimal)


def _number_pattern(decimal):
    grouping = "." if decimal == "," else ","
    return re.compile(
        r"^[+-]?(?:(?:[0-9]+|[0-9]{1,3}(?:[%s ][0-9]{3})+)(?:%s[0-9]*)?|%s[0-9]+)"
        r"(?:[eE][+-]?[0-9]+)?$"
        % (re.escape(grouping), re.escape(decimal), re.escape(decimal))
    )


_NUMBER_PATTERNS = {".": _number_pattern("."), ",": _number_pattern(",")}


def parse_number(text, decimal="."):
    """Read a typed or pasted number the way the project writes numbers.

    Args:
        text (str): the cell text.
        decimal (str): the project's decimal symbol, ``"."`` or ``","``. The
            other one is accepted only as digit grouping, in groups of three.

    Returns:
        (float): the finite number.

    Raises:
        EditError: when the text is not a number in that notation. Ambiguous
            text such as ``1,5`` in a dot-decimal project is refused rather
            than guessed, and so are ``nan``, ``inf`` and values too large for
            a double.
    """
    cleaned = re.sub(r"\s+", " ", text, flags=re.UNICODE).strip()
    if not _NUMBER_PATTERNS.get(decimal, _NUMBER_PATTERNS["."]).match(cleaned):
        raise EditError(t("err_number"))
    grouping = "." if decimal == "," else ","
    normalized = cleaned.replace(" ", "").replace(grouping, "").replace(decimal, ".")
    value = float(normalized)
    if math.isinf(value) or math.isnan(value):
        raise EditError(t("err_number"))
    return value


def yes_tokens(yes_label):
    """Return the lower-case texts read as Yes, in every shipped language."""
    return token_set("tokens_yes") | translations("ui_yes") | set((yes_label.lower(),))


def no_tokens(no_label):
    """Return the lower-case texts read as No, in every shipped language."""
    return token_set("tokens_no") | translations("ui_no") | set((no_label.lower(),))


def make_codec(doc, unit_mode):
    """Return the ``ValueCodec`` of ``doc`` that speaks the user's language."""
    return ValueCodec(doc, unit_mode, t("ui_yes"), t("ui_no"))


class ValueCodec(object):
    """Reads and writes parameter values as grid text for one unit mode.

    Every cell is converted with the traits of its own parameter, never with
    the column's: a name-keyed column can mix specs. A cell the column cannot
    represent in the current mode (see ``ColumnSpec.accepts``) reads as
    Revit's own text and is not editable.
    """

    def __init__(self, doc, unit_mode, yes_label, no_label):
        self.doc = doc
        self.unit_mode = unit_mode if unit_mode in UNIT_MODES else UNIT_DISPLAY
        self.yes_label = yes_label
        self.no_label = no_label
        self._worksets = None
        self._units = None
        self._decimal = None
        self._trait_cache = {}
        self._field_units = {}
        self._named_elements = {}
        self._reference_samples = {}
        self._labels = {}

    @property
    def units(self):
        """The project's ``DB.Units``."""
        if self._units is None:
            self._units = self.doc.GetUnits()
        return self._units

    @property
    def decimal(self):
        """The project's decimal symbol as ``"."`` or ``","``."""
        if self._decimal is None:
            comma = self.units.DecimalSymbol == DB.DecimalSymbol.Comma
            self._decimal = "," if comma else "."
        return self._decimal

    def traits_of(self, parameter):
        """Return the ``ParameterTraits`` of a live parameter."""
        return read_traits(parameter, self.doc, self._trait_cache)

    def describe(self, column, parameter):
        """Fill ``column``'s metadata from ``parameter``."""
        column.describe(parameter, self.doc, self._trait_cache)

    def is_editable(self, column, parameter):
        """Whether the grid may offer this cell for editing."""
        if parameter.IsReadOnly:
            return False
        return column.accepts(self.traits_of(parameter), self.unit_mode)

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
        if not parameter.HasValue:
            return ""
        traits = self.traits_of(parameter)
        if not column.accepts(traits, self.unit_mode):
            return parameter.AsValueString() or ""
        storage = traits.storage
        if traits.is_workset:
            return parameter.AsValueString() or ""
        if storage == DB.StorageType.String:
            return parameter.AsString() or ""
        if storage == DB.StorageType.Double:
            return self._read_double(column, parameter, traits)
        if storage == DB.StorageType.Integer:
            if traits.is_yesno:
                return self.yes_label if parameter.AsInteger() else self.no_label
            return parameter.AsValueString() or safe_strtype(parameter.AsInteger())
        if storage == DB.StorageType.ElementId:
            if parameter.AsElementId() == DB.ElementId.InvalidElementId:
                return ""
            return parameter.AsValueString() or ""
        return ""

    def _shows_revit_text(self, traits):
        return self.unit_mode == UNIT_DISPLAY or (
            self.unit_mode == UNIT_NUMBER and traits.unit_id is None
        )

    def _read_double(self, column, parameter, traits):
        if self._shows_revit_text(traits):
            custom = self._field_units_for(column, traits)
            if custom is not None:
                return DB.UnitFormatUtils.Format(
                    custom, DB.ForgeTypeId(traits.spec_id), parameter.AsDouble(), False
                )
            return parameter.AsValueString() or format_number(
                parameter.AsDouble(), self.decimal
            )
        value = parameter.AsDouble()
        if self.unit_mode == UNIT_NUMBER:
            value = DB.UnitUtils.ConvertFromInternalUnits(value, traits.unit_id)
        return format_number(value, self.decimal)

    def _field_units_for(self, column, traits):
        """Return ``DB.Units`` applying the schedule field's own format, or None."""
        field_format = column.field_format
        if (
            field_format is None
            or column.traits is None
            or traits.spec_id != column.traits.spec_id
        ):
            return None
        if column.key not in self._field_units:
            project = self.units
            custom = DB.Units(DB.UnitSystem.Metric)
            custom.DecimalSymbol = project.DecimalSymbol
            custom.DigitGroupingSymbol = project.DigitGroupingSymbol
            custom.DigitGroupingAmount = project.DigitGroupingAmount
            custom.SetFormatOptions(DB.ForgeTypeId(traits.spec_id), field_format)
            self._field_units[column.key] = custom
        return self._field_units[column.key]

    def write(self, column, parameter, text):
        traits = self.traits_of(parameter)
        if not column.accepts(traits, self.unit_mode):
            if traits.cell_kind() != column.cell_kind():
                raise EditError(t("err_kind_differs"))
            raise EditError(t("err_spec_differs"))
        storage = traits.storage
        if storage == DB.StorageType.String:
            self._require(parameter.Set(text))
        elif storage == DB.StorageType.Double:
            self._write_double(column, parameter, traits, text)
        elif storage == DB.StorageType.Integer:
            self._write_integer(column, parameter, traits, text)
        elif storage == DB.StorageType.ElementId:
            self._write_reference(column, parameter, text)
        else:
            raise EditError(t("err_unsupported"))

    @staticmethod
    def _require(accepted):
        if accepted is False:
            raise EditError(t("err_rejected"))

    def _write_double(self, column, parameter, traits, text):
        text = text.strip()
        if not text:
            raise EditError(t("err_empty"))
        if self._shows_revit_text(traits):
            custom = self._field_units_for(column, traits)
            if custom is not None:
                value = self._parse_like_revit(custom, traits, text)
                self._require(parameter.Set(value))
            else:
                self._require(parameter.SetValueString(text))
            return
        value = parse_number(text, self.decimal)
        if self.unit_mode == UNIT_NUMBER:
            value = DB.UnitUtils.ConvertToInternalUnits(value, traits.unit_id)
        self._require(parameter.Set(value))

    @staticmethod
    def _parse_like_revit(units, traits, text):
        """Return ``text`` parsed with ``units`` like the Revit UI does.

        Raises:
            EditError: when Revit cannot parse the text.

        Note:
            The ``ValueParsingOptions`` overload hands its out value back as a
            tuple on every engine, so no ``clr.Reference`` is needed. Revit's
            own message is not available that way, which is why a refusal is
            reported with the bundle's text.
        """
        try:
            parsed, value = DB.UnitFormatUtils.TryParse(
                units, DB.ForgeTypeId(traits.spec_id), text, DB.ValueParsingOptions()
            )
        except Exception as ex:
            logger.debug("Revit could not parse '%s': %s", text, ex)
            raise EditError(t("err_rejected"))
        if not parsed:
            raise EditError(t("err_rejected"))
        return value

    def _write_integer(self, column, parameter, traits, text):
        token = text.strip()
        if not token:
            raise EditError(t("err_empty"))
        lowered = token.lower()
        if traits.is_yesno:
            if lowered in yes_tokens(self.yes_label):
                self._require(parameter.Set(1))
            elif lowered in no_tokens(self.no_label):
                self._require(parameter.Set(0))
            else:
                raise EditError(t("err_yes_no"))
            return
        if traits.is_workset:
            workset_id = self.worksets().get(token)
            if workset_id is None:
                raise EditError(t("err_workset"))
            self._require(parameter.Set(workset_id))
            return
        if INTEGER_TEXT.match(token):
            self._require(parameter.Set(int(token)))
            return
        number = self._integer_labels(column, parameter).get(lowered)
        if number is not None:
            self._require(parameter.Set(number))
            return
        self._require(parameter.SetValueString(token))

    def _write_reference(self, column, parameter, text):
        name = text.strip()
        if not name:
            self._require(parameter.Set(DB.ElementId.InvalidElementId))
            return
        shown = self._reference_labels(column, parameter).get(name.lower(), set())
        if len(shown) == 1:
            self._require(parameter.Set(next(iter(shown))))
            return
        if len(shown) > 1:
            raise EditError(t("err_ambiguous"))
        current = self.doc.GetElement(parameter.AsElementId())
        if current is None:
            current = self._reference_sample(column, parameter)
        if current is None:
            raise EditError(t("err_reference"))
        matches = self._named_elements_of(current).get(name.lower(), [])
        if not matches:
            raise EditError(t("err_reference"))
        if len(matches) > 1:
            raise EditError(t("err_ambiguous"))
        self._require(parameter.Set(matches[0]))

    def _category_elements(self, owner):
        collector = DB.FilteredElementCollector(self.doc).OfCategoryId(
            owner.Category.Id
        )
        if isinstance(owner, DB.ElementType):
            return collector.WhereElementIsElementType()
        return collector.WhereElementIsNotElementType()

    def _scan_key(self, column, owner):
        category = owner.Category if owner is not None else None
        return (
            column.key,
            category.Id.ToString() if category is not None else None,
            isinstance(owner, DB.ElementType),
        )

    def _integer_labels(self, column, parameter):
        """Return ``{label: value}`` of the unambiguous integer labels the category shows."""
        owner = parameter.Element
        if owner is None or owner.Category is None:
            return {}
        cache_key = ("integer",) + self._scan_key(column, owner)
        if cache_key not in self._labels:
            found = {}
            for element in self._category_elements(owner):
                candidate = column.find(element)
                if (
                    candidate is None
                    or candidate.StorageType != DB.StorageType.Integer
                    or not candidate.HasValue
                ):
                    continue
                label = candidate.AsValueString()
                if label:
                    found.setdefault(label.lower(), set()).add(candidate.AsInteger())
            self._labels[cache_key] = dict(
                (label, next(iter(values)))
                for label, values in found.items()
                if len(values) == 1
            )
        return self._labels[cache_key]

    def _reference_labels(self, column, parameter):
        """Return ``{label: {element id}}`` for the references the category shows."""
        owner = parameter.Element
        if owner is None or owner.Category is None:
            return {}
        cache_key = ("reference",) + self._scan_key(column, owner)
        if cache_key not in self._labels:
            found = {}
            for element in self._category_elements(owner):
                candidate = column.find(element)
                if (
                    candidate is None
                    or candidate.StorageType != DB.StorageType.ElementId
                ):
                    continue
                target = candidate.AsElementId()
                label = candidate.AsValueString()
                if label and target != DB.ElementId.InvalidElementId:
                    found.setdefault(label.lower(), set()).add(target)
            self._labels[cache_key] = found
        return self._labels[cache_key]

    def _reference_sample(self, column, parameter):
        owner = parameter.Element
        cache_key = self._scan_key(column, owner)
        if cache_key not in self._reference_samples:
            self._reference_samples[cache_key] = self._find_reference_sample(
                column, owner
            )
        return self._reference_samples[cache_key]

    def _find_reference_sample(self, column, owner):
        if owner is None or owner.Category is None:
            return None
        for element in self._category_elements(owner):
            candidate = column.find(element)
            if candidate is None or candidate.StorageType != DB.StorageType.ElementId:
                continue
            referenced = self.doc.GetElement(candidate.AsElementId())
            if referenced is not None:
                return referenced
        return None

    def _named_elements_of(self, sample):
        element_class = sample.GetType()
        sample_category = sample.Category
        cache_key = (
            element_class.FullName,
            sample_category.Id.ToString() if sample_category is not None else None,
        )
        if cache_key not in self._named_elements:
            by_name = {}
            collector = DB.FilteredElementCollector(self.doc).OfClass(element_class)
            for element in collector:
                if not self._same_category(element, sample_category):
                    continue
                for label in self._labels_of(element):
                    by_name.setdefault(label.lower(), []).append(element.Id)
            self._named_elements[cache_key] = by_name
        return self._named_elements[cache_key]

    @staticmethod
    def _same_category(element, category):
        if category is None or element.Category is None:
            return True
        return element.Category.Id == category.Id

    @staticmethod
    def _labels_of(element):
        labels = [query.get_name(element)]
        if isinstance(element, DB.FamilySymbol):
            labels.append(element.FamilyName + " : " + query.get_name(element))
        return labels
