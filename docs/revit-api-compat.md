# Revit API compatibility lint

pyRevit scripts run unchanged across many Revit years, but the Revit API
does not stay put: members are added, deprecated, and removed (for example
`ElementId.IntegerValue` disappears in 2026, `DisplayUnitType` after 2021,
`BuiltInParameterGroup` after 2024). `dev/scripts/check_revit_api_compat.py`
is a static checker that finds uses of such APIs that are not protected for
every Revit year the code can run in.

It is plain CPython 3.10+ with no dependencies. It parses code with `ast`
and never imports or runs it, so it works without Revit, in CI, and on any
third-party extension. Older interpreters exit with code `2`: the findings
are matched against the baseline by message, so the analysis must read every
file the same way on every interpreter, and `match` statements only parse
from 3.10.

The build runs it as part of `dotnet run -- ci` (`CheckRevitApiCompatModule`),
after version stamping, so a local build gates on it too and CI needs no extra
step. The module also fails when `catalog.json` does not cover exactly the
Revit years `dev/Directory.Build.targets` builds for. Its tests live in
`dev/scripts/test_standalone_revit_api_compat.py`, which CI runs with the
other standalone suites.

## Running it

| Command | What it lints |
|---------|---------------|
| `pipenv run check-revit-api` | The CI targets, `extensions/pyRevitTools.extension` and `pyrevitlib`, against the committed baseline |
| `python dev/scripts/check_revit_api_compat.py path/to/My.extension` | Any files or folders |
| `... --git-url https://github.com/org/repo.git [--git-ref tag]` | A shallow clone in a temp dir (repeatable) |
| `... --extensions all` | Every extension listed in `extensions/extensions.json` |

Useful flags:

- `--revit-years 2023-2027`: the years an unconstrained script must support.
  The default is every cataloged year (2021 onward).
- `--format text|json|github`: `github` prints workflow annotations.
- `--strict` fails on warnings too. `--errors-only` hides warnings.
- `--exclude GLOB` skips files.

Exit code `0` means clean, `1` means errors were found (or warnings with
`--strict`), and `2` means a usage or I/O problem. That includes any
failed clone, because the scan is then incomplete. Clones are only parsed. No
hooks, submodules, or scripts from them run.

## When is a use protected?

Each line is analyzed with the set of Revit years it can execute in. A use
is reported only for years in that set where the API does not exist.

1. **Bundle metadata.** The analysis starts from the script's effective
   `min_revit_version`/`max_revit_version`. These are intersected over the
   extension root and every parent bundle. A bundle.yaml value wins over the
   script's `__min_revit_ver__`/`__max_revit_ver__`, the same precedence the
   C# loader (`ExtensionParser.cs`) applies. Code under an extension's `lib/`
   inherits the extension root's range.
2. **Runtime version checks** narrow the set inside their branch:
   `HOST_APP.is_newer_than(v[, or_equal])`, `is_older_than(v)` and
   `is_exactly(v)`, plus comparisons of a version value with a year
   (`revit_version > 2022`, `int(app.VersionNumber) >= 2024`) and
   `pyrevit.compat.NETCORE`/`NETFRAMEWORK`. Narrowing also works through
   `and`/`or`/`not`, ternaries, flags such as
   `IS_2022 = HOST_APP.is_newer_than(2021)`, and early exits (`return`,
   `raise`, `script.exit()`, `forms.alert(..., exitscript=True)`).
3. **Feature detection** narrows by what it actually probes:
   - `hasattr(obj, "X")` or `getattr(obj, "X", default)` (also through a
     variable holding the result, e.g. `if probe is None: raise`): uses of
     `X` itself are protected in the true branch, even in years where only
     some updates have `X`. That branch is limited to the years `X` exists,
     and the false branch to the years it does not. Other APIs in either
     branch are still checked: probing `ColorFillScheme` does not cover
     `STEPImportOptions`.
   - A `try` whose handler catches `AttributeError`, `ImportError`,
     `TypeError` or `Exception`, or is bare, absorbs failures in its body.
     Its handlers are checked only for the years something cataloged in the
     body is missing, and code after a `try` that returns on success gets
     the same treatment. If nothing cataloged can fail in the body, the
     handlers are checked for every year.

   Flags and probe variables resolve per function scope, so a name bound in
   one function never answers for another.

Helpers that already contain the version branch don't trigger findings, so
prefer them:

- `pyrevit.compat.get_elementid_value_func()` and
  `get_elementid_from_value_func()`
- `pyrevit.revit.db.ensure.revision_has_numbertype()`
- `pyrevit.revit.units`
- `pyrevit.revit.db.ParamDef`

Deprecation warnings are skipped inside a version branch: the author has
already handled the version there.

## Findings

| Code | Severity | Meaning |
|------|----------|---------|
| `API-MISSING` | error | A type or member is used in a year where it does not exist |
| `API-OVERLOAD` | error | A call passes a Revit type that no remaining overload accepts (e.g. `BindingMap.Insert(..., BuiltInParameterGroup)` after 2024) |
| `API-DEPRECATED` | warning | Used in a year where it is `[Obsolete]` |
| `DOTNET` | error/warning | A .NET Framework API used where Revit runs on .NET 8+ (2025+) |
| `ENGINE` | error | An IronPython-only module (`wpf`) in a `#! python3` script |
| `BUNDLE` | error | `min/max_revit_version` is not a 4-digit year, so the loader hides the component |
| `PARSE` | warning (error for `#! python3`) | The file is not Python 3 syntax and was not analyzed. See `check_py3_compat.py` |
| `SUPPRESS` | error/warning | A `compat-ignore` without a reason (error) or one that suppresses nothing (warning) |

