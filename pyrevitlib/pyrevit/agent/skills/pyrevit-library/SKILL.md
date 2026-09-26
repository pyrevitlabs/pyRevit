---
name: pyrevit-library
description: Map of the shared Python libraries every script can import, pyrevitlib (pyrevit.revit) and rpw, and how to find a function in them. Read it before writing raw Revit API code for lookups, element or view creation, parameters, units, transactions or navigation.
---

# pyrevitlib and rpw

pyRevit ships two maintained libraries that agent scripts can import on every engine. Use them first: their functions handle version differences, engine quirks and the Revit API traps agents fall into. Write raw `DB.` code only for what they don't cover.

## Finding a function

`lookup_pyrevit_api` searches both libraries from their source, without Revit:

- `lookup_pyrevit_api(query="section box")` searches names and docstrings.
- `lookup_pyrevit_api(query="create_gable_roof")` returns the signature, the full docstring and the import line.
- `lookup_pyrevit_api(query="pyrevit.revit.db.create")` lists a module.

When a script fails on a name from these libraries, the error hint lists similar names.

## Where things live

```python
from pyrevit import revit
from pyrevit.revit.db import query, create, update
from pyrevit.revit import units, ui
```

| Need | Use |
|---|---|
| Transaction | `with revit.Transaction("name"):` rolls back and re-raises on an exception |
| Current document, view, selection | `revit.doc`, `revit.uidoc`, `revit.active_view`, `revit.get_selection()` |
| Levels, types, family types, views by name; raises with the valid names | `query.find_level`, `query.find_type(DB.WallType, "name")`, `query.find_family_symbol("36\" x 84\"", family_name=..., category="OST_Doors")`, `query.find_view`, `query.find_plan_view(level)` |
| Other lookups (return None or a list when nothing matches) | `query.get_types_by_class`, `query.get_family_symbol`, `query.get_all_views`, `query.get_view_by_name`, `query.get_category("OST_Walls")`, `query.get_elements_by_categories`, `query.get_param`, `query.get_sheets`, `query.get_elements_by_parameter`… |
| Extents | `query.get_elements_bounding_box(elements)`, `query.get_model_elements()` |
| Walls, floors, ceilings, rooms, room separation, model lines | `create.create_wall(s)`, `create.create_floor`, `create.create_ceiling`, `create.create_room`, `create.create_room_separation_lines`, `create.create_model_lines` |
| Roofs | `create.create_gable_roof`, `create_hip_roof`, `create_shed_roof`, `create_footprint_roof`; `update.attach_wall_tops(walls, roof)` |
| Doors, windows, furniture, columns | `create.place_hosted_instance`, `create.place_family_instance`, `create.create_column` |
| Views | `create.create_plan_view`, `create_model_3d_view`, `create_section_view`, `create_elevation_view` |
| Drawings | `query.get_face_references(element, direction)`, `create.create_dimension`, `create.tag_elements`, `create.create_room_tags`, `create.create_schedule`, `create.create_sheet`, `create.place_on_sheet` |
| View framing and visibility | `update.set_section_box`, `update.orient_3d_view`, `update.set_3d_view_camera`, `update.crop_view_to_elements`, `update.set_crop_region`, `update.hide_non_model_categories`, `update.hide_categories` |
| Navigation | `ui.request_view_change(view)`, `ui.zoom_to_elements(elements)`, `ui.zoom_fit()` |
| Units | `units.parse_length("32'-6\"")` (feet), `units.parse_slope("8:12")` (rise over run), `units.format_length(value)` |
| Parameters | `query.get_param(element, name)`, `update.update_param_value(param, value)` |
| Element ids across Revit versions | `from pyrevit.compat import get_elementid_value_func` |
| Wrappers with a friendlier API | `from rpw import db`: `db.Collector(of_class="Wall", is_not_type=True)`, `db.Element(element).parameters["Comments"].value`, `db.Room`, `db.Wall`, `db.View`, graphic overrides |

Functions that create elements take points as `DB.XYZ` or `(x, y[, z])` tuples, and lengths as feet or strings such as `32'-6"` and `900mm`. Types, levels and family types can be passed by name.

## Rules

- **Libraries first, raw API second.** Look the task up with `lookup_pyrevit_api` before writing `DB.` code for it.
- **Prefer `find_*` to `get_*` in agent scripts.** `get_*` returns None and the script carries on; `find_*` stops with the names that exist.
- **Don't use `pyrevit.forms` or `rpw.ui.forms`.** Agent runs have no user to answer a dialog.
- **Report library gaps.** If a common step has no function, say so in your answer; the maintainers add missing functions to the libraries.
