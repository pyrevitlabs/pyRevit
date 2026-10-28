# Understanding pyRevit Architecture

This guide provides an overview of pyRevit’s architecture to help new contributors understand how the software works.

Whether you want to create tools, troubleshoot issues, or contribute code, understanding these components will help you navigate the project.

## Components of pyRevit

1. **pyRevit Add-In (pyRevitLoader)** — `dev/pyRevitLoader/`
    - A small piece of C# code that starts pyRevit inside Revit.
    - Calls the C# session manager directly to build the UI and button commands (no IronPython bootstrap).

2. **pyRevit Python Libraries (pyrevitlib)** — `pyrevitlib/pyrevit/`
    - Python packages that simplify working with the .NET Revit API.
    - Provide tools to create ribbon buttons, run scripts, and more.

3. **Extensions** — see [Extensions](extensions.md) for bundle structure, `bundle.yaml`, script engines, and hooks.
    - These are the tools and features users see inside Revit.
    - They are mostly written in python, but can also be C#/VB.NET scripts, dynamo projects, and so on
    - Bundled extensions appear in the "pyRevit" tab, offering many tools.
    - Users can add extensions by:
        - Enabling listed extensions in `extensions/extensions.json` via the "Extensions" button in pyRevit.
        - Creating custom extensions and adding their paths to the configuration.

4. **pyRevit Command-Line Interface (CLI)** — `dev/pyRevitLabs/pyRevitCLI/`
    - A tool for managing configurations, running scripts in bulk, and troubleshooting.
    - Useful for corporate setups and advanced users.
    - The `pyrevit env` report includes the configured CPython engine version (`activeCpythonEngineVersion` in JSON).

5. **Telemetry Server**
    - A small server (written in Go) that tracks usage data of pyRevit tools.
    - Stores data in MongoDB or PostgreSQL for business intelligence.

6. **Agent runtime** (experimental) — `dev/pyRevitLabs.PyRevit.Runtime/Agent/`, `pyrevitlib/pyrevit/agent/`, `pyrevit mcp`
    - Lets MCP-capable coding agents run Python in a live Revit session through a local named pipe, with every model change approved in Revit.
    - See [Agent runtime](agent-runtime.md).

