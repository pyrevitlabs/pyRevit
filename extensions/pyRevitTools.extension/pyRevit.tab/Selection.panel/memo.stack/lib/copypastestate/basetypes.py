"""Base class and constants for the Copy/Paste State actions."""

# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import DB


COPYPASTE_MARKER_PROPNAME = "is_copypaste_action"

COMPATIBLE_VIEWTYPES = [
    [
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.EngineeringPlan,
        DB.ViewType.AreaPlan,
    ]
]


class CopyPasteStateAction(object):
    """Base class for the properties Copy State and Paste State can transfer.

    Subclasses are marked with ``moduleutils.mark(COPYPASTE_MARKER_PROPNAME)``,
    which is how `copypastestate.get_actions` finds them. The state is stored with
    ``script.store_data`` in a slot named after the class.

    Attributes:
        name (str): Localized label of the action in the selection dialog.
        this_project (bool): Whether the stored state belongs to the project it was
            copied in. Actions with ``False`` can paste into any project.

    Example:
        ```python
        @moduleutils.mark(COPYPASTE_MARKER_PROPNAME)
        class ViewScale(CopyPasteStateAction):
            name = "View Scale"

            def copy(self):
                script.store_data(self.__class__.__name__, revit.active_view.Scale)

            def paste(self):
                scale = script.load_data(self.__class__.__name__)
                with revit.Transaction("Paste view scale"):
                    revit.active_view.Scale = scale

            @staticmethod
            def validate_context():
                return not isinstance(revit.active_view, DB.TableView)
        ```
    """

    name = None
    invalid_context_msg = None
    this_project = True

    def copy(self):
        """Store the state of the active view or selection.

        Raises:
            PyRevitException: The state cannot be read. The message is shown to the
                user.
        """
        pass

    def paste(self):
        """Apply the stored state to the active view or selection.

        Raises:
            PyRevitException: The state cannot be applied. The message is shown to
                the user.
        """
        pass

    @staticmethod
    def validate_context():
        """Tell whether the action can run on the active view and selection.

        Runs silently for every action to build the selection dialog, so it must
        not show any form.

        Returns:
            bool: True if the action is available now.
        """
        return

    @staticmethod
    def is_compatible_viewtype(target_view, source_viewtype):
        """Check if view types are compatible for this action."""
        if target_view.ViewType == source_viewtype:
            return True

        for compat_viewtypes in COMPATIBLE_VIEWTYPES:
            if (
                target_view.ViewType in compat_viewtypes
                and source_viewtype in compat_viewtypes
            ):
                return True

        return False
