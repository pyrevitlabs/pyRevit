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

- `script.py` / `script.cs` / `script.vb` / `script.rb` / `script.dyn` / `script.gh` / `script.ghx` — the command's entry point; the file extension picks the [script engine](#script-engines).
- `config.py` (or the matching extension for the script's language) — runs instead of `script.py` on a shift-click; falls back to `script.py` itself if absent.
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
- `context` — restricts when the button is enabled (active view, selected category, workset, etc.); see the context grammar in `pyrevit.extensions.genericcomps._parse_context_directives`.
- `min_revit_version` / `max_revit_version`.
- `is_beta`, `highlight` (`new` or `updated`), `collapsed`.
- `engine` — `clean`, `full_frame`, `persistent`, `mainthread` (plus Dynamo-specific `automate`, `dynamo_path`, `dynamo_path_check_existing`, `dynamo_force_manual_run`, `dynamo_model_nodes_info`).
- `layout` — reorders/nests child buttons instead of relying on folder order; use `---` for a separator and `>>>` to start a slideout.

Bundle-type-specific keys: `modules` (link buttons), `assembly` / `command_class` / `availability_class` (invoke/link buttons), `hyperlink` (URL buttons).

???+ info

    The full key list lives in the `MDATA_*` constants in `pyrevitlib/pyrevit/extensions/__init__.py`, and is consumed by `_read_bundle_metadata()` in `pyrevitlib/pyrevit/extensions/genericcomps.py`. `extensions/pyRevitBundlesCreatorExtension.extension` has a worked `bundle.yaml` example per bundle type, and its own UI scaffolds new bundles interactively.

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

There is no exhaustive published list of event names — `extensions/pyRevitDevHooks.extension/hooks/` has one example script per supported event and is the most complete reference. Hook registration is handled by `pyrevitlib/pyrevit/loader/hooks.py`.