Command execution itself lives in a separate component, **PyRevit.Runtime** (`dev/pyRevitLabs.PyRevit.Runtime/`) — see [How pyRevit Commands run](#how-pyrevit-commands-run).

## How pyRevit Loads in Revit

!!! tip "TL;DR:"

    - Revit reads the `.addin` manifest in the Addins folders
    - The `.addin` manifest points to `pyRevitLoader.dll`
    - `pyRevitLoader.dll` calls the C# session manager to build the UI and the button commands
    - The C# session manager runs `session_preload.py` / `session_postload.py` to drive the Python services that have not yet been ported to C#

### .addin Manifest

- The installer creates a file with `.addin` extension, called manifest, in the Revit Addins folder, instructing Revit to load pyRevit when it starts.
- The Addins folder can be located in one of these paths, depending on pyRevit installation:
    - `C:\ProgramData\Autodesk\Revit\Addins` (for all users)
    - `%APPDATA%\Autodesk\Revit\Addins` (for the current user only)
- The manifest points to `pyRevitLoader.dll`, which acts as the entry point for pyRevit.

### pyRevitLoader.dll

The `pyRevitLoader.dll` file is a small C# program that:

- Ensures required .NET assemblies are loaded.
- Calls the C# session manager to load the session.

???+ info

    the source code is in `PyRevitLoaderApplication.cs` and it is an implementation of the Revit API `IExternalApplication` _interface_ (the standard way to create a plugin for Revit).

There are multiple versions of `pyRevitLoader.dll` to support:

- different Revit versions:
    - One for Revit 2025 and newer, built with .NET 8.
    - Another for Revit 2021-2024, built with the .NET Framework.
- different IronPython versions; to this date:
    - version 2.7.12, the default one
    - version 3.4.2, more recent but not fully tested.

They share the same source code, but are _compiled against_ the different .net runtimes and IronPython versions.

The legacy pure-Python loader (which supported pre-2021 Revit versions) has been removed; the C# loader requires Revit 2021+. That floor is also why `release/pyrevit-hosts.json` carries no pre-2021 record — see [Which Revit versions are listed](adding-revit-version.md#which-revit-versions-are-listed).

!!! note

    Only one IronPython runtime engine can be attached at a time; switching it (Settings UI or `pyrevit attach`) rewrites the `.addin` manifest to the matching `pyRevitLoader.dll` build. CPython selection is separate and doesn't touch the manifest. Manifests can also go stale from clone switches or mixed attachments — `pyrevit attach`/`switch` fixes them by recreating the manifest.

### Session loading

`PyRevitLoaderApplication.OnStartup` calls `SessionManagerService.LoadSession`, which:

- Runs `session_preload.py` to set up environment variables, the logging/script console, update checks, telemetry, and API routes.
- Loads extensions and creates UI elements like ribbons and buttons in C# (see [below](#extensions-discovery)).
- Registers and activates hooks, which enable features like event-driven scripts.
- Runs `session_postload.py` to finalize the session (cleanup, doc colorizer, routes server, output teardown).

A reload re-enters the same `LoadSession` entry, so initial startup and reload share one code path.

???+ info

    `session_preload.py` and `session_postload.py` are small scripts that call
    [pyrevit.loader.sessionmgr.perform_preload][] and
    [pyrevit.loader.sessionmgr.perform_postload][]. They drive the residual Python
    session services that have not yet been ported to C#.

### Extensions discovery

- pyRevit scans known paths and user defined folders to find extensions.
- For each extension, it builds a .net assembly to create buttons, tabs, and other UI elements.

???+ info

    Extensions directories are detected by [pyrevit.userconfig.PyRevitConfig.get_ext_root_dirs][].
    Extension components discovery is performed by [pyrevit.extensions.extensionmgr.get_installed_ui_extensions][].
    Assemblies are generated by [pyrevit.loader.asmmaker][] with types from [pyrevit.runtime.create_type][].

## How pyRevit Commands run

!!! tip "TL;DR:"

    Command execution is handled by the c# project `pyRevitLabs.Pyrevit.Runtime`

Each button generated by the [Extension discovery](#extensions-discovery) is bound to a command derived by the `ScriptCommand.cs` source code.

This code deals with:

- detecting the modifier keys hold while clicking the button, and change the behavior accordingly
- calling `ScriptExcecutor.ExcecuteScript` passing the python script (or any other supportesd script) for the command

???+ info

    The `ScriptCommand` class implements Revit’s `IExternalCommand` interface.
    The `Execute` method is the one called when you click the Ribbon button.

In turn, the code in `ScriptExecutor.cs` calls the appropriate script engine based on the type of (IronPython, CPython, .NET, and so on).

???+ info

    You can find the code of the engines in the files that end with `Engine.cs`, in `dev/pyRevitLabs.PyRevit.Runtime/`:

    - `IronPythonEngine.cs` — default Python engine.
    - `CPythonEngine.cs` — modern Python (3.12).
    - `CLREngine.cs` — C#/VB.NET execution.
    - `DynamoBIMEngine.cs` — Dynamo graphs.
    - `GrasshopperEngine.cs` — Grasshopper definitions.

### Engine cache and Reload

Engines are cached per session in AppDomain data, keyed by engine type id, and a Reload clears that
cache through `ScriptEngineManager.ClearEngines`. `ScriptEngine.Shutdown()` is therefore a
*cache eviction*, not a process teardown: it runs on Reload and on Refresh Engine, and it must
leave anything process-wide alone.

`CPythonEngine` is the one engine whose host is a process-wide singleton. The CPython interpreter
and its pythonnet metatype are started on the first CPython command of the process and stay up
until Revit exits, so a Reload just drops the engine object and the next `#! python3` command
re-attaches to the live interpreter. pythonnet's own `PythonEngine.Shutdown` is deliberately never
called mid-session: it is a soft shutdown that stashes the CLR metatype state into the still-running
interpreter as a `BinaryFormatter` blob, and that blob cannot be read back once Revit's Reload has
duplicated assemblies into its assembly load context. A side effect is that `engine: clean` on a
`python3` bundle yields a fresh engine object but not a fresh interpreter, so `sys.modules` entries
imported before a Reload survive it. The contract is asserted by the tests in
`dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Runtime.CPython.Tests/`.

### Forms across Python engines

`pyrevit.forms` exports one engine-neutral API, listed once in
`forms/_common.py`. IronPython adds the legacy names it exported before the
module split (`forms/_ipy_legacy.py`, listed in `forms/_legacy_exports.py`).
CPython imports any real `pyrevit.forms` submodule on first access and reports
any other public name as unsupported. Shared behavior lives in `forms/base.py`
(window resources, loading and ownership), `forms/_theme.py` (palette,
contrast and title-bar theming), input/list/command dialogs, selectors, prompt
bars, reactive models and `forms/dockable.py` (dockable panels, with the
deferred pane show in `forms/_pane_show.py`). `forms/native.py` contains Revit
task dialogs and native pickers. Engine-specific WPF operations live in
`forms/backends/`, behind the names in `forms/_backend.py`, plus the
CPython-only XAML preparation in `forms/_xaml.py`: for example the
dockable pane provider, which is a Python `IDockablePaneProvider` under
IronPython and a managed provider under CPython, so CPython never creates a
Python-derived Revit interface type. Feature modules never compare native and
Python objects; they read list items through `_backend.items_of` and related
helpers, and `_backend.list_source` returns a managed snapshot to reassign
rather than edit. The CPython controller keeps every callback in one
`_EventRegistry` (`backends/_events.py`), which also runs release hooks such
as the theme unsubscription. A form adapts its own `DataContext`; a child control
can take a model directly or through `forms.set_data_context(control, model)`,
and CPython bindings, including TwoWay ones, see a managed model. Direct routed events such as `Loaded` or
`MouseEnter` cannot be observed inside templates under CPython and fail at load,
except inside a `ContextMenu` or `ToolTip`; elsewhere in templates mouse-button
events are rebuilt from `MouseDown`/`MouseUp`. Reading a
form's `DataContext` returns the Python model, which the form keeps alive. The
controller keeps all backend state in one `_pyrevit_backend` attribute, so
subclasses may use names such as `_events`, `_window` or `_closed`. A native
root property assigned before the XAML loads, as `script.load_ui` windows may
do, is applied after loading unless the XAML root sets it, as with
`LoadComponent`. A controller is accepted wherever .NET expects a type its
native root satisfies (`child.Owner = parent`,
`WindowInteropHelper(window)`, `MessageBox.Show(window, ...)`); `object`
targets such as `Tag` keep the Python object.

IronPython continues to populate its CLR-derived windows with
`wpf.LoadComponent`. CPython owns a native WPF window through a Python controller;
it creates no Python-derived CLR window types, avoiding type registration
collisions on repeated commands. Its loader preserves XML namespace prefixes,
prepends theme/localization dictionaries before parsing, resolves named controls,
and attaches control events after loading. Because handlers attach after
parsing, `Checked` and `SelectionChanged` are replayed once for controls that
load checked or selected, but only where IronPython's attribute-ordered loader
would have delivered them: when the state takes effect after the event
attribute, or the element sets no state attribute. `IsChecked`, `SelectedIndex`,
`SelectedItem`, `SelectedValue` and `IsSelected` take effect at their attribute
position, but a selection also waits for its items: child items and property
elements count as after every attribute, and an `ItemsSource` attribute at its
own position. Other events raised during
parsing, such as `TextChanged`, are not replayed. Event attributes are found
by reflecting the element's type, including `clr-namespace` types from loaded
assemblies; the fixed list in `forms/_xaml.py` is only the fallback for types
that do not resolve. Names inside resource entries are
resolved through their resource dictionary. Template names remain in their own
namescopes; template event sources are tagged with a `Uid` and matched from
root-level routed handlers, or get a direct handler when the tunnelling preview
event first reaches them, so WPF's handled-event order is preserved. Direct
(non-routed) events such as `MouseEnter` are not supported inside templates.
Template elements inside a `ContextMenu` or `ToolTip`, whose events never reach
the window, are marked with the `PythonEvents.Hook` attached property instead;
WPF hands each instance to the backend as it creates it, and the handlers attach
to that instance directly, as IronPython attaches template handlers.
CPython reactive models expose
a managed `BindingModel` for two-way WPF binding while selector results retain
the original Python or Revit object identity.

Plain Python data reaches WPF under CPython the way it does under IronPython.
Importing the CPython backend loads `pyRevitLabs.PyRevit.Forms.Binding` and
registers pythonnet codecs (`forms/backends/_proxies.py`). A Python list, tuple
or other iterable assigned to a non-generic `IEnumerable`, `IList` or
`ICollection`, such as `ItemsSource`, becomes a `PythonListProxy`. That proxy
reads sized sequences live, so `Items.Refresh()` shows edits to the Python list,
and copies other iterables once. A plain class instance or namedtuple assigned to
`object`, such as `DataContext`, `Tag` or a list item, becomes a
`PythonObjectProxy`. Its property descriptors read and write attributes live and
convert values to CLR `bool`, `int`/`long`, `double`, `string`, null or nested
proxies, so triggers, sorting, filters, `DisplayMemberPath` and
`SelectedValuePath` behave as under IronPython. Both the proxy and the
`BindingModel` type each property by its current value, as IronPython 3 does,
so an `int` binds to a `double` target such as `ProgressBar.Maximum`.
`set_data_context` turns a Python list into a live list proxy, so
`{Binding Count}` resolves and WPF can hash the context. A Reactive model assigned to
`object` gets its `BindingModel` adapter, and a Python `int` becomes a CLR
`Int32` (or `Int64` when larger) rather than a pythonnet `PyInt`, so values
stored in that adapter match `SelectedValuePath` and trigger values. Every proxy, and every tracked
adapter, goes back to Python as the original object: `ItemsSource`,
`SelectedItem`, `Items[i]`, event arguments, filter predicates and
`DataContext`. Proxies compare by Python identity, so unhashable objects work,
and they take the GIL on each access.
The codecs are process-wide once registered and claim only those four CLR
targets, plus reference types a form's native root satisfies; Python lists
passed as `object`, dicts and other builtins stay pythonnet objects. The bundled
pythonnet also converts any Python value assigned to a `bool` or `bool?`
property, field or delegate return by truthiness, and does so for a method
argument when no overload accepts it otherwise, so `args.Handled = re.match(...)`
works as under IronPython. A Python class that only implements .NET interfaces,
such as an `IValueConverter`, needs no `__namespace__`: pythonnet generates its
CLR type in a namespace named after its module and reuses it when a re-run
command redefines the class. `pyrevit.framework.wpf` under CPython offers
`LoadComponent` for plain CLR targets such as a new `DataTemplate`, and raises
`PyRevitCPythonNotSupported` for Python-derived windows and controls. The bundled pythonnet clears its conversion caches when a
codec is registered, so the late registration also covers types converted
earlier in the session.

| API | IronPython | CPython |
| --- | --- | --- |
| `alert`, `alert_ifnot` | Supported | Supported |
| `pick_file`, `pick_folder`, `save_file`, Excel picker wrappers | Supported | Supported |
| `GetValueWindow` string/date/slider/dropdown modes and input wrappers | Supported | Supported |
| `WPFWindow`, `TemplateUserInputWindow` | Existing behavior | Modal custom XAML, deferred event handlers and direct CLR event subscriptions; individual tool workflows still require migration review |
| `SelectFromList`, `CommandSwitchWindow`, `SearchPrompt` | Supported | Supported, including filtering, groups, checks and keyboard acceptance |
| `Reactive`, `reactive`, `TemplateListItem` | Supported | Supported through managed binding adapters |
| View/sheet/revision/schedule/template/level/document/parameter selectors | Supported | Supported |
| `settings_window` | Supported | Supported, including dynamically created control callbacks |
| Progress/warning bars | Supported | Supported within a synchronous command scope |
| Persistent modeless windows, dockable panels, `activate_open_window` | Supported | Supported through composed WPF roots and a managed Revit pane provider; requires a live Revit session |
| Color picker, image/family-parameter selectors, notifications | Supported | Implemented; live coverage remains incomplete |
| Other legacy forms exports | Existing behavior | Unsupported unless listed in `_common.__all__` |

Unported CPython APIs continue to raise `PyRevitCPythonNotSupported` with the
feature name. For a name IronPython exported before the split (for example
`CPDialogs` or `Autodesk`), the error is a plain `PyRevitCPythonNotSupported`,
so `from pyrevit.forms import <name>` and code catching it around imports keep
the "not supported under CPython" message; `hasattr` on such a name raises it
too. Any other unknown name, or a submodule whose import fails, raises a
subclass that is also an `AttributeError`, so `hasattr` and `getattr` with a
default treat it as absent and `from pyrevit.forms import <name>` reports
`ImportError`. `GetValueWindow` rejects an unknown `value_type` with
`PyRevitException` on both engines before creating any control. Standard form
signatures and engine selection are unchanged.
WebView forms and changing the default Python engine are separate workstreams
under [the CPython migration RFC](https://github.com/pyrevitlabs/pyRevit/issues/3567).

CPython forms must be created on the Revit STA UI thread. Modal callbacks execute
within the dialog lifetime; they do not establish an independent Revit API
context. Accept publishes the response before closing; Escape or window close
returns `None`. Close and failed initialization release event callbacks and
theme subscriptions. A callback exception surfaces as under IronPython whenever
Python code is below the event: it leaves `RaiseEvent`, or `ShowDialog` (which
WPF leaves open), and the window stays open. Input that reaches a callback with
no Python code below it, such as a click on a modeless window or a dockable
page after its command finished, logs the exception instead of letting it reach
the WPF Dispatcher, where it could terminate Revit.

Run `dotnet test dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Forms.Tests/pyRevitLabs.PyRevit.Forms.Tests.csproj -c Release`
for real WPF/pythonnet tests on .NET Framework 4.8, .NET 8 and .NET 10 using the
shipped CPython interpreter. The fixture substitutes Revit dependencies; it does
not validate Revit ownership or host events. The proxies have their own real-WPF
tests in `dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Forms.Binding.Tests`. Portable tests run with
`python -m unittest discover -s dev/scripts -p 'test_standalone_forms*.py'`.
The sibling `pyRevitLabs.PyRevit.Forms.IronPython.Tests` project drives the same
interactive cases with the shipped IronPython 2.7 and 3 engines (select with
`-p:IronPythonVersion=IPY2712PR` or `IPY342`). The build pipeline does not run
these two projects; run them manually before changing `pyrevit.forms`. Inside
Revit, run `pyrevit.unittests.forms_acceptance.run(doc)`
through pyRevit MCP with each engine and `dry_run=true`. The runner creates real
selector fixtures and always rolls its transaction group back. On Revit 2026.5,
23 cases passed without skips under CPython 3.12.3 (run `c94af430887c`); 21
shared cases passed under IronPython 3.4.2 (run `2530e1bffe3b`) with two
CPython-composition probes skipped. This covers actual modal control events,
two-way binding, selection identity, settings and scoped overlays. Native picker,
persistent dockable-panel behavior and other Revit generations are not covered
by those results. The DevTools **Debug → Forms Tests** pulldown runs this
suite under each engine (**Test IronPython Forms**, **Test CPython Forms**) and
opens the forms by hand (**Test IronPython Forms Manual**, **Test CPython Forms
Manual**) for picker, ownership and theme inspection.

Run `python dev/scripts/forms_usage.py` to inventory bundled-tool references,
excluding DevTools. The current inventory has no syntax skips. The most-used
dialogs are `alert` (102 files), `SelectFromList` (42) and `CommandSwitchWindow`
(37); the shared list and command dialogs are exercised under both engines.
Counts describe API references, not proof that every calling tool runs under
CPython. The 26 files using custom `WPFWindow` subclasses now use the composed
modal or modeless controller, but still need individual workflow review. The
inventory also audits every bundled custom
XAML handler declaration against the CPython deferred-event registry (330
bindings at this revision); it does not execute each tool workflow. The
published CPython surface now covers all 397 bundled references, including
dockable-panel registration and control APIs. That count is an API-coverage
guardrail, not evidence that all tool workflows are compatible: native CLR
subclass assumptions, persistent pane lifetimes and callbacks requiring a Revit
API context require live Revit validation.
