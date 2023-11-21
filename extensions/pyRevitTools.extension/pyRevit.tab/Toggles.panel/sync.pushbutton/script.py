import datetime
from pyrevit import DB, UI, revit, HOST_APP
from pyrevit import script, forms, coreutils

doc = revit.doc

my_config = script.get_config()
try:
    close = getattr(my_config, "close_inactive_views")
except:
    close = False


def close_inactive_views(closing_config=close, document=doc):
    """Closes all inactive views except for the starting view.

    Parameters:
    closing_config (bool): Flag indicating whether to close inactive views or not.
    document (Document): The Revit document. Default is the active document.

    Returns:
    None
    """
    if closing_config:
        starting_view_id = DB.StartingViewSettings.GetStartingViewSettings(document).ViewId
        starting_view = document.GetElement(starting_view_id)
        if starting_view:
            uidoc = revit.uidoc
            HOST_APP.uidoc.RequestViewChange(starting_view)
            uidoc.ActiveView = starting_view
            all_open_views = uidoc.GetOpenUIViews()
            for ui_view in all_open_views :
                doc_view = document.GetElement(ui_view.ViewId)
                if doc_view.Name != starting_view.Name :
                    ui_view.Close()
        else:
            forms.show_balloon(
                "No Starting View Set", 
                "No Starting View Set", 
                )


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

        close_inactive_views(close)

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
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime).seconds)
        endtime_hms_claim = "Synchronisation took {}s.".format(endtime_hms)
        forms.show_balloon(endtime_hms_claim, "{}s. to synchronize".format(endtime_hms))
    else :
        forms.alert("Current Document is not Workshared and was not synched", "Error")


if __name__ == "__main__":
    sync_document()
