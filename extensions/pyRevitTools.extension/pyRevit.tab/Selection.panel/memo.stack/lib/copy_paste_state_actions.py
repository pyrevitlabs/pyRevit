# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
from pyrevit import revit, script, forms, DB
import pickle
import math


def is_close(a, b, rnd=5):
    return a == b or int(a*10**rnd) == int(b*10**rnd)


def copy_paste_action(func):
    func.is_copy_paste_action = True
    return func


class DataFile:
    def __init__(self, action_name, mode='r'):
        self.datafile = script.get_document_data_file(
            file_id='CopyPasteState_' + action_name,
            file_ext='pym',
            add_cmd_name=False)
        self.mode = mode

    def __enter__(self):
        self.file = open(self.datafile, self.mode)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()
        if exception_value:
            forms.alert(str(exception_value))

    def dump(self, value):
        # make picklable (serialize)
        value_serialized = revit.serializable.serialize(value)
        pickle.dump(value_serialized, self.file)

    def load(self):
        # unpickle (deserialize)
        value_serialized = pickle.load(self.file)
        return revit.serializable.deserialize(value_serialized)


class CopyPasteStateAction:
    name = '-'

    def copy(self, datafile):
        pass

    def paste(self, datafile):
        pass

    @staticmethod
    def validate_context():
        return

    def copy_wrapper(self):
        validate_msg = self.validate_context()
        if validate_msg:
            forms.alert(validate_msg)
        else:
            with DataFile(self.__class__.__name__, 'w') as datafile:
                self.copy(datafile)

    def paste_wrapper(self):
        validate_msg = self.validate_context()
        if validate_msg:
            forms.alert(validate_msg)
        else:
            with DataFile(self.__class__.__name__, 'r') as datafile:
                self.paste(datafile)


@copy_paste_action
class ViewZoomPanState(CopyPasteStateAction):
    name = 'View Zoom/Pan State'

    def copy(self, datafile):
        datafile.dump(type(revit.active_view).__name__)
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        corner_list = active_ui_view.GetZoomCorners()
        datafile.dump(corner_list)
        # dump ViewOrientation3D
        if isinstance(revit.active_view, DB.View3D):
            orientation = revit.active_view.GetOrientation()
            datafile.dump(orientation)
        elif isinstance(revit.active_view, DB.ViewSection):
            direction = revit.active_view.ViewDirection
            datafile.dump(direction)

    def paste(self, datafile):
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        view_type_saved = datafile.load()
        if view_type_saved != type(revit.active_view).__name__:
            raise Exception(
                'Saved view type (%s) is different from active view (%s)' % (
                    view_type_saved, type(revit.active_view).__name__))
        vc1, vc2 = datafile.load()
        # load ViewOrientation3D
        if isinstance(revit.active_view, DB.View3D):
            if revit.active_view.IsLocked:
                raise Exception('Current view orientation is locked')
            view_orientation = datafile.load()
            revit.active_view.SetOrientation(view_orientation)
        elif isinstance(revit.active_view, DB.ViewSection):
            direction = datafile.load()
            angle = direction.AngleTo(revit.active_view.ViewDirection)
            if not is_close(angle, math.pi) and not is_close(angle, 0):
                raise Exception("Views are not parallel")
        active_ui_view.ZoomAndCenterRectangle(vc1, vc2)

    @staticmethod
    def validate_context():
        if not isinstance(revit.active_view, (
                DB.ViewPlan,
                DB.ViewSection,
                DB.View3D,
                DB.ViewSheet,
                DB.ViewDrafting)):
            return "Type of active view is not supported"


@copy_paste_action
class SectionBox3DState(CopyPasteStateAction):
    name = '3D Section Box State'

    def copy(self, datafile):
        section_box = revit.active_view.GetSectionBox()
        view_orientation = revit.active_view.GetOrientation()
        datafile.dump(section_box)
        datafile.dump(view_orientation)

    def paste(self, datafile):
        section_box = datafile.load()
        view_orientation = datafile.load()
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        with revit.Transaction('Paste Section Box Settings'):
            revit.active_view.SetSectionBox(section_box.deserialize())
            revit.active_view.SetOrientation(view_orientation.deserialize())
        active_ui_view.ZoomToFit()

    @staticmethod
    def validate_context():
        if not isinstance(revit.active_view, DB.View3D):
            return "You must be on a 3D view to copy and paste 3D section box."
