# -*- coding: UTF-8 -*-

from __future__ import print_function

import traceback
from pyrevit import script, forms, revit, DB

doc = revit.doc
uidoc = revit.uidoc

logger = script.get_logger()
output = script.get_output()

class UI(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name, handle_esc=False)

        self.server = revit.dc3dserver.Server()
        if not self.server:
            script.exit()

        self.Closed += self.form_closed

    def form_closed(self, sender, args):
        try:
            self.server.remove_server()
            uidoc.RefreshActiveView()
        except:
            print(traceback.format_exc())

    def button_apply(self, sender, args):
        try:
            x = float(self.txtCoordX.Text)
            y = float(self.txtCoordY.Text)
            z = float(self.txtCoordZ.Text)
            width = float(self.txtWidth.Text)
            height = float(self.txtHeight.Text)
            length = float(self.txtLength.Text)
            color = DB.ColorWithTransparency(
                int(self.txtRed.Text),
                int(self.txtGreen.Text),
                int(self.txtBlue.Text),
                int(self.txtTransp.Text)
            )

        except ValueError:
            forms.alert("Input value invalid!", sub_msg=traceback.format_exc())
            return

        bb = DB.BoundingBoxXYZ()
        bb.Min = DB.XYZ(
            - width / 2,
            - length / 2,
            - height / 2,
        )
        bb.Max = DB.XYZ(
            width / 2,
            length / 2,
            height / 2,
        )

        bb.Transform = DB.Transform.CreateTranslation(
            DB.XYZ(x, y, z)
        )

        mesh = revit.dc3dserver.Mesh.from_boundingbox(
            bb,
            color
        )

        self.server.meshes = [mesh]
        uidoc.RefreshActiveView()

    def button_select(self, sender, args):
        element = revit.pick_element()
        geometry = revit.query.get_geometry(element)

        mesh = []
        for geo in geometry:
            if not isinstance(geo, DB.Solid) or geo.Volume == 0:
                continue
            solid_mesh = revit.dc3dserver.Mesh.from_solid(doc, geo)
            if not solid_mesh:
                continue
            mesh.append(solid_mesh)

        self.server.meshes = mesh
        uidoc.RefreshActiveView()

ui = UI("ui.xaml")
ui.show(modal=False)
