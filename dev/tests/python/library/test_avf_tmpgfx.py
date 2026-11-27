"""Host-free tests for ``pyrevit.revit.avf`` and ``tmpgfx``.

Loads both modules with the Revit modules stubbed. The cases marked
``regression`` come from a live Revit 2026 run on 2026-11-27: face selection
returned only faces turned away from the viewer, the reference of such a face
crashed Revit in a plan view, ``display_avf_values_at_points`` raised
``NameError``, and every temporary graphics handler dispatched clicks on
controls it did not own. The remaining cases cover the contracts of
``avf.show_values`` and ``tmpgfx.get_manager``.
"""

import hashlib
import importlib.util
import json
import pathlib
import struct
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ROOT = pathlib.Path(__file__).resolve().parents[4]
LIBRARY = ROOT / "pyrevitlib" / "pyrevit" / "revit"
ICON = (
    ROOT
    / "extensions"
    / "pyRevitDevTools.extension"
    / "pyRevitDev.tab"
    / "Developer Examples.panel"
    / "TemporaryGraphics.pushbutton"
    / "warning.bmp"
)


class XYZ:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z

    def __add__(self, other):
        return XYZ(self.X + other.X, self.Y + other.Y, self.Z + other.Z)

    def __truediv__(self, factor):
        return XYZ(self.X / factor, self.Y / factor, self.Z / factor)

    def Normalize(self):
        return self

    def DotProduct(self, other):
        return self.X * other.X + self.Y * other.Y + self.Z * other.Z


class UV:
    def __init__(self, u, v):
        self.U, self.V = u, v


class Face:
    def __init__(self, name, normal, area=10.0, reference="reference", inside=None):
        self.name = name
        self.normal = normal
        self.Area = area
        self.Reference = reference and "{} of {}".format(reference, name)
        self.inside = inside

    def GetBoundingBox(self):
        return types.SimpleNamespace(Min=UV(0.0, 0.0), Max=UV(2.0, 4.0))

    def ComputeNormal(self, uv):
        return self.normal

    def IsInside(self, uv):
        return self.inside is None or self.inside(uv)


class Solid:
    def __init__(self, *faces):
        self.Faces = list(faces)


class ElementId:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, ElementId) and other.value == self.value

    def __hash__(self):
        return hash(self.value)


class Document:
    def __init__(self, number=1):
        self.number = number
        self.elements = {}
        self.IsValidObject = True

    def GetHashCode(self):
        return self.number

    def GetElement(self, element_id):
        return self.elements.get(element_id.value)

    def Equals(self, other):
        return other is self


class View:
    def __init__(self):
        self.Name = "view"
        self.Document = Document()
        self.ViewDirection = XYZ(0.0, 0.0, 1.0)
        self.DetailLevel = "Fine"
        self.AnalysisDisplayStyleId = None
        self.allows_analysis = True
        self.visible_ids = {1}
        self.collector_count = 0

    def AllowsAnalysisDisplay(self):
        return self.allows_analysis

    def collect(self):
        self.collector_count += 1
        return Collector(self.visible_ids)


class View3D(View):
    IsSectionBoxActive = False
    IsPerspective = False


class Element:
    def __init__(self, *faces, **options):
        self.Id = ElementId(options.get("element_id", 1))
        self.geometry = [Solid(*faces)]
        self.get_geometry_error = None
        self.journal = None
        self.Document = None

    def get_BoundingBox(self, view):
        if self.journal is not None:
            self.journal.append("read")
        return types.SimpleNamespace(Min=XYZ(0.0, 0.0, 0.0), Max=XYZ(2.0, 2.0, 2.0))


class NetList(list):
    def __class_getitem__(cls, item):
        return cls

    def Add(self, item):
        self.append(item)


class Schema:
    def __init__(self, name, description):
        self.Name = name
        self.description = description
        self.units = []
        self.IsVisible = True

    def SetUnits(self, names, multipliers):
        if any(multiplier <= 0 for multiplier in multipliers):
            raise ValueError("must be positive")
        self.units = list(names)
        self.multipliers = list(multipliers)

    @property
    def Description(self):
        return self.description

    def GetNumberOfUnits(self):
        return len(self.units)

    def GetUnitsName(self, index):
        return self.units[index]

    def GetUnitsMultiplier(self, index):
        return self.multipliers[index]


class SpatialFieldManager:
    """Numbers results and primitives from one counter that never goes back."""

    def __init__(self, journal=None):
        self.journal = [] if journal is None else journal
        self.anchors = []
        self.updates = []
        self.rejects_references = False
        self.rejects_values = False
        self.schemas = {}
        self.primitives = {}
        self.measurement_names = None
        self.counter = 0
        self.created = False

    def next_number(self):
        self.counter += 1
        return self.counter

    def SetMeasurementNames(self, names):
        self.measurement_names = list(names)

    def GetRegisteredResults(self):
        return list(self.schemas)

    def GetResultSchema(self, index):
        return self.schemas[index]

    def SetResultSchema(self, index, schema):
        self.schemas[index] = schema

    def RegisterResult(self, schema):
        index = self.next_number()
        self.schemas[index] = schema
        return index

    def AddSpatialFieldPrimitive(self, *anchor):
        if anchor and self.rejects_references:
            raise ValueError("must point to either Face or Curve visible in the view")
        self.anchors.append(anchor)
        self.journal.append("add")
        number = self.next_number()
        self.primitives[number] = None
        return number

    def UpdateSpatialFieldPrimitive(self, primitive, points, values, schema):
        if self.rejects_values:
            raise ValueError("value rejected")
        self.updates.append((primitive, points, values, schema))
        self.primitives[primitive] = (schema, values.args[0][0].args[0][0])

    def RemoveSpatialFieldPrimitive(self, primitive):
        del self.primitives[primitive]

    def Clear(self):
        self.schemas.clear()
        self.primitives.clear()

    def values_of(self, name):
        return sorted(
            value
            for schema, value in self.primitives.values()
            if self.schemas[schema].Name == name
        )


