"""Tested building blocks for agent scripts, injected as ``kit``.

Agents kept re-deriving the same Revit API recipes and getting them subtly
wrong: roofs sloped in the wrong units or on the wrong edges, out parameters
that don't marshal on IronPython 3.4, type lookups that silently return None,
views that frame level lines instead of the model. Each helper here is the
recipe done once, checked, and written to fail loudly with a message that
says what to do next.

Invariant:
    Must stay parseable by IronPython 2.7, IronPython 3.4 and CPython 3,
    because the agent host picks the engine per request.

Note:
    Lengths are feet, like the Revit API. :meth:`Kit.ft` converts drawing
    strings such as ``32'-6"`` or ``900mm``. Helpers that change the model
    need an open transaction; use ``with kit.transaction("name"):``.
"""

import io
import math
import re
import types

import System
from System.Collections.Generic import List

from pyrevit.api import DB

AGENT_MARK_PREFIX = "agent:"
MAX_LISTED_NAMES = 40

_VIEW_KINDS = {
    "plan": [DB.ViewType.FloorPlan],
    "ceiling": [DB.ViewType.CeilingPlan],
    "structural": [DB.ViewType.EngineeringPlan],
    "area": [DB.ViewType.AreaPlan],
    "3d": [DB.ViewType.ThreeD],
    "section": [DB.ViewType.Section],
    "elevation": [DB.ViewType.Elevation],
    "detail": [DB.ViewType.Detail],
    "drafting": [DB.ViewType.DraftingView],
    "legend": [DB.ViewType.Legend],
    "schedule": [DB.ViewType.Schedule],
    "sheet": [DB.ViewType.DrawingSheet],
}

_PLAN_FAMILIES = {
    "plan": DB.ViewFamily.FloorPlan,
    "ceiling": DB.ViewFamily.CeilingPlan,
    "structural": DB.ViewFamily.StructuralPlan,
}

_DIRECTIONS = {
    "southeast": (-1.0, 1.0, -1.0),
    "southwest": (1.0, 1.0, -1.0),
    "northeast": (-1.0, -1.0, -1.0),
    "northwest": (1.0, -1.0, -1.0),
    "south": (0.0, 1.0, -0.6),
    "north": (0.0, -1.0, -0.6),
    "east": (-1.0, 0.0, -0.6),
    "west": (1.0, 0.0, -0.6),
    "top": (0.0, 0.0001, -1.0),
}

_SIDES = {
    "south": (0.0, -1.0),
    "north": (0.0, 1.0),
    "east": (1.0, 0.0),
    "west": (-1.0, 0.0),
}

_UNFRAMED_CATEGORIES = (
    "OST_ProjectBasePoint",
    "OST_SharedBasePoint",
    "OST_Cameras",
    "OST_SectionBox",
    "OST_Topography",
    "OST_Toposolid",
    "OST_RvtLinks",
)

_FEET_INCHES = re.compile(
    r"^\s*(?:(?P<feet>-?\d+(?:\.\d+)?)\s*')?\s*-?\s*"
    r"(?:(?P<inches>\d+(?:\.\d+)?)?\s*(?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?\s*\")?\s*$"
)
_METRIC = re.compile(r"^\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\s*$")
_RATIO = re.compile(
    r"^\s*(?P<rise>\d+(?:\.\d+)?)\s*(?::|/|\s+in\s+)\s*(?P<run>\d+(?:\.\d+)?)\s*$"
)
_DEGREES = re.compile(r"^\s*(?P<deg>\d+(?:\.\d+)?)\s*deg(?:rees)?\s*$")


class KitError(Exception):
    """A kit precondition failed; the message says what to change."""