Each finding includes a fix: the replacement API or pyRevit helper, a
`HOST_APP` guard with the right year, and, inside a bundle, the
`min_revit_version`/`max_revit_version` that would scope it.

**How references are matched.** References resolved to a qualified type
(`DB.X`, `from Autodesk.Revit.DB import X`, star imports, `pyrevit`/`rpw`
re-exports) are exact.

A bare attribute such as `elem.IntegerValue` has no type information. It is
reported only when no Revit type offers that name in the failing years. For
example, `Value` is skipped because other Revit types have it in every year.
Names that also exist on .NET types (`ShowDialog`, `FileName`, ...) are
skipped as well. `overrides.json` can re-enable a name, demote it to a
warning, or exempt receivers by pattern. For instance, `workset.Id.IntegerValue`
is exempt because `WorksetId.IntegerValue` still exists.

An instance entry has three states for `match`: absent leaves the catalog's
verdict alone, `false` disables the name, and `true` re-enables a name the
catalog marks as shared with .NET (`bcl`). `ParameterType` relies on `true`,
since `System.Reflection.ParameterInfo` has it too but scripts almost always
mean `Definition.ParameterType`. Removing a `match: true` silently drops that
coverage.

`receiver_exempt` is a regular expression searched in the receiver's last
identifier, ignoring a trailing `.Id`: `workset.Id` is tested as `workset`.
Anchor it with `$`, so `field_element` is not exempted by `field`.

Attributes a local class defines are not Revit API uses inside that class or on
variables built from it (`w = Wrapper(); w.GetDataType()`). A class declaring
the name does not hide its use on any other receiver.

## Suppressing a finding

Put a justified pragma on the line, or anywhere in the statement's header
(so formatter reflows keep it attached):

```python
class Handler(UI.ITemporaryGraphicsHandler):  # compat-ignore: only imported on 2022+
value = eid.IntegerValue  # compat-ignore[API-MISSING]: reached only on Revit 2023
```

A pragma without a reason is an error, and an unused one is a warning.

## Baseline

`revit_api_catalog/baseline.json` lists the findings that existed when the
lint was introduced, so CI fails only on new ones. Entries match on path,
code and message, not line numbers. After fixing some, run:

```bash
python dev/scripts/check_revit_api_compat.py --baseline --update-baseline
```

Don't add entries by hand. A new finding needs a fix or a justified
suppression.

## The API catalog

The checker reads two files in `dev/scripts/revit_api_catalog/`:

- `catalog.json` is **generated**. It holds facts read from Autodesk's own
  assemblies. For every Revit year from 2021, the earliest and the newest
  `Nice3point.Revit.Api.RevitAPI`/`RevitAPIUI` NuGet packages are diffed:
  - the years each public type and member exists, inherited members included
    (moving a member to a base class is not a removal)
  - the first year it carries `[Obsolete]`, with Autodesk's message, which
    usually names the replacement
  - overloads whose Revit-typed parameters went away while the name survived

  It also flags instance member names that collide with the .NET 8 BCL and
  Windows Desktop reference packs. Scraped documentation is used only for
  context. The assemblies are the ground truth for when something exists.
- `overrides.json` is **curated**. It holds what assemblies cannot express:
  - pyRevit helper hints
  - fix wording
  - ambiguity tiers and receiver exemptions
  - .NET runtime entries (e.g. `AppDomain.CreateDomain`, `BinaryFormatter`)
  - engine entries

  It is merged at load time, so editing it needs no regeneration.

Users run any update of a year, so a year counts as available only when its
first and its latest update both have the API. Years where only one of them
does are stored as `partial` and linted as missing. For example,
`STEPImportOptions` arrived in a 2024 update. The fix hint then points to
`hasattr(...)`, because a `HOST_APP` year check cannot tell updates apart.
Overload changes are read from each year's latest update only.

### Regenerating (on demand)

Regeneration is a maintenance step, never part of a lint run. Do it when a
new Revit release (or an update that deprecates API) ships:

```bash
pip install dnfile
python dev/scripts/build_revit_api_catalog.py
python -m unittest discover -s dev/scripts -p test_standalone_revit_api_compat.py
python dev/scripts/check_revit_api_compat.py --baseline
```

It downloads about 100 MB of packages (cached under the system temp dir,
`--cache-dir` to change) and takes a few minutes. `dnfile` is deliberately
not in the Pipfile because only this step needs it. Review the
`catalog.json` diff like code. `ShippedCatalogTests` pins the known breaks, so
a surprising change there fails loudly.

### Verifying in Revit

The DevTools button **Unit Tests > Revit API Catalog Tests**
(`pyrevitlib/pyrevit/unittests/test_revit_api_catalog.py`; **Run All Tests**
leaves it out because it resolves hundreds of types) checks, inside the running Revit, that every cataloged
type and member exists exactly when the catalog says it does. `partial`
years are not checked, because the answer depends on the installed update.
Failures name the running update (e.g. `Revit 2024.2`). Run it in each Revit
version you have after regenerating. It needs a clone, because installers
don't ship `dev/`.

## Limits

- There is no type inference. An ambiguous bare attribute is skipped rather
  than guessed, so some real breaks on shared names go unreported (e.g.
  `rev.NumberType` is only a warning).
- Guards are followed within a function, not across calls. A helper that is
  only called under a version check needs a guard of its own or a justified
  suppression. The same goes for a fallback the analysis cannot connect to
  its failing attempt, e.g. one that depends on the receiver's type.
- IronPython 2-only syntax (`print "x"`) cannot be parsed by CPython's `ast`.
  Those files are reported as `PARSE` warnings and skipped.
- The Python 2 vs 3 language axis is covered by
  `dev/scripts/check_py3_compat.py`, not here.
