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
          - ToolName
          - AnotherTool
      - name: "Complex Panel"
        layout_file: "ComplexPanel.panel.yaml"
```

### Tab Properties

| Key | Required | Description |
|-----|----------|-------------|
| `name` | Yes | Tab name (also used as the display title) |
| `panels` | Yes | List of panel definitions |

### Panel Properties

| Key | Required | Description |
|-----|----------|-------------|
| `name` | Yes | Panel name (display title shown below the panel) |
| `layout` | Either this or `layout_file` | Inline list of layout items |
| `layout_file` | Either this or `layout` | Path to an external `.panel.yaml` file |

## Panel Layout Items

The `layout` list supports these item types:

### Tool Reference (string)

References a tool by its folder name (without the `.pushbutton`/`.pulldown`/etc. postfix):

```yaml
layout:
  - MyButton          # References tools/MyButton.pushbutton/
  - MyPulldown        # References tools/MyPulldown.pulldown/
```

### Stack (mapping)

Groups 2-3 buttons vertically in a compact stack:

```yaml
layout:
  - stack:
      - SmallButton1
      - SmallButton2
      - SmallButton3
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
  - Pick
  - "Set Workset"
  - stack:
      - Isolate
      - Filter
      - Select
  - "---"
  - stack:
      - MAppend
      - MWrite
      - MRead
```

## Tool Naming

Tools are referenced by their **folder name without the postfix**:

| Folder Name | Reference in YAML |
|-------------|-------------------|
| `Color Splasher.pushbutton` | `Color Splasher` |
| `MyTool.pulldown` | `MyTool` |
| `Sync Views.smartbutton` | `Sync Views` |

Names are case-insensitive during lookup but should match the folder name for clarity.

## Custom User Layouts

Users can import custom layouts via **Settings > Extension Layout**:

- **Import** - Copies layout YAML files to `%APPDATA%\pyRevit\Layouts\{ExtensionName}\` and configures pyRevit to use them instead of the bundled layout.
- **Export** - Copies the currently active layout files to a folder for editing.
- **Reset** - Clears the custom layout and reverts to the bundled default.
- **Disable All Custom Layouts** - A global toggle that temporarily ignores all user custom layouts without deleting them.

Custom layouts override the bundled `extension_layout.yaml` but reference the same tools. This lets users rearrange the ribbon without modifying extension source files.

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
- Tools not referenced in any layout YAML will not appear in the ribbon (they are discovered but not placed).
- Duplicate tool names across `tools/` and legacy folders: the `tools/` version takes priority.
- After changing layout files, a pyRevit reload is required to see changes.
