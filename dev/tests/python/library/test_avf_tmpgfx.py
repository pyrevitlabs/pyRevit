"""Host-free regression tests for ``pyrevit.revit.avf`` and ``tmpgfx``.

Loads both modules with the Revit modules stubbed. The cases come from a live
Revit 2026 run on 2026-11-27: face selection returned only faces turned away
from the viewer, the reference of such a face crashed Revit in a plan view,
``display_avf_values_at_points`` raised ``NameError``, and every temporary
graphics handler dispatched clicks on controls it did not own.
"""

import importlib.util
import pathlib
import struct
import sys
import types
import unittest

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

pytestmark = pytest.mark.regression

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
    def __init__(self, name, normal, area=10.0, reference="reference"):
        self.name = name
        self.normal = normal
        self.Area = area
        self.Reference = reference and "{} of {}".format(reference, name)

    def GetBoundingBox(self):
        return types.SimpleNamespace(Min=UV(0.0, 0.0), Max=UV(2.0, 4.0))

    def ComputeNormal(self, uv):
        return self.normal


class Solid:
    def __init__(self, *faces):
        self.Faces = list(faces)


class View:
    def __init__(self):
        self.Name = "view"
        self.Document = object()
        self.ViewDirection = XYZ(0.0, 0.0, 1.0)
        self.DetailLevel = "Fine"
        self.visible_ids = {1}
        self.collector_count = 0

    def collect(self):
        self.collector_count += 1
        return Collector(self.visible_ids)


class View3D(View):
    IsSectionBoxActive = False


class Element:
    def __init__(self, *faces, **options):
        self.Id = options.get("element_id", 1)
        self.geometry = [Solid(*faces)]
        self.journal = None

    def get_BoundingBox(self, view):
        if self.journal is not None:
            self.journal.append("read")
        return types.SimpleNamespace(Min=XYZ(0.0, 0.0, 0.0), Max=XYZ(2.0, 2.0, 2.0))


class NetList(list):
    def __class_getitem__(cls, item):
        return cls

    def Add(self, item):
        self.append(item)


class SpatialFieldManager:
    def __init__(self, journal=None):
        self.journal = [] if journal is None else journal
        self.anchors = []
        self.updates = []
        self.rejects_references = False

    def GetRegisteredResults(self):
        return []

    def RegisterResult(self, schema):
        return 7

    def AddSpatialFieldPrimitive(self, *anchor):
        if anchor and self.rejects_references:
            raise ValueError("must point to either Face or Curve visible in the view")
        self.anchors.append(anchor)
        self.journal.append("add")
        return len(self.anchors)

    def UpdateSpatialFieldPrimitive(self, primitive, points, values, schema):
        self.updates.append((primitive, points, values, schema))


class Collector:
    def __init__(self, view_ids):
        self.view_ids = view_ids

    def WherePasses(self, wanted):
        self.wanted = wanted
        return self

    def ToElementIds(self):
        return self.view_ids.intersection(self.wanted)


