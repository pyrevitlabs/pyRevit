# Extensions

Extensions are the tools and features users see inside Revit — mostly Python, but a bundle can also be C#/VB.NET, Ruby, a Dynamo graph, or a Grasshopper definition. Two kinds exist:

- **UI extensions** (`*.extension`) — ship buttons, panels, and tabs. This page covers their structure.
- **Library extensions** (`*.lib`) — plain Python packages other extensions can import; no bundle hierarchy.

See [Proposing an External Extension](custom_extension.md) for how to get a third-party extension listed in `extensions/extensions.json`.

## Bundle structure

Extensions follow this hierarchy:

```text
MyExtension.extension/
  extension.json          # optional extension-level manifest
  startup.py               # optional, runs once when the extension loads
  commands/                # optional, runner commands (*_command.py) for `pyrevit run`
  checks/                  # optional, preflight checks
  MyTab.tab/
    MyPanel.panel/
      MyButton.pushbutton/
        bundle.yaml         # button configuration
        script.py           # Python script (or .cs/.vb/.rb/.dyn/.gh/.ghx)
        icon.png             # button icon
```

Supported bundle types (folder postfix): `pushbutton`, `smartbutton`, `pulldown`, `splitbutton`, `splitpushbutton`, `panelbutton`, `stack`, `linkbutton`, `invokebutton`, `nobutton`, `content`, `urlbutton`, `combobox`.

???+ info

    Postfixes and every other constant on this page are defined in [pyrevit.extensions][] (`pyrevitlib/pyrevit/extensions/__init__.py`).

## Bundle files

A command bundle (e.g. `.pushbutton`) can contain:

- `*script.py` / `*script.cs` / `*script.vb` / `*script.rb` / `*script.dyn` / `*script.gh` / `*script.ghx` — the command's entry point; the file extension picks the [script engine](#script-engines).
- `*config.py` (or the matching extension for the script's language) — runs instead of `script.py` on a shift-click; falls back to `script.py` itself if absent.
- `bundle.yaml` — [metadata](#bundleyaml) for the button.
- `icon.png` — button icon; `on.png` / `off.png` for a toggle button's two states; `icon.dark.png` for a dark-theme variant.
- `tooltip.*` — media (image/gif) shown in the extended tooltip.
- `*help.*` — a help file linked from the tooltip.
- `lib/` — extra Python modules, auto-added to `sys.path` for this bundle's scripts.
- `bin/` — extra binaries/assemblies available to this bundle.
- `hooks/` — [event-driven scripts](#hooks) scoped to this bundle.

The same `lib/`, `bin/`, and `hooks/` folders are also recognized at the tab, panel, or extension level, where they apply to everything underneath.

## bundle.yaml

Common keys:

- `title`, `tooltip` — either a plain string or a map of locale (`en_us`, `fr_fr`, `ko`, ...) to string, for translations.
- `author` / `authors`, `help_url`.
- `context` — restricts when the button is enabled (active view, selected category, workset, etc.); see the context grammar in `pyrevit.extensions.genericcomps._parse_context_directives` or human friendly [here](https://pyrevitlabs.notion.site/Bundle-Context-630fa1f3611f4ee0aa15d290275e7ef3).
- `min_revit_version` / `max_revit_version`.
- `is_beta`, `highlight` (`new` or `updated`), `collapsed`.
- `engine` — `clean`, `full_frame`, `persistent`, `mainthread` (plus Dynamo-specific `automate`, `dynamo_path`, `dynamo_path_check_existing`, `dynamo_force_manual_run`, `dynamo_model_nodes_info`).
- `layout` — reorders/nests child buttons instead of relying on folder order; use `---` for a separator and `>>>` to start a slideout.
- `background` / `background_dark` — panel bundles only; see [Panel background colors](#panel-background-colors).

Bundle-type-specific keys: `modules` (link buttons), `assembly` / `command_class` / `availability_class` (invoke/link buttons), `hyperlink` (URL buttons).

???+ info

    The full key list lives in the `MDATA_*` constants in `pyrevitlib/pyrevit/extensions/__init__.py`, and is consumed by `_read_bundle_metadata()` in `pyrevitlib/pyrevit/extensions/genericcomps.py`. `extensions/pyRevitBundlesCreatorExtension.extension` has a worked `bundle.yaml` example per bundle type, and its own UI scaffolds new bundles interactively.

## Panel background colors

A `*.panel` bundle can paint its own background. `background` takes either one color for the main
panel surface, or a map naming each area:

```yaml
background: '#BB005591'
```

```yaml
background:
  panel: '#BB005591'
  title: '#E2A000'
  slideout: '#E25200'
```

Colors are `#RRGGBB` or `#AARRGGBB`.

`background_dark` takes the same two forms and applies when Revit runs in dark theme, the same way
`icon.dark.png` replaces `icon.png`. Its scalar form also sets only the main panel surface:

```yaml
background: '#BB005591'
background_dark: '#BB1E3A5F'
```

Each area falls back to its `background` color when `background_dark` leaves that area unset, so a
bundle can override the title bar alone. A bundle that declares `background_dark` only keeps the
stock Revit background in light theme. Switching theme in Revit repaints the panels without a
reload; on Revit 2021–2023 the theme API is unavailable, so `background_dark` is ignored and
`background` always applies.

## Script engines

The script engine is picked by the `script.*` file extension found in the bundle:

- `.py` — IronPython (default) or CPython, disambiguated by a `#! python3` shebang on the script's first line.
- `.cs` / `.vb` — compiled and run through the CLR engine.
- `.rb` — Ruby (IronRuby).
- `.dyn` — Dynamo graph.
- `.gh` / `.ghx` — Grasshopper definition.

Engine behavior (clean/full-frame/persistent/mainthread) is configured separately via the `engine:` block in `bundle.yaml`. See [Script engines](architecture.md#how-pyrevit-commands-run) in the architecture overview for how a button click reaches the engine at runtime.

## Extension manifest

`extension.json` at the extension root is optional; when present it can declare metadata (`name`, `description`, `author`, `url`, `image`, `dependencies`, ...) and a `templates` block used to substitute values into every `bundle.yaml` under the extension at load time. See `extensions/pyRevitDevHooks.extension/extension.json` for a real example.

This is different from the entry an extension gets in `extensions/extensions.json` (the catalog pyRevit's "Extensions" button reads from) — see [Proposing an External Extension](custom_extension.md) for that schema.

## Hooks

A `hooks/` folder (at the bundle, tab, panel, or extension level) can hold Python scripts named after a Revit/pyRevit event, e.g. `doc-opened.py`, `view-activated.py`, `command-before-exec[ID_INPLACE_COMPONENT].py` (the bracketed suffix scopes the hook to one command id). Each script runs whenever that event fires while the extension is loaded.

There is no exhaustive published list of event names — `extensions/pyRevitDevHooks.extension/hooks/` has one example script per supported event and is the most complete reference. Hook registration is handled by `pyrevitlib/pyrevit/loader/hooks.py`. A more detailed list of event names is published [here](https://pyrevitlabs.notion.site/Extension-Hooks-b771ecf65f6a45fe87ae12beab2a73a6).

## Runner commands

A `commands/` folder at the root of a UI extension holds scripts that the CLI can run against Revit models without a ribbon button. A file is a runner command when it ends in `_command.py` (case-insensitive); its name is the file name without that trailing postfix, so `commands/list_views_command.py` is the command `list_views` and `Foo_Command.PY` is the command `Foo`. Other files in the folder, and subfolders, are ignored. The constants are `ExtensionUICommandsDirName` and `ExtensionUICommandPostfix` in `PyRevitConsts.cs`, and the scan is `PyRevitExtension.GetCommands()`.

```text
pyrevit run commands                              # list the commands of every registered clone and installed extension
pyrevit run list_views "C:\models\house.rvt"      # run a command by name on a model
pyrevit run list_views --models=models.txt --revit=2026   # run it on every model listed in a text file, one path per line
pyrevit run C:\scripts\one_off.py "house.rvt"     # a path to a .py file runs that script instead of looking up a command
pyrevit run list_views --revit=2026 --inputs="{\"level\": \"L1\"}"   # hand the script a JSON object as __inputs__
pyrevit run list_views --revit=2026 --inputs-file=inputs.json          # the same, read from a JSON file
```

- The name lookup is case-insensitive. It searches the extensions of the clone attached to the target Revit first, then installed extensions. The first match wins; when a later extension defines the same command name, `pyrevit run` prints a warning to standard error naming the file that runs and the file it shadows.
- The runner starts Revit from a generated journal with the attached pyRevit and quits Revit when the script ends. Without `--revit`, the Revit version comes from the model, or is the newest installed; the `--models` form always requires `--revit`.
- The script runs in a full-frame engine with output windows suppressed; what the script prints and logs (`script.get_logger()`) goes to the run's log file. Besides the usual builtins it gets `__models__` (the model paths passed on the command line), `__batchexec__` (`True`) and `__logfile__` (the run's log file).
- `--inputs=<json>` or `--inputs-file=<path>` hands the script structured input, like `pyrevit agent run --inputs`. The text must be a JSON object; the CLI refuses anything else before Revit starts. The script gets it as `__inputs__`, the JSON text (`"{}"` when neither option is passed), so `inputs = json.loads(__inputs__)` works the same on every engine. The text travels in the journal, so keep it small and pass larger data by path.
- The script opens the models itself (`HOST_APP.app.OpenDocumentFile(path)`) and is responsible for saving and closing them. Error dialogs are dismissed automatically unless `--allowdialogs` is passed.

`extensions/pyRevitDevTools.extension/commands/list_views_command.py` is the reference example.

## Preflight checks

A `checks/` folder at the root of a UI extension holds [preflight][pyrevit.preflight] checks: model-quality scripts offered by the *Preflight Checks* button in pyRevitTools. Only files ending in `_check.py` (case-insensitive) are imported, at the time the dialog opens. `checks/` is not on `sys.path`, and the checks are loaded with the import path of the Preflight Checks button, which belongs to pyRevitTools. A check can import from `pyrevitlib` and from pyRevitTools' own `lib/` folders, but a check in any other UI extension cannot import from that extension's `lib/`; a failing import raises in the loader and the dialog does not open. Keep checks from other extensions self-contained. Other file types (JSON data, `locale/` resources) can stay in `checks/`; the loader ignores them and the checks read them by path.

Each class in a file that derives from `pyrevit.preflight.PreflightTestCase` becomes one entry in the dialog:

- The entry name is the class attribute `name`, or, when `name` is absent, the file name with the trailing `_check.py` removed (`model_check_views_check.py` becomes `model_check_views`).
- The class docstring is required. Its first line is the subtitle and the remaining lines are the description; a missing docstring is logged as an error.
- The optional class attribute `author` overrides the extension's author.
- `setUp(doc, output)`, `startTest(doc, output)`, `tearDown(doc, output)` and `doCleanups(doc, output)` run in that order on a fresh instance against the active document. An exception in any of them aborts the run, so `tearDown` and `doCleanups` are skipped after a failure; don't rely on them for cleanup that must always happen.

Checks from all enabled UI extensions are merged into one list; a disabled extension, such as the default-disabled pyRevitDevTools, contributes none. `extensions/pyRevitDevTools.extension/checks/view_count_check.py` is the reference example, and the checks in `extensions/pyRevitTools.extension/checks/` show localized, multi-check files.

## The `__revit__` host handle

Every script pyRevit runs — commands, event hooks, smart buttons, combo boxes — gets a `__revit__` builtin. The contract is:

> `__revit__` is an `Autodesk.Revit.UI.UIApplication` wherever a usable session handle exists, and `None` only outside a Revit host.

Revit hands subscribers four unrelated application types depending on the event that fired: `UIApplication`, `Application`, `UIControlledApplication` and `ControlledApplication`. Every `Application_*` hook is registered on `uiApp.Application`, so its sender is DB-only.

`PyRevitLabs.PyRevit.Runtime.RevitAppResolver` funnels every handle into one shape before it reaches a script:

| `__eventsender__` type | How `__revit__` is derived |
|---|---|
| `UIApplication` | used as-is, and remembered as the session handle |
| `Application` | wrapped in a new `UIApplication` |
| `UIControlledApplication` | unwrapped from its private `m_uiapplication` field, same one the session loader reflects at startup |
| `ControlledApplication`, anything else, `None` | the session handle recorded at session load |

The session handle is seeded first-write-wins, so a handle Revit may invalidate when its event returns can never displace the one that stays valid for the whole process.

`__revit__` is not going away — too much third-party code depends on it. New code should prefer `HOST_APP.uiapp` / `HOST_APP.app`, which are the same object behind a named accessor.

### DB-only event hooks

`__revit__` is always live in an `Application_*` hook, but "live" is not "fully usable": Revit does not guarantee `UIApplication.ActiveUIDocument` while a DB-only event is still running. The documented behaviour, which the pyrevit accessors implement, is:

| Accessor | DB-only `Application_*` hook | Where to get the document instead |
|---|---|---|
| `HOST_APP.uiapp`, `HOST_APP.app` | a working `UIApplication` / `Application` | — |
| `HOST_APP.uidoc`, `HOST_APP.doc` | `None` | `EXEC_PARAMS.event_doc`, or `revit.doc` (which falls back to it) |
| `__eventsender__` | the raw sender, exactly as Revit sent it | — |

Scripts that type-switch on `__revit__` to discover what fired the hook should switch on `__eventsender__` instead — that is the value normalization never touches.

`extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel/Engine Tests.pulldown/lib/revithandle.py` reports all of the above for a live run. The *Test IronPython Revit Handle* and *Test CPython Revit Handle* pushbuttons run it through the runtime engines, under each engine; *Test Smart Button Revit Handle* runs it through `ScriptExecutor`, the other of the two sites that inject the builtin. `extensions/pyRevitDevHooks.extension/lib/hooks_logger.py` records the handle and sender type on every development-hook log line, so `hooks.log` shows the same thing for all hook contexts.
