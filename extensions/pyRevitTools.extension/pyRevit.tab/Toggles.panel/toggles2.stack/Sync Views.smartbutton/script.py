# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
# pylint: disable=broad-except,missing-docstring
import os
import os.path as op
import pickle as pl
import clr

from pyrevit import framework
from pyrevit import script, revit
from pyrevit import DB, UI


__doc__ = 'Keep views synchronized. This means that as you pan and zoom and '\
          'switch between Plan and RCP views, this tool will keep the views '\
          'in the same zoomed area so you can keep working in the same '\
          'area without the need to zoom and pan again.\n'\
          'This tool works best when the views are maximized.'


SYNC_VIEW_ENV_VAR = 'SYNCVIEWACTIVE'


def get_data_filename(document):
    project_name = op.splitext(op.basename(document.PathName))[0]
    return project_name + '_pySyncRevitActiveViewZoomState'


def get_datafile(document):
    data_filename = get_data_filename(document)
    return script.get_instance_data_file(data_filename)


def copyzoomstate(sender, args):
    try:
        if script.get_envvar(SYNC_VIEW_ENV_VAR):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()
            current_ui_view = None

            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view

            is_view3d = isinstance(args.CurrentActiveView, DB.View3D)
            is_viewplan = isinstance(args.CurrentActiveView, DB.ViewPlan)
            if current_ui_view and (is_view3d or is_viewplan):
                cornerlist = current_ui_view.GetZoomCorners()

                f = open(get_datafile(event_doc), 'w')
                # dump zoom and center
                pl.dump(revit.serializable.serialize_list(cornerlist), f)
                # dump ViewOrientation3D
                if is_view3d:
                    orientation = args.CurrentActiveView.GetOrientation()
                    pl.dump(revit.serializable.ViewOrientation3D(orientation),
                            f)
                f.close()
    except Exception as exc:
        pass


def applyzoomstate(sender, args):
    try:
        if script.get_envvar(SYNC_VIEW_ENV_VAR):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()
            current_ui_view = None
            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view

            is_view3d = isinstance(args.CurrentActiveView, DB.View3D)
            is_viewplan = isinstance(args.CurrentActiveView, DB.ViewPlan)
            if current_ui_view and (is_view3d or is_viewplan):
                f = open(get_datafile(event_doc), 'r')
                vc1, vc2 = pl.load(f)
                view_orientation = None
                # load ViewOrientation3D
                if is_view3d and not args.CurrentActiveView.IsLocked:
                    try:
                        view_orientation = pl.load(f)
                    except EOFError:
                        pass
                f.close()
                # apply view orientation
                if view_orientation:
                    args.CurrentActiveView.SetOrientation(
                        view_orientation.deserialize())
                # apply zoom and center
                if (is_viewplan and not view_orientation) or \
                        (is_view3d and view_orientation):
                    current_ui_view.ZoomAndCenterRectangle(vc1.deserialize(),
                                                           vc2.deserialize())
    except Exception as exc:
        pass


def togglestate():
    new_state = not script.get_envvar(SYNC_VIEW_ENV_VAR)
    # remove last datafile on start
    if new_state:
        # try:
        data_filename = get_data_filename(revit.doc)
        if os.path.exists(data_filename):
            os.remove(data_filename)
        # except Exception:
        #     pass
    script.set_envvar(SYNC_VIEW_ENV_VAR, new_state)
    script.toggle_icon(new_state)


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    try:
        __rvt__.ViewActivating += \
            framework.EventHandler[
                UI.Events.ViewActivatingEventArgs](copyzoomstate)
        __rvt__.ViewActivated += \
            framework.EventHandler[
                UI.Events.ViewActivatedEventArgs](applyzoomstate)
        return True
    except Exception:
        return False


if __name__ == '__main__':
    togglestate()