class Context:
    def __init__(self, *args):
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
    anything = lambda *args, **kwargs: types.SimpleNamespace(
        SetUnits=lambda *a: None, args=args
    )
    manager_type = types.SimpleNamespace(
        GetSpatialFieldManager=lambda target: None,
        CreateSpatialFieldManager=lambda target, count: sfm,
    )
    db = types.SimpleNamespace(
        UV=UV,
        XYZ=XYZ,
        Solid=Solid,
        View3D=View3D,
        ElementId=int,
        ViewDetailLevel=types.SimpleNamespace(
            Coarse="Coarse", Medium="Medium", Fine="Fine", Undefined="Undefined"
        ),
        ElementIdSetFilter=lambda ids: set(ids),
        FilteredElementCollector=lambda doc, view_id: view.collect(),
        Analysis=types.SimpleNamespace(
            SpatialFieldManager=manager_type,
            AnalysisResultSchema=anything,
            ValueAtPoint=anything,
            FieldValues=anything,
            FieldDomainPointsByXYZ=lambda points: ("xyz", points),
            FieldDomainPointsByUV=lambda points: ("uv", points),
        ),
    )
    view.Id = 99
    logger = types.SimpleNamespace(
        warning=lambda *a: None,
        error=lambda *a: None,
        debug=lambda *a: None,
        exception=lambda message, *a: pytest.fail(message),
    )
    query = types.SimpleNamespace(
        get_geometry=lambda element, **options: element.geometry,
        get_elements_by_class=lambda *a, **k: [],
    )
    stubs = {
        "pyrevit": stub_module("pyrevit", DB=db, PyRevitException=RuntimeError),
        "pyrevit.revit": stub_module("pyrevit.revit", Transaction=Context, query=query),
        "pyrevit.framework": stub_module(
            "pyrevit.framework",
            List=NetList,
            System=types.SimpleNamespace(String=str, Double=float),
        ),
        "pyrevit.coreutils": stub_module("pyrevit.coreutils"),
        "pyrevit.coreutils.logger": stub_module(
            "pyrevit.coreutils.logger", get_logger=lambda name: logger
        ),
        "pyrevit.compat": stub_module(
            "pyrevit.compat", get_elementid_value_func=lambda: int
        ),
    }
    return load("avf", stubs)


def slab(reference="reference", element_id=1):
    return Element(
        Face("underside", XYZ(0.0, 0.0, -1.0), area=20.0, reference=reference),
        Face("edge", XYZ(1.0, 0.0, 0.0), area=30.0, reference=reference),
        Face("top", XYZ(0.0, 0.0, 1.0), reference=reference),
        element_id=element_id,
    )


class DisplayTests(unittest.TestCase):
    def display(self, view, element=None, sfm=None, **options):
        sfm = sfm or SpatialFieldManager()
        avf = load_avf(sfm, view)
        results = avf.display_avf_values({element or slab(): 1.0}, view, **options)
        self.assertEqual({1: (True, 1)}, results)
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
        self.assertEqual([1, 2, 3], created)
        self.assertEqual([2, 2, 1], [len(update[1][1]) for update in sfm.updates])


class Document:
    def __init__(self, number):
        self.number = number

    def GetHashCode(self):
        return self.number


def load_tmpgfx():
    class Manager:
        def __init__(self):
            self.next_index = 0

        def AddControl(self, data, view_id):
            self.next_index += 1
            return self.next_index

        def RemoveControl(self, index):
            pass

    managers = {}
    db = types.SimpleNamespace(
        InCanvasControlData=lambda path, position: (path, position),
        TemporaryGraphicsManager=types.SimpleNamespace(
            GetTemporaryGraphicsManager=lambda doc: managers.setdefault(doc, Manager())
        ),
    )
    external = types.SimpleNamespace(
        ExternalServices=types.SimpleNamespace(
            BuiltInExternalServices=types.SimpleNamespace(
                TemporaryGraphicsHandlerService="service"
            )
        )
    )
    stubs = {
        "pyrevit": stub_module(
            "pyrevit",
            DB=db,
            UI=types.SimpleNamespace(ITemporaryGraphicsHandler=object),
        ),
        "pyrevit.api": stub_module("pyrevit.api", ExternalService=external),
        "pyrevit.framework": stub_module(
            "pyrevit.framework", Guid=types.SimpleNamespace(NewGuid=object)
        ),
        "pyrevit.compat": stub_module(
            "pyrevit.compat", get_elementid_value_func=lambda: int
        ),
    }
    return load("tmpgfx", stubs)


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


class ExampleIconTests(unittest.TestCase):
    def test_icon_is_24_bit_with_the_transparency_key_in_the_corner(self):
        data = ICON.read_bytes()
        offset = struct.unpack_from("<I", data, 10)[0]
        width, height, _, bits = struct.unpack_from("<iiHH", data, 18)
        self.assertEqual((32, 32, 24), (width, height, bits))
        blue, green, red = data[offset : offset + 3]
        self.assertEqual((0, 128, 128), (red, green, blue))


if __name__ == "__main__":
    unittest.main()
