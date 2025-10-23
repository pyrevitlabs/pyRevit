# -*- coding: utf-8 -*-
# type: ignore
"""Section Box Navigator - Modeless window for section box navigation."""
import pickle
from pyrevit import revit, script, forms, DB, UI, traceback
from pyrevit.framework import System, List, Math
from pyrevit.revit import events
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

# --------------------
# Initialize Variables
# --------------------

uidoc = revit.uidoc
doc = revit.doc
active_view = revit.active_view

logger = script.get_logger()
output = script.get_output()
output.close_others()

datafile = script.get_document_data_file("SectionBox", "pym")

length_format = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length)
length_unit = length_format.GetUnitTypeId()
length_unit_label = DB.LabelUtils.GetLabelForUnit(length_unit)
ufu = DB.UnitFormatUtils

# --------------------
# Helper Functions
# --------------------


def get_all_levels():
    """Get all levels sorted by elevation."""
    return sorted(
        list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()),
        key=lambda x: x.Elevation,
    )


def get_next_level_above(z_coordinate, all_levels, tolerance=1e-5):
    """Get the next level above the given Z coordinate."""
    for level in all_levels:
        if level.Elevation > z_coordinate + tolerance:
            return level, level.Elevation
    return None, None


def get_next_level_below(z_coordinate, all_levels, tolerance=1e-5):
    """Get the next level below the given Z coordinate."""
    for level in reversed(all_levels):
        if level.Elevation < z_coordinate - tolerance:
            return level, level.Elevation
    return None, None


def get_section_box_info(view):
    """Get section box information from the current view."""
    if not view.IsSectionBoxActive:
        with open(datafile, "rb") as f:
            view_boxes = pickle.load(f)
        bbox_data = view_boxes[get_elementid_value(view.Id)]
        section_box = revit.deserialize(bbox_data)
    else:
        section_box = view.GetSectionBox()
    transform = section_box.Transform
    min_point = section_box.Min
    max_point = section_box.Max

    transformed_min = transform.OfPoint(min_point)
    transformed_max = transform.OfPoint(max_point)

    return {
        "box": section_box,
        "transform": transform,
        "min_point": min_point,
        "max_point": max_point,
        "transformed_min": transformed_min,
        "transformed_max": transformed_max,
    }


def create_preview_mesh(section_box, color):
    """Create a mesh for DC3D preview."""
    try:
        mesh = revit.dc3dserver.Mesh.from_boundingbox(
            section_box, color, black_edges=False
        )
        return mesh
    except Exception:
        logger.error("Error creating preview mesh: {}".format(traceback.format_exc()))
        return None


# --------------------
# Event Handler
# --------------------


class HelperEventHandler(UI.IExternalEventHandler):
    """Event handler for executing Revit API operations."""

    def __init__(self, action):
        self.action = action
        self.parameters = None

    def Execute(self, uiapp):
        try:
            self.action(self.parameters)
        except Exception as ex:
            logger.error("Error in Execute: {}".format(ex))

    def GetName(self):
        return "SectionBoxNavigatorHandler"


# --------------------
# View Changed Monitor
# --------------------


@events.handle("doc-changed")
def on_document_changed(sender, args):
    """Handle document changed events to detect section box changes."""
    try:
        # Check if any view was modified
        modified_element_ids = args.GetModifiedElementIds()

        for elem_id in modified_element_ids:
            elem = doc.GetElement(elem_id)
            if isinstance(elem, DB.View):
                # Check if it's the active view
                if elem.Id == doc.ActiveView.Id:
                    # Trigger update in the form if it exists
                    if hasattr(on_document_changed, "form_instance"):
                        form = on_document_changed.form_instance
                        if form:
                            try:
                                form.Dispatcher.Invoke(System.Action(form.update_info))
                            except Exception:
                                pass
                    break
    except Exception:
        pass


# --------------------
# Main Form
# --------------------


