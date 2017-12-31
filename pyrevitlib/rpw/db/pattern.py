""" Pattern Wrappers """

from rpw import DB
from rpw.db.element import Element
from rpw.utils.mixins import ByNameCollectMixin


class LinePatternElement(Element, ByNameCollectMixin):
    """
    `DB.LinePatternElement` Wrapper

    Solid, Dash, etc

    Attribute:
        _revit_object (DB.LinePatternElement): Wrapped ``DB.LinePatternElement``

    """

    _revit_object_class = DB.LinePatternElement
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    def __repr__(self):
        return Element.__repr__(self, data={'name': self.name})


class FillPatternElement(LinePatternElement):
    """
    `DB.FillPatternElement` Wrapper

    Solid, Horizontal, Vertical, Diagonal Down, etc

    Attribute:
        _revit_object (DB.FillPatternElement): Wrapped ``DB.FillPatternElement``
    """

    _revit_object_class = DB.FillPatternElement
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}