class Collector:
    def __init__(self, view_ids):
        self.view_ids = view_ids

    def WherePasses(self, wanted):
        self.wanted = {element_id.value for element_id in wanted}
        return self

    def ToElementIds(self):
        return [ElementId(number) for number in self.view_ids & self.wanted]


class DisplayStyle:
    def __init__(self, name, kind):
        self.Name = name
        self.Id = name
        self.kind = kind
        self.settings = types.SimpleNamespace(MarkerSize=1.0 / 96)

    def GetMarkersAndTextSettings(self):
        return self.settings

    def SetMarkersAndTextSettings(self, settings):
        self.settings = settings


class AppDomainStub:
    def __init__(self):
        self.data = {}
        self.CurrentDomain = self

    def GetData(self, slot):
        return self.data.get(slot)

    def SetData(self, slot, value):
        self.data[slot] = value


class Context:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def stub_module(name, **members):
    module = types.ModuleType(name)
    module.__dict__.update(members)
    return module


def load(module_name, stubs):
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            "stubbed_" + module_name, LIBRARY / (module_name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def load_avf(sfm, view):
    def record(*args, **kwargs):
        return types.SimpleNamespace(args=args)

    def manager_of(target):
        return sfm if sfm.created else None

    def create_manager(target, count):
        sfm.created = True
        return sfm

    def style_factory(kind):
        def create(doc, name, *settings):
            style = DisplayStyle(name, kind)
            styles.append(style)
            return style

        return create

    styles = []
    db = types.SimpleNamespace(
        UV=UV,
        XYZ=XYZ,
        Solid=Solid,
        View3D=View3D,
        ElementId=ElementId,
        ViewDetailLevel=types.SimpleNamespace(
            Coarse="Coarse", Medium="Medium", Fine="Fine", Undefined="Undefined"
        ),
        ElementIdSetFilter=lambda ids: list(ids),
        FilteredElementCollector=lambda doc, view_id: view.collect(),
        Analysis=types.SimpleNamespace(
            SpatialFieldManager=types.SimpleNamespace(
                GetSpatialFieldManager=manager_of,
                CreateSpatialFieldManager=create_manager,
            ),
            AnalysisResultSchema=Schema,
            ValueAtPoint=record,
            FieldValues=record,
            FieldDomainPointsByXYZ=lambda points: ("xyz", points),
            FieldDomainPointsByUV=lambda points: ("uv", points),
        ),
    )
    view.Id = ElementId(99)
    logger = types.SimpleNamespace(
        warning=lambda *a: None,
        error=lambda *a: None,
        debug=lambda *a: None,
        exception=lambda message, *a: pytest.fail(message),
    )

    def get_geometry(element, **options):
        if element.get_geometry_error:
            raise element.get_geometry_error
        return element.geometry

    query = types.SimpleNamespace(
        get_geometry=get_geometry,
        get_elements_by_class=lambda *a, **k: [],
        get_name=lambda item: item.Name,
    )
    stubs = {
        "pyrevit": stub_module(
            "pyrevit",
            DB=db,
            HOST_APP=types.SimpleNamespace(uidoc=None),
            PyRevitException=RuntimeError,
        ),
        "pyrevit.revit": stub_module("pyrevit.revit", Transaction=Context, query=query),
        "pyrevit.framework": stub_module(
            "pyrevit.framework",
            AppDomain=AppDomainStub(),
            List=NetList,
            System=types.SimpleNamespace(String=str, Double=float),
        ),
        "pyrevit.coreutils": stub_module("pyrevit.coreutils"),
        "pyrevit.coreutils.logger": stub_module(
            "pyrevit.coreutils.logger", get_logger=lambda name: logger
        ),
        "pyrevit.compat": stub_module(
            "pyrevit.compat",
            get_elementid_value_func=lambda: lambda element_id: element_id.value,
            get_elementid_from_value_func=lambda: ElementId,
        ),
    }
    module = load("avf", stubs)
    module.get_or_create_marker_display_style = style_factory("marker")
    module.get_or_create_colored_surface_display_style = style_factory("colored")
    module.created_styles = styles
    return module


def slab(reference="reference", element_id=1):
    return Element(
        Face("underside", XYZ(0.0, 0.0, -1.0), area=20.0, reference=reference),
        Face("edge", XYZ(1.0, 0.0, 0.0), area=30.0, reference=reference),
        Face("top", XYZ(0.0, 0.0, 1.0), reference=reference),
        element_id=element_id,
    )


@pytest.mark.regression
class DisplayTests(unittest.TestCase):
    def display(self, view, element=None, sfm=None, **options):
        sfm = sfm or SpatialFieldManager()
        avf = load_avf(sfm, view)
        results = avf.display_avf_values({element or slab(): 1.0}, view, **options)
        self.assertEqual([1], list(results))
        self.assertTrue(results[1][0])
        return sfm

    def assert_point_anchor(self, sfm):
        self.assertEqual([()], sfm.anchors)
        kind, points = sfm.updates[0][1]
        self.assertEqual("xyz", kind)
        self.assertEqual((1.0, 1.0, 1.0), (points[0].X, points[0].Y, points[0].Z))

    def test_face_selection_returns_the_face_turned_toward_the_viewer(self):
        avf = load_avf(SpatialFieldManager(), View3D())
        face = avf.get_face_facing_direction(slab(), XYZ(0.0, 0.0, 1.0))
        self.assertEqual("top", face.name)

    def test_open_3d_view_anchors_to_the_visible_face(self):
        sfm = self.display(View3D())
        self.assertEqual([("reference of top",)], sfm.anchors)
        self.assertEqual("uv", sfm.updates[0][1][0])

    def test_2d_view_never_passes_a_face_to_revit(self):
        self.assert_point_anchor(self.display(View()))

    def test_section_box_never_passes_a_face_to_revit(self):
        view = View3D()
        view.IsSectionBoxActive = True
        self.assert_point_anchor(self.display(view))

    def test_perspective_view_never_passes_a_face_to_revit(self):
        view = View3D()
        view.IsPerspective = True
        self.assert_point_anchor(self.display(view))

    def test_unreadable_face_still_places_a_point(self):
        element = slab()
        element.geometry = None
        element.get_geometry_error = ValueError("no geometry for you")
        self.assert_point_anchor(self.display(View3D(), element))

    def test_hidden_element_never_passes_a_face_to_revit(self):
        view = View3D()
        view.visible_ids = set()
        self.assert_point_anchor(self.display(view))

    def test_face_without_reference_uses_a_point(self):
        self.assert_point_anchor(self.display(View3D(), slab(reference=None)))

    def test_rejected_face_reference_falls_back_to_a_point(self):
        sfm = SpatialFieldManager()
        sfm.rejects_references = True
        self.assert_point_anchor(self.display(View3D(), sfm=sfm))

    def test_visibility_is_queried_once_per_call(self):
        view = View3D()
        view.visible_ids = {1, 2, 3}
        avf = load_avf(SpatialFieldManager(), view)
        elements = [slab(element_id=number) for number in (1, 2, 3)]
        results = avf.display_avf_values(dict.fromkeys(elements, 1.0), view)
        self.assertEqual(3, sum(success for success, _ in results.values()))
        self.assertEqual(1, view.collector_count)

    def test_no_element_is_read_after_the_first_primitive_is_added(self):
        view = View3D()
        view.visible_ids = {1, 2, 3}
        journal = []
        avf = load_avf(SpatialFieldManager(journal), view)
        elements = [slab(element_id=number) for number in (1, 2, 3)]
        for element in elements:
            element.journal = journal
        avf.display_avf_values(dict.fromkeys(elements, 1.0), view)
        self.assertEqual(["read"] * 3 + ["add"] * 3, journal)

    def test_bbox_center_can_be_forced(self):
        self.assert_point_anchor(self.display(View3D(), use_bbox_center=True))

    def test_values_at_points_are_chunked_into_primitives(self):
        sfm = SpatialFieldManager()
        view = View()
        avf = load_avf(sfm, view)
        pairs = [(XYZ(float(i), 0.0, 0.0), float(i)) for i in range(5)]
        created = avf.display_avf_values_at_points(
            pairs, view, max_points_per_primitive=2
        )
        self.assertEqual(3, len(created))
        self.assertEqual([2, 2, 1], [len(update[1][1]) for update in sfm.updates])


class ShowValuesCase(unittest.TestCase):
    view_type = View

    def setUp(self):
        self.view = self.view_type()
        self.sfm = SpatialFieldManager()
        self.avf = load_avf(self.sfm, self.view)
        self.view.visible_ids = {1, 2, 3}
        self.elements = []
        for number in (1, 2, 3):
            element = slab(element_id=number)
            element.Document = self.view.Document
            self.view.Document.elements[number] = element
            self.elements.append(element)

    def show(self, values, **options):
        return self.avf.show_values(self.view, values, **options)


class ShowValuesTests(ShowValuesCase):
    def test_repeating_a_name_replaces_its_values(self):
        self.show({1: 10, 2: 20}, name="A")
        report = self.show({1: 11}, name="A", unit="min")
        self.assertEqual(2, report["removed"])
        self.assertEqual([11.0], self.sfm.values_of("A"))
        self.assertEqual(1, len(self.sfm.schemas))
        self.assertEqual(["min"], list(self.sfm.schemas.values())[0].units)

    def test_empty_values_remove_the_name(self):
        self.show({1: 10}, name="A")
        self.assertEqual(1, self.show({}, name="A")["removed"])
        self.assertEqual([], self.sfm.values_of("A"))

    def test_other_names_stay(self):
        self.show({1: 10}, name="A")
        self.show({2: 20}, name="B")
        self.assertEqual(1, self.avf.clear_values(self.view, "A"))
        self.assertEqual(0, self.avf.clear_values(self.view, "A"))
        self.assertEqual([20.0], self.sfm.values_of("B"))

    def test_values_cleared_elsewhere_are_forgotten_not_removed(self):
        self.show({1: 10}, name="A")
        self.sfm.Clear()
        foreign = self.sfm.AddSpatialFieldPrimitive()
        self.assertEqual(0, self.avf.clear_values(self.view, "A"))
        self.assertIn(foreign, self.sfm.primitives)
        report = self.show({1: 12}, name="A")
        self.assertEqual((0, False), (report["removed"], report["untracked_result"]))

    def test_a_result_added_some_other_way_is_reported(self):
        self.avf.display_avf_values({self.elements[0]: 1.0}, self.view, schema_name="A")
        self.assertTrue(self.show({2: 2}, name="A")["untracked_result"])
        self.assertFalse(self.show({2: 3}, name="A")["untracked_result"])
        self.assertEqual([1.0, 3.0], self.sfm.values_of("A"))

    def add_the_old_way(self, value, unit):
        self.avf.display_avf_values(
            {self.elements[0]: value}, self.view, schema_name="A", unit=unit
        )
        return next(s for s in self.sfm.schemas.values() if s.Name == "A")

    def test_a_result_added_some_other_way_keeps_its_unit(self):
        schema = self.add_the_old_way(90, "min")
        for _ in range(2):
            self.show({2: 5}, name="A")
            self.show({3: 6}, name="A", keep_others=True)
        self.assertIs(schema, next(iter(self.sfm.schemas.values())))
        self.assertEqual(["min"], schema.units)
        self.assertEqual("AVF values from pyRevit", schema.description)

    def test_changing_a_borrowed_result_is_refused_before_anything_changes(self):
        self.add_the_old_way(90, "min")
        self.show({2: 5}, name="A")
        for options in ({"unit": "h"}, {"description": "mine"}):
            with self.subTest(options=options):
                with self.assertRaises(RuntimeError):
                    self.show({3: 6}, name="A", **options)
        self.assertEqual([5.0, 90.0], self.sfm.values_of("A"))
        self.assertTrue(self.show({3: 6}, name="A", unit="min")["shown"])

    def test_a_result_shared_later_keeps_its_unit(self):
        writers = {
            "display": lambda: self.add_the_old_way(120, "min"),
            "points": lambda: self.avf.display_avf_values_at_points(
                [(XYZ(0.0, 0.0, 0.0), 120.0)], self.view, schema_name="A"
            ),
        }
        for label, write_the_old_way in writers.items():
            with self.subTest(writer=label):
                self.setUp()
                self.show({2: 5}, name="A", unit="min")
                write_the_old_way()
                with self.assertRaises(RuntimeError):
                    self.show({2: 5}, name="A", unit="h")
                self.show({2: 6}, name="A")
                schema = next(iter(self.sfm.schemas.values()))
                self.assertEqual(["min"], schema.units)

    def test_a_lower_level_call_that_writes_nothing_locks_nothing(self):
        def display(values):
            self.avf.display_avf_values(values, self.view, schema_name="A")

        def points(pairs):
            self.avf.display_avf_values_at_points(pairs, self.view, schema_name="A")

        def update(values):
            self.avf.update_avf_values({}, values, self.view, schema_name="A")

        calls = {
            "display nothing": lambda: display({}),
            "no points": lambda: points([]),
            "update nothing": lambda: update({}),
            "update unknown": lambda: update({self.elements[1]: 1.0}),
        }
        for label, write_nothing in calls.items():
            with self.subTest(call=label):
                self.setUp()
                self.show({1: 5}, name="A", unit="min")
                write_nothing()
                self.show({1: 1}, name="A", unit="h")

    def test_a_unit_revit_rejects_removes_nothing(self):
        self.show({1: 10}, name="A")
        self.view.AnalysisDisplayStyleId = "mine"
        with self.assertRaises(ValueError):
            self.show({2: 20}, name="A", unit=[("h", 0)])
        self.assertEqual([10.0], self.sfm.values_of("A"))
        self.assertEqual("mine", self.view.AnalysisDisplayStyleId)

    def test_a_rolled_back_style_raises_and_values_stay_clearable(self):
        view = self.view

        class RolledBack(Context):
            def __exit__(self, *args):
                view.AnalysisDisplayStyleId = None
                return False

        committed, self.avf.Transaction = self.avf.Transaction, RolledBack
        with self.assertRaises(RuntimeError):
            self.show({1: 10}, name="A")
        self.avf.Transaction = committed
        self.assertEqual(1, self.avf.clear_values(self.view, "A"))
        self.assertEqual([], self.sfm.values_of("A"))

    def test_a_cleared_view_frees_the_name_again(self):
        self.add_the_old_way(90, "min")
        self.show({2: 5}, name="A")
        self.sfm.Clear()
        self.show({2: 5}, name="A", unit="h")
        self.assertEqual(["h"], next(iter(self.sfm.schemas.values())).units)

    def custom_style(self):
        style = DisplayStyle("mine", "custom")
        style.Id = ElementId(77)
        self.view.Document.elements[77] = style
        return style

    def test_a_custom_style_is_restored_while_keeping_values(self):
        self.custom_style()
        self.show({1: 1}, name="A", style=self.view.Document.elements[77])
        self.show({2: 2}, name="B")
        report = self.show({3: 3}, name="A", keep_others=True)
        self.assertEqual("mine", report["style"])
        self.assertEqual(ElementId(77), self.view.AnalysisDisplayStyleId)

    def test_a_deleted_custom_style_leaves_the_view_style(self):
        self.show({1: 1}, name="A", style=self.custom_style())
        self.show({2: 2}, name="B")
        del self.view.Document.elements[77]
        report = self.show({3: 3}, name="A", keep_others=True)
        self.assertIsNone(report["style"])
        self.assertEqual("pyRevit AVF Marker - B", self.view.AnalysisDisplayStyleId)

    def test_keys_can_be_elements_ids_or_integers(self):
        report = self.show(
            [(self.elements[0], 1), (ElementId(2), "2.5"), (3, 3), (404, 4)]
        )
        self.assertEqual([1, 2, 3], report["shown"])
        self.assertEqual([404], list(report["failed"]))
        json.dumps(report)

    def test_element_of_another_document_is_reported(self):
        self.elements[0].Document = Document(2)
        report = self.show({self.elements[0]: 1})
        self.assertEqual([], report["shown"])
        self.assertIn("another document", report["failed"][1])

    def foreign_element(self, element_id):
        element = slab(element_id=element_id)
        element.Document = Document(2)
        return element

    def test_an_id_passed_twice_across_documents_changes_nothing(self):
        self.show({1: 10}, name="A", unit="min", keep_others=True)
        foreign = self.foreign_element(1)
        for pairs in ([(foreign, 1), (1, 2)], [(1, 2), (foreign, 1)]):
            with self.subTest(first=pairs[0][0] is foreign):
                with self.assertRaises(RuntimeError):
                    self.show(pairs, name="A", unit="h", keep_others=True)
        self.assertEqual([10.0], self.sfm.values_of("A"))

    def test_a_foreign_element_does_not_stand_in_for_a_local_one(self):
        self.show({1: 10}, name="A", unit="min", keep_others=True)
        foreign = self.foreign_element(1)
        with self.assertRaises(RuntimeError):
            self.show([(foreign, 1)], name="A", unit="h", keep_others=True)
        report = self.show([(foreign, 1), (2, 20)], name="A", keep_others=True)
        self.assertEqual([1, 2], report["present"])
        self.assertIn("another document", report["failed"][1])
        self.assertEqual([10.0, 20.0], self.sfm.values_of("A"))

    def test_a_value_revit_rejects_leaves_no_empty_primitive(self):
        self.sfm.rejects_values = True
        report = self.show({1: 1})
        self.assertEqual({1: "value rejected"}, report["failed"])
        self.assertEqual({}, self.sfm.primitives)

    def test_invalid_requests_change_nothing(self):
        self.show({1: 10}, name="A")
        invalid = [
            ({1: float("nan")}, {}),
            ({1: float("inf")}, {}),
            ({1: "ten"}, {}),
            ([(1, 1), (ElementId(1), 2)], {}),
            ({1: 1}, {"style": "markers"}),
            ({1: 1}, {"style": "colored"}),
            ({1: 1}, {"style": None, "marker_size_mm": 2}),
            ({1: 1}, {"marker_size_mm": 0}),
            ({1: 1}, {"unit": ""}),
        ]
        for values, options in invalid:
            with self.subTest(values=values, options=options):
                with self.assertRaises(RuntimeError):
                    self.show(values, name="A", **options)
        self.assertEqual([10.0], self.sfm.values_of("A"))

    def test_view_without_analysis_display_is_refused(self):
        self.view.allows_analysis = False
        with self.assertRaises(RuntimeError):
            self.show({1: 1})
        self.assertFalse(self.sfm.created)

    def test_marker_style_is_assigned_and_sized_in_millimetres(self):
        report = self.show({1: 1}, name="Fire: [A]", marker_size_mm=2)
        style = self.avf.created_styles[-1]
        self.assertEqual("pyRevit AVF Marker - Fire_ _A_", report["style"])
        self.assertEqual(report["style"], self.view.AnalysisDisplayStyleId)
        self.assertAlmostEqual(2 / 304.8, style.settings.MarkerSize)

    def test_no_style_leaves_the_view_style(self):
        self.view.AnalysisDisplayStyleId = "mine"
        self.assertIsNone(self.show({1: 1}, style=None)["style"])
        self.assertEqual("mine", self.view.AnalysisDisplayStyleId)

    def test_new_manager_names_the_measurement(self):
        self.show({1: 1})
        self.assertEqual(["Value"], self.sfm.measurement_names)


class KeepOthersTests(ShowValuesCase):
    def keep(self, values, **options):
        return self.show(values, name="A", keep_others=True, **options)

    def unit_of_a(self):
        return list(self.sfm.schemas.values())[0].units

    def test_values_are_added_and_updated_one_at_a_time(self):
        self.keep({1: 10})
        added = self.keep({2: 20})
        self.assertEqual(([2], [1, 2], 0), self.summary(added))
        updated = self.keep({1: 11})
        self.assertEqual(([1], [1, 2], 1), self.summary(updated))
        self.assertEqual([11.0, 20.0], self.sfm.values_of("A"))

    @staticmethod
    def summary(report):
        return report["shown"], report["present"], report["removed"]

    def test_repeating_a_call_adds_nothing_twice(self):
        self.keep({1: 10, 2: 20})
        self.keep({1: 10, 2: 20})
        self.assertEqual([10.0, 20.0], self.sfm.values_of("A"))
        self.assertEqual(2, len(self.sfm.primitives))

    def test_none_removes_one_value_even_of_a_deleted_element(self):
        self.keep({1: 10, 2: 20})
        del self.view.Document.elements[2]
        report = self.keep({2: None, 404: None})
        self.assertEqual(([], [1], 1), self.summary(report))
        self.assertEqual({}, report["failed"])
        self.assertEqual([10.0], self.sfm.values_of("A"))

    def test_none_without_keep_others_changes_nothing(self):
        self.keep({1: 10})
        with self.assertRaises(RuntimeError):
            self.show({1: None}, name="A")
        self.assertEqual([10.0], self.sfm.values_of("A"))

    def test_default_call_still_replaces_everything(self):
        self.keep({1: 10, 2: 20})
        report = self.show({3: 30}, name="A")
        self.assertEqual(([3], [3], 2), self.summary(report))

    def test_unit_and_description_are_inherited(self):
        self.keep({1: 10}, unit="min", description="Rating")
        self.keep({2: 20})
        self.assertEqual(["min"], self.unit_of_a())
        self.assertEqual("Rating", list(self.sfm.schemas.values())[0].description)

    def test_another_unit_is_refused_while_other_values_remain(self):
        self.keep({1: 10, 2: 20}, unit="min")
        with self.assertRaises(RuntimeError):
            self.keep({1: 1}, unit="h")
        self.assertEqual([10.0, 20.0], self.sfm.values_of("A"))
        self.assertEqual(["min"], self.unit_of_a())

    def test_unit_can_change_when_every_other_value_is_passed(self):
        self.keep({1: 60, 2: 120}, unit="min")
        self.keep({1: 1, 2: None}, unit="h")
        self.assertEqual(["h"], self.unit_of_a())
        self.assertEqual([1.0], self.sfm.values_of("A"))

    def test_failed_update_keeps_the_earlier_value(self):
        self.keep({1: 10})
        self.sfm.rejects_values = True
        report = self.keep({1: 11})
        self.assertEqual(([], [1], 0), self.summary(report))
        self.assertEqual([10.0], self.sfm.values_of("A"))

    def test_failed_update_with_a_new_unit_drops_the_old_number(self):
        self.keep({1: 60}, unit="min")
        self.sfm.rejects_values = True
        report = self.keep({1: 1}, unit="h")
        self.assertEqual(([], [], 1), self.summary(report))
        self.assertEqual({}, self.sfm.primitives)

    def test_marker_is_the_automatic_style_of_a_new_name(self):
        self.assertEqual("pyRevit AVF Marker - A", self.keep({1: 1})["style"])

    def test_the_style_choice_is_remembered_while_keeping_values(self):
        self.keep({1: 1}, style=None)
        self.assertIsNone(self.keep({2: 2})["style"])

    def test_nothing_is_inherited_after_clearing(self):
        self.keep({1: 10}, unit="min", style=None)
        self.avf.clear_values(self.view, "A")
        report = self.keep({2: 20})
        self.assertEqual(["Value"], self.unit_of_a())
        self.assertEqual("pyRevit AVF Marker - A", report["style"])
        self.assertEqual([2], report["present"])

    def test_values_cleared_elsewhere_are_not_resurrected(self):
        self.keep({1: 10})
        self.sfm.Clear()
        self.assertEqual([2], self.keep({2: 20})["present"])
        self.assertEqual([20.0], self.sfm.values_of("A"))


class ShowValuesIn3DTests(ShowValuesCase):
    view_type = View3D

    def test_colored_surface_reports_the_elements_it_can_paint(self):
        self.view.visible_ids = {1}
        report = self.show({1: 1, 2: 2}, style="colored")
        self.assertEqual([1, 2], report["shown"])
        self.assertEqual([1], report["on_faces"])

    def test_adding_a_value_keeps_the_colored_surface(self):
        self.show({1: 1}, name="A", style="colored", keep_others=True)
        report = self.show({2: 2}, name="A", keep_others=True)
        self.assertEqual("pyRevit AVF Colored Surface - A", report["style"])
        self.assertEqual([2], report["on_faces"])


class SamplePointTests(unittest.TestCase):
    def test_sample_point_avoids_an_opening_in_the_middle(self):
        avf = load_avf(SpatialFieldManager(), View3D())

        def outside_the_opening(uv):
            return not (0.6 < uv.U < 1.4 and 1.2 < uv.V < 2.8)

        face = Face("wall", XYZ(0.0, 0.0, 1.0), inside=outside_the_opening)
        point = avf._get_sample_uv(face)
        self.assertTrue(outside_the_opening(point), (point.U, point.V))

    def test_face_that_no_sample_hits_is_not_used(self):
        view = View3D()
        sfm = SpatialFieldManager()
        avf = load_avf(sfm, view)

        def narrow_border(uv):
            return uv.U < 0.1 or uv.U > 1.9

        element = Element(Face("frame", XYZ(0.0, 0.0, 1.0), inside=narrow_border))
        self.assertIsNone(
            avf._get_sample_uv(Face("f", XYZ(0, 0, 1), inside=narrow_border))
        )
        results = avf.display_avf_values({element: 1.0}, view)
        self.assertTrue(results[1][0])
        self.assertEqual([()], sfm.anchors)
        self.assertEqual("xyz", sfm.updates[0][1][0])


class Guid:
    def __init__(self, text):
        self.text = text

    def __eq__(self, other):
        return isinstance(other, Guid) and other.text == self.text

    def __hash__(self):
        return hash(self.text)

    @staticmethod
    def NewGuid():
        return Guid(object())


class ActiveServers(list):
    def Add(self, item):
        self.append(item)


class HandlerService:
    def __init__(self):
        self.servers = {}
        self.active = []

    def AddServer(self, server):
        self.servers[server.guid] = server

    def RemoveServer(self, guid):
        del self.servers[guid]
        self.active = [other for other in self.active if other != guid]

    def GetRegisteredServerIds(self):
        return list(self.servers)

    def GetActiveServerIds(self):
        return ActiveServers(self.active)

    def SetActiveServers(self, active):
        self.active = list(active)


class GraphicsManager:
    def __init__(self):
        self.next_index = 0
        self.live = set()
        self.fails = False

    def AddControl(self, data, view_id):
        if self.fails:
            return -1
        self.next_index += 1
        self.live.add(self.next_index)
        return self.next_index

    def RemoveControl(self, index):
        self.live.remove(index)


def load_tmpgfx():
    graphics = {}
    service = HandlerService()
    envvars = {}
    db = types.SimpleNamespace(
        InCanvasControlData=lambda path, position: (path, position),
        TemporaryGraphicsManager=types.SimpleNamespace(
            GetTemporaryGraphicsManager=lambda doc: graphics.setdefault(
                doc, GraphicsManager()
            )
        ),
    )
    external = types.SimpleNamespace(
        ExternalServices=types.SimpleNamespace(
            BuiltInExternalServices=types.SimpleNamespace(
                TemporaryGraphicsHandlerService="service"
            )
        ),
        ExternalServiceRegistry=types.SimpleNamespace(GetService=lambda key: service),
    )
    logger = types.SimpleNamespace(
        debug=lambda *a: None, exception=lambda message, *a: pytest.fail(message)
    )
    stubs = {
        "pyrevit": stub_module(
            "pyrevit",
            DB=db,
            UI=types.SimpleNamespace(ITemporaryGraphicsHandler=object),
            PyRevitException=RuntimeError,
        ),
        "pyrevit.api": stub_module("pyrevit.api", ExternalService=external),
        "pyrevit.framework": stub_module("pyrevit.framework", Guid=Guid),
        "pyrevit.compat": stub_module(
            "pyrevit.compat", get_elementid_value_func=lambda: int
        ),
        "pyrevit.coreutils": stub_module(
            "pyrevit.coreutils",
            envvars=types.SimpleNamespace(
                get_pyrevit_env_var=envvars.get,
                set_pyrevit_env_var=envvars.__setitem__,
            ),
            get_str_hash=lambda text: hashlib.md5(text.encode("utf-8")).hexdigest(),
        ),
        "pyrevit.coreutils.logger": stub_module(
            "pyrevit.coreutils.logger", get_logger=lambda name: logger
        ),
    }
    module = load("tmpgfx", stubs)
    module.service = service
    module.graphics = graphics
    return module


@pytest.mark.regression
class ClickDispatchTests(unittest.TestCase):
    def setUp(self):
        tmpgfx = load_tmpgfx()
        clicks = self.clicks = []

        class Recorder(tmpgfx.Handler):
            def on_click(self, index, payload):
                clicks.append((index, payload))

        self.handler = Recorder(register=False)
        self.document = Document(1)
        self.manager = tmpgfx.ControlManager(self.document, handler=self.handler)
        self.view = types.SimpleNamespace(Id=5)

    def click(self, document, index):
        self.handler.OnClick(types.SimpleNamespace(Document=document, Index=index))

    def test_owned_control_dispatches_its_payload(self):
        index = self.manager.add_control("icon.bmp", None, self.view, payload="wall")
        self.click(self.document, index)
        self.assertEqual([(index, "wall")], self.clicks)

    def test_owned_control_without_payload_still_dispatches(self):
        index = self.manager.add_control("icon.bmp", None, self.view)
        self.click(self.document, index)
        self.assertEqual([(index, None)], self.clicks)

    def test_foreign_index_is_ignored(self):
        index = self.manager.add_control("icon.bmp", None, self.view)
        self.click(self.document, index + 1)
        self.assertEqual([], self.clicks)

    def test_same_index_in_another_document_is_ignored(self):
        index = self.manager.add_control("icon.bmp", None, self.view)
        self.click(Document(2), index)
        self.assertEqual([], self.clicks)

    def test_removed_control_is_ignored(self):
        index = self.manager.add_control("icon.bmp", None, self.view)
        self.manager.remove_control(index, self.view)
        self.click(self.document, index)
        self.assertEqual([], self.clicks)


@pytest.mark.regression
class ExampleIconTests(unittest.TestCase):
    def test_icon_is_24_bit_with_the_transparency_key_in_the_corner(self):
        data = ICON.read_bytes()
        offset = struct.unpack_from("<I", data, 10)[0]
        width, height, _, bits = struct.unpack_from("<iiHH", data, 18)
        self.assertEqual((32, 32, 24), (width, height, bits))
        blue, green, red = data[offset : offset + 3]
        self.assertEqual((0, 128, 128), (red, green, blue))


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpgfx = load_tmpgfx()
        self.document = Document(1)
        self.view = types.SimpleNamespace(Id=5)
        self.clicks = []

    def handler_class(self, label):
        tmpgfx, clicks = self.tmpgfx, self.clicks

        class Labelled(tmpgfx.Handler):
            def __init__(self, guid):
                tmpgfx.Handler.__init__(self, guid=guid)

            def on_click(self, index, payload):
                clicks.append((label, payload, self.clicked_document.number))

        return Labelled

    def get_manager(self, label="first", tool="Tool", document=None):
        return self.tmpgfx.get_manager(
            tool, document or self.document, self.handler_class(label)
        )

    def click(self, document, index):
        event = types.SimpleNamespace(Document=document, Index=index)
        for handler in list(self.tmpgfx.service.servers.values()):
            handler.OnClick(event)

    def test_a_rerun_replaces_the_handler_and_keeps_its_controls(self):
        index = self.get_manager("first").add_control(
            "icon.bmp", None, self.view, payload="old"
        )
        manager = self.get_manager("second")
        self.assertEqual(1, len(self.tmpgfx.service.servers))
        self.assertEqual(1, manager.control_count())
        self.click(self.document, index)
        self.assertEqual([("second", "old", 1)], self.clicks)

    def test_no_factory_keeps_the_current_handler(self):
        manager = self.get_manager("first")
        self.assertIs(manager, self.tmpgfx.get_manager("Tool", self.document))
        index = manager.add_control("icon.bmp", None, self.view)
        self.click(self.document, index)
        self.assertEqual([("first", None, 1)], self.clicks)

    def test_each_document_has_its_own_manager_on_one_handler(self):
        other = Document(2)
        first = self.get_manager()
        second = self.get_manager(document=other)
        self.assertIsNot(first, second)
        self.assertIs(first.handler, second.handler)
        self.assertEqual(1, len(self.tmpgfx.service.servers))

    def test_closed_documents_are_dropped_with_their_payloads(self):
        closed = Document(2)
        self.get_manager(document=closed).add_control(
            "icon.bmp", None, self.view, payload="held"
        )
        self.get_manager().add_control("icon.bmp", None, self.view, payload="open")
        closed.IsValidObject = False
        handler = self.get_manager("second").handler
        self.assertEqual(["open"], list(handler._control_map.values()))
        self.assertEqual(1, self.tmpgfx.dispose("Tool"))
        self.assertEqual(0, self.tmpgfx.dispose("Tool"))

    def test_dispose_leaves_other_tools_and_controls_alone(self):
        self.get_manager(tool="Tool").add_control("icon.bmp", None, self.view)
        self.get_manager(tool="Other").add_control("icon.bmp", None, self.view)
        graphics = self.tmpgfx.graphics[self.document]
        graphics.live.add(404)
        self.assertEqual(1, self.tmpgfx.dispose("Tool"))
        self.assertEqual(0, self.tmpgfx.dispose("Tool"))
        self.assertEqual({2, 404}, graphics.live)
        self.assertEqual(
            [self.tmpgfx.get_tool_guid("Other")], list(self.tmpgfx.service.servers)
        )

    def test_factory_must_use_the_tool_id(self):
        with self.assertRaises(RuntimeError):
            self.tmpgfx.get_manager(
                "Tool", self.document, lambda guid: self.tmpgfx.Handler(register=False)
            )

    def test_failing_to_add_a_control_raises(self):
        manager = self.get_manager()
        self.tmpgfx.graphics[self.document].fails = True
        with self.assertRaises(RuntimeError):
            manager.add_control("icon.bmp", None, self.view)
        self.assertEqual(0, manager.control_count())

    def test_removing_an_unknown_control_raises(self):
        with self.assertRaises(KeyError):
            self.get_manager().remove_control(404, self.view)

    def test_clearing_tolerates_controls_that_are_already_gone(self):
        manager = self.get_manager()
        manager.add_control("icon.bmp", None, self.view)
        manager.add_control("icon.bmp", None, self.view)
        self.tmpgfx.graphics[self.document].live.remove(1)
        self.assertEqual(1, manager.clear(self.view))
        self.assertEqual(0, manager.control_count())


if __name__ == "__main__":
    unittest.main()