class Kit(object):
    """Helpers bound to one document. Agent scripts get an instance as ``kit``.

    Call ``kit.help()`` for the list of helpers with their signatures.
    """

    def __init__(self, uidoc):
        self.uidoc = uidoc
        self.doc = uidoc.Document if uidoc else None

    # ------------------------------------------------------------- discovery
    def help(self):
        """Return every public helper with its signature and summary."""
        entries = []
        for name in sorted(dir(Kit)):
            if name.startswith("_"):
                continue
            member = getattr(Kit, name)
            if not callable(member):
                continue
            doc = (getattr(member, "__doc__", None) or "").strip().split("\n")[0]
            entries.append("kit.%s%s  %s" % (name, _signature(member), doc))
        return entries

    # ------------------------------------------------------------ transactions
    def transaction(self, name):
        """Context manager: commits on success, rolls back on any exception."""
        return _Transaction(self.doc, name)

    # ------------------------------------------------------------------ units
    @staticmethod
    def ft(value):
        """Convert a length to feet.

        Accepts numbers (already feet) and strings: ``32'-6"``, ``32' 6 1/2"``,
        ``6"``, ``12'``, ``900mm``, ``90cm``, ``2.5m``.
        """
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        metric = _METRIC.match(text)
        if metric:
            factor = {"mm": 304.8, "cm": 30.48, "m": 0.3048}[metric.group("unit")]
            return float(metric.group("value")) / factor
        imperial = _FEET_INCHES.match(text)
        if imperial and ("'" in text or '"' in text):
            feet = float(imperial.group("feet") or 0.0)
            inches = float(imperial.group("inches") or 0.0)
            if imperial.group("num"):
                inches += float(imperial.group("num")) / float(imperial.group("den"))
            sign = -1.0 if feet < 0 or text.startswith("-") else 1.0
            return sign * (abs(feet) + inches / 12.0)
        try:
            return float(text)
        except ValueError:
            raise KitError(
                "Can't read length %r. Use feet as a number, 32'-6\", 6\", 900mm or 2.5m."
                % value
            )

    @staticmethod
    def pitch(value):
        """Convert a roof pitch to the rise-over-run ratio Revit's slope APIs take.

        ``"8:12"``, ``"8/12"`` and ``"8 in 12"`` give 0.667; ``"30deg"`` gives
        tan(30 degrees); a number is taken as rise over run already.

        Important:
            ``FootPrintRoof.set_SlopeAngle`` takes rise over run, not radians
            or degrees. Passing degrees builds a roof hundreds of feet tall.
        """
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value)
        ratio = _RATIO.match(text)
        if ratio:
            return float(ratio.group("rise")) / float(ratio.group("run"))
        degrees = _DEGREES.match(text)
        if degrees:
            return math.tan(math.radians(float(degrees.group("deg"))))
        raise KitError(
            "Can't read pitch %r. Use '8:12', '30deg' or a rise/run number." % value
        )

    # ---------------------------------------------------------------- lookups
    def levels(self):
        """All levels, lowest first."""
        found = DB.FilteredElementCollector(self.doc).OfClass(DB.Level).ToElements()
        return sorted(found, key=lambda level: level.Elevation)

    def level(self, name=None):
        """A level by name. Without a name: the active plan's level, else the lowest."""
        if isinstance(name, DB.Level):
            return name
        levels = self.levels()
        if not levels:
            raise KitError(
                "The document has no levels; create one with DB.Level.Create(doc, elevation_ft)."
            )
        if name is None:
            view = self.uidoc.ActiveView if self.uidoc else None
            generated = getattr(view, "GenLevel", None)
            return generated if generated is not None else levels[0]
        for level in levels:
            if level.Name == name:
                return level
        raise KitError(
            "No level named %r. Levels: %s."
            % (name, ", ".join(level.Name for level in levels))
        )

    def type_names(self, type_class):
        """Names of all element types of ``type_class`` (for example DB.WallType)."""
        return sorted(name_of(item) for item in self._types(type_class))

    def type_named(self, type_class, name):
        """An element type by exact name; raises with the available names if missing."""
        if isinstance(name, DB.ElementType):
            return name
        items = self._types(type_class)
        for item in items:
            if name_of(item) == name:
                return item
        raise KitError(
            "No %s named %r. Available: %s."
            % (type_class.__name__, name, _listing(name_of(item) for item in items))
        )

    def wall_type(self, name):
        """A wall type by name."""
        return self.type_named(DB.WallType, name)

    def floor_type(self, name):
        """A floor type by name."""
        return self.type_named(DB.FloorType, name)

    def roof_type(self, name):
        """A roof type by name."""
        return self.type_named(DB.RoofType, name)

    def ceiling_type(self, name):
        """A ceiling type by name."""
        return self.type_named(DB.CeilingType, name)

    def symbols(self, category=None, family=None):
        """Family types as ``"Family : Type"`` strings, filtered by category and family name."""
        return sorted(
            "%s : %s" % (symbol.FamilyName, name_of(symbol))
            for symbol in self._symbols(category, family)
        )

    def symbol(self, name, family=None, category=None):
        """A family type (FamilySymbol) by type name, optionally by family and category.

        Activates it when needed, so call it inside a transaction.
        """
        if isinstance(name, DB.FamilySymbol):
            found = name
        else:
            matches = [s for s in self._symbols(category, family) if name_of(s) == name]
            if not matches:
                raise KitError(
                    "No family type %r%s. Available: %s."
                    % (
                        name,
                        " in family %r" % family if family else "",
                        _listing(self.symbols(category, family)),
                    )
                )
            if len(matches) > 1 and family is None:
                raise KitError(
                    "Several families have a type named %r: %s. Pass family=..."
                    % (name, ", ".join(sorted(set(s.FamilyName for s in matches))))
                )
            found = matches[0]
        if not found.IsActive:
            self._require_transaction("activate a family type")
            found.Activate()
            self.doc.Regenerate()
        return found

    def category(self, value):
        """A Category from a BuiltInCategory, its name (``"OST_Walls"``) or its UI name."""
        if isinstance(value, DB.Category):
            return value
        if isinstance(value, DB.BuiltInCategory):
            return DB.Category.GetCategory(self.doc, value)
        text = str(value)
        if text.startswith("OST_"):
            return DB.Category.GetCategory(self.doc, getattr(DB.BuiltInCategory, text))
        for category in self.doc.Settings.Categories:
            if category.Name == text:
                return category
        raise KitError(
            "No category %r. Use a BuiltInCategory such as 'OST_Walls'." % value
        )

    # --------------------------------------------------------------- geometry
    @staticmethod
    def xyz(x, y=None, z=0.0):
        """An XYZ from numbers, a tuple, or an XYZ."""
        if isinstance(x, DB.XYZ):
            return x
        if y is None:
            values = list(x)
            return DB.XYZ(values[0], values[1], values[2] if len(values) > 2 else z)
        return DB.XYZ(x, y, z)

    def line(self, start, end, z=0.0):
        """A bound line between two points given as tuples or XYZ."""
        return DB.Line.CreateBound(self.xyz(start, z=z), self.xyz(end, z=z))

    @staticmethod
    def rect(x1, y1, x2, y2):
        """The four corners of an axis-aligned rectangle, counter-clockwise."""
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def loop(self, points, z=0.0):
        """A closed CurveLoop through ``points`` (tuples or XYZ) at height ``z``."""
        result = DB.CurveLoop()
        for start, end in _edges(points):
            result.Append(self.line(start, end, z))
        return result

    def curve_array(self, points, z=0.0, closed=True):
        """A CurveArray through ``points``; closed by default."""
        result = DB.CurveArray()
        pairs = _edges(points) if closed else zip(points[:-1], points[1:])
        for start, end in pairs:
            result.Append(self.line(start, end, z))
        return result

    def bbox(self, element, view=None):
        """Model extents as ``{"min", "max", "size"}`` lists in feet, or None."""
        box = element.get_BoundingBox(view)
        if box is None:
            return None
        return {
            "min": [box.Min.X, box.Min.Y, box.Min.Z],
            "max": [box.Max.X, box.Max.Y, box.Max.Z],
            "size": [
                box.Max.X - box.Min.X,
                box.Max.Y - box.Min.Y,
                box.Max.Z - box.Min.Z,
            ],
        }

    # ----------------------------------------------------------------- walls
    def wall(
        self,
        start,
        end,
        wall_type,
        level=None,
        height=10.0,
        top_level=None,
        base_offset=0.0,
        structural=False,
    ):
        """A straight wall along its location line from ``start`` to ``end``.

        ``top_level`` (a Level or name) makes the wall's top follow that level
        instead of an unconnected ``height``.
        """
        self._require_transaction("create walls")
        level = self.level(level)
        wall_type = self.wall_type(wall_type)
        created = DB.Wall.Create(
            self.doc,
            self.line(start, end, level.Elevation),
            wall_type.Id,
            level.Id,
            self.ft(height),
            self.ft(base_offset),
            False,
            structural,
        )
        if top_level is not None:
            created.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(
                self.level(top_level).Id
            )
        return created

    def walls(self, points, wall_type, level=None, height=10.0, closed=True, **options):
        """Walls along a polyline of points; closed by default."""
        pairs = _edges(points) if closed else zip(points[:-1], points[1:])
        return [
            self.wall(start, end, wall_type, level, height, **options)
            for start, end in pairs
        ]

    def attach_top(self, walls, target):
        """Attach wall tops to a roof, floor or ceiling, so gable walls follow the rake."""
        self._require_transaction("attach walls")
        if not hasattr(DB.Wall, "AddAttachment"):
            raise KitError("Wall.AddAttachment needs Revit 2024 or later.")
        for wall in _as_list(walls):
            wall.AddAttachment(target.Id, DB.AttachmentLocation.Top)
        self.doc.Regenerate()

    # ------------------------------------------------------ floors, ceilings
    def floor(self, points, floor_type, level=None, offset=0.0, structural=False):
        """A floor on the closed outline ``points``, ``offset`` feet above the level."""
        self._require_transaction("create floors")
        level = self.level(level)
        floor_type = self.floor_type(floor_type)
        loops = List[DB.CurveLoop]([self.loop(points, level.Elevation)])
        if hasattr(DB.Floor, "Create"):
            created = DB.Floor.Create(self.doc, loops, floor_type.Id, level.Id)
        else:
            created = self.doc.Create.NewFloor(
                self.curve_array(points, level.Elevation), floor_type, level, structural
            )
        if offset:
            created.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).Set(
                self.ft(offset)
            )
        return created

    def ceiling(self, points, ceiling_type, level=None, offset=8.0):
        """A ceiling on the closed outline ``points``, ``offset`` feet above the level."""
        self._require_transaction("create ceilings")
        level = self.level(level)
        ceiling_type = self.ceiling_type(ceiling_type)
        loops = List[DB.CurveLoop]([self.loop(points, level.Elevation)])
        created = DB.Ceiling.Create(self.doc, loops, ceiling_type.Id, level.Id)
        created.get_Parameter(DB.BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM).Set(
            self.ft(offset)
        )
        return created

    # ----------------------------------------------------------------- roofs
    def footprint_roof(self, points, roof_type, level=None, slopes=None, offset=0.0):
        """A footprint roof on the closed outline ``points`` (eave line, overhang included).

        ``slopes`` maps edge index (edge i runs from points[i] to points[i+1])
        to a pitch (``"8:12"``, ``"30deg"`` or rise/run). Edges not listed
        don't define a slope. Returns ``(roof, model_curves)``.
        """
        self._require_transaction("create roofs")
        level = self.level(level)
        roof_type = self.roof_type(roof_type)
        footprint = self.curve_array(points, level.Elevation)
        roof, model_curves = self._new_footprint_roof(footprint, level, roof_type)
        if offset:
            roof.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM).Set(
                self.ft(offset)
            )
        edges = _edges(points)
        slopes = slopes or {}
        for model_curve in model_curves:
            index = _matching_edge(model_curve.GeometryCurve, edges)
            pitch = slopes.get(index)
            roof.set_DefinesSlope(model_curve, pitch is not None)
            if pitch is not None:
                roof.set_SlopeAngle(model_curve, self.pitch(pitch))
        self.doc.Regenerate()
        return roof, list(model_curves)

    def gable_roof(
        self, x1, y1, x2, y2, roof_type, pitch, ridge="x", level=None, offset=0.0
    ):
        """A rectangular gable roof; the rectangle is the eave outline, overhangs included.

        ``ridge="x"`` runs the ridge along X (eaves on the edges parallel to
        X), ``"y"`` along Y. ``offset`` raises the eave above the level. The
        built roof is measured and a KitError is raised when its rise doesn't
        match the pitch, which catches slopes on the wrong edges.
        """
        points = self.rect(x1, y1, x2, y2)
        eaves = [0, 2] if ridge == "x" else [1, 3]
        roof, _ = self.footprint_roof(
            points, roof_type, level, dict((index, pitch) for index in eaves), offset
        )
        span = abs(y2 - y1) if ridge == "x" else abs(x2 - x1)
        self._check_rise(roof, level, offset, span / 2.0 * self.pitch(pitch))
        return roof

    def hip_roof(self, x1, y1, x2, y2, roof_type, pitch, level=None, offset=0.0):
        """A rectangular hip roof with the same pitch on all four edges."""
        points = self.rect(x1, y1, x2, y2)
        roof, _ = self.footprint_roof(
            points, roof_type, level, dict((index, pitch) for index in range(4)), offset
        )
        span = min(abs(y2 - y1), abs(x2 - x1))
        self._check_rise(roof, level, offset, span / 2.0 * self.pitch(pitch))
        return roof

    def shed_roof(
        self, x1, y1, x2, y2, roof_type, pitch, low_side="south", level=None, offset=0.0
    ):
        """A rectangular shed roof sloping down toward ``low_side`` (south, east, north, west)."""
        edge = {"south": 0, "east": 1, "north": 2, "west": 3}[low_side]
        points = self.rect(x1, y1, x2, y2)
        roof, _ = self.footprint_roof(points, roof_type, level, {edge: pitch}, offset)
        span = abs(y2 - y1) if low_side in ("south", "north") else abs(x2 - x1)
        self._check_rise(roof, level, offset, span * self.pitch(pitch))
        return roof

    # ------------------------------------------------- doors, windows, columns
    def opening(self, symbol, wall, x, y, sill=None):
        """A door or window hosted by ``wall`` at plan point (x, y), with an optional sill height."""
        self._require_transaction("place doors and windows")
        symbol = self.symbol(symbol)
        level = self.doc.GetElement(wall.LevelId)
        created = self.doc.Create.NewFamilyInstance(
            DB.XYZ(x, y, level.Elevation),
            symbol,
            wall,
            level,
            DB.Structure.StructuralType.NonStructural,
        )
        if sill is not None:
            created.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(
                self.ft(sill)
            )
        return created

    def place(self, symbol, x, y, level=None, structural_type=None, rotation=0.0):
        """A level-based family instance (furniture, fixtures, columns) at (x, y).

        ``rotation`` is in degrees around the insertion point.
        """
        self._require_transaction("place family instances")
        symbol = self.symbol(symbol)
        level = self.level(level)
        point = DB.XYZ(x, y, level.Elevation)
        created = self.doc.Create.NewFamilyInstance(
            point,
            symbol,
            level,
            structural_type or DB.Structure.StructuralType.NonStructural,
        )
        if rotation:
            axis = DB.Line.CreateBound(point, point + DB.XYZ.BasisZ)
            DB.ElementTransformUtils.RotateElement(
                self.doc, created.Id, axis, math.radians(rotation)
            )
        return created

    def column(self, symbol, x, y, level=None, top_level=None, structural=True):
        """A column at (x, y) from ``level`` up to ``top_level``."""
        created = self.place(
            symbol,
            x,
            y,
            level,
            DB.Structure.StructuralType.Column
            if structural
            else DB.Structure.StructuralType.NonStructural,
        )
        if top_level is not None:
            created.get_Parameter(DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM).Set(
                self.level(top_level).Id
            )
        return created

    # ----------------------------------------------------------------- rooms
    def room(self, x, y, name=None, number=None, level=None, allow_unenclosed=False):
        """A room at plan point (x, y).

        Raises a KitError when the point isn't enclosed by room-bounding
        walls or separation lines, which is how gaps in a layout show up.
        """
        self._require_transaction("create rooms")
        level = self.level(level)
        created = self.doc.Create.NewRoom(level, DB.UV(x, y))
        if name:
            created.Name = name
        if number:
            created.Number = str(number)
        self.doc.Regenerate()
        if created.Area <= 0 and not allow_unenclosed:
            raise KitError(
                "Room %r at (%.2f, %.2f) is not enclosed: a wall or separation line around it is missing or doesn't meet its neighbour."
                % (name or "", x, y)
            )
        return created

    def room_separation(self, points, level=None, closed=False):
        """Room separation lines along ``points`` on a level (open polyline by default)."""
        self._require_transaction("create room separation lines")
        level = self.level(level)
        plan = self._plan_for(level)
        sketch = self._sketch_plane(level.Elevation)
        curves = self.curve_array(points, level.Elevation, closed)
        return list(self.doc.Create.NewRoomBoundaryLines(sketch, curves, plan))

    def model_lines(self, points, level=None, closed=False):
        """Model lines along ``points`` at the level's elevation."""
        self._require_transaction("create model lines")
        level = self.level(level)
        sketch = self._sketch_plane(level.Elevation)
        pairs = _edges(points) if closed else zip(points[:-1], points[1:])
        return [
            self.doc.Create.NewModelCurve(
                self.line(start, end, level.Elevation), sketch
            )
            for start, end in pairs
        ]

    # ------------------------------------------------------------ parameters
    def param(self, element, name):
        """A parameter by BuiltInParameter, its name (``"ALL_MODEL_MARK"``) or UI name.

        Raises with the element's parameter names when it isn't found.
        """
        parameter = None
        if isinstance(name, DB.BuiltInParameter):
            parameter = element.get_Parameter(name)
        elif str(name).isupper() and hasattr(DB.BuiltInParameter, str(name)):
            parameter = element.get_Parameter(getattr(DB.BuiltInParameter, str(name)))
        else:
            parameter = element.LookupParameter(name)
        if parameter is None:
            raise KitError(
                "%s has no parameter %r. Parameters: %s."
                % (
                    type(element).__name__,
                    str(name),
                    _listing(p.Definition.Name for p in element.Parameters),
                )
            )
        return parameter

    def get(self, element, name):
        """A parameter value: string, number (internal units) or ElementId."""
        parameter = self.param(element, name)
        storage = parameter.StorageType
        if storage == DB.StorageType.String:
            return parameter.AsString()
        if storage == DB.StorageType.Integer:
            return parameter.AsInteger()
        if storage == DB.StorageType.Double:
            return parameter.AsDouble()
        if storage == DB.StorageType.ElementId:
            return parameter.AsElementId()
        return parameter.AsValueString()

    def set(self, element, name, value):
        """Set a parameter; raises when it is read-only or Revit rejects the value.

        Numbers are internal units (feet); length strings like ``6"`` are converted.
        """
        self._require_transaction("set parameters")
        parameter = self.param(element, name)
        if parameter.IsReadOnly:
            raise KitError(
                "Parameter %r is read-only on %s." % (str(name), type(element).__name__)
            )
        if parameter.StorageType == DB.StorageType.Double and not isinstance(
            value, (int, float)
        ):
            value = self.ft(value)
        if not parameter.Set(value):
            raise KitError("Revit rejected %r for parameter %r." % (value, str(name)))
        return parameter

    # ------------------------------------------------------ re-runnable stages
    def mark(self, elements, label):
        """Tag elements with ``label`` in their Comments, so :meth:`clear` can remove them later."""
        self._require_transaction("mark elements")
        for element in _as_list(elements):
            parameter = element.get_Parameter(
                DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
            )
            if parameter is not None and not parameter.IsReadOnly:
                parameter.Set(AGENT_MARK_PREFIX + label)
        return elements

    def marked(self, label):
        """Elements tagged with ``label`` by :meth:`mark`."""
        wanted = AGENT_MARK_PREFIX + label
        found = []
        for element in DB.FilteredElementCollector(
            self.doc
        ).WhereElementIsNotElementType():
            parameter = element.get_Parameter(
                DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS
            )
            if parameter is not None and parameter.AsString() == wanted:
                found.append(element)
        return found

    def clear(self, label):
        """Delete everything tagged with ``label``; returns how many were deleted.

        Run it first in a stage script so rerunning the stage replaces its output.
        """
        self._require_transaction("delete elements")
        ids = List[DB.ElementId]([element.Id for element in self.marked(label)])
        if ids.Count:
            self.doc.Delete(ids)
        return ids.Count

    def load(self, path):
        """Run a helper file from the workspace and return it as a module.

        The file is read fresh on every call, so edits apply to the next run,
        and it sees ``doc``, ``uidoc``, ``DB`` and ``kit`` as globals. Keep
        shared plan data and helpers in one file instead of pasting them into
        every script.
        """
        module = types.ModuleType(
            str(
                re.sub(
                    r"\W", "_", path.split("\\")[-1].split("/")[-1].rsplit(".", 1)[0]
                )
            )
        )
        module.__file__ = path
        module.__dict__.update(
            {"doc": self.doc, "uidoc": self.uidoc, "DB": DB, "kit": self}
        )
        with io.open(path, encoding="utf-8") as source:
            code = compile(source.read(), path, "exec")
        exec(code, module.__dict__)
        return module

    # ---------------------------------------------------------------- views
    def views(self, kind=None, name_contains=None):
        """Views as ``{"id", "name", "type", "level"}`` dicts, templates excluded.

        ``kind``: plan, ceiling, structural, area, 3d, section, elevation,
        detail, drafting, legend, schedule or sheet.
        """
        wanted = _VIEW_KINDS.get(kind) if kind else None
        if kind and wanted is None:
            raise KitError(
                "Unknown view kind %r. Kinds: %s."
                % (kind, ", ".join(sorted(_VIEW_KINDS)))
            )
        rows = []
        for view in DB.FilteredElementCollector(self.doc).OfClass(DB.View):
            if view.IsTemplate or (wanted and view.ViewType not in wanted):
                continue
            if name_contains and name_contains.lower() not in view.Name.lower():
                continue
            level = getattr(view, "GenLevel", None)
            rows.append(
                {
                    "id": view.Id,
                    "name": view.Name,
                    "type": str(view.ViewType),
                    "level": level.Name if level is not None else None,
                }
            )
        return sorted(rows, key=lambda row: (row["type"], row["name"]))

    def view(self, name_or_id):
        """A view by name or id; raises with similar names when missing."""
        if isinstance(name_or_id, DB.View):
            return name_or_id
        if isinstance(name_or_id, (int, DB.ElementId)):
            element = self.doc.GetElement(
                name_or_id
                if isinstance(name_or_id, DB.ElementId)
                else DB.ElementId(name_or_id)
            )
            if isinstance(element, DB.View):
                return element
            raise KitError("No view with id %s." % name_or_id)
        views = [
            v
            for v in DB.FilteredElementCollector(self.doc).OfClass(DB.View)
            if not v.IsTemplate
        ]
        for candidate in views:
            if candidate.Name == name_or_id:
                return candidate
        words = [word for word in str(name_or_id).lower().split() if len(word) > 2]
        similar = [
            v.Name for v in views if any(word in v.Name.lower() for word in words)
        ]
        raise KitError(
            "No view named %r. Similar: %s." % (name_or_id, _listing(similar))
        )

    def plan(self, level=None, name=None, kind="plan", template=None):
        """A new floor, ceiling or structural plan of a level (``kind``: plan, ceiling, structural)."""
        self._require_transaction("create views")
        level = self.level(level)
        family = _PLAN_FAMILIES.get(kind)
        if family is None:
            raise KitError(
                "Plan kind must be plan, ceiling or structural, not %r." % kind
            )
        created = DB.ViewPlan.Create(
            self.doc, self._view_family_type(family).Id, level.Id
        )
        self._finish_view(created, name or "%s - %s" % (level.Name, kind), template)
        return created

    def view3d(
        self,
        name=None,
        direction="southeast",
        elements=None,
        model_only=True,
        template=None,
    ):
        """A new isometric 3D view looking from ``direction``, framed on ``elements`` or the whole model.

        ``direction``: southeast, southwest, northeast, northwest, south,
        north, east, west or top. ``model_only`` hides levels, grids and
        annotations, which otherwise stretch the framing.
        """
        self._require_transaction("create views")
        created = DB.View3D.CreateIsometric(
            self.doc, self._view_family_type(DB.ViewFamily.ThreeDimensional).Id
        )
        self._finish_view(created, name or "Agent 3D", template)
        if model_only:
            self.model_only(created)
        self.orient(created, direction)
        self.section_box(created, elements)
        return created

    def section(
        self, start, end, name=None, bottom=None, top=None, depth=10.0, template=None
    ):
        """A new section along the line start -> end, looking to the left of that direction.

        A line drawn west to east looks north. ``bottom`` and ``top`` default
        to the lowest level and 10 ft above the highest; ``depth`` is the
        far clip distance.
        """
        self._require_transaction("create views")
        start, end = self.xyz(start), self.xyz(end)
        levels = self.levels()
        bottom = (
            self.ft(bottom)
            if bottom is not None
            else (levels[0].Elevation if levels else 0.0) - 1.0
        )
        top = (
            self.ft(top)
            if top is not None
            else (levels[-1].Elevation if levels else 0.0) + 10.0
        )
        along = DB.XYZ(end.X - start.X, end.Y - start.Y, 0.0)
        if along.IsZeroLength():
            raise KitError("Section start and end are the same point.")
        half = along.GetLength() / 2.0
        direction = along.Normalize()
        transform = DB.Transform.Identity
        transform.Origin = DB.XYZ((start.X + end.X) / 2.0, (start.Y + end.Y) / 2.0, 0.0)
        transform.BasisX = direction
        transform.BasisY = DB.XYZ.BasisZ
        transform.BasisZ = direction.CrossProduct(DB.XYZ.BasisZ)
        box = DB.BoundingBoxXYZ()
        box.Transform = transform
        box.Min = DB.XYZ(-half, bottom, -self.ft(depth))
        box.Max = DB.XYZ(half, top, 0.0)
        created = DB.ViewSection.CreateSection(
            self.doc, self._view_family_type(DB.ViewFamily.Section).Id, box
        )
        self._finish_view(created, name or "Agent Section", template)
        return created

    def elevation(self, side="south", name=None, plan=None, offset=10.0, template=None):
        """A new exterior elevation of the whole model seen from ``side`` (south, north, east, west).

        The marker is placed ``offset`` feet outside the model's extents, on
        ``plan`` (default: a floor plan of the lowest level).
        """
        self._require_transaction("create views")
        if side not in _SIDES:
            raise KitError(
                "Elevation side must be one of %s." % ", ".join(sorted(_SIDES))
            )
        plan = self.view(plan) if plan is not None else self._plan_for(self.levels()[0])
        low, high = self._model_extents(None)
        centre = DB.XYZ((low.X + high.X) / 2.0, (low.Y + high.Y) / 2.0, 0.0)
        dx, dy = _SIDES[side]
        reach = (
            abs(high.X - low.X) * abs(dx) + abs(high.Y - low.Y) * abs(dy)
        ) / 2.0 + self.ft(offset)
        point = DB.XYZ(centre.X + dx * reach, centre.Y + dy * reach, 0.0)
        marker = DB.ElevationMarker.CreateElevationMarker(
            self.doc,
            self._view_family_type(DB.ViewFamily.Elevation).Id,
            point,
            plan.Scale,
        )
        wanted = DB.XYZ(dx, dy, 0.0)
        for index in range(4):
            created = marker.CreateElevation(self.doc, plan.Id, index)
            if created.ViewDirection.IsAlmostEqualTo(wanted):
                self._finish_view(
                    created, name or "Agent %s Elevation" % side.title(), template
                )
                return created
            self.doc.Delete(created.Id)
        raise KitError("Couldn't create a %s-facing elevation from the marker." % side)

    def orient(self, view3d, direction="southeast"):
        """Point a 3D view from a named direction (see :meth:`view3d`)."""
        self._require_transaction("orient views")
        if direction not in _DIRECTIONS:
            raise KitError(
                "Direction must be one of %s." % ", ".join(sorted(_DIRECTIONS))
            )
        view3d.SetOrientation(_orientation(DB.XYZ(*_DIRECTIONS[direction])))
        return view3d

    def look_at(self, view3d, eye, target):
        """Point a 3D view from ``eye`` toward ``target`` (points as tuples or XYZ)."""
        self._require_transaction("orient views")
        eye, target = self.xyz(eye), self.xyz(target)
        forward = (target - eye).Normalize()
        orientation = _orientation(forward)
        view3d.SetOrientation(
            DB.ViewOrientation3D(eye, orientation.UpDirection, forward)
        )
        return view3d

    def section_box(self, view3d, elements=None, padding=2.0):
        """Fit a 3D view's section box around ``elements`` or all model elements."""
        self._require_transaction("set section boxes")
        low, high = self._model_extents(elements)
        pad = self.ft(padding)
        box = DB.BoundingBoxXYZ()
        box.Min = DB.XYZ(low.X - pad, low.Y - pad, low.Z - pad)
        box.Max = DB.XYZ(high.X + pad, high.Y + pad, high.Z + pad)
        view3d.SetSectionBox(box)
        view3d.IsSectionBoxActive = True
        return view3d

    def crop_to(self, view, elements=None, padding=3.0):
        """Crop a plan, section or elevation to ``elements`` or all model elements."""
        self._require_transaction("crop views")
        low, high = self._model_extents(elements)
        pad = self.ft(padding)
        inverse = view.CropBox.Transform.Inverse
        corners = [
            inverse.OfPoint(DB.XYZ(x, y, z))
            for x in (low.X, high.X)
            for y in (low.Y, high.Y)
            for z in (low.Z, high.Z)
        ]
        box = view.CropBox
        box.Min = DB.XYZ(
            min(c.X for c in corners) - pad, min(c.Y for c in corners) - pad, box.Min.Z
        )
        box.Max = DB.XYZ(
            max(c.X for c in corners) + pad, max(c.Y for c in corners) + pad, box.Max.Z
        )
        view.CropBox = box
        view.CropBoxActive = True
        view.CropBoxVisible = False
        return view

    def model_only(self, view):
        """Hide every non-model category (levels, grids, annotations) in a view."""
        self._require_transaction("change view visibility")
        for category in self.doc.Settings.Categories:
            if (
                category.CategoryType != DB.CategoryType.Model
                and view.CanCategoryBeHidden(category.Id)
            ):
                view.SetCategoryHidden(category.Id, True)
        return view

    def hide(self, view, categories=None, elements=None):
        """Permanently hide categories (BuiltInCategory or ``"OST_..."`` names) and elements in a view.

        For a temporary preview, use the show_elements tool instead.
        """
        self._require_transaction("change view visibility")
        for value in _as_list(categories):
            category = self.category(value)
            if not view.CanCategoryBeHidden(category.Id):
                raise KitError(
                    "Category %r can't be hidden in view %r."
                    % (category.Name, view.Name)
                )
            view.SetCategoryHidden(category.Id, True)
        if elements:
            view.HideElements(
                List[DB.ElementId]([element.Id for element in _as_list(elements)])
            )
        return view

    def apply_template(self, view, template_name):
        """Apply a view template by name."""
        self._require_transaction("apply view templates")
        templates = [
            v
            for v in DB.FilteredElementCollector(self.doc).OfClass(DB.View)
            if v.IsTemplate
        ]
        for template in templates:
            if template.Name == template_name:
                view.ViewTemplateId = template.Id
                return view
        raise KitError(
            "No view template %r. Templates: %s."
            % (template_name, _listing(t.Name for t in templates))
        )

    # ---------------------------------------------------------- navigation
    def open(self, view):
        """Ask Revit to make ``view`` active once the script finishes.

        The switch happens after the run, so zoom the new view in a later call.
        """
        view = self.view(view)
        self.uidoc.RequestViewChange(view)
        return view

    def zoom_to(self, elements=None, padding=3.0):
        """Zoom the active view to ``elements`` (default: all model elements)."""
        low, high = self._model_extents(elements)
        pad = self.ft(padding)
        ui_view = self._active_ui_view()
        ui_view.ZoomAndCenterRectangle(
            DB.XYZ(low.X - pad, low.Y - pad, low.Z - pad),
            DB.XYZ(high.X + pad, high.Y + pad, high.Z + pad),
        )

    def zoom_fit(self):
        """Zoom the active view to fit everything visible."""
        self._active_ui_view().ZoomToFit()

    # --------------------------------------------------------------- internal
    def _require_transaction(self, action):
        if not self.doc.IsModifiable:
            raise KitError(
                "To %s, open a transaction first: with kit.transaction('name'): ... (in run_modify)."
                % action
            )

    def _types(self, type_class):
        return list(
            DB.FilteredElementCollector(self.doc)
            .OfClass(type_class)
            .WhereElementIsElementType()
        )

    def _symbols(self, category, family):
        collector = DB.FilteredElementCollector(self.doc).OfClass(DB.FamilySymbol)
        if category is not None:
            collector = collector.OfCategoryId(self.category(category).Id)
        return [s for s in collector if family is None or s.FamilyName == family]

    def _new_footprint_roof(self, footprint, level, roof_type):
        method = self.doc.Create.GetType().GetMethod("NewFootPrintRoof")
        arguments = System.Array[System.Object](
            [footprint, level, roof_type, DB.ModelCurveArray()]
        )
        roof = method.Invoke(self.doc.Create, arguments)
        return roof, arguments[3]

    def _check_rise(self, roof, level, offset, expected):
        base = self.level(level).Elevation + self.ft(offset)
        measured = roof.get_BoundingBox(None).Max.Z - base
        if measured < expected * 0.8 - 0.5 or measured > expected * 1.25 + 2.5:
            raise KitError(
                "Roof rise is %.2f ft but the pitch and span give %.2f ft: the slopes are on the wrong edges or the pitch is wrong."
                % (measured, expected)
            )

    def _view_family_type(self, family):
        for view_type in DB.FilteredElementCollector(self.doc).OfClass(
            DB.ViewFamilyType
        ):
            if view_type.ViewFamily == family:
                return view_type
        raise KitError("The document has no %s view type." % family)

    def _finish_view(self, view, name, template):
        view.Name = self._unique_view_name(name)
        if template:
            self.apply_template(view, template)

    def _unique_view_name(self, name):
        taken = set(
            v.Name for v in DB.FilteredElementCollector(self.doc).OfClass(DB.View)
        )
        candidate, counter = name, 2
        while candidate in taken:
            candidate = "%s (%d)" % (name, counter)
            counter += 1
        return candidate

    def _plan_for(self, level):
        for view in DB.FilteredElementCollector(self.doc).OfClass(DB.ViewPlan):
            if (
                not view.IsTemplate
                and view.GenLevel is not None
                and view.GenLevel.Id == level.Id
            ):
                return view
        raise KitError(
            "Level %r has no plan view; create one with kit.plan(level)." % level.Name
        )

    def _sketch_plane(self, elevation):
        plane = DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisZ, DB.XYZ(0, 0, elevation))
        return DB.SketchPlane.Create(self.doc, plane)

    def _model_extents(self, elements):
        if elements:
            candidates = _as_list(elements)
        else:
            unframed = self._unframed_category_names()
            candidates = [
                element
                for element in DB.FilteredElementCollector(
                    self.doc
                ).WhereElementIsNotElementType()
                if element.Category is not None
                and element.Category.CategoryType == DB.CategoryType.Model
                and not element.ViewSpecific
                and not isinstance(element, DB.Level)
                and element.Category.Name not in unframed
            ]
        low = high = None
        for element in candidates:
            if isinstance(element, DB.ElementId):
                element = self.doc.GetElement(element)
            box = element.get_BoundingBox(None) if element is not None else None
            if box is None:
                continue
            if low is None:
                low, high = box.Min, box.Max
                continue
            low = DB.XYZ(
                min(low.X, box.Min.X), min(low.Y, box.Min.Y), min(low.Z, box.Min.Z)
            )
            high = DB.XYZ(
                max(high.X, box.Max.X), max(high.Y, box.Max.Y), max(high.Z, box.Max.Z)
            )
        if low is None:
            raise KitError("Nothing to frame: no elements with a bounding box.")
        return low, high

    def _unframed_category_names(self):
        names = set()
        for built_in in _UNFRAMED_CATEGORIES:
            if not hasattr(DB.BuiltInCategory, built_in):
                continue
            category = DB.Category.GetCategory(
                self.doc, getattr(DB.BuiltInCategory, built_in)
            )
            if category is not None:
                names.add(category.Name)
        return names

    def _active_ui_view(self):
        active = self.uidoc.ActiveView.Id
        for ui_view in self.uidoc.GetOpenUIViews():
            if ui_view.ViewId == active:
                return ui_view
        raise KitError("The active view has no open window.")


