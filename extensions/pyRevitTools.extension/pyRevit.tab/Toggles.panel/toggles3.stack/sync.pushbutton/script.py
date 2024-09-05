import datetime
from pyrevit import DB, UI, revit, HOST_APP
from pyrevit import script, forms, coreutils
from pyrevit.compat import get_elementid_value_func

doc = revit.doc

logger = script.get_logger()

my_config = script.get_config()
try:
    view_handling = getattr(my_config, "view_handling")
except:
    view_handling = "nothing"
    setattr(
        my_config,
        "view_handling",
        "nothing"
    )
    script.save_config()

view_cache = []


def close_inactive_views(view_handling="nothing", document=doc):
    """
    Close inactive views in the Autodesk Revit project based on specified handling.

    Args:
        view_handling (str, optional): Specifies how to handle inactive views.
            Options are:
            - "nothing": Do nothing and return.
            - anything else: Add closed views to the view cache for potential reopening.
        document (Autodesk.Revit.DB.Document, optional): The Revit document to perform
            the operation on. Default is the active document.

    Returns:
        None

    Example:
        >>> close_inactive_views(view_handling="reopen")
    """
    if view_handling == "nothing":
        return
    starting_view_id = DB.StartingViewSettings.GetStartingViewSettings(document).ViewId
    starting_view = document.GetElement(starting_view_id)
    if starting_view:
        uidoc = revit.uidoc
        HOST_APP.uidoc.RequestViewChange(starting_view)
        uidoc.ActiveView = starting_view
        all_open_views = uidoc.GetOpenUIViews()
        for ui_view in all_open_views:
            if view_handling == "reopen":
                view_cache.append(ui_view.ViewId)
            doc_view = document.GetElement(ui_view.ViewId)
            if doc_view.Id != starting_view.Id :
                ui_view.Close()
    else:
        forms.show_balloon(
            "No Starting View Set",
            "No Starting View Set",
            )


def set_active_view(view):
    """
    Set the active view in the Autodesk Revit project to the specified view.

    Args:
        view (Autodesk.Revit.DB.View): The view to be set as the active view.

    Returns:
        str: The name of the activated view.

    Raises:
        TypeError: If the input element is not a View.

    Example:
        >>> active_view_name = set_active_view(my_view)
    """
    if not isinstance(view, DB.View):
        raise TypeError(
            'Element [{}] is not a View!'.format(view.Id))
    name = view.Name
    if view.ViewType != DB.ViewType.Internal and \
            view.ViewType != DB.ViewType.ProjectBrowser:
        revit.uidoc.ActiveView = view
        logger.debug('Active View is: {}'.format(view.Name))
        return name
    else:
        logger.info('View {} ({}) cannot be activated.'.format(
            name, view.ViewType))
        return 'INTERNAL / PB: ' + name



def sync_document():
    """Synchronizes the current document with the central model.

    This function checks if the document is workshared
    and not a family document or a linked document.
    If it meets the criteria, it performs the following steps:

    1. Sets the active view to the starting view when possible.
    2. Closes all inactive views.
    3. Transacts with central using the specified options.
    4. Saves the document.
    5. Reloads the latest version of the document.
    6. Saves the document again.
    7. Synchronizes the document with the central model.

    If the document does not meet the criteria, an error message is displayed.

    Note: This function is specific to the pyRevit extension.
    """
    if doc.IsWorkshared and not doc.IsFamilyDocument and not doc.IsLinked:
        timer = coreutils.Timer()

        close_inactive_views(view_handling)

        trans_options = DB.TransactWithCentralOptions()
        sync_options = DB.SynchronizeWithCentralOptions()
        relinquish_all = True
        relinquish_options = DB.RelinquishOptions(relinquish_all)
        reload_latest_options = DB.ReloadLatestOptions()

        save_options = DB.SaveOptions()

        sync_options.SetRelinquishOptions(relinquish_options)
        sync_options.Compact = True
        sync_options.Comment = "Synchronisation from pyRevit"
        doc.Save(save_options)
        doc.ReloadLatest(reload_latest_options)
        doc.Save(save_options)
        doc.SynchronizeWithCentral(trans_options , sync_options)

        if view_handling == "reopen":
            for v_id in view_cache:
                view = doc.GetElement(v_id)
                try:
                    set_active_view(view)
                except:
                    get_elementid_value = get_elementid_value_func()
                    logger.warn(
                        "Failed to reopen view {}".format(get_elementid_value(v_id)))

        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime).seconds)
        endtime_hms_claim = "Synchronisation took {}s.".format(endtime_hms)
        forms.show_balloon(endtime_hms_claim, "{}s. to synchronize".format(endtime_hms))
    else :
        forms.alert("Current Document is not Workshared and was not synched", "Error")


if __name__ == "__main__":
    sync_document()
