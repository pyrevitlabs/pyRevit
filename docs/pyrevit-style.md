# Writing pyRevit-style code

What a pyRevit script should look like, for new contributors and for AI agents. The rule behind everything below: **use `pyrevit` first, drop to raw Revit API only for what it doesn't cover.** The library already absorbs Revit-version differences, engine quirks, and API traps.

## The shape of a button script

```python
# -*- coding: utf-8 -*-
"""Lists all sheets revised under any revision."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.revit import query

logger = script.get_logger()
output = script.get_output()


def collect_revised_sheets():
    sheets = query.get_elements_by_categories([DB.BuiltInCategory.OST_Sheets])
    return sorted(
        (sheet for sheet in sheets if sheet.GetAllRevisionIds()),
        key=lambda sheet: sheet.SheetNumber,
    )


def main():
    sheets = collect_revised_sheets()
    if not sheets:
        forms.alert("No revised sheets found.", exitscript=True)

    for sheet in sheets:
        output.print_md("**{}** {}".format(sheet.SheetNumber, output.linkify(sheet.Id)))


main()
```

- Titles, tooltips, icons and authorship belong in `bundle.yaml` next to `script.py` (see [Extensions](extensions.md)).
- Module-level handles come first and are named the same everywhere: `logger`, `output`, and `selection` when needed. Don't invent alternatives.
- Logic lives in small functions. The entry point is a `main()` called at the bottom of `script.py`.
- Helpers a script outgrows go in separate modules next to `script.py` in the bundle folder (it is on `sys.path` automatically), rather than into one 1500-line file. A `lib/` subfolder is optional.

## Imports

```python
from pyrevit import forms, script  # helpers
from pyrevit import HOST_APP  # constants
from pyrevit import revit, DB, UI  # wrappers
from pyrevit.revit import query, create, update
from pyrevit.compat import get_elementid_value_func
```

- `DB` and `UI` come from `pyrevit`, never `import Autodesk.Revit.DB` or `clr.AddReference("RevitAPI")`.
- Standard library first, then `pyrevit`, then bundle-local modules, separated by blank lines.
- .NET types come from `pyrevit.framework`, not from `System` directly: `from pyrevit.framework import List, Dictionary, ObservableCollection, Forms, Drawing, Media, Path, File`. The module already loads the right assemblies for the running Revit (.NET Framework vs .NET 8/10) and engine, so the import works everywhere instead of only where you tested it. It re-exports the common `System`, `System.Collections.Generic`, `System.IO`, `System.Windows` and `System.Windows.Forms` types. Check there before writing `from System... import`, e.g. `from pyrevit.framework import List` instead of `from System.Collections.Generic import List`.
- Within the `pyrevit` imports, group by role on separate lines and label each group with a trailing comment: `helpers` (what the script uses to talk to the user), `constants` (host and environment facts), `wrappers` (what it uses to talk to Revit). This is the one place trailing comments are wanted. Reading the block tells you at a glance what a script touches, and keeps `from pyrevit import ...` from turning into one long unsorted line.

## Use the library before writing raw API

| Need | Use |
|---|---|
| Document, view, selection | `revit.doc`, `revit.uidoc`, `revit.active_view`, `revit.get_selection()` |
| Transaction | `with revit.Transaction("Name"):` |
| Finding things | `revit.query.*` (`get_types_by_class`, `get_param`, `get_name`, `get_all_views`, ...) |
| Creating things | `revit.create.*` (walls, floors, views, sheets, tags, legends, ...) |
| Changing things | `revit.update.*` (`update_param_value`, `set_section_box`, ...) |
| Element id as int across Revit versions | `get_elementid_value_func()` from `pyrevit.compat` |
| Version branches | `HOST_APP.is_newer_than(2021)`, `HOST_APP.is_older_than(...)`, `HOST_APP.is_exactly(...)` |

Search before you write: `pyrevit.revit.db.query`, `create` and `update` hold hundreds of helpers. Reaching for `FilteredElementCollector` to find a level, a family symbol or a view by name usually means a `query.find_*` / `query.get_*` function already exists.

## Transactions

- Always use the context manager. Never call `Start()` / `Commit()` by hand.
- `revit.Transaction` rolls back and re-raises on exception.
- Group related edits with `revit.TransactionGroup`.
- Read-only work needs no transaction. Don't open one "just in case".
- Keep transactions short. Gather first, then open one transaction and apply.

```python
with revit.Transaction("Rename sheets"):
    for sheet in sheets:
        sheet.Name = new_name_for(sheet)
```

## User interaction

Use `pyrevit.forms` for every prompt instead of building WinForms/WPF by hand.