class SectionBoxNavigatorForm(forms.WPFWindow):
    """Modeless form for section box navigation."""

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name, handle_esc=False)

        self.current_view = doc.ActiveView
        self.all_levels = get_all_levels()
        self.preview_server = None
        self.preview_box = None

        # Initialize DC3D Server
        try:
            self.preview_server = revit.dc3dserver.Server(
                uidoc=uidoc,
                name="Section Box Navigator Preview",
                description="Preview for section box adjustments",
            )
        except Exception:
            logger.warning("Could not initialize DC3D server")

        # Setup event handler
        self.event_handler = HelperEventHandler(self.execute_action)
        self.ext_event = UI.ExternalEvent.Create(self.event_handler)
        self.pending_action = None

        # Register this form instance for the event handler
        on_document_changed.form_instance = self

        self.txtNudgeUnit.Text = length_unit_label
        self.txtExpandUnit.Text = length_unit_label
        # Initial update
        self.update_info()

        # Event subscriptions
        self.Closed += self.form_closed

        self.Show()

    def on_view_changed(self):
        """Callback when view changes - kept for compatibility."""
        try:
            self.Dispatcher.Invoke(System.Action(self.update_info))
        except Exception:
            pass

    def update_info(self):
        """Update the information display."""
        try:
            self.current_view = doc.ActiveView

            if not self.current_view.IsSectionBoxActive:
                self.txtTopLevel.Text = "Top: No section box active"
                self.txtTopPosition.Text = ""
                self.txtBottomLevel.Text = "Bottom: No section box active"
                self.txtBottomPosition.Text = ""
                return

            info = get_section_box_info(self.current_view)
            if not info:
                return

            transformed_max = info["transformed_max"]
            transformed_min = info["transformed_min"]

            # Get levels
            top_level, top_level_elevation = get_next_level_above(
                transformed_max.Z, self.all_levels
            )
            bottom_level, bottom_level_elevation = get_next_level_below(
                transformed_min.Z, self.all_levels
            )

            if top_level_elevation:
                top_level_elevation = ufu.Format(
                    doc.GetUnits(), DB.SpecTypeId.Length, top_level_elevation, False
                )
            if bottom_level_elevation:
                bottom_level_elevation = ufu.Format(
                    doc.GetUnits(), DB.SpecTypeId.Length, bottom_level_elevation, False
                )

            # Update top info
            if top_level:
                self.txtTopLevel.Text = "Top: Next level up: {} @ {}".format(
                    top_level.Name, top_level_elevation
                )
            else:
                self.txtTopLevel.Text = "Top: No level above"

            top = ufu.Format(
                doc.GetUnits(), DB.SpecTypeId.Length, transformed_max.Z, False
            )
            self.txtTopPosition.Text = "Position: {}".format(top)

            # Update bottom info
            if bottom_level:
                self.txtBottomLevel.Text = "Bottom: Next level down: {} @ {}".format(
                    bottom_level.Name, bottom_level_elevation
                )
            else:
                self.txtBottomLevel.Text = "Bottom: No level below"

            bottom = ufu.Format(
                doc.GetUnits(), DB.SpecTypeId.Length, transformed_min.Z, False
            )
            self.txtBottomPosition.Text = "Position: {}".format(bottom)

        except Exception:
            logger.error("Error updating info: {}".format(traceback.format_exc()))

    def execute_action(self, params):
        """Execute an action in Revit context."""
        try:
            action_type = params["action"]

            if action_type == "move_to_level":
                self.do_move_to_level(params)
            elif action_type == "nudge":
                self.do_nudge(params)
            elif action_type == "toggle":
                self.do_toggle()
            elif action_type == "hide":
                self.do_hide()
            elif action_type == "align":
                self.do_align()
            elif action_type == "expand_shrink":
                self.do_expand_shrink(params)

            # Update info after action
            self.Dispatcher.Invoke(System.Action(self.update_info))

        except Exception as e:
            logger.error("Error executing action: {}".format(e))

    def do_move_to_level(self, params):
        """Move section box to level."""
        top_level = params.get("top_level")
        bottom_level = params.get("bottom_level")

        info = get_section_box_info(self.current_view)
        if not info:
            return

        adjust_top = top_level is not None
        adjust_bottom = bottom_level is not None

        # Calculate distances
        top_distance = 0
        bottom_distance = 0

        if adjust_top:
            top_distance = top_level.Elevation - info["transformed_max"].Z

        if adjust_bottom:
            bottom_distance = bottom_level.Elevation - info["transformed_min"].Z

        self.adjust_section_box(
            top_distance, bottom_distance, adjust_top, adjust_bottom
        )

    def do_nudge(self, params):
        """Nudge section box."""
        distance_mm = params.get("distance", 0)
        adjust_top = params.get("adjust_top", False)
        adjust_bottom = params.get("adjust_bottom", False)

        self.adjust_section_box(distance_mm, distance_mm, adjust_top, adjust_bottom)

    def do_expand_shrink(self, params):
        """Expand or shrink the section box in all directions."""
        amount = params.get("amount", 0)
        is_expand = params.get("is_expand", True)

        info = get_section_box_info(self.current_view)
        if not info:
            return

        # Get current box dimensions
        min_point = info["min_point"]
        max_point = info["max_point"]
        transform = info["transform"]

        # Calculate the adjustment (negative for shrink)
        adjustment = amount if is_expand else -amount

        # Expand/shrink in all three local directions
        # X direction (left/right)
        new_min_x = min_point.X - adjustment
        new_max_x = max_point.X + adjustment

        # Y direction (front/back)
        new_min_y = min_point.Y - adjustment
        new_max_y = max_point.Y + adjustment

        # Z direction (up/down)
        new_min_z = min_point.Z - adjustment
        new_max_z = max_point.Z + adjustment

        # Validate dimensions
        if new_max_x <= new_min_x or new_max_y <= new_min_y or new_max_z <= new_min_z:
            forms.alert("Section box would become invalid (too small).", title="Error")
            return

        # Create new box
        new_box = DB.BoundingBoxXYZ()
        new_box.Min = DB.XYZ(new_min_x, new_min_y, new_min_z)
        new_box.Max = DB.XYZ(new_max_x, new_max_y, new_max_z)
        new_box.Transform = transform

        with revit.Transaction("Expand/Shrink Section Box"):
            self.current_view.SetSectionBox(new_box)

    def do_toggle(self):
        """Toggle section box."""
        self.current_view = doc.ActiveView
        current_view_id_value = get_elementid_value(self.current_view.Id)
        sectionbox_active_state = self.current_view.IsSectionBoxActive

        try:
            with open(datafile, "rb") as f:
                view_boxes = pickle.load(f)
        except Exception:
            view_boxes = {}

        with revit.Transaction("Toggle SectionBox"):
            if sectionbox_active_state:
                try:
                    sectionbox = self.current_view.GetSectionBox()
                    if sectionbox:
                        view_boxes[current_view_id_value] = revit.serialize(sectionbox)
                        with open(datafile, "wb") as f:
                            pickle.dump(view_boxes, f)
                    self.current_view.IsSectionBoxActive = False
                except Exception as ex:
                    logger.error("Error saving section box: {}".format(ex))
            else:
                try:
                    if current_view_id_value in view_boxes:
                        bbox_data = view_boxes[current_view_id_value]
                        restored_bbox = revit.deserialize(bbox_data)
                        self.current_view.SetSectionBox(restored_bbox)
                except Exception as ex:
                    logger.error(
                        "No saved section box found or failed to load: {}".format(ex)
                    )

    def do_hide(self):
        """Hide or Unhide section box."""
        self.current_view = doc.ActiveView
        with revit.Transaction("Toggle SB visbility"):
            self.current_view.EnableRevealHiddenMode()
            view_elements = (
                DB.FilteredElementCollector(revit.doc, self.current_view.Id)
                .OfCategory(DB.BuiltInCategory.OST_SectionBox)
                .ToElements()
            )
            for sec_box in [
                x for x in view_elements if x.CanBeHidden(self.current_view)
            ]:
                if sec_box.IsHidden(self.current_view):
                    self.current_view.UnhideElements(List[DB.ElementId]([sec_box.Id]))
                else:
                    self.current_view.HideElements(List[DB.ElementId]([sec_box.Id]))

            self.current_view.DisableTemporaryViewMode(
                DB.TemporaryViewMode.RevealHiddenElements
            )

    def do_align(self):
        """Align to face"""
        self.current_view = doc.ActiveView
        try:
            world_normal = None

            with forms.WarningBar(title="Pick a face on a solid object"):
                reference = uidoc.Selection.PickObject(
                    UI.Selection.ObjectType.PointOnElement,
                    "Pick a face on a solid object",
                )

            instance = doc.GetElement(reference.ElementId)
            picked_point = reference.GlobalPoint

            if isinstance(instance, DB.RevitLinkInstance):
                linked_doc = instance.GetLinkDocument()
                linked_element_id = reference.LinkedElementId
                element = linked_doc.GetElement(linked_element_id)
                transform = instance.GetTransform()
            else:
                element = instance
                transform = DB.Transform.Identity

            # Get geometry
            options = DB.Options()
            options.ComputeReferences = True
            options.IncludeNonVisibleObjects = True
            options.DetailLevel = self.current_view.DetailLevel

            geom_elem = element.get_Geometry(options)

            def extract_solids(geom_element):
                solids = []
                for geom_obj in geom_element:
                    if isinstance(geom_obj, DB.Solid) and geom_obj.Faces.Size > 0:
                        solids.append(geom_obj)
                    elif isinstance(geom_obj, DB.GeometryInstance):
                        solids.extend(extract_solids(geom_obj.GetInstanceGeometry()))
                return solids

            solids = extract_solids(geom_elem)

            # Find face that contains the picked point
            target_face = None
            for solid in solids:
                for face in solid.Faces:
                    try:
                        result = face.Project(picked_point)
                        if result and result.XYZPoint.DistanceTo(picked_point) < 1e-6:
                            target_face = face
                            break
                    except Exception:
                        continue
                if target_face:
                    break

            if not target_face:
                forms.alert(
                    "Couldn't find a face at the picked point.", exitscript=True
                )

            local_normal = target_face.ComputeNormal(DB.UV(0.5, 0.5)).Normalize()
            world_normal = transform.OfVector(local_normal).Normalize()

            # --- Orient section box ---
            box = self.current_view.GetSectionBox()
            box_normal = box.Transform.BasisX.Normalize()
            angle = world_normal.AngleTo(box_normal)

            # Choose rotation axis - Z axis in world coordinates
            axis = DB.XYZ(0, 0, 1.0)
            origin = DB.XYZ(
                box.Min.X + (box.Max.X - box.Min.X) / 2,
                box.Min.Y + (box.Max.Y - box.Min.Y) / 2,
                box.Min.Z,
            )

            if world_normal.Y * box_normal.X < 0:
                rotate = DB.Transform.CreateRotationAtPoint(
                    axis, Math.PI / 2 - angle, origin
                )
            else:
                rotate = DB.Transform.CreateRotationAtPoint(axis, angle, origin)

            box.Transform = box.Transform.Multiply(rotate)

            with revit.Transaction("Orient Section Box to Face"):
                self.current_view.SetSectionBox(box)
                uidoc.RefreshActiveView()

        except Exception as ex:
            logger.error("Error: {}".format(str(ex)))

    def adjust_section_box(
        self, distance_top, distance_bottom, adjust_top=True, adjust_bottom=False
    ):
        """Adjust the section box."""
        info = get_section_box_info(self.current_view)
        if not info:
            return False

        transform = info["transform"]
        min_point = info["min_point"]
        max_point = info["max_point"]

        # Create new points
        new_min_point = DB.XYZ(
            min_point.X,
            min_point.Y,
            min_point.Z + distance_bottom if adjust_bottom else min_point.Z,
        )

        new_max_point = DB.XYZ(
            max_point.X,
            max_point.Y,
            max_point.Z + distance_top if adjust_top else max_point.Z,
        )

        # Validate
        if new_max_point.Z <= new_min_point.Z:
            forms.alert("Invalid section box dimensions.", title="Error")
            return False

        # Create new box
        new_box = DB.BoundingBoxXYZ()
        new_box.Min = new_min_point
        new_box.Max = new_max_point
        new_box.Transform = transform

        with revit.Transaction("Adjust Section Box"):
            self.current_view.SetSectionBox(new_box)

        return True

    def show_preview(self, preview_type="nudge", params=None):
        """Show preview of adjusted section box."""
        if not self.preview_server or not self.chkPreview.IsChecked:
            return

        try:
            info = get_section_box_info(self.current_view)
            if not info:
                return

            transform = info["transform"]
            min_point = info["min_point"]
            max_point = info["max_point"]

            # Initialize preview points
            preview_min = min_point
            preview_max = max_point

            if preview_type == "nudge":
                # Handle nudge preview
                distance_top = params.get("distance_top", 0)
                distance_bottom = params.get("distance_bottom", 0)
                adjust_top = params.get("adjust_top", False)
                adjust_bottom = params.get("adjust_bottom", False)

                preview_min = DB.XYZ(
                    min_point.X,
                    min_point.Y,
                    min_point.Z + distance_bottom if adjust_bottom else min_point.Z,
                )

                preview_max = DB.XYZ(
                    max_point.X,
                    max_point.Y,
                    max_point.Z + distance_top if adjust_top else max_point.Z,
                )

            elif preview_type == "level":
                # Handle level-based preview
                distance_top = params.get("distance_top", 0)
                distance_bottom = params.get("distance_bottom", 0)
                adjust_top = params.get("adjust_top", False)
                adjust_bottom = params.get("adjust_bottom", False)

                preview_min = DB.XYZ(
                    min_point.X,
                    min_point.Y,
                    min_point.Z + distance_bottom if adjust_bottom else min_point.Z,
                )

                preview_max = DB.XYZ(
                    max_point.X,
                    max_point.Y,
                    max_point.Z + distance_top if adjust_top else max_point.Z,
                )

            elif preview_type == "expand_shrink":
                # Handle expand/shrink preview
                adjustment = params.get("adjustment", 0)

                preview_min = DB.XYZ(
                    min_point.X - adjustment,
                    min_point.Y - adjustment,
                    min_point.Z - adjustment,
                )

                preview_max = DB.XYZ(
                    max_point.X + adjustment,
                    max_point.Y + adjustment,
                    max_point.Z + adjustment,
                )

            # Validate preview box dimensions
            if (
                preview_max.X <= preview_min.X
                or preview_max.Y <= preview_min.Y
                or preview_max.Z <= preview_min.Z
            ):
                return

            # Create preview box
            preview_box = DB.BoundingBoxXYZ()
            preview_box.Min = preview_min
            preview_box.Max = preview_max
            preview_box.Transform = transform

            # Create mesh with semi-transparent color
            color = DB.ColorWithTransparency(100, 150, 255, 150)
            mesh = create_preview_mesh(preview_box, color)

            if mesh:
                self.preview_server.meshes = [mesh]
                uidoc.RefreshActiveView()

        except Exception:
            logger.error("Error showing preview: {}".format(traceback.format_exc()))

    def hide_preview(self):
        """Hide the preview."""
        if self.preview_server:
            try:
                self.preview_server.meshes = []
                uidoc.RefreshActiveView()
            except Exception:
                pass

    # Button Handlers

    def btn_top_up_click(self, sender, e):
        """Move top up to next level."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_level, _ = get_next_level_above(info["transformed_max"].Z, self.all_levels)
        if not next_level:
            forms.alert("No level found above", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_level,
            "bottom_level": None,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_top_down_click(self, sender, e):
        """Move top down to next level."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_level, _ = get_next_level_below(info["transformed_max"].Z, self.all_levels)
        if not next_level:
            forms.alert("No level found below", title="Error")
            return

        if next_level.Elevation <= info["transformed_min"].Z:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_level,
            "bottom_level": None,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_bottom_up_click(self, sender, e):
        """Move bottom up to next level."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_level, _ = get_next_level_above(info["transformed_min"].Z, self.all_levels)
        if not next_level:
            forms.alert("No level found above", title="Error")
            return

        if next_level.Elevation >= info["transformed_max"].Z:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": None,
            "bottom_level": next_level,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_bottom_down_click(self, sender, e):
        """Move bottom down to next level."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_level, _ = get_next_level_below(info["transformed_min"].Z, self.all_levels)
        if not next_level:
            forms.alert("No level found below", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": None,
            "bottom_level": next_level,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_box_up_click(self, sender, e):
        """Move entire box up to next levels."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_top, _ = get_next_level_above(info["transformed_max"].Z, self.all_levels)
        next_bottom, _ = get_next_level_above(
            info["transformed_min"].Z, self.all_levels
        )

        if not next_top or not next_bottom:
            forms.alert("Cannot find levels above", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_top,
            "bottom_level": next_bottom,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_box_down_click(self, sender, e):
        """Move entire box down to next levels."""
        info = get_section_box_info(self.current_view)
        if not info:
            return

        next_top, _ = get_next_level_below(info["transformed_max"].Z, self.all_levels)
        next_bottom, _ = get_next_level_below(
            info["transformed_min"].Z, self.all_levels
        )

        if not next_top or not next_bottom:
            forms.alert("Cannot find levels below", title="Error")
            return

        if next_top.Elevation <= next_bottom.Elevation:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_top,
            "bottom_level": next_bottom,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_nudge_top_up_click(self, sender, e):
        """Nudge top up."""
        try:
            distance = float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": True,
                "adjust_bottom": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid nudge amount", title="Error")

    def btn_nudge_top_down_click(self, sender, e):
        """Nudge top down."""
        try:
            distance = -float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": True,
                "adjust_bottom": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid nudge amount", title="Error")

    def btn_nudge_bottom_up_click(self, sender, e):
        """Nudge bottom up."""
        try:
            distance = float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": False,
                "adjust_bottom": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid nudge amount", title="Error")

    def btn_nudge_bottom_down_click(self, sender, e):
        """Nudge bottom down."""
        try:
            distance = -float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": False,
                "adjust_bottom": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid nudge amount", title="Error")

    def btn_expansion_top_up_click(self, sender, e):
        """Expand the section box."""
        try:
            amount = float(self.txtExpandAmount.Text)
            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)
            self.pending_action = {
                "action": "expand_shrink",
                "amount": amount,
                "is_expand": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid expansion amount", title="Error")

    def btn_expansion_top_down_click(self, sender, e):
        """Shrink the section box."""
        try:
            amount = float(self.txtExpandAmount.Text)
            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)
            self.pending_action = {
                "action": "expand_shrink",
                "amount": amount,
                "is_expand": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert("Invalid expansion amount", title="Error")

    def btn_preview_nudge_enter(self, sender, e):
        """Show preview when hovering over nudge buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            distance = float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)

            button_content = sender.Content
            adjust_top = "Top" in button_content
            adjust_bottom = "Bottom" in button_content

            if "-" in button_content:
                distance = -distance

            params = {
                "distance_top": distance,
                "distance_bottom": distance,
                "adjust_top": adjust_top,
                "adjust_bottom": adjust_bottom,
            }
            self.show_preview("nudge", params)
        except Exception:
            pass

    def btn_preview_level_box_enter(self, sender, e):
        """Show preview when hovering over level buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            info = get_section_box_info(self.current_view)
            if not info:
                return

            button_content = sender.Content

            # Determine which button was hovered
            is_top = "Top" in button_content
            is_bottom = "Bottom" in button_content
            is_box = "Box" in button_content
            is_up = "↑" in button_content

            distance_top = 0
            distance_bottom = 0
            adjust_top = False
            adjust_bottom = False

            if is_box:
                # Box up or down - move both
                if is_up:
                    next_top, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels
                    )
                    next_bottom, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels
                    )
                    if next_top and next_bottom:
                        distance_top = next_top.Elevation - info["transformed_max"].Z
                        distance_bottom = (
                            next_bottom.Elevation - info["transformed_min"].Z
                        )
                        adjust_top = True
                        adjust_bottom = True
                else:
                    next_top, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels
                    )
                    next_bottom, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels
                    )
                    if next_top and next_bottom:
                        distance_top = next_top.Elevation - info["transformed_max"].Z
                        distance_bottom = (
                            next_bottom.Elevation - info["transformed_min"].Z
                        )
                        adjust_top = True
                        adjust_bottom = True
            elif is_top:
                # Top up or down
                if is_up:
                    next_level, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels
                    )

                if next_level:
                    distance_top = next_level.Elevation - info["transformed_max"].Z
                    adjust_top = True
            elif is_bottom:
                # Bottom up or down
                if is_up:
                    next_level, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels
                    )

                if next_level:
                    distance_bottom = next_level.Elevation - info["transformed_min"].Z
                    adjust_bottom = True

            if adjust_top or adjust_bottom:
                params = {
                    "distance_top": distance_top,
                    "distance_bottom": distance_bottom,
                    "adjust_top": adjust_top,
                    "adjust_bottom": adjust_bottom,
                }
                self.show_preview("level", params)

        except Exception:
            pass

    def btn_preview_expansion_enter(self, sender, e):
        """Show preview when hovering over expansion buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            amount = float(self.txtExpandAmount.Text)
            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)

            button_content = sender.Content
            is_expand = "Expand" in button_content

            # Calculate adjustment (negative for shrink)
            adjustment = amount if is_expand else -amount

            params = {
                "adjustment": adjustment,
            }
            self.show_preview("expand_shrink", params)

        except Exception:
            pass

    def btn_preview_enter(self, sender, e):
        """Show preview when hovering over buttons."""
        if not self.chkPreview.IsChecked:
            return
        try:
            params = {
                "distance_top": 0,
                "distance_bottom": 0,
                "adjust_top": 0,
                "adjust_bottom": 0,
            }
            self.show_preview("nudge", params)
        except Exception:
            pass

    def btn_preview_leave(self, sender, e):
        """Hide preview when leaving buttons."""
        self.hide_preview()

    def btn_toggle_box_click(self, sender, e):
        """Toggle section box - to be implemented by user."""
        self.pending_action = {
            "action": "toggle",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_hide_box_click(self, sender, e):
        """Toggle section box - to be implemented by user."""
        self.pending_action = {
            "action": "hide",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_align_box_click(self, sender, e):
        """Toggle section box - to be implemented by user."""
        self.pending_action = {
            "action": "align",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_refresh_click(self, sender, e):
        """Manually refresh the information."""
        self.all_levels = get_all_levels()
        self.update_info()

    def form_closed(self, sender, args):
        """Cleanup when form is closed."""
        try:
            # Unregister event handlers
            events.stop_events()

            # Clear form instance reference
            on_document_changed.form_instance = None

            # Remove DC3D server
            if self.preview_server:
                try:
                    self.preview_server.remove_server()
                except Exception:
                    pass

            # Refresh view
            try:
                uidoc.RefreshActiveView()
            except Exception:
                pass

        except Exception:
            logger.error("Error during cleanup: {}".format(traceback.format_exc()))


# ---------
# Run main
# ---------

if __name__ == "__main__":
    try:
        # Check if section box is active
        if not active_view.IsSectionBoxActive:
            try:
                with open(datafile, "rb") as f:
                    view_boxes = pickle.load(f)
                bbox_data = view_boxes[get_elementid_value(active_view.Id)]
                restored_bbox = revit.deserialize(bbox_data)
            except Exception:
                forms.alert(
                    "The current view does not have an active section box.",
                    title="No Section Box",
                    exitscript=True,
                )
            forms.alert(
                "Stored SectionBox for this view found! Restore?",
                cancel=True,
                exitscript=True,
            )
            with revit.Transaction("Restore SectionBox"):
                active_view.SetSectionBox(restored_bbox)

        # Launch the form
        form = SectionBoxNavigatorForm("SectionBoxNavigator.xaml")

    except Exception as e:
        logger.error("Error launching form: {}".format(e))
        forms.alert("An error occurred: {}".format(str(e)), title="Error")