class _Transaction(object):
    def __init__(self, doc, name):
        self._transaction = DB.Transaction(doc, name)

    def __enter__(self):
        self._transaction.Start()
        return self._transaction

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self._transaction.Commit()
        elif self._transaction.HasStarted() and not self._transaction.HasEnded():
            self._transaction.RollBack()
        return False


def name_of(element):
    """An element's name, including types whose ``Name`` IronPython can't read directly."""
    try:
        return element.Name
    except Exception:
        parameter = element.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
        return (
            parameter.AsString()
            if parameter is not None
            else DB.Element.Name.__get__(element)
        )


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if (
        isinstance(value, (DB.Element, DB.ElementId))
        or isinstance(value, str)
        or not hasattr(value, "__iter__")
    ):
        return [value]
    return list(value)


def _edges(points):
    points = list(points)
    return [
        (points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    ]


def _matching_edge(curve, edges):
    start, end = curve.GetEndPoint(0), curve.GetEndPoint(1)
    best, best_distance = None, None
    for index, (a, b) in enumerate(edges):
        a, b = Kit.xyz(a), Kit.xyz(b)
        distance = min(
            _plan_distance(start, a) + _plan_distance(end, b),
            _plan_distance(start, b) + _plan_distance(end, a),
        )
        if best_distance is None or distance < best_distance:
            best, best_distance = index, distance
    return best


def _plan_distance(p, q):
    return math.hypot(p.X - q.X, p.Y - q.Y)


def _orientation(direction):
    forward = direction.Normalize()
    right = forward.CrossProduct(DB.XYZ.BasisZ)
    if right.IsZeroLength():
        right = DB.XYZ.BasisX
    up = right.Normalize().CrossProduct(forward).Normalize()
    return DB.ViewOrientation3D(forward.Negate().Multiply(1000.0), up, forward)


def _listing(names):
    names = sorted(set(name for name in names if name))
    shown = ", ".join(names[:MAX_LISTED_NAMES])
    if len(names) > MAX_LISTED_NAMES:
        shown += ", ... (%d more)" % (len(names) - MAX_LISTED_NAMES)
    return shown or "(none)"


def _signature(function):
    function = getattr(function, "__func__", function)
    code = getattr(function, "__code__", None) or getattr(function, "func_code", None)
    if code is None:
        return "(...)"
    names = list(code.co_varnames[: code.co_argcount])
    defaults = getattr(function, "__defaults__", None) or ()
    if names and names[0] == "self":
        names = names[1:]
    parts = []
    first_default = len(names) - len(defaults)
    for index, name in enumerate(names):
        if index >= first_default:
            parts.append("%s=%r" % (name, defaults[index - first_default]))
        else:
            parts.append(name)
    if code.co_flags & 0x08:
        parts.append("**options")
    return "(%s)" % ", ".join(parts)