```python
forms.check_selection(exitscript=True)
views = forms.select_views(multiple=True)
choice = forms.CommandSwitchWindow.show(["Option A", "Option B"], message="Pick one:")
picked = forms.SelectFromList.show(items, multiselect=True, name_attr="Name")
forms.alert("Done.", sub_msg="3 sheets updated.")
```

- A cancelled dialog returns a falsy value. Check it and call `script.exit()` or `forms.alert(..., exitscript=True)`.
- Validate preconditions up front with `forms.check_*` helpers (`check_selection`, `check_modeldoc`, `check_workshared`, `check_viewtype`, ...).
- Larger dialogs: subclass `forms.WPFWindow` with a sibling `.xaml` file.
- Long loops get a `forms.ProgressBar`.

## Output

- Use `output = script.get_output()` and `output.print_md(...)` for results. Plain `print` is fine for one-liners.
- Make elements clickable with `output.linkify(element.Id)`.
- Report problems with `logger.error(...)` / `logger.warning(...)`, never silent `except: pass`.
- Escape user-controlled text before HTML output with `coreutils.escape_for_html`.

## Settings and data files

- Persisted user settings: `script.get_config("section")`, then `script.save_config()`.
- Per-script data files: `script.get_data_file(...)`, `script.get_instance_data_file(...)`. Never hardcode paths.
- Bundle-relative files: `script.get_bundle_file("name.ext")`.

## Python compatibility

Scripts run on IronPython 2.7 by default, and can also run on CPython 3 and IronPython 3.4.

- Use `"...{}".format(x)`. f-strings only in scripts that start with a `#! python3` shebang.
- No `print x`, `iteritems()`, `xrange`, `basestring`, `unicode`.
- `six` ships bundled in `site-packages/` and can be imported on every engine (`import six`, `six.iteritems(d)`, `six.string_types`) when you need code that runs on both Python 2 and 3.
- Run `pipenv run check-py3 <path>` to catch portability issues.

## Style rules

Conventions from [AGENTS.md](https://github.com/pyrevitlabs/pyRevit/blob/develop/AGENTS.md). Only `ruff format` is automated; the rest is checked in review:

- **No inline comments.** Make the code self-explanatory with names and small functions. Exceptions: tooling pragmas (`# noqa`, `# type: ignore`), `TODO` / `FIXME` with an owner and ticket, and the group labels on `pyrevit` imports (see [Imports](#imports)).
- **Docstrings on public symbols only**, Google style, and only where they add what the code can't say: purpose, contract, side effects, exceptions, invariants. Don't restate the signature.
- `ruff format` formats Python on commit. Run `pipenv run ruff check --fix <path>` before finishing.
- Names: `snake_case` functions and variables, `PascalCase` classes, `UPPER_CASE` constants. Revit API members keep their original `PascalCase`.
- Prefer early returns over deep nesting. Prefer `for`/comprehensions over `map`/`filter` chains.

## Anti-patterns

| Don't | Do |
|---|---|
| `clr.AddReference("RevitAPI")` + `from Autodesk.Revit.DB import *` | `from pyrevit import DB` |
| `__revit__.ActiveUIDocument.Document` | `revit.doc` |
| `t = Transaction(doc, "x"); t.Start() ... t.Commit()` | `with revit.Transaction("x"):` |
| `System.Windows.Forms.MessageBox.Show` | `forms.alert` |
| `from System.Collections.Generic import List` | `from pyrevit.framework import List` |
| Hand-rolled collector to find a level/view/type by name | `query.find_level`, `query.find_view`, `query.find_type` |
| `element.Id.IntegerValue` | `get_elementid_value_func()(element.Id)` |
| `if revit_version == "2022": ...` string compares | `HOST_APP.is_newer_than(2021)` |
| `except: pass` | catch the specific exception and `logger.error(...)` |
| One 1500-line `script.py` | `main()` plus helper modules next to `script.py` |

## For AI agents

- Look a function up before writing it: search `pyrevitlib/pyrevit/revit/db/{query,create,update}.py`, or use the MCP `lookup_pyrevit_api` tool.
- Prefer `find_*` helpers over `get_*` in unattended runs: they stop with the list of valid names instead of returning `None`.
- Don't use `pyrevit.forms` in unattended agent runs. There is no user to answer.
- Match the surrounding file's style over this guide when they conflict, and keep pre-existing comments.
- Before finishing: `pipenv run ruff check --fix <path>`, `pipenv run check-py3 <path>`, and test the button in Revit with a dev clone (see [Developer guide](dev-guide.md)).
