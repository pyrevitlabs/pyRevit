import os
import os.path as op
import pickle as pl
import clr

import pyrevit.coreutils.envvars as envvars

from scriptutils import this_script

clr.AddReference('PresentationCore')

# noinspection PyUnresolvedReferences
from System import EventHandler, Uri
import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI.Events as UIEvents


__doc__ = 'Keep views synchronized. This means that as you pan and zoom and switch between Plan and RCP views, this ' \
          'tool will keep the views in the same zoomed area so you can keep working in the same area without '        \
          'the need to zoom and pan again.\n This tool works best when the views are maximized.'


class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


SYNC_VIEW_ENV_VAR = 'SYNCVIEWACTIVE'
# todo: sync views - 3D


def copyzoomstate(sender, args):
    if envvars.get_pyrevit_env_var(SYNC_VIEW_ENV_VAR):
        event_uidoc = sender.ActiveUIDocument
        event_doc = sender.ActiveUIDocument.Document
        active_ui_views = event_uidoc.GetOpenUIViews()
        current_ui_view = None
        for active_ui_view in active_ui_views:
            if active_ui_view.ViewId == args.CurrentActiveView.Id:
                current_ui_view = active_ui_view

        if isinstance(args.CurrentActiveView, DB.ViewPlan):
            project_name = op.splitext(op.basename(event_doc.PathName))[0]
            data_file = this_script.get_instance_data_file(project_name + '_pySyncRevitActiveViewZoomState')

            cornerlist = current_ui_view.GetZoomCorners()

            vc1 = cornerlist[0]
            vc2 = cornerlist[1]
            p1 = Point()
            p2 = Point()
            p1.x = vc1.X
            p1.y = vc1.Y
            p2.x = vc2.X
            p2.y = vc2.Y

            f = open(data_file, 'w')
            pl.dump(p1, f)
            pl.dump(p2, f)
            f.close()


def applyzoomstate(sender, args):
    if envvars.get_pyrevit_env_var(SYNC_VIEW_ENV_VAR):
        event_uidoc = sender.ActiveUIDocument
        event_doc = sender.ActiveUIDocument.Document
        active_ui_views = event_uidoc.GetOpenUIViews()
        current_ui_view = None
        for active_ui_view in active_ui_views:
            if active_ui_view.ViewId == args.CurrentActiveView.Id:
                current_ui_view = active_ui_view

        if isinstance(args.CurrentActiveView, DB.ViewPlan):
            project_name = op.splitext(op.basename(event_doc.PathName))[0]
            data_file = this_script.get_instance_data_file(project_name + '_pySyncRevitActiveViewZoomState')
            f = open(data_file, 'r')
            p2 = pl.load(f)
            p1 = pl.load(f)
            f.close()
            vc1 = DB.XYZ(p1.x, p1.y, 0)
            vc2 = DB.XYZ(p2.x, p2.y, 0)
            current_ui_view.ZoomAndCenterRectangle(vc1, vc2)


def togglestate():
    new_state = not envvars.get_pyrevit_env_var(SYNC_VIEW_ENV_VAR)
    envvars.set_pyrevit_env_var(SYNC_VIEW_ENV_VAR, new_state)
    this_script.toggle_icon(new_state)


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    try:
        __rvt__.ViewActivating += EventHandler[UIEvents.ViewActivatingEventArgs](copyzoomstate)
        __rvt__.ViewActivated += EventHandler[UIEvents.ViewActivatedEventArgs](applyzoomstate)
        return True
    except:
        return False


if __name__ == '__main__':
    togglestate()
