# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
# pylint: disable=broad-except,missing-docstring
import os
import os.path as op
import pickle as pl
import clr
import math

from pyrevit import framework
from pyrevit import script, revit
from pyrevit import DB, UI


__doc__ = 'Keep views synchronized. This means that as you pan and zoom and '\
          'switch between Plan and RCP views, this tool will keep the views '\
          'in the same zoomed area so you can keep working in the same '\
          'area without the need to zoom and pan again.\n'\
          'This tool works best when the views are maximized.'

SYNC_VIEW_ENV_VAR = 'SYNCVIEWACTIVE'

SUPPORTED_VIEW_TYPES = (
    DB.ViewPlan,
    DB.ViewSection,
    DB.View3D,
    DB.ViewSheet,
    DB.ViewDrafting
)

def get_data_filename(document):
    project_name = op.splitext(op.basename(document.PathName))[0]
    return project_name + '_pySyncRevitActiveViewZoomState'


def get_datafile(document):
    data_filename = get_data_filename(document)
    return script.get_instance_data_file(data_filename)

def is_close(a, b, rnd=5):
    return a == b or int(a*10**rnd) == int(b*10**rnd)

def copyzoomstate(sender, args):
    try:
        if script.get_envvar(SYNC_VIEW_ENV_VAR) and \
                isinstance(args.CurrentActiveView, SUPPORTED_VIEW_TYPES):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()

            current_ui_view = None
            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view
            if not current_ui_view:
                return

            cornerlist = current_ui_view.GetZoomCorners()

            f = open(get_datafile(event_doc), 'w')
            try:
                pl.dump(type(args.CurrentActiveView).__name__, f)
                # dump zoom and center
                pl.dump(revit.serializable.serialize_list(cornerlist), f)
                # dump ViewOrientation3D
                if isinstance(args.CurrentActiveView, DB.View3D):
                    orientation = args.CurrentActiveView.GetOrientation()
                    pl.dump(revit.serializable.ViewOrientation3D(orientation),
                            f)
                elif isinstance(args.CurrentActiveView, DB.ViewSection):
                    direction = args.CurrentActiveView.ViewDirection
                    pl.dump(revit.serializable.XYZ(direction), f)
            except Exception:
                pass
            finally:
                f.close()
    except Exception:
        pass
    

def applyzoomstate(sender, args):
    try:
        if script.get_envvar(SYNC_VIEW_ENV_VAR) and \
                isinstance(args.CurrentActiveView, SUPPORTED_VIEW_TYPES):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()

            current_ui_view = None
            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view
            if not current_ui_view:
                return
            f = open(get_datafile(event_doc), 'r')
            
            try:
                view_type_saved = pl.load(f)
                if view_type_saved != type(args.CurrentActiveView).__name__:
                    raise Exception()
                vc1, vc2 = pl.load(f)
                # load ViewOrientation3D
                if isinstance(args.CurrentActiveView, DB.View3D):
                    if args.CurrentActiveView.IsLocked:
                        raise Exception()
                    view_orientation = pl.load(f)
                    args.CurrentActiveView.SetOrientation(
                        view_orientation.deserialize())
                elif isinstance(args.CurrentActiveView, DB.ViewSection):
                    direction = pl.load(f)
                    angle = direction.deserialize().AngleTo(
                                args.CurrentActiveView.ViewDirection)
                    if not is_close(angle, math.pi) and not is_close(angle, 0):
                        raise Exception()

            except Exception:
                pass
            else:
                # apply zoom and center
                current_ui_view.ZoomAndCenterRectangle(vc1.deserialize(), vc2.deserialize())
            finally:
                f.close()            
    except Exception:
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
