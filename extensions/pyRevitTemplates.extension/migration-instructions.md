# Migrating from Legacy Folder Structure to Layout YAML

This guide walks through converting an existing pyRevit extension from the legacy folder-based UI structure to the new layout YAML system.

## Prerequisites

- pyRevit with layout support enabled (new loader)
- An existing extension using the legacy `.tab/.panel/` folder structure

## Overview

Migration is a two-step process:
1. Generate the layout YAML from your existing extension (automated)
2. Optionally reorganize tool bundles into `tools/` (manual, not required but encouraged)

The layout system scans both `tools/` and legacy folders for tool bundles, so you can migrate incrementally or leave tools in place.

## Step 1: Generate Layout YAML (Automated)

pyRevit includes a developer tool that generates layout YAML files by parsing your existing folder structure:

### Using the Dev Pushbutton (in Revit)

1. Enable the **pyRevitDevTools** extension in Settings > Extensions
2. Reload pyRevit
3. Run the **Generate Layout** button from the Dev Tools tab
4. Select your extension directory
5. The tool generates `extension_layout.yaml` and any needed `*.panel.yaml` files

### Using Python (programmatically)

```python
from pyrevit.extensions.layout_cli import generate_layout

# Generate layout files in the extension directory
files = generate_layout(r'C:\path\to\MyExtension.extension')
print('Generated:', files)
```

The generator:
- Reads the existing `.tab/.panel/.stack/` structure
- Respects ordering from `bundle.yaml` layout keys
- Creates external `*.panel.yaml` files for panels with more than 3 items
- Preserves separators (`---`) and slideouts (`>>>`)
- Handles stacks and their children

## Step 2: Verify the Generated Layout

Open the generated `extension_layout.yaml` and check that:
- Tab names match what you expect
- Panel ordering is correct
- All tools are referenced

Compare with your ribbon in Revit. If something looks wrong, edit the YAML directly.

## Step 3 (Optional): Move Tools to `tools/`

You can move tool bundles from the legacy structure into a flat `tools/` directory. This is optional since the tool index scans both locations.

**Before:**
```
MyExtension.extension/
    MyTab.tab/
        MyPanel.panel/
            ButtonA.pushbutton/
            ButtonB.pushbutton/
            mystack.stack/
                SmallA.pushbutton/
                SmallB.pushbutton/
```

**After:**
```
MyExtension.extension/
    extension_layout.yaml
    tools/
        ButtonA.pushbutton/
        ButtonB.pushbutton/
        SmallA.pushbutton/
        SmallB.pushbutton/
```

Benefits of moving to `tools/`:
- Flat structure is easier to browse
- Tool names are immediately visible
- No need to navigate deep nesting
- Organizational subfolders within `tools/` are allowed (they're recursed into)

If you move tools, you can delete the empty `.tab/.panel/.stack/` folders and any `bundle.yaml` files that only contained layout keys.

## Step 4: Clean Up (Optional)

After confirming the layout YAML works correctly:

1. **Remove `bundle.yaml` layout keys** from panels/tabs (no longer needed)
2. **Delete empty structural folders** (`.tab`, `.panel`, `.stack` directories that no longer contain tools)
3. **Keep `bundle.yaml` in tool bundles** - these still define tool-level settings (title, tooltip, author, min_revit_ver, etc.)

## Incremental Migration

You don't have to move all tools at once. The system supports a hybrid state:

```
MyExtension.extension/
    extension_layout.yaml           # Declares the UI structure
    tools/                          # New tools go here
        NewFeature.pushbutton/
    OldTab.tab/                     # Legacy tools still found here
        OldPanel.panel/
            OldButton.pushbutton/   # Still indexed and usable in layout YAML
```

The layout YAML references tools by name regardless of location. Both `NewFeature` and `OldButton` work in the layout.

## Example Migration

### Original Legacy Structure

```
BIMTools.extension/
    BIM.tab/
        bundle.yaml                 # layout: [Modeling, Export]
        Modeling.panel/
            bundle.yaml             # layout: [Create Wall, Create Floor, ---]
            Create Wall.pushbutton/
                script.py
                icon.png
            Create Floor.pushbutton/
                script.py
                icon.png
        Export.panel/
            IFC Export.pushbutton/
                script.py
                icon.png
```

### Generated Layout

```yaml
# extension_layout.yaml
tabs:
  - name: "BIM"
    panels:
      - name: "Modeling"
        layout:
          - "Create Wall"
          - "Create Floor"
          - "---"
      - name: "Export"
        layout:
          - "IFC Export"
```

### After Moving Tools to `tools/`

```
BIMTools.extension/
    extension_layout.yaml
    tools/
        Create Wall.pushbutton/
            script.py
            icon.png
        Create Floor.pushbutton/
            script.py
            icon.png
        IFC Export.pushbutton/
            script.py
            icon.png
```

## Important Notes

- **Reload required** - After adding/modifying layout files, reload pyRevit to see changes.
- **Tool names must be unique** - Within an extension, every tool bundle folder name (without postfix) must be unique. Duplicates are logged as warnings and the first-found wins.
- **Unique IDs change** - Layout mode generates unique IDs as `extensionname_toolname` (flat), vs the legacy path-based format. This means compiled command caches from the previous format are invalid. Delete `%APPDATA%\pyRevit\{RevitVersion}\*.dll` and `*.cs` files if you encounter "Wrong Full Class Name" errors after migrating.
- **Case insensitive** - Tool name lookups are case-insensitive, but keep the YAML reference matching the folder name for clarity.
- **`bundle.yaml` still matters for tools** - Each tool bundle can still have a `bundle.yaml` for title, tooltip, icon settings, supported Revit versions, etc. Only the *structural* layout information (panel ordering, stacks) moves to the YAML.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tool not appearing in ribbon | Check spelling in YAML matches folder name (without postfix) |
| "Tool not found" warning in logs | Verify the tool bundle exists in `tools/` or legacy structure |
| "Wrong Full Class Name" error | Delete compiled DLLs in `%APPDATA%\pyRevit\{Year}\` |
| Panel order wrong | Check `extension_layout.yaml` panel ordering |
| Stacks not rendering correctly | Ensure stack has 2-3 items max |
| Changes not visible | Reload pyRevit (Settings > Reload) |
