"""Pickup painted surface material and apply to other surfaces."""
#pylint: disable=E0401,C0111,W0613,C0103,broad-except
from pyrevit import revit, UI
from pyrevit import forms
from pyrevit import script

logger = script.get_logger()

with forms.WarningBar(title='Pick source object:'):
    source_face = revit.pick_face()


if source_face:
    material_id = source_face.MaterialElementId
    material = revit.doc.GetElement(material_id)

    logger.debug('Selected material id:%s name:%s', material.Id, material.Name)

    with forms.WarningBar(title='Pick faces to match materials:'):
        while True:
            try:
                dest_ref = \
                    revit.uidoc.Selection.PickObject(
                        UI.Selection.ObjectType.Face
                        )
            except Exception:
                break

            if not dest_ref:
                break

            dest_element = revit.doc.GetElement(dest_ref)
            dest_face = dest_element.GetGeometryObjectFromReference(dest_ref)

            with revit.Transaction('Match Painted Materials'):
                revit.doc.Paint(dest_element.Id,
                                dest_face,
                                material_id)
