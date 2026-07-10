# -*- coding: utf-8 -*-
from pyrevit import forms, revit, script, DB
from pyrevit.revit import query

logger = script.get_logger()


def get_views_with_sfm():
    """Map each view that has an active SpatialFieldManager to that manager."""
    v_sfm_dict = {}
    for v in query.get_all_views():
        try:
            sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(v)
            if sfm is None:
                continue
            v_sfm_dict[v] = sfm
        except Exception as ex:
            logger.debug("Skipped view " + str(getattr(v, "Id", v)) + " : " + str(ex))
    return v_sfm_dict


def main():
    """Let user select which view(s) to purge AVF (SpatialFieldManager) data from."""
    v_sfm_dict = get_views_with_sfm()

    if not v_sfm_dict:
        print("No views with an active Analysis Visualization Framework (AVF) found.")
        return

    selection = forms.SelectFromList.show(
        list(v_sfm_dict.keys()),
        name_attr="Name",
        multiselect=True,
        title="Select Views to Purge AVF",
        button_name="Purge Selected Views",
    )

    if not selection:
        print("Nothing selected.")
        return

    purged = 0
    skipped = 0

    # Transaction not necessary, added to safeguard in case future Revit versions require it
    with revit.Transaction("Purge AVF"):
        for v in selection:
            sfm = v_sfm_dict.get(v)
            if not sfm:
                skipped += 1
                continue
            try:
                sfm.Clear()
                purged += 1
                print("Purged AVF: " + v.Name)
            except Exception as ex:
                logger.exception(
                    "Failed purging AVF on view " + v.Name + " : " + str(ex)
                )
                skipped += 1

    revit.uidoc.RefreshActiveView()
    print("Done. Purged: " + str(purged) + " | Skipped: " + str(skipped))


if __name__ == "__main__":
    main()
