"""Keep views synchronized. This means that as you pan and zoom and
switch between Plan and RCP views, this tool will keep the views
in the same zoomed area so you can keep working in the same
area without the need to zoom and pan again.
This tool works best when the views are maximized.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
import os.path as op
import pickle as pl
import math

from pyrevit import framework
from pyrevit import script, revit
from pyrevit import DB, UI


logger = script.get_logger()


SYNC_VIEW_ENV_VAR = 'SYNCVIEWACTIVE'

SUPPORTED_VIEW_TYPES = (
    DB.ViewPlan,
    DB.ViewSection,
    DB.View3D,
    DB.ViewSheet,
    DB.ViewDrafting
)


def get_data_filename(document):
    """Get temporary datafile name for given document"""
    project_name = op.splitext(op.basename(document.PathName))[0]
    return project_name + '_pySyncRevitActiveViewZoomState'


def get_datafile(document):
    """Get datafile for given document"""
    data_filename = get_data_filename(document)
    return script.get_instance_data_file(data_filename)


def is_close(a, b, rnd=5):
    """Determine if a is close enough to b"""
    return a == b or int(a*10**rnd) == int(b*10**rnd)


def copy_zoomstate(sender, args):
    """Copy zoom state to data file"""
    try:
        # if syncinc is active, and current view is supported
        if script.get_envvar(SYNC_VIEW_ENV_VAR) and \
                isinstance(args.CurrentActiveView, SUPPORTED_VIEW_TYPES):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()

            # find current uiview
            current_ui_view = None
            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view
            if not current_ui_view:
                return

            # get zoom corners
            cornerlist = current_ui_view.GetZoomCorners()
            # and save the info
            f = open(get_datafile(event_doc), 'w')
            try:
                # dump current view type
                pl.dump(type(args.CurrentActiveView).__name__, f)
                # dump zoom and center
                pl.dump([revit.serialize(x) for x in cornerlist], f)
                # dump ViewOrientation3D
                if isinstance(args.CurrentActiveView, DB.View3D):
                    orientation = args.CurrentActiveView.GetOrientation()
                    pl.dump(revit.serialize(orientation),
                            f)
                elif isinstance(args.CurrentActiveView, DB.ViewSection):
                    direction = args.CurrentActiveView.ViewDirection
                    pl.dump(revit.serialize(direction), f)
            except Exception as copy_ex:
                logger.dev_log("copy_zoomstate::store", str(copy_ex))
            finally:
                f.close()
    except Exception as ex:
        logger.dev_log("copy_zoomstate::", str(ex))


def apply_zoomstate(sender, args):
    """Apple zoom state from data file"""
    try:
        # if syncinc is active, and current view is supported
        if script.get_envvar(SYNC_VIEW_ENV_VAR) and \
                isinstance(args.CurrentActiveView, SUPPORTED_VIEW_TYPES):
            event_uidoc = sender.ActiveUIDocument
            event_doc = sender.ActiveUIDocument.Document
            active_ui_views = event_uidoc.GetOpenUIViews()

            # grab current uiview
            current_ui_view = None
            for active_ui_view in active_ui_views:
                if active_ui_view.ViewId == args.CurrentActiveView.Id:
                    current_ui_view = active_ui_view
            if not current_ui_view:
                return

            # load zoom data
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
                        args.CurrentActiveView.ViewDirection
                        )
                    if not is_close(angle, math.pi) and not is_close(angle, 0):
                        raise Exception("View directions do not match")

            except Exception as apply_ex:
                logger.dev_log("copy_zoomstate::load", str(apply_ex))
            else:
                # apply zoom and center
                current_ui_view.ZoomAndCenterRectangle(
                    vc1.deserialize(),
                    vc2.deserialize()
                    )
            finally:
                f.close()
    except Exception as ex:
        logger.dev_log("apply_zoomstate::", str(ex))


def toggle_state():
    """Toggle tool state"""
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


#pylint: disable=unused-argument
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    """pyRevit smartbuttom init"""
    try:
        __rvt__.ViewActivating += \
            framework.EventHandler[
                UI.Events.ViewActivatingEventArgs](copy_zoomstate)
        __rvt__.ViewActivated += \
            framework.EventHandler[
                UI.Events.ViewActivatedEventArgs](apply_zoomstate)
        return True
    except Exception:
        return False


if __name__ == '__main__':
    toggle_state()
