"""Observable item contracts shared by selection dialogs and custom forms."""

from . import _backend
from .base import WPF_COLLAPSED
from .base import WPF_VISIBLE
from pyrevit.compat import safe_strtype


Reactive = _backend.Reactive


class reactive(property):
    """Decorator for WPF bound properties."""

    def __init__(self, getter):
        def newgetter(ui_control):
            try:
                return getter(ui_control)
            except AttributeError:
                return None

        super(reactive, self).__init__(newgetter)

    def setter(self, setter):
        """Property setter."""

        def newsetter(ui_control, newvalue):
            oldvalue = self.fget(ui_control)
            if oldvalue != newvalue:
                setter(ui_control, newvalue)
                ui_control.OnPropertyChanged(setter.__name__)

        return property(
            fget=self.fget, fset=newsetter, fdel=self.fdel, doc=self.__doc__
        )


class TemplateListItem(Reactive):
    """Base class for checkbox option wrapping another object."""

    def __init__(self, orig_item, checked=False, checkable=True, name_attr=None):
        """Initialize the checkbox option and wrap given obj.

        Args:
            orig_item (any): Object to wrap (must have name property
                             or be convertable to string with str()
            checked (bool): Initial state. Defaults to False
            checkable (bool): Use checkbox for items
            name_attr (str): Get this attribute of wrapped object as name
        """
        super(TemplateListItem, self).__init__()
        self.item = orig_item
        self.state = checked
        self._nameattr = name_attr
        self._checkable = checkable

    def __bool__(self):
        # Python 3 requires __bool__ to return an actual bool; state may be
        # any truthy value (e.g. an int passed as `checked`)
        return bool(self.state)

    __nonzero__ = __bool__

    def __str__(self):
        return self.name or str(self.item)

    def __contains__(self, value):
        return value in self.name

    def __getattr__(self, param_name):
        return getattr(self.item, param_name)

    @property
    def name(self):
        """Name property."""
        # get custom attr, or name or just str repr
        if self._nameattr:
            return safe_strtype(getattr(self.item, self._nameattr))
        elif hasattr(self.item, "name"):
            return getattr(self.item, "name", "")
        else:
            return safe_strtype(self.item)

    def unwrap(self):
        """Unwrap and return wrapped object."""
        return self.item

    @reactive
    def checked(self):
        """Id checked."""
        return self.state

    @checked.setter
    def checked(self, value):
        self.state = value

    @property
    def checkable(self):
        """List Item CheckBox Visibility."""
        return WPF_VISIBLE if self._checkable else WPF_COLLAPSED

    @checkable.setter
    def checkable(self, value):
        self._checkable = value


class ParamDef(TemplateListItem):
    """Parameter definition for :func:`select_parameters`.

    Inherits from :obj:`TemplateListItem` for use with SelectFromList.

    Attributes:
        name (str): parameter name
        istype (bool): true if type parameter, otherwise false
        definition (Autodesk.Revit.DB.Definition): parameter definition object
        isreadonly (bool): true if the parameter value can't be edited
        isunit (bool): true if its ForgeTypeId is measurable
        storagetype (Autodesk.Revit.DB.StorageType): String, Integer, Double or ElementId
        displayvalue (str): display string of the current parameter value, or None
        hasvalue (bool): true if the parameter has a value to display
        grouptype (str): name of parameter group
        isshared (bool): is the parameter shared
        paramid (str): stringified parameter ElementId (integer id)
    """

    _fields = (
        "name",
        "istype",
        "definition",
        "isreadonly",
        "isunit",
        "storagetype",
        "displayvalue",
        "hasvalue",
        "grouptype",
        "isshared",
        "paramid",
    )

    def __init__(
        self,
        name,
        istype,
        definition,
        isreadonly,
        isunit,
        storagetype,
        displayvalue,
        hasvalue,
        grouptype,
        isshared,
        paramid,
        checked=False,
    ):
        super(ParamDef, self).__init__(orig_item=None, checked=checked)
        self._name = name
        self.istype = istype
        self.definition = definition
        self.isreadonly = isreadonly
        self.isunit = isunit
        self.storagetype = storagetype
        self.displayvalue = displayvalue
        self.hasvalue = hasvalue
        self.grouptype = grouptype
        self.isshared = isshared
        self.paramid = paramid

    @property
    def name(self):
        """Parameter name."""
        return self._name

    def unwrap(self):
        """Return self so SelectFromList returns ParamDef instances."""
        return self

    def __nonzero__(self):
        return True

    __bool__ = __nonzero__

    def __iter__(self):
        for f in self._fields:
            yield getattr(self, f)

    def __len__(self):
        return len(self._fields)

    def __getitem__(self, index):
        return tuple(self)[index]

    def _asdict(self):
        return {f: getattr(self, f) for f in self._fields}
