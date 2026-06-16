# Extension Layout YAML Guide

Extension layout YAML files decouple a pyRevit extension's **UI structure** (tabs, panels, button arrangement) from its **physical folder structure**. Instead of encoding the ribbon layout in directory names and nesting, you declare it in one or two small YAML files.

## How It Works

When an extension contains an `extension_layout.yaml` file at its root, pyRevit uses **layout mode** instead of the legacy directory-walking approach:

1. **Tool Discovery** - pyRevit scans the `tools/` directory (and the legacy folder structure, if present) for all recognized tool bundles (`.pushbutton`, `.pulldown`, `.splitbutton`, `.smartbutton`, `.panelbutton`). Each tool is indexed by its folder name (without the postfix).

2. **Layout Declaration** - `extension_layout.yaml` declares the tab/panel structure and references tools by name. The parser arranges discovered tools into the declared UI structure.

3. **Result** - You can reorganize the ribbon by editing YAML files alone. No folder renaming or moving required.

## File Structure

```
MyExtension.extension/
    extension_layout.yaml       # Required: declares tabs and panels
    MyPanel.panel.yaml          # Optional: external panel layout (for complex panels)
    tools/                      # Tool bundles live here
        MyButton.pushbutton/
            script.py
            icon.png
            bundle.yaml
        MyPulldown.pulldown/
            ButtonA.pushbutton/
                script.py
            ButtonB.pushbutton/
                script.py
```

Tools can also remain in the legacy `.tab/.panel/` folder structure. The tool index scans both locations, so the layout YAML works as a pure arrangement overlay regardless of where tools physically reside.

## extension_layout.yaml

This is the main file that declares tabs and their panels:

```yaml
tabs:
  - name: "My Tab"
    panels:
      - name: "My Panel"
        layout:
          - "ToolName"
          - "AnotherTool"
      - name: "Complex Panel"
        layout_file: "ComplexPanel.panel.yaml"
```

### Tab Properties

| Key | Required | Description |
|-----|----------|-------------|
| `name` | Yes | Tab name. Also the ribbon-tab display text and the key extensions merge on |
| `title` | No | Reserved for parity with panels; the ribbon tab currently displays `name` |
| `highlight` | No | `new` or `updated` — shows a highlight badge on the tab |
| `panels` | Yes | List of panel definitions |

### Panel Properties

| Key | Required | Description |
|-----|----------|-------------|
| `name` | Yes | Panel name (identity within the tab) |
| `title` | No | Display title shown below the panel; defaults to `name`. May be a locale map (see below) |
| `layout` | Either this or `layout_file` | Inline list of layout items |
| `layout_file` | Either this or `layout` | Path to an external `.panel.yaml` file |
| `highlight` | No | `new` or `updated` — shows a highlight badge on the panel |
| `collapsed` | No | `true` to start the panel collapsed |
| `is_beta` | No | `true` to hide the panel unless beta tools are enabled |
| `background` | No | Panel background color(s) — string or `{panel, title, slideout}` map |

The parser looks up keys by name, so key ordering does not affect behavior. The auto-generator outputs `name`/`title` first, then presentation keys, then `layout`.

### Panel Appearance

```yaml
panels:
  - name: "Modeling"
    highlight: new            # "new" or "updated" badge
    collapsed: true           # start collapsed
    background: "#2D2D30"     # single color for the whole panel
    layout:
      - "Create Wall"
  - name: "Review"
    background:               # or target parts individually
      panel: "#1E1E1E"
      title: "#007ACC"
      slideout: "#252526"
    layout:
      - "Audit"
```

### Localized Titles (i18n)

A panel `title` may be a locale map instead of a string. The Layout Builder displays the resolved label for the active locale and preserves the full map on save:

```yaml
panels:
  - name: "Selection"
    title:
      en_us: "Selection"
      chinese_s: "选择"
    layout:
      - "Pick"
```

## Panel Layout Items

The `layout` list supports these item types:

### Tool Reference (string)

References a tool by its folder name (without the `.pushbutton`/`.pulldown`/etc. postfix):

```yaml
layout:
  - "MyButton"          # References tools/MyButton.pushbutton/
  - "MyPulldown"        # References tools/MyPulldown.pulldown/
```

Tool names can be quoted or unquoted in YAML — the parser accepts both.

### Stack (mapping)

Groups 2-3 buttons vertically in a compact stack:

```yaml
layout:
  - stack:
      - "SmallButton1"
      - "SmallButton2"
      - "SmallButton3"
```

Stacks display buttons at 16x16 icon size, stacked vertically. Maximum 3 items per stack.

### Separator (string `---`)

Adds a vertical separator line between groups:

```yaml
layout:
  - ToolA
  - "---"
  - ToolB
```

### Slideout (string `>>>`)

Everything after `>>>` goes into a slideout panel (expandable drawer below the panel):

```yaml
layout:
  - MainTool
  - ">>>"
  - HiddenTool1
  - HiddenTool2
```

## External Panel Files (*.panel.yaml)

For panels with many items, use an external file to keep `extension_layout.yaml` clean:

```yaml
# In extension_layout.yaml:
panels:
  - name: "Selection"
    layout_file: "Selection.panel.yaml"
```

```yaml
# Selection.panel.yaml:
title: "Selection"
layout:
  - "Pick"
  - "Set Workset"
  - stack:
      - "Isolate"
      - "Filter"
      - "Select"
  - "---"
  - stack:
      - "MAppend"
      - "MWrite"
      - "MRead"
```

