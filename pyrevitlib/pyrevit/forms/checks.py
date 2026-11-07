"""Document and selection preconditions with native user feedback."""

from .native import alert
from pyrevit import DB
from pyrevit import DOCS
from pyrevit import coreutils
from pyrevit import revit


def check_workshared(doc=None, message="Model is not workshared."):
    """Verify if model is workshared and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        message (str): prompt message if returning False

    Returns:
        (bool): True if doc is workshared
    """
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        alert(message, warn_icon=True)
        return False
    return True


def check_selection(exitscript=False, message="At least one element must be selected."):
    """Verify if selection is not empty notify user if it is.

    Args:
        exitscript (bool): exit script if returning False
        message (str): prompt message if returning False

    Returns:
        (bool): True if selection has at least one item
    """
    if revit.get_selection().is_empty:
        alert(message, exitscript=exitscript)
        return False
    return True


def check_familydoc(doc=None, family_cat=None, exitscript=False):
    """Verify document is a Family and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        family_cat (str): family category name
        exitscript (bool): exit script if returning False

    Returns:
        (bool): True if doc is a Family and of provided category

    Examples:
        ```python
        from pyrevit import forms
        forms.check_familydoc(doc=revit.doc, family_cat='Data Devices')
        True
        ```
    """
    doc = doc or DOCS.doc
    family_cat = revit.query.get_category(family_cat)
    if doc.IsFamilyDocument and family_cat:
        if doc.OwnerFamily.FamilyCategory.Id == family_cat.Id:
            return True
    elif doc.IsFamilyDocument and not family_cat:
        return True

    family_type_msg = " of type {}".format(family_cat.Name) if family_cat else ""
    alert(
        "Active document must be a Family document{}.".format(family_type_msg),
        exitscript=exitscript,
    )
    return False


def check_modeldoc(doc=None, exitscript=False):
    """Verify document is a not a Model and notify user if not.

    Args:
        doc (DB.Document): target document, current of not provided
        exitscript (bool): exit script if returning False

    Returns:
        (bool): True if doc is a Model

    Examples:
        ```python
        from pyrevit import forms
        forms.check_modeldoc(doc=revit.doc)
        True
        ```
    """
    doc = doc or DOCS.doc
    if not doc.IsFamilyDocument:
        return True

    alert(
        "Active document must be a Revit model (not a Family).", exitscript=exitscript
    )
    return False


def check_modelview(view, exitscript=False):
    """Verify target view is a model view.

    Args:
        view (DB.View): target view
        exitscript (bool): exit script if returning False

    Returns:
        (bool): True if view is model view

    Examples:
        ```python
        from pyrevit import forms
        forms.check_modelview(view=revit.active_view)
        True
        ```
    """
    if not isinstance(view, (DB.View3D, DB.ViewPlan, DB.ViewSection)):
        alert("Active view must be a model view.", exitscript=exitscript)
        return False
    return True


def check_viewtype(view, view_type, exitscript=False):
    """Verify target view is of given type.

    Args:
        view (DB.View): target view
        view_type (DB.ViewType): type of view
        exitscript (bool): exit script if returning False

    Returns:
        (bool): True if view is of given type

    Examples:
        ```python
        from pyrevit import forms
        forms.check_viewtype(revit.active_view, DB.ViewType.DrawingSheet)
        True
        ```
    """
    if view.ViewType != view_type:
        alert(
            "Active view must be a {}.".format(
                " ".join(coreutils.split_words(str(view_type)))
            ),
            exitscript=exitscript,
        )
        return False
    return True


def check_graphicalview(view, exitscript=False):
    """Verify target view is a graphical view.

    Args:
        view (DB.View): target view
        exitscript (bool): exit script if returning False

    Returns:
        (bool): True if view is a graphical view

    Examples:
        ```python
        from pyrevit import forms
        forms.check_graphicalview(revit.active_view)
        True
        ```
    """
    if not view.Category:
        alert("Active view must be a grahical view.", exitscript=exitscript)
        return False
    return True


def ask_to_use_selected(type_name, count=None, multiple=True):
    """Ask user if wants to use currently selected elements.

    Args:
        type_name (str): Element type of expected selected elements
        count (int): Number of selected items
        multiple (bool): Whether multiple selected items are allowed
    """
    report = type_name.lower()
    # multiple = True
    message = (
        "You currently have %s selected. Do you want to proceed with "
        "currently selected item(s)?"
    )
    # check is selecting multiple is allowd
    if not multiple:
        # multiple = False
        message = (
            "You currently have %s selected and only one is required. "
            "Do you want to use the first selected item?"
        )

    # check if count is provided
    if count is not None:
        report = "{} {}".format(count, report)
    return alert(message % report, yes=True, no=True)


def inform_wip():
    """Show work-in-progress prompt to user and exit script.

    Examples:
        ```python
        forms.inform_wip()
        ```
    """
    alert("Work in progress.", exitscript=True)