The panel `name` comes from the entry in `extension_layout.yaml`; the external file carries the `title`, the `layout`, and any presentation keys (`highlight`, `collapsed`, `background`, `is_beta`). A `title` set on the outer entry takes precedence over the file's. The auto-generator outputs `title` before `layout`.

## Tool Naming

Tools are referenced by their **folder name without the postfix**:

| Folder Name | Reference in YAML |
|-------------|-------------------|
| `Color Splasher.pushbutton` | `"Color Splasher"` |
| `MyTool.pulldown` | `"MyTool"` or `MyTool` |
| `Sync Views.smartbutton` | `"Sync Views"` |

Names are case-insensitive during lookup but should match the folder name for clarity. Names are valid YAML strings either way — the auto-generator emits values unquoted where YAML allows it and quotes only when needed (e.g. `'---'`, `'>>>'`).

## Custom User Layouts

Custom layouts override the bundled `extension_layout.yaml` but reference the same tools. This lets users rearrange the ribbon without modifying extension source files. Custom layouts are stored in `%APPDATA%\pyRevit\Layouts\{ExtensionName}\` and resolved per extension via a `custom_layout_path` entry in the user INI.

There are two ways to author one:

### Layout Builder (visual editor)

Launch **Layout Builder** from the `pyRevit` tab. The window has two panes:

- **Left** - searchable list of all tools discoverable in the extension, with a "Show All / Hide Placed" toggle.
- **Right** - the current tab/panel/stack/tool tree, with buttons to add Tab/Panel/Stack/Separator/Slideout, move items up/down, remove items, and insert the selected tool at the selected location.

Saving writes the result to the custom-layout cache for the chosen extension and reloads pyRevit. The bundled extension source is never modified.

If the extension ships layout presets (see below), a **Load Preset** button is shown.

### Settings dialog (file-based import/export)

Under **Settings > Extension Layout** the dialog lists every extension that contains an `extension_layout.yaml`, with a `Custom` / `Default` status column and per-row buttons:

- **Import** - Copies layout YAML files (`extension_layout.yaml` plus any `*.panel.yaml` siblings) from a folder you pick into `%APPDATA%\pyRevit\Layouts\{ExtensionName}\` and points pyRevit at them.
- **Export** - Copies the currently active layout files to a folder you pick, ready for editing in any text editor.
- **Reset** - Clears the custom layout for that extension and reverts to the bundled default.

A global **Disable all custom layouts** checkbox temporarily ignores every user custom layout without deleting them — useful for support diagnostics.

## Developer-Shipped Layout Presets

Extension authors can bundle alternative layouts as **presets** under `<extension>/layouts/`:

```
MyExtension.extension/
    extension_layout.yaml           # default layout
    layouts/
        Minimal.layout.yaml         # preset: "Minimal"
        Detailer.layout.yaml        # preset: "Detailer"
    tools/
        ...
```

Each `*.layout.yaml` file uses the same schema as `extension_layout.yaml`. The preset name is the filename with `.layout.yaml` stripped. Presets are surfaced to users through the Layout Builder's **Load Preset** button. Loading a preset replaces the current draft in the builder; nothing is written until the user saves.

Use presets to ship alternative workflows (e.g. "Author", "Reviewer", "Detailer") without forcing one layout on every user.

## Complete Example

```yaml
# extension_layout.yaml
tabs:
  - name: "BIM Tools"
    panels:
      - name: "Modeling"
        layout:
          - "Create Wall"
          - "Create Floor"
          - "---"
          - stack:
              - "Quick Door"
              - "Quick Window"
              - "Quick Column"
      - name: "Annotation"
        layout_file: "Annotation.panel.yaml"
      - name: "Export"
        layout:
          - "IFC Export"
          - ">>>"
          - "Export Settings"
          - "Batch Export"
```

This matches the format produced by the auto-generator. See the bundled
`extension_layout.yaml` in this template extension for a live example.

## Comparison with Legacy Mode

| Aspect | Legacy (folder-based) | Layout (YAML-based) |
|--------|----------------------|---------------------|
| UI structure | Encoded in `.tab/.panel/.stack/` folders | Declared in YAML |
| Rearranging tools | Rename/move folders | Edit YAML |
| Adding a tool | Create folder in correct panel | Create bundle in `tools/`, add name to YAML |
| Separators | Defined in `bundle.yaml` layout key | Inline `"---"` in YAML |
| Slideouts | Defined in `bundle.yaml` layout key | Inline `">>>"` in YAML |
| Unique IDs | Full path-based (`ext_tab_panel_tool`) | Flat (`extensionname_toolname`) |

## Notes

- If `extension_layout.yaml` is missing, the extension falls back to legacy folder-based parsing automatically.
- Tools not referenced in any layout YAML will not appear in the ribbon, but they are still compiled into the extension assembly. This means editing the layout (via Layout Builder or by hand) to surface a previously-hidden tool does not require an assembly rebuild on the next reload.
- Duplicate tool names across `tools/` and legacy folders: the `tools/` version takes priority.
- A tool referenced from more than one location is placed once (at its first reference); the duplicate is logged and skipped, since a tool maps to a single command.
- Panel appearance from `bundle.yaml` (`highlight`, `collapsed`, `background`, `is_beta`) and localized `title`s are carried over by the auto-generator when migrating a legacy extension, so the ribbon looks the same after conversion.
- After changing layout files, a pyRevit reload is required to see changes.
